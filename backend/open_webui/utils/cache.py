import json
import hashlib
import logging
from typing import Optional, Dict, Any
import redis
from open_webui.env import REDIS_URL, LLM_CACHE_TTL
from open_webui.config import OLLAMA_BASE_URL

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
        normalized = unicodedata.normalize("NFD", normalized)

        # Remove extra whitespace and normalize spaces
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove trailing punctuation (language-agnostic)
        # Remove question marks, exclamation marks, periods, etc. at the end
        normalized = re.sub(r"[?!.,;:]+\s*$", "", normalized)

        # Remove leading/trailing quotes and brackets (common in both languages)
        normalized = re.sub(r'^["\'\[\(]+|["\'\]\)]+$', "", normalized)

        # Normalize common punctuation patterns
        # Multiple punctuation marks become single
        normalized = re.sub(r"[?!]{2,}", "?", normalized)
        normalized = re.sub(r"[.]{2,}", ".", normalized)

        # Clean up any double spaces created by normalization
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _normalize_messages(self, messages: list) -> list:
        """Normalize messages by extracting the actual user query, excluding RAG context"""
        if not messages:
            return []

        # Find the last user message for caching purposes
        last_user_message = None
        for message in reversed(messages):
            if message.get("role") == "user":
                last_user_message = message
                break

        if not last_user_message:
            return []

        # Get original content
        original_content = last_user_message.get("content", "")

        # Extract actual user query from RAG-injected content
        user_query = self._extract_user_query_from_rag(original_content)

        # Normalize the user query for semantic caching
        normalized_content = self._normalize_text_content(user_query)

        # Only cache based on the actual user query to avoid RAG context affecting cache keys
        normalized_msg = {
            "role": last_user_message.get("role"),
            "content": normalized_content,
        }
        # Remove None values
        normalized_msg = {k: v for k, v in normalized_msg.items() if v is not None}
        return [normalized_msg]

    def _extract_user_query_from_rag(self, content: str) -> str:
        """
        Extract the actual user query from RAG-injected content.
        RAG templates inject context and instructions, but we only want to cache based on the user's actual question.
        """
        import re

        # Look for the user query section in RAG templates
        # Pattern 1: <user_query>actual query</user_query>
        user_query_match = re.search(
            r"<user_query>\s*(.*?)\s*</user_query>", content, re.DOTALL
        )
        if user_query_match:
            return user_query_match.group(1).strip()

        # Pattern 2: Look for content after "user_query" or similar markers
        query_patterns = [
            r"user_query[:\s]*\n(.*?)(?:\n\n|\Z)",  # user_query: followed by the query
            r"<user_query[^>]*>(.*?)</user_query>",  # XML-style tags
            r"### user[_\s]*query[:\s]*\n(.*?)(?:\n\n|\Z)",  # Markdown headers
        ]

        for pattern in query_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                if (
                    query and len(query) < 1000
                ):  # Sanity check - user queries shouldn't be massive
                    return query

        # Pattern 3: If content contains RAG markers, extract the last line as it's often the user query
        rag_markers = [
            "### Task:",
            "<context>",
            "</context>",
            "source_id",
            "incorporating inline citations",
        ]
        if any(marker in content for marker in rag_markers):
            # Split by lines and find the last substantial line
            lines = content.split("\n")
            for line in reversed(lines):
                line = line.strip()
                # Look for lines that look like user queries (not system instructions)
                if (
                    line
                    and len(line) > 3
                    and len(line) < 500
                    and not line.startswith("#")
                    and not line.startswith("<")
                    and not line.startswith("*")
                    and not any(
                        marker in line
                        for marker in [
                            "Task:",
                            "Guidelines:",
                            "Output:",
                            "Example:",
                            "Context:",
                        ]
                    )
                ):
                    return line

        # Fallback: if no RAG patterns detected, return original content
        # This handles normal conversations without web search
        return content

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
                    if isinstance(models_data, dict) and "data" in models_data:
                        available_models = [
                            model.get("id", "") for model in models_data["data"]
                        ]
                    elif isinstance(models_data, list):
                        available_models = [
                            model.get("id", "") for model in models_data
                        ]

                    if available_models:
                        # Sort by model name length (shorter names often indicate smaller/faster models)
                        # This is a heuristic that often works for model naming conventions
                        sorted_models = sorted(
                            available_models, key=lambda x: (len(x), x)
                        )

                        # Log available models for debugging
                        log.debug(
                            f"Available models for classification: {sorted_models[:5]}..."
                        )

                        # Return the first (likely smallest/fastest) available model
                        return sorted_models[0]

            except Exception as e:
                log.debug(f"Could not get models from OpenWebUI API: {e}")

            # Fallback: Try Ollama for local testing
            try:
                ollama_url = (
                    OLLAMA_BASE_URL.rstrip("/")
                    if OLLAMA_BASE_URL
                    else "http://localhost:11434"
                )
                response = requests.get(f"{ollama_url}/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    available_model_names = [m.get("name", "") for m in models]

                    if available_model_names:
                        # For local Ollama, sort by name length as a heuristic for size
                        sorted_models = sorted(
                            available_model_names, key=lambda x: (len(x), x)
                        )
                        log.debug(
                            f"Using Ollama model for classification: {sorted_models[0]}"
                        )
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
        obvious_time_words = [
            "today",
            "now",
            "current",
            "latest",
            "aujourd'hui",
            "maintenant",
        ]
        if any(word in content.lower() for word in obvious_time_words):
            return True

        # Get available classification model
        classification_model = self._get_available_classification_model()
        if not classification_model:
            # No AI model available, use enhanced pattern matching
            log.debug(
                "🔍 CLASSIFICATION - Using fallback pattern matching (no AI model available)"
            )
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

            # Try Ollama first (faster, no circular dependency)
            try:
                ollama_url = (
                    OLLAMA_BASE_URL.rstrip("/")
                    if OLLAMA_BASE_URL
                    else "http://localhost:11434"
                )
                response = requests.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": classification_model,
                        "messages": [
                            {"role": "user", "content": classification_prompt}
                        ],
                        "stream": False,
                        "options": {"temperature": 0.1},
                    },
                    timeout=2,  # Reduced timeout for classification
                )
                if response.status_code == 200:
                    result = response.json()
                    response_text = (
                        result.get("message", {}).get("content", "").strip().upper()
                    )
                    is_time_dependent = "TIME_DEPENDENT" in response_text
                    log.debug(
                        f"🔍 CLASSIFICATION - Ollama result: {response_text} -> {'TIME_DEPENDENT' if is_time_dependent else 'TIME_INDEPENDENT'}"
                    )
                    return is_time_dependent
                else:
                    log.debug(
                        f"🔍 CLASSIFICATION - Ollama failed: {response.status_code}"
                    )
            except Exception as e:
                log.debug(f"🔍 CLASSIFICATION - Ollama error: {e}")

            # If Ollama fails, fall back to pattern matching to avoid circular dependency
            log.debug(
                "🔍 CLASSIFICATION - Using fallback pattern matching (Ollama failed)"
            )
            return self._fallback_time_detection(content)

        except Exception as e:
            log.debug(f"🔍 CLASSIFICATION - Error: {e}")
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
            r"\b(what\'s|what is) (happening|going on|new)\b",
            r"\b(latest|recent|current|today\'s|this week\'s)\b",
            r"\b(right now|at the moment|currently)\b",
            r"\b(stock price|market|weather|news|breaking)\b",
            # French patterns
            r"\b(qu\'est-ce qui se passe|que se passe-t-il)\b",
            r"\b(dernières|récentes|actuelles|d\'aujourd\'hui)\b",
            r"\b(en ce moment|actuellement|maintenant)\b",
            r"\b(prix des actions|marché|météo|nouvelles)\b",
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
            if message.get("role") == "user":
                last_user_message = message
                break

        if not last_user_message:
            return False

        content = last_user_message.get("content", "")

        # Extract the actual user query from RAG content for analysis
        actual_user_query = self._extract_user_query_from_rag(content)

        # Use AI-powered time dependency detection on the actual user query, not RAG context
        if self._is_time_dependent_content(actual_user_query):
            return False

        # Check for form data that indicates non-idempotent requests
        if form_data:
            # NOTE: We now ALLOW web_search because we cache based on the user query, not the search results
            # The search results are dynamic, but the user's question can still be cached if it's time-independent

            # Check if MCP tools are being used (these often have side effects)
            if form_data.get("tools") or form_data.get("tool_ids"):
                return False

            # Check for system prompts with time references
            system_content = form_data.get("system", "").lower()
            if any(
                indicator in system_content
                for indicator in ["current date", "today is", "the time is"]
            ):
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
            if message.get("role") == "user":
                last_user_message = message
                break

        if not last_user_message:
            return False

        content = last_user_message.get("content", "").lower()

        # Check for system-generated prompts that we should NOT cache
        system_indicators = [
            "create a concise",
            "generate 1-3 broad tags",
            "categorizing the main themes",
            "<chat_history>",
            "respond only with the title text",
            "json format:",
            "### task:",
            "examples of titles:",
            "### guidelines:",
            "### output:",
        ]

        is_user_question = not any(
            indicator in content for indicator in system_indicators
        )

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

    def _generate_cache_key(
        self, model: str, messages: list, parameters: Dict[str, Any]
    ) -> str:
        """Generate a cache key from model, messages, and parameters"""
        # Normalize inputs to ensure consistent cache keys
        normalized_messages = self._normalize_messages(messages)
        normalized_parameters = self._normalize_parameters(parameters)

        # Create a simple string representation for hashing
        key_data = {
            "model": model,
            "messages": normalized_messages,
            "parameters": normalized_parameters,
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def would_be_cached(
        self,
        model: str,
        messages: list,
        parameters: Dict[str, Any],
        form_data: dict = None,
    ) -> bool:
        """
        Check if a request would be cached (either cache hit or cacheable for future storage).
        This can be used by RAG systems to skip web search for cacheable queries.
        """
        if not self.connected:
            return False

        try:
            # Check for existing cache hit
            cached_response = self.get_cached_response(
                model, messages, parameters, form_data
            )
            if cached_response:
                return True

            # Check if this request would be cacheable for future storage
            return self._is_cacheable_request(messages, form_data)
        except Exception:
            return False

    def get_cached_response(
        self,
        model: str,
        messages: list,
        parameters: Dict[str, Any],
        form_data: dict = None,
    ) -> Optional[str]:
        """Get cached response if available - OPTIMIZED for instant cache hits"""
        if not self.connected:
            return None

        # Extract user query for logging
        user_query = "N/A"
        if messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    user_query = self._extract_user_query_from_rag(content)[:50] + (
                        "..."
                        if len(self._extract_user_query_from_rag(content)) > 50
                        else ""
                    )
                    break

        try:
            # Generate cache key for lookup
            cache_key = self._generate_cache_key(model, messages, parameters)

            # Test Redis connectivity
            self.redis_client.ping()

            # Check for existing cached response
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                log.info(f"🎯 CACHE HIT [{model}] Query: '{user_query}'")
                return cached_data

            # Cache miss - check if this request would be cacheable for future storage
            if not self._is_cacheable_request(messages, form_data):
                log.info(
                    f"🚫 CACHE SKIP [{model}] Query: '{user_query}' - Not cacheable"
                )
                return None

            log.info(
                f"❌ CACHE MISS [{model}] Query: '{user_query}' - Will cache response"
            )
            return None

        except Exception as e:
            log.error(f"❌ Cache lookup error: {e}")
            return None

    def cache_response(
        self,
        model: str,
        messages: list,
        parameters: Dict[str, Any],
        response: str,
        ttl: int = None,
        form_data: dict = None,
    ) -> bool:
        """Cache a response"""
        if not self.connected:
            return False

        # Extract user query for logging
        user_query = "N/A"
        if messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    user_query = self._extract_user_query_from_rag(content)[:50] + (
                        "..."
                        if len(self._extract_user_query_from_rag(content)) > 50
                        else ""
                    )
                    break

        # Only cache idempotent, time-independent requests
        if not self._is_cacheable_request(messages, form_data):
            log.debug(
                f"🚫 STORAGE SKIP [{model}] Query: '{user_query}' - Not cacheable"
            )
            return False

        try:
            cache_key = self._generate_cache_key(model, messages, parameters)
            cache_ttl = ttl or LLM_CACHE_TTL

            # Store the response
            self.redis_client.setex(cache_key, cache_ttl, response)
            log.info(f"💾 CACHED [{model}] Query: '{user_query}' (TTL: {cache_ttl}s)")
            return True

        except Exception as e:
            log.error(f"❌ Cache storage error: {e}")
            return False


# Global cache instance
_cache_instance = None


def get_cache() -> LLMResponseCache:
    """Get or create the global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMResponseCache()
    return _cache_instance
