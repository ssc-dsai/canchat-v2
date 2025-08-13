import json
import hashlib
import logging
from typing import Optional, Dict, Any
import redis
from open_webui.env import REDIS_URL, LLM_CACHE_TTL

log = logging.getLogger(__name__)

class LLMResponseCache:
    """Simple Redis-based cache for LLM responses"""
    
    def __init__(self):
        self.redis_client = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.connected = True
            log.info(f"✅ Redis cache connected to {REDIS_URL}")
        except Exception as e:
            log.error(f"❌ Failed to connect to Redis: {e}")
            self.connected = False
            self.redis_client = None
    
    def _normalize_text_content(self, text: str) -> str:
        """
        Language-agnostic text normalization for semantic caching.
        Handles both English and French content without language-specific rules.
        """
        if not text:
            return ""
        
        import re
        import unicodedata
        
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Normalize Unicode characters (handles accented characters consistently)
        # This ensures "café" and "cafe" are treated the same way
        normalized = unicodedata.normalize('NFD', normalized)
        
        # Remove extra whitespace and normalize spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove trailing punctuation (language-agnostic)
        # Remove question marks, exclamation marks, periods, etc. at the end
        normalized = re.sub(r'[?!.,;:]+\s*$', '', normalized)
        
        # Remove leading/trailing quotes and brackets (common in both languages)
        normalized = re.sub(r'^["\'\[\(]+|["\'\]\)]+$', '', normalized)
        
        # Normalize common punctuation patterns
        # Multiple punctuation marks become single
        normalized = re.sub(r'[?!]{2,}', '?', normalized)
        normalized = re.sub(r'[.]{2,}', '.', normalized)
        
        # Clean up any double spaces created by normalization
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def _normalize_messages(self, messages: list) -> list:
        """Normalize messages by keeping only the last user message for caching"""
        if not messages:
            return []
        
        # Find the last user message for caching purposes
        last_user_message = None
        for message in reversed(messages):
            if message.get('role') == 'user':
                last_user_message = message
                break
        
        if not last_user_message:
            return []
        
        # Get original content and normalize it for semantic caching
        original_content = last_user_message.get("content", "")
        normalized_content = self._normalize_text_content(original_content)
            
        # Only cache based on the last user message to avoid conversation history affecting cache keys
        normalized_msg = {
            "role": last_user_message.get("role"),
            "content": normalized_content
        }
        # Remove None values
        normalized_msg = {k: v for k, v in normalized_msg.items() if v is not None}
        return [normalized_msg]
    
    def _get_available_classification_model(self) -> Optional[str]:
        """
        Dynamically find the best available model for classification.
        Works with any LiteLLM deployment or local models.
        """
        try:
            import requests
            
            # Try to get available models from the OpenWebUI models endpoint
            # This will include all configured models (LiteLLM, Ollama, OpenAI, etc.)
            try:
                response = requests.get("http://localhost:8080/api/models", timeout=2)
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = []
                    
                    # Extract model IDs from the response
                    if isinstance(models_data, dict) and 'data' in models_data:
                        available_models = [model.get('id', '') for model in models_data['data']]
                    elif isinstance(models_data, list):
                        available_models = [model.get('id', '') for model in models_data]
                    
                    if available_models:
                        # Sort by model name length (shorter names often indicate smaller/faster models)
                        # This is a heuristic that often works for model naming conventions
                        sorted_models = sorted(available_models, key=lambda x: (len(x), x))
                        
                        # Log available models for debugging
                        log.debug(f"Available models for classification: {sorted_models[:5]}...")
                        
                        # Return the first (likely smallest/fastest) available model
                        return sorted_models[0]
                        
            except Exception as e:
                log.debug(f"Could not get models from OpenWebUI API: {e}")
                
            # Fallback: Try Ollama for local testing
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    available_model_names = [m.get('name', '') for m in models]
                    
                    if available_model_names:
                        # For local Ollama, sort by name length as a heuristic for size
                        sorted_models = sorted(available_model_names, key=lambda x: (len(x), x))
                        log.debug(f"Using Ollama model for classification: {sorted_models[0]}")
                        return sorted_models[0]
                        
            except Exception as e:
                log.debug(f"Could not get Ollama models: {e}")
                
        except Exception as e:
            log.debug(f"Error getting classification model: {e}")
            
        return None

    def _is_time_dependent_content(self, content: str) -> bool:
        """
        Use AI to dynamically determine if content is time-dependent.
        This is more robust than static keyword matching.
        """
        # Quick static checks for obvious cases (performance optimization)
        obvious_time_words = ['today', 'now', 'current', 'latest', "aujourd'hui", 'maintenant']
        if any(word in content.lower() for word in obvious_time_words):
            return True
        
        # Get available classification model
        classification_model = self._get_available_classification_model()
        if not classification_model:
            # No AI model available, use enhanced pattern matching
            return self._fallback_time_detection(content)
            
        # For more complex cases, use a lightweight classification prompt
        classification_prompt = f"""
Analyze this user question and determine if the answer would change over time.

Question: "{content}"

Consider:
- Does it ask about current/recent events, news, weather, stock prices?
- Does it reference time-sensitive data that changes frequently?
- Does it ask about "what's happening" or real-time information?
- Would the answer be different if asked today vs. next month?

Respond with exactly one word: "TIME_DEPENDENT" or "TIME_INDEPENDENT"
"""
        
        try:
            import requests
            
            # Use OpenWebUI's chat completions endpoint (works with any configured model)
            try:
                response = requests.post(
                    "http://localhost:8080/api/chat/completions",
                    json={
                        "model": classification_model,
                        "messages": [{"role": "user", "content": classification_prompt}],
                        "temperature": 0.1,
                        "max_tokens": 5,
                        "stream": False
                    },
                    timeout=5  # Slightly longer timeout for external APIs
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    
                    # Handle different response formats
                    if 'choices' in result_data and result_data['choices']:
                        result = result_data['choices'][0]['message']['content'].strip().upper()
                    elif 'response' in result_data:
                        result = result_data['response'].strip().upper()
                    else:
                        result = str(result_data).upper()
                    
                    return 'TIME_DEPENDENT' in result
                    
            except Exception as e:
                log.warning(f"OpenWebUI classification failed: {e}")
                
            # Fallback: Direct Ollama call for local testing
            if classification_model and ':' in classification_model:  # Likely an Ollama model
                try:
                    response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": classification_model,
                            "prompt": classification_prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.1,
                                "num_predict": 5
                            }
                        },
                        timeout=3
                    )
                    
                    if response.status_code == 200:
                        result = response.json().get('response', '').strip().upper()
                        return 'TIME_DEPENDENT' in result
                        
                except Exception as e:
                    log.warning(f"Ollama classification failed: {e}")
                
        except Exception as e:
            log.warning(f"Time dependency classification error: {e}")
        
        # Fallback to enhanced pattern matching if AI fails
        return self._fallback_time_detection(content)
    
    def _fallback_time_detection(self, content: str) -> bool:
        """
        Enhanced pattern-based fallback for time dependency detection.
        Uses linguistic patterns rather than just keywords.
        """
        content_lower = content.lower()
        
        # Pattern-based detection (more robust than keywords)
        time_patterns = [
            # Question patterns that often indicate time dependency
            r'\b(what\'s|what is) (happening|going on|new)\b',
            r'\b(latest|recent|current|today\'s|this week\'s)\b',
            r'\b(right now|at the moment|currently)\b',
            r'\b(stock price|market|weather|news|breaking)\b',
            
            # French patterns
            r'\b(qu\'est-ce qui se passe|que se passe-t-il)\b',
            r'\b(dernières|récentes|actuelles|d\'aujourd\'hui)\b',
            r'\b(en ce moment|actuellement|maintenant)\b',
            r'\b(prix des actions|marché|météo|nouvelles)\b',
        ]
        
        import re
        return any(re.search(pattern, content_lower) for pattern in time_patterns)

    def _is_cacheable_request(self, messages: list, form_data: dict = None) -> bool:
        """
        Determine if a request is cacheable based on idempotency requirements.
        Only cache requests that are truly idempotent and time-independent.
        """
        if not self._is_user_question(messages):
            return False
            
        # Get the last user message
        last_user_message = None
        for message in reversed(messages):
            if message.get('role') == 'user':
                last_user_message = message
                break
                
        if not last_user_message:
            return False
            
        content = last_user_message.get('content', '')
        
        # Use AI-powered time dependency detection
        if self._is_time_dependent_content(content):
            return False
            
        # Check for form data that indicates non-idempotent requests
        if form_data:
            # Check if RAG/search is enabled in the request
            if form_data.get('web_search', False):
                return False
                
            # Check if MCP tools are being used
            if form_data.get('tools') or form_data.get('tool_ids'):
                return False
                
            # Check for system prompts with time references
            system_content = form_data.get('system', '').lower()
            if any(indicator in system_content for indicator in ['current date', 'today is', 'the time is']):
                return False
        
        return True

    def _is_user_question(self, messages: list) -> bool:
        """
        Check if this is a direct user question (not a system-generated request like title/tags).
        Only cache direct user questions to avoid cache misses from LLM response variations.
        """
        if not messages:
            return False
        
        # Check the last user message in the conversation
        last_user_message = None
        for message in reversed(messages):
            if message.get('role') == 'user':
                last_user_message = message
                break
        
        if not last_user_message:
            return False
            
        content = last_user_message.get('content', '').lower()
        
        # Check for system-generated prompts that we should NOT cache
        system_indicators = [
            'create a concise',
            'generate 1-3 broad tags',
            'categorizing the main themes',
            '<chat_history>',
            'respond only with the title text',
            'json format:',
            '### task:',
            'examples of titles:',
            '### guidelines:',
            '### output:'
        ]
        
        is_user_question = not any(indicator in content for indicator in system_indicators)
        
        # For caching purposes, we want to cache based on the specific user question
        # So we need to create a cache key based on just the user question, not the full conversation
        return is_user_question
    
    def _normalize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters by keeping only cache-relevant fields"""
        # Only include parameters that actually affect the model response
        relevant_params = {
            "temperature": parameters.get("temperature"),
            "max_tokens": parameters.get("max_tokens"),
            "top_p": parameters.get("top_p"),
            "top_k": parameters.get("top_k"),
            "repeat_penalty": parameters.get("repeat_penalty"),
            "seed": parameters.get("seed"),
            "stop": parameters.get("stop"),
        }
        # Remove None values
        return {k: v for k, v in relevant_params.items() if v is not None}
    
    def _generate_cache_key(self, model: str, messages: list, parameters: Dict[str, Any]) -> str:
        """Generate a cache key from model, messages, and parameters"""
        # Normalize inputs to ensure consistent cache keys
        normalized_messages = self._normalize_messages(messages)
        normalized_parameters = self._normalize_parameters(parameters)
        
        # Create a simple string representation for hashing
        key_data = {
            "model": model,
            "messages": normalized_messages,
            "parameters": normalized_parameters
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get_cached_response(self, model: str, messages: list, parameters: Dict[str, Any], form_data: dict = None) -> Optional[str]:
        """Get cached response if available - OPTIMIZED for instant cache hits"""
        if not self.connected:
            log.warning("❌ Redis not connected, cache disabled")
            return None
        
        print(f"DEBUG: CACHE CHECK - Evaluating request with {len(messages)} messages")
        if messages:
            print(f"DEBUG: CACHE CHECK - First message content preview: {messages[0].get('content', '')[:100]}...")
        
        # PERFORMANCE OPTIMIZATION: Check cache first before expensive cacheable validation
        # Generate cache key immediately for fast lookup
        try:
            cache_key = self._generate_cache_key(model, messages, parameters)
            print(f"DEBUG: Cache LOOKUP key: {cache_key}")
            
            # Test Redis connectivity
            try:
                self.redis_client.ping()
                print(f"DEBUG: Redis PING successful")
            except Exception as e:
                print(f"DEBUG: Redis PING failed: {e}")
                return None
            
            # INSTANT CACHE CHECK - no expensive AI classification needed for existing keys
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                log.info(f"🎯 INSTANT Cache HIT for model: {model} - returning cached response")
                print(f"DEBUG: INSTANT Cache HIT! Found data: {cached_data[:50]}...")
                return cached_data
            
            # Cache miss - now we need to check if this request is cacheable
            print(f"DEBUG: Cache MISS - checking if request is cacheable for future storage")
            if not self._is_cacheable_request(messages, form_data):
                print(f"DEBUG: CACHE SKIP - Request not cacheable (time-dependent or non-idempotent)")
                log.info("🚫 Skipping cache for non-cacheable request")
                return None
            
            log.info(f"❌ Cache MISS for model: {model} - will cache new response")
            print(f"DEBUG: Cache MISS! Key not found in Redis but request is cacheable")
            return None
                
        except Exception as e:
            log.error(f"❌ Error getting cached response: {e}")
            return None
    
    def cache_response(self, model: str, messages: list, parameters: Dict[str, Any], response: str, ttl: int = None, form_data: dict = None) -> bool:
        """Cache a response"""
        if not self.connected:
            log.warning("❌ Redis not connected, cannot cache response")
            return False
        
        print(f"DEBUG: CACHE STORAGE CHECK - Evaluating request with {len(messages)} messages")
        if messages:
            print(f"DEBUG: CACHE STORAGE CHECK - First message content preview: {messages[0].get('content', '')[:100]}...")
        
        # Only cache idempotent, time-independent requests
        if not self._is_cacheable_request(messages, form_data):
            print(f"DEBUG: CACHE STORAGE SKIP - Request not cacheable (time-dependent or non-idempotent)")
            log.info("🚫 Skipping cache storage for non-cacheable request")
            return False
        
        print(f"DEBUG: CACHE STORAGE PROCEED - This IS a user question, proceeding with cache storage")
            
        try:
            print(f"DEBUG: STORAGE Input - Model: {model}")
            print(f"DEBUG: STORAGE Input - Messages: {messages}")
            print(f"DEBUG: STORAGE Input - Parameters: {parameters}")
            print(f"DEBUG: STORAGE Normalized - Messages: {self._normalize_messages(messages)}")
            print(f"DEBUG: STORAGE Normalized - Parameters: {self._normalize_parameters(parameters)}")
            
            cache_key = self._generate_cache_key(model, messages, parameters)
            cache_ttl = ttl or LLM_CACHE_TTL
            
            # Store the response
            self.redis_client.setex(cache_key, cache_ttl, response)
            log.info(f"💾 Cached response for model: {model} (TTL: {cache_ttl}s)")
            print(f"DEBUG: Cache STORAGE key: {cache_key}")  # Force print to console
            print(f"DEBUG: Stored response: {response[:50]}...")
            return True
            
        except Exception as e:
            log.error(f"❌ Error caching response: {e}")
            return False

# Global cache instance
_cache_instance = None

def get_cache() -> LLMResponseCache:
    """Get or create the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMResponseCache()
    return _cache_instance
