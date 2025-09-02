"""
Pure txtai-wikipedia semantic search - absolutely generic
"""

import importlib.util
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger(__name__)


def _get_txtai_embeddings():
    """Lazy load txtai.embeddings.Embeddings with clear error message"""
    try:
        from txtai.embeddings import Embeddings

        return Embeddings
    except ImportError:
        raise ImportError(
            "txtai is required for Wikipedia grounding. "
            "Install with: pip install txtai[similarity]"
        )


def _get_transformers_pipeline():
    """Lazy load transformers.pipeline with clear error message"""
    try:
        from transformers import pipeline

        return pipeline
    except ImportError:
        raise ImportError(
            "transformers is required for language detection. "
            "Install with: pip install transformers"
        )


def _check_optional_dependency(module_name: str) -> bool:
    """Check if an optional dependency is available"""
    return importlib.util.find_spec(module_name) is not None


class WikiSearchGrounder:
    """Pure txtai-wikipedia implementation with lazy loading"""

    def __init__(self):
        self.max_content_length = 4000
        self.max_search_results = 5
        self.embeddings = None
        self.translator = None
        self.model_loaded = False
        self.translation_loaded = False
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize models (call once before using search methods)"""
        if self._initialized:
            return True

        success = True

        # Initialize txtai model
        if not self._load_txtai_model():
            success = False

        # Initialize translation model (optional)
        self._load_translation_model()

        self._initialized = success
        return success

    async def ensure_initialized(self) -> bool:
        """Ensure models are initialized before use"""
        if not self._initialized:
            return await self.initialize()
        return True

    def _should_ground_query(self, query: str) -> bool:
        """
        Intelligent determination of whether a query needs factual/recent information.
        Supports both English and French queries.

        Returns True for queries that likely need factual information,
        False for creative/personal tasks that don't benefit from grounding.
        """
        query_lower = query.lower().strip()

        # Special case: time-related queries (can be very short)
        time_queries_en = [
            r"\b(what\s+time\s+is\s+it|current\s+time|time\s+now|what\'s\s+the\s+time|what\s+is\s+the\s+time|what\s+the\s+time)",
            r"\b(what\s+(is\s+the\s+)?date|current\s+date|today\'s\s+date)",
            r"\b(what\s+day\s+is\s+it|what\s+day\s+is\s+today)",
        ]

        time_queries_fr = [
            r"\b(quelle\s+heure\s+est(-il|)\s*\??|heure\s+actuelle|heure\s+maintenant|quelle\s+heure)",
            r"\b(quelle\s+(est\s+la\s+)?date|date\s+actuelle|date\s+d\'aujourd\'hui)",
            r"\b(quel\s+jour\s+(sommes(-nous|)|est(-ce|))|quel\s+jour\s+aujourd\'hui)",
        ]

        # Check time queries first (these should always be grounded regardless of length)
        for pattern in time_queries_en + time_queries_fr:
            if re.search(pattern, query_lower):
                log.info(f"🔍 Query matches time pattern, should ground: {pattern}")
                return True

        # Skip very short queries (except time queries which were handled above)
        if len(query_lower) < 10:
            return False

        # English patterns that DON'T need grounding (creative/personal tasks)
        creative_patterns_en = [
            # Greeting/message creation
            r"\b(write|create|make|generate|compose|draft)\s+(a\s+)?(greeting|message|email|letter|note|memo|invitation)",
            r"\b(help\s+me\s+)?(write|create|make|compose)\s+(something|anything)",
            r"\bgreet(ing)?\s+(message|email|text)",
            # Creative content
            r"\b(tell\s+me\s+a\s+)?(joke|story|riddle|poem)",
            r"\b(write|create|make|generate)\s+(a\s+)?(story|poem|song|lyrics|script|dialogue)",
            r"\bcreative\s+(writing|content|ideas)",
            r"\bbrainstorm(ing)?",
            # Personal/opinion requests
            r"\bgive\s+me\s+(your\s+)?(opinion|thoughts|advice|suggestions)",
            r"\bwhat\s+(do\s+you\s+)?(think|feel|believe|recommend)",
            r"\byour\s+(opinion|thoughts|recommendation|suggestion)",
            # Task/instructional requests
            r"\b(help\s+me\s+)?(do|complete|finish|solve)",
            r"\bhow\s+(do\s+i\s+|can\s+i\s+|to\s+)?(make|create|build|fix|repair)",
            r"\bstep\s+by\s+step",
            r"\btutorial",
            r"\bguide\s+me",
            # Code/technical creation
            r"\b(write|create|generate|build)\s+(code|program|script|function|class)",
            r"\bhelp\s+(me\s+)?(code|program|debug)",
            # Explanations of concepts (without "latest" or "current")
            r"\bexplain\s+(?!.*\b(latest|current|recent|today|now|202[4-9])\b)",
            r"\btell\s+me\s+about\s+(?!.*\b(latest|current|recent|today|now|202[4-9])\b)",
            # Role playing
            r"\bact\s+(like|as)\s+",
            r"\bpretend\s+(you\s+are|to\s+be)",
            r"\brole\s*play",
            # Format/style requests
            r"\bformat\s+(this|it|that)",
            r"\brewrite\s+(this|it|that)",
            r"\bsummariz(e|ing)\s+(this|it|that)",
            r"\btranslate\s+(this|it|that)",
        ]

        # French patterns that DON'T need grounding
        creative_patterns_fr = [
            # Greeting/message creation
            r"\b(écri(s|vez)|créer?|fair(e|es?)|générer?|composer|rédiger)\s+(un\s+)?(message|email|lettre|note|mémo|invitation)",
            r"\b(aide?z?(-moi)?\s+)?(écri(s|vez)|créer?|composer)\s+(quelque\s+chose|quelque\s+chose)",
            r"\bmessage\s+(de\s+)?(salutation|accueil)",
            # Creative content
            r"\b(racont(e|ez)(-moi)?\s+)?(une\s+)?(blague|histoire|devinette|poème)",
            r"\b(écri(s|vez)|créer?|fair(e|es?)|générer?)\s+(un(e)?\s+)?(histoire|poème|chanson|paroles|script|dialogue)",
            r"\bcréati(f|ve|on)\s+(littéraire|contenu|idées)",
            r"\bremue(-|\s+)méninges",
            # Personal/opinion requests
            r"\bdonne(z)?(-moi)?\s+(votre\s+|ton\s+)?(avis|opinion|conseil|suggestion)",
            r"\bque\s+(pense(z|s)(-vous|-tu)|ressent(ez|s)(-vous|-tu)|croi(ez|s)(-vous|-tu)|recommande(z|s)(-vous|-tu))",
            r"\b(votre|ton)\s+(avis|opinion|recommandation|suggestion)",
            # Task/instructional requests
            r"\b(aide(z)?(-moi)?\s+)?(fair(e|es?)|terminer|finir|résoudre)",
            r"\bcomment\s+(puis(-je)|faire|créer|construire|réparer)",
            r"\bétape\s+par\s+étape",
            r"\btutoriel",
            r"\bguide(z)?(-moi)",
            # Code/technical creation
            r"\b(écri(s|vez)|créer?|générer?|construire)\s+(code|programme|script|fonction|classe)",
            r"\baide(z)?(-moi)?\s+(coder|programmer|déboguer)",
            # Explanations of concepts (without "dernier/actuel/récent")
            r"\bexpliqu(e|ez)(-moi)?\s+(?!.*(dernier|actuel|récent|aujourd\'hui|maintenant|2024|2025))",
            r"\bparle(z)?(-moi)?\s+de\s+(?!.*(dernier|actuel|récent|aujourd\'hui|maintenant|2024|2025))",
            # Role playing
            r"\b(agis|agisse(z)?|comporte(-toi|-vous))\s+(comme|en\s+tant\s+que)",
            r"\bfais\s+(semblant|comme\s+si)",
            r"\bjeu\s+de\s+rôle",
            # Format/style requests
            r"\bformat(e|ez)\s+(ceci|cela|ça)",
            r"\brééc(ris|rive(z)?)\s+(ceci|cela|ça)",
            r"\brésume(z)?\s+(ceci|cela|ça)",
            r"\btradui(s|se(z)?)\s+(ceci|cela|ça)",
        ]

        # Check creative patterns first (these should NOT be grounded)
        for pattern in creative_patterns_en + creative_patterns_fr:
            if re.search(pattern, query_lower):
                log.info(
                    f"🔍 Query matches creative pattern, skipping grounding: {pattern}"
                )
                return False

        # English patterns that SHOULD be grounded (factual/recent information needs)
        factual_patterns_en = [
            # Time and date queries
            r"\b(what\s+time\s+is\s+it|current\s+time|time\s+now|what\'s\s+the\s+time|what\s+is\s+the\s+time|what\s+the\s+time)",
            r"\b(what\s+(is\s+the\s+)?date|current\s+date|today\'s\s+date)",
            r"\b(what\s+day\s+is\s+it|what\s+day\s+is\s+today)",
            # Current events / news
            r"\b(latest|current|recent|new|today|this\s+(week|month|year)|2024|2025)",
            r"\b(what\'s\s+happening|news|events|updates)",
            r"\bhappening\s+(now|today|recently)",
            # Enhanced temporal patterns
            r"\b(as\s+of|up\s+to\s+date|current\s+status|currently|nowadays|these\s+days)",
            r"\b(still\s+(active|alive|operating|running)|no\s+longer|anymore)",
            r"\b(now|present|today|contemporary)",
            # Age and time-sensitive queries
            r"\b(how\s+old|age|born|died|since\s+when|until\s+when)",
            r"\b(active|inactive|retired|current\s+(position|role|status))",
            # Factual queries
            r"\b(when\s+(did|was|were)|what\s+(happened|is\s+the|was\s+the)|where\s+(is|was|are|were)|who\s+(is|was|are|were))",
            r"\b(how\s+many|how\s+much|statistics|data|facts|information\s+about)",
            r"\b(population|temperature|weather|price|cost|rate)",
            # Dynamic/changing information
            r"\b(status|condition|situation|state\s+of)",
            r"\b(available|unavailable|open|closed|operating|running)",
            r"\b(leader|president|prime\s+minister|CEO|director|head\s+of)",
            # Research/lookup queries
            r"\b(find\s+(information|data)|research|look\s+up|search\s+for)",
            r"\b(definition\s+of|meaning\s+of|what\s+(does|is)|explain\s+what)",
            # Specific entities (likely need current info)
            r"\b(company|organization|government|politics|economy|market)",
            r"\b(celebrity|politician|scientist|author|artist)",
            # Location/geography
            r"\b(country|city|state|province|region|capital|location)",
            # Technology/science (likely evolving)
            r"\b(technology|software|AI|artificial\s+intelligence|machine\s+learning|research)",
            # Comparative queries
            r"\b(better|worse|best|worst|compare|comparison|versus|vs\.?)",
            r"\b(difference\s+between|similarities\s+between)",
        ]

        # French patterns that SHOULD be grounded
        factual_patterns_fr = [
            # Time and date queries
            r"\b(quelle\s+heure\s+est(-il|)\s*\??|heure\s+actuelle|heure\s+maintenant|quelle\s+heure)",
            r"\b(quelle\s+(est\s+la\s+)?date|date\s+actuelle|date\s+d\'aujourd\'hui)",
            r"\b(quel\s+jour\s+(sommes(-nous|)|est(-ce|))|quel\s+jour\s+aujourd\'hui)",
            # Current events / news
            r"\b(dernier|dernière|actuel|récent|récente|nouveau|nouvelle|aujourd\'hui|cette\s+(semaine|mois|année)|2024|2025)",
            r"\b(qu\'est(-ce\s+qui|ce\s+que)\s+se\s+passe|nouvelles|événements|actualités|mises\s+à\s+jour)",
            r"\bse\s+passe\s+(maintenant|aujourd\'hui|récemment)",
            # Enhanced temporal patterns
            r"\b(à\s+ce\s+jour|jusqu\'à\s+présent|état\s+actuel|actuellement|de\s+nos\s+jours)",
            r"\b(encore\s+(actif|vivant|en\s+fonctionnement)|ne\s+.+\s+plus|plus\s+maintenant)",
            r"\b(maintenant|présent|aujourd\'hui|contemporain)",
            # Age and time-sensitive queries
            r"\b(quel\s+âge|âge|né|décédé|depuis\s+quand|jusqu\'à\s+quand)",
            r"\b(actif|inactif|retraité|poste\s+actuel|rôle\s+actuel|statut\s+actuel)",
            # Factual queries
            r"\b(quand\s+(a|est|était|sont|étaient)|qu\'est(-ce\s+qui|ce\s+que)\s+(s\'est\s+passé|est|était)|où\s+(est|était|sont|étaient)|qui\s+(est|était|sont|étaient))",
            r"\bquand\s+.*?\s+(a|ont)\s+(commencé|débuté)",
            r"\bquand\s+.*commencé",
            r"\b(combien\s+(de|d\')|statistiques|données|faits|informations\s+sur)",
            r"\b(population|température|météo|prix|coût|taux)",
            # Dynamic/changing information
            r"\b(statut|condition|situation|état\s+de)",
            r"\b(disponible|indisponible|ouvert|fermé|en\s+fonctionnement)",
            r"\b(dirigeant|président|premier\s+ministre|PDG|directeur|chef\s+de)",
            # Research/lookup queries
            r"\b(trouvez?\s+(informations?|données)|recherch(e|er|ez)|cherch(e|er|ez))",
            r"\b(définition\s+(de|d\')|signification\s+(de|d\')|qu\'est(-ce\s+que|ce\s+qui)|expliqu(e|ez)\s+ce\s+que)",
            # Specific entities
            r"\b(entreprise|organisation|gouvernement|politique|économie|marché)",
            r"\b(célébrité|politicien|scientifique|auteur|artiste)",
            # Location/geography
            r"\b(pays|ville|état|province|région|capitale|lieu|endroit)",
            # Technology/science
            r"\b(technologie|logiciel|IA|intelligence\s+artificielle|apprentissage\s+(automatique|machine)|recherche)",
            # Comparative queries
            r"\b(meilleur|pire|mieux|comparer|comparaison|contre|vs\.?|comparez)",
            r"\b(différence\s+entre|similitudes\s+entre)",
            # Additional formal conjugations (vous forms)
            r"\b(pouvez-vous\s+(me\s+)?(dire|expliquer|donner)|savez-vous)",
            r"\b(connaissez-vous|avez-vous\s+(des\s+)?informations)",
        ]

        # Check factual patterns
        for pattern in factual_patterns_en + factual_patterns_fr:
            if re.search(pattern, query_lower):
                log.info(f"🔍 Query matches factual pattern, should ground: {pattern}")
                return True

        # Default: if no clear pattern matches, lean towards NOT grounding
        # This prevents over-grounding and respects user intent for creative tasks
        log.info("🔍 Query doesn't match clear factual patterns, skipping grounding")
        return False

    def _load_translation_model(self) -> bool:
        """Load HuggingFace translation pipeline"""
        if self.translation_loaded:
            return True

        if not _check_optional_dependency("transformers"):
            log.warning(
                "transformers not available for translation. Install with: pip install transformers>=4.46.0"
            )
            return False

        try:
            pipeline = _get_transformers_pipeline()

            log.info("Loading French-to-English translation pipeline...")
            # Use a lightweight multilingual translation model
            self.translator = pipeline(
                "translation",
                model="Helsinki-NLP/opus-mt-fr-en",
                device=-1,  # Use CPU to avoid memory issues
            )
            self.translation_loaded = True
            log.info("HuggingFace translation pipeline loaded successfully")
            return True
        except Exception as e:
            log.warning(f"Translation pipeline failed to load: {e}")
            return False

    def _detect_language(self, text: str) -> str:
        """Simple language detection - check for French indicators"""
        french_words = [
            "qui",
            "est",
            "le",
            "la",
            "les",
            "des",
            "du",
            "de",
            "et",
            "ou",
            "que",
            "dans",
            "avec",
            "pour",
            "par",
            "sur",
        ]
        text_lower = text.lower()
        french_count = sum(
            1
            for word in french_words
            if f" {word} " in f" {text_lower} "
            or text_lower.startswith(f"{word} ")
            or text_lower.endswith(f" {word}")
        )

        # If multiple French words detected, likely French
        if french_count >= 2:
            return "fr"
        return "en"

    def _translate_to_english(self, text: str) -> str:
        """Translate text to English if French is detected"""
        if not self.translation_loaded:
            return text

        try:
            detected_lang = self._detect_language(text)
            if detected_lang == "fr":
                # The model expects French input
                translated_result = self.translator(text)
                translated_text = translated_result[0]["translation_text"]
                log.info(f"Translated query: '{text}' -> '{translated_text}'")
                return translated_text
            return text
        except Exception as e:
            log.warning(f"Translation failed, using original query: {e}")
            return text

    def _load_txtai_model(self) -> bool:
        """Load txtai-wikipedia from local filesystem cache or HuggingFace Hub"""
        if self.model_loaded:
            return True

        if not _check_optional_dependency("txtai"):
            log.error(
                "txtai is not available. Please install with: pip install txtai[graph]>=8.6.0"
            )
            return False

        try:
            import os
            import glob

            Embeddings = _get_txtai_embeddings()

            # Import TXTAI_CACHE_DIR from config for proper environment variable support
            from open_webui.config import TXTAI_CACHE_DIR

            # Try loading from local filesystem cache first using configurable cache directory
            cache_base = os.path.join(
                TXTAI_CACHE_DIR, "hub", "models--neuml--txtai-wikipedia"
            )
            snapshots_dir = os.path.join(cache_base, "snapshots")

            if os.path.exists(snapshots_dir):
                # Find the latest snapshot directory
                snapshot_dirs = glob.glob(os.path.join(snapshots_dir, "*"))
                if snapshot_dirs:
                    # Use the first available snapshot (there should typically be only one)
                    latest_snapshot = sorted(snapshot_dirs)[-1]

                    # Check if required files exist
                    embeddings_file = os.path.join(latest_snapshot, "embeddings")
                    documents_file = os.path.join(latest_snapshot, "documents")
                    config_file = os.path.join(latest_snapshot, "config.json")

                    if all(
                        os.path.exists(f)
                        for f in [embeddings_file, documents_file, config_file]
                    ):
                        log.info(
                            f"Loading txtai-wikipedia model from local cache: {latest_snapshot}"
                        )
                        self.embeddings = Embeddings()
                        self.embeddings.load(latest_snapshot)
                        self.model_loaded = True
                        log.info(
                            "txtai-wikipedia model loaded successfully from local cache"
                        )
                        return True
                    else:
                        log.warning(
                            f"Required files missing in cache snapshot: {latest_snapshot}"
                        )
                else:
                    log.debug(f"No snapshots found in: {snapshots_dir}")
            else:
                log.debug(f"Cache directory not found: {snapshots_dir}")

            # Fallback to HuggingFace Hub if local cache is not available
            log.info(
                "Local cache not found, loading txtai-wikipedia model from HuggingFace Hub..."
            )
            self.embeddings = Embeddings()
            self.embeddings.load(
                provider="huggingface-hub", container="neuml/txtai-wikipedia"
            )
            self.model_loaded = True
            log.info("txtai-wikipedia model loaded successfully from HuggingFace Hub")
            return True
        except Exception as e:
            log.error(f"Failed to load txtai-wikipedia: {e}")
            return False

    async def search(self, query: str) -> List[Dict]:
        """Pure txtai search with translation support"""
        # Ensure models are initialized
        if not await self.ensure_initialized():
            return []

        try:
            # Translate query to English for better search results
            original_query = query
            search_query = self._translate_to_english(query)

            # Use basic search with translated query
            results = self.embeddings.search(search_query)

            # Format results and apply score threshold
            formatted = []
            for result in results[: self.max_search_results * 2]:  # Get more to filter
                if isinstance(result, dict):
                    score = result.get("score", 0)

                    # Only include high-quality results (score > 0.8)
                    if score > 0.8:
                        title = result.get("id", "")
                        content = result.get("text", "")

                        if len(content) > self.max_content_length:
                            content = content[: self.max_content_length] + "..."

                        formatted.append(
                            {
                                "title": title,
                                "content": content,
                                "score": score,
                                "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                "source": "txtai-wikipedia",
                                "original_query": original_query,
                                "search_query": search_query,
                            }
                        )

                        # Stop when we have enough high-quality results
                        if len(formatted) >= self.max_search_results:
                            break

            return formatted

        except Exception as e:
            log.error(f"Search failed: {e}")
            return []

    def _is_time_query(self, query: str) -> bool:
        """Check if query is asking for current time/date information"""
        query_lower = query.lower().strip()

        time_patterns = [
            r"\b(what\s+time\s+is\s+it|current\s+time|time\s+now|what\'s\s+the\s+time|what\s+is\s+the\s+time|what\s+the\s+time)",
            r"\b(what\s+(is\s+the\s+)?date|current\s+date|today\'s\s+date)",
            r"\b(what\s+day\s+is\s+it|what\s+day\s+is\s+today)",
            r"\b(quelle\s+heure\s+est(-il|)\s*\??|heure\s+actuelle|heure\s+maintenant|quelle\s+heure)",
            r"\b(quelle\s+(est\s+la\s+)?date|date\s+actuelle|date\s+d\'aujourd\'hui)",
            r"\b(quel\s+jour\s+(sommes(-nous|)|est(-ce|))|quel\s+jour\s+aujourd\'hui)",
        ]

        for pattern in time_patterns:
            if re.search(pattern, query_lower):
                return True
        return False

    async def ground_query(self, query: str, request=None, user=None) -> Optional[Dict]:
        """Main grounding method with intelligent query filtering"""

        # Basic length check
        if len(query.strip()) < 3:
            log.info("🔍 Query too short, skipping grounding")
            return None

        # Intelligent filtering: check if this query actually needs factual information
        if not self._should_ground_query(query):
            log.info(
                "🔍 Query doesn't need factual grounding based on content analysis"
            )
            return None

        # Special handling for time queries - don't search Wikipedia, just provide context
        if self._is_time_query(query):
            log.info(
                "🔍 Time query detected, providing temporal context without search"
            )
            return {
                "original_query": query,
                "grounding_data": [],  # No search results needed
                "source": "temporal-context",
                "timestamp": datetime.now().isoformat(),
                "is_time_query": True,
            }

        log.info(
            "🔍 Query determined to need factual grounding, proceeding with search"
        )
        results = await self.search(query)

        if not results:
            log.info("🔍 No search results found")
            return None

        return {
            "original_query": query,
            "grounding_data": results,
            "source": "txtai-wikipedia",
            "timestamp": datetime.now().isoformat(),
        }

    async def ground_query_always(
        self, query: str, request=None, user=None
    ) -> Optional[Dict]:
        """Ground query without intelligent filtering (always mode)"""

        # Basic length check only
        if len(query.strip()) < 3:
            log.info("🔍 Query too short, skipping grounding")
            return None

        # Special handling for time queries - don't search Wikipedia, just provide context
        if self._is_time_query(query):
            log.info(
                "🔍 Time query detected in always mode, providing temporal context without search"
            )
            return {
                "original_query": query,
                "grounding_data": [],  # No search results needed
                "source": "temporal-context",
                "timestamp": datetime.now().isoformat(),
                "is_time_query": True,
            }

        log.info("🔍 Always mode: grounding without content analysis")
        results = await self.search(query)

        if not results:
            log.info("🔍 No search results found")
            return None

        return {
            "original_query": query,
            "grounding_data": results,
            "source": "txtai-wikipedia",
            "timestamp": datetime.now().isoformat(),
        }

    def format_grounding_context(self, grounding_data: Dict) -> str:
        """Format for LLM context with translation info and current date awareness"""
        if not grounding_data:
            return ""

        from datetime import datetime

        # Get current date and time information
        current_date = datetime.now()
        formatted_date = current_date.strftime("%Y-%m-%d")
        formatted_time = current_date.strftime("%I:%M:%S %p")
        formatted_weekday = current_date.strftime("%A")

        # Try to get timezone information
        try:
            import time

            timezone_name = (
                time.tzname[time.daylight] if time.daylight else time.tzname[0]
            )
        except:
            timezone_name = "UTC"

        context = []
        context.append("=== GROUNDING CONTEXT ===")
        context.append(f"Current Date: {formatted_date} ({formatted_weekday})")
        context.append(f"Current Time: {formatted_time} {timezone_name}")
        context.append("")

        # Check if this is a time query
        is_time_query = grounding_data.get("is_time_query", False)

        if is_time_query:
            context.append(
                "DIRECT TIME RESPONSE: The user is asking for current time/date information."
            )
            context.append(
                "You should directly provide the current date and time information shown above."
            )
            context.append(
                "No need to search for additional information - just answer based on the temporal context provided."
            )
            context.append("")
        else:
            context.append(
                "IMPORTANT: When answering questions, consider the current date above. For topics that change over time (current events, politics, technology, leadership positions, etc.), acknowledge what information might be outdated and provide context about recency when relevant. If you're unsure about the currentness of information, mention that the information may not reflect the most recent developments as of the current date."
            )
            context.append("")

        context.append(f"Query: {grounding_data.get('original_query', '')}")

        # Only process search results if we have grounding data
        if "grounding_data" in grounding_data and grounding_data["grounding_data"]:
            # Show if translation was used
            first_result = grounding_data["grounding_data"][0]
            if first_result.get("search_query") != first_result.get("original_query"):
                context.append(
                    f"Search Query (translated): {first_result.get('search_query', '')}"
                )

            context.append(f"Source: {grounding_data.get('source', 'txtai-wikipedia')}")
            context.append("")

            for i, item in enumerate(grounding_data["grounding_data"], 1):
                title = item.get("title", "Unknown")
                content = item.get("content", "")
                score = item.get("score", 0)

                context.append(f"[{i}] {title}")
                if score > 0:
                    context.append(f"Score: {score:.3f}")
                context.append(f"Content: {content}")
                context.append("")
        else:
            context.append(
                f"Source: {grounding_data.get('source', 'temporal-context')}"
            )
            context.append("")

        context.append("=== END GROUNDING ===")
        return "\n".join(context)


# Global instance
wiki_search_grounder = WikiSearchGrounder()
