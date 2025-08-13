import logging
import sys
import time

from typing import Any
import random
import json
import inspect

from fastapi import Request
from starlette.responses import StreamingResponse


from open_webui.socket.main import (
    get_event_call,
    get_event_emitter,
)
from open_webui.functions import generate_function_chat_completion

from open_webui.routers.openai import (
    generate_chat_completion as generate_openai_chat_completion,
)

from open_webui.routers.ollama import (
    generate_chat_completion as generate_ollama_chat_completion,
)

from open_webui.routers.pipelines import (
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)

from open_webui.models.functions import Functions


from open_webui.utils.plugin import load_function_module_by_id
from open_webui.utils.models import get_all_models, check_model_access
from open_webui.utils.payload import convert_payload_openai_to_ollama
from open_webui.utils.response import (
    convert_response_ollama_to_openai,
    convert_streaming_response_ollama_to_openai,
)

from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL, BYPASS_MODEL_ACCESS_CONTROL, ENABLE_LLM_CACHE, LLM_CACHE_TTL


logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# Import Redis cache utility if caching is enabled
if ENABLE_LLM_CACHE:
    try:
        from open_webui.utils.cache import get_cache
        log.info("✅ LLM response caching enabled")
    except ImportError:
        log.warning("❌ Cache module not available, caching disabled")
        ENABLE_LLM_CACHE = False


def extract_user_message_from_messages(messages: list) -> str:
    """Extract the last user message from the conversation"""
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("content"):
            return message["content"]
    return ""


def extract_text_from_response(response) -> str:
    """Extract text content from various response formats"""
    if isinstance(response, str):
        return response
    
    if isinstance(response, dict):
        # OpenAI format
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            elif "text" in choice:
                return choice["text"]
        
        # Ollama format
        if "message" in response and "content" in response["message"]:
            return response["message"]["content"]
        
        # Direct content
        if "content" in response:
            return response["content"]
    
    return str(response)


def create_response_from_text(text: str, model_id: str) -> dict:
    """Create a proper response format from cached text"""
    return {
        "id": f"cache-{model_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        },
        # Add metadata to indicate this is a cached response
        "cached": True,
        "web_search": False  # Explicitly indicate no web search was used
    }


async def create_streaming_response_from_text(text: str, model_id: str):
    """Create a streaming response from cached text - ultra-fast delivery"""
    
    # Single chunk with all content for instant delivery
    chunk = {
        "id": f"chatcmpl-cache-{model_id}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "delta": {"content": text},
                "finish_reason": None
            }
        ]
    }
    yield f"data: {json.dumps(chunk)}\n\n"
    
    # Completion signal
    final_chunk = {
        "id": f"chatcmpl-cache-{model_id}",
        "object": "chat.completion.chunk", 
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    bypass_filter: bool = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    models = request.app.state.MODELS

    model_id = form_data["model"]
    if model_id not in models:
        raise Exception("Model not found")

    # EARLY CACHE CHECK - Before any processing overhead
    cache = None
    is_streaming = form_data.get("stream", False)
    # Check if web search was originally enabled (before middleware might have disabled it)
    has_web_search = form_data.get("web_search", False) or "web_search_results" in form_data
    original_web_search = form_data.get("original_web_search", has_web_search)  # Middleware should set this
    log.info(f"🔧 PROCESSING [{model_id}] Streaming: {is_streaming}, Web Search: {original_web_search} {'(skipped)' if original_web_search and not has_web_search else ''}")
    
    # Get messages for use throughout the function (needed for caching)
    messages = form_data.get("messages", [])
    
    if ENABLE_LLM_CACHE:
        try:
            cache = get_cache()
            
            # Create cache parameters from request (optimize for cache hit rate)
            cache_params = {
                # Use temperature 0.0 for caching to ensure deterministic, consistent responses
                # This maximizes cache hit rate and provides reliable cached answers
                "temperature": 0.0,  # Force deterministic for caching
                "max_tokens": form_data.get("max_tokens"),
                "top_p": form_data.get("top_p"),
                "stream": False  # Always use False for consistent cache keys
            }
            
            # Check for cached response even for streaming requests
            # Pass form_data to help the cache system understand the request context
            cached_response = cache.get_cached_response(model_id, messages, cache_params, form_data)
            if cached_response:
                log.info(f"🎯 CACHE HIT [{model_id}] Serving instant response (Web Search: {original_web_search})")
                # Return immediately, bypassing ALL pipeline processing including web search
                return create_response_from_text(cached_response, model_id)
            # Note: cache miss logging is handled by get_cached_response()
        except Exception as e:
            log.error(f"❌ Cache error: {e}")
            cache = None

    # Process the form_data through the pipeline
    try:
        form_data = process_pipeline_inlet_filter(request, form_data, user, models)
    except Exception as e:
        raise e

    model = models[model_id]

    # Check if user has access to the model
    if not bypass_filter and user.role == "user":
        try:
            check_model_access(user, model)
        except Exception as e:
            raise e

    if model["owned_by"] == "arena":
        model_ids = model.get("info", {}).get("meta", {}).get("model_ids")
        filter_mode = model.get("info", {}).get("meta", {}).get("filter_mode")
        if model_ids and filter_mode == "exclude":
            model_ids = [
                model["id"]
                for model in list(request.app.state.MODELS.values())
                if model.get("owned_by") != "arena" and model["id"] not in model_ids
            ]

        selected_model_id = None
        if isinstance(model_ids, list) and model_ids:
            selected_model_id = random.choice(model_ids)
        else:
            model_ids = [
                model["id"]
                for model in list(request.app.state.MODELS.values())
                if model.get("owned_by") != "arena"
            ]
            selected_model_id = random.choice(model_ids)

        form_data["model"] = selected_model_id

        if form_data.get("stream") == True:

            async def stream_wrapper(stream):
                yield f"data: {json.dumps({'selected_model_id': selected_model_id})}\n\n"
                async for chunk in stream:
                    yield chunk

            response = await generate_chat_completion(
                request, form_data, user, bypass_filter=True
            )
            return StreamingResponse(
                stream_wrapper(response.body_iterator),
                media_type="text/event-stream",
                background=response.background,
            )
        else:
            return {
                **(
                    await generate_chat_completion(
                        request, form_data, user, bypass_filter=True
                    )
                ),
                "selected_model_id": selected_model_id,
            }

    if model.get("pipe"):
        # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
        response = await generate_function_chat_completion(
            request, form_data, user=user, models=models
        )
        
        # Cache the function response if caching is enabled and not streaming
        if cache and not form_data.get("stream", False):
            try:
                response_text = extract_text_from_response(response)
                # Use same cache_params as lookup for consistency
                cache_params_for_storage = {
                    "temperature": 0.0,  # Force deterministic for caching
                    "max_tokens": None,
                    "top_p": None,
                    "stream": False  # Always use False for consistent cache keys
                }
                cache.cache_response(model_id, messages, cache_params_for_storage, response_text, LLM_CACHE_TTL)
            except Exception as e:
                log.error(f"❌ Error caching function response: {e}")
        elif cache and form_data.get("stream", False):
            log.debug(f"⚡ Streaming function response - not caching")
        else:
            log.debug(f"⚠️ Cache is None - cannot cache function response")
        
        return response
    if model["owned_by"] == "ollama":
        # Using /ollama/api/chat endpoint
        form_data = convert_payload_openai_to_ollama(form_data)
        response = await generate_ollama_chat_completion(
            request=request, form_data=form_data, user=user, bypass_filter=bypass_filter
        )
        if form_data.get("stream"):
            response.headers["content-type"] = "text/event-stream"
            
            # Wrap streaming response for caching
            if cache:
                async def streaming_wrapper_with_cache():
                    collected_content = ""
                    async for chunk in convert_streaming_response_ollama_to_openai(response):
                        # Forward chunk to client immediately
                        yield chunk
                        
                        # Collect content for caching while streaming
                        if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                            try:
                                data_str = chunk[6:].strip()  # Remove "data: " prefix
                                if data_str:
                                    chunk_data = json.loads(data_str)
                                    if "choices" in chunk_data and chunk_data["choices"]:
                                        choice = chunk_data["choices"][0]
                                        if "delta" in choice and "content" in choice["delta"]:
                                            content = choice["delta"]["content"]
                                            if content:  # Only add non-empty content
                                                collected_content += content
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                # Log parsing errors for debugging
                                log.debug(f"Failed to parse chunk for caching: {e}")
                                pass
                    
                    # Cache the collected response after streaming completes
                    if collected_content.strip():
                        try:
                            # Use same cache_params as lookup for consistency
                            cache_params_for_storage = {
                                "temperature": 0.0,  # Force deterministic for caching
                                "max_tokens": None,
                                "top_p": None,
                                "stream": False  # Always use False for consistent cache keys
                            }
                            cache.cache_response(model_id, messages, cache_params_for_storage, collected_content, LLM_CACHE_TTL)
                        except Exception as e:
                            log.error(f"❌ Error caching streaming Ollama response: {e}")
                    else:
                        log.debug("⚠️ No content collected from streaming response to cache")
                
                return StreamingResponse(
                    streaming_wrapper_with_cache(),
                    headers=dict(response.headers),
                    background=response.background,
                )
            else:
                return StreamingResponse(
                    convert_streaming_response_ollama_to_openai(response),
                    headers=dict(response.headers),
                    background=response.background,
                )
        else:
            converted_response = convert_response_ollama_to_openai(response)
            
            # Cache the response if caching is enabled
            if cache:
                try:
                    response_text = extract_text_from_response(converted_response)
                    # Use same cache_params as lookup for consistency
                    cache_params_for_storage = {
                        "temperature": 0.0,  # Force deterministic for caching
                        "max_tokens": None,
                        "top_p": None,
                        "stream": False  # Always use False for consistent cache keys
                    }
                    cache.cache_response(model_id, messages, cache_params_for_storage, response_text, LLM_CACHE_TTL)
                except Exception as e:
                    log.error(f"❌ Error caching Ollama response: {e}")
            else:
                log.debug("⚠️ Cache is None - cannot cache Ollama response")
            
            return converted_response
    else:
        response = await generate_openai_chat_completion(
            request=request, form_data=form_data, user=user, bypass_filter=bypass_filter
        )
        
        # Cache the response if caching is enabled and not streaming
        if cache and not form_data.get("stream", False):
            try:
                response_text = extract_text_from_response(response)
                # Use same cache_params as lookup for consistency
                cache_params_for_storage = {
                    "temperature": 0.0,  # Force deterministic for caching
                    "max_tokens": None,
                    "top_p": None,
                    "stream": False  # Always use False for consistent cache keys
                }
                cache.cache_response(model_id, messages, cache_params_for_storage, response_text, LLM_CACHE_TTL)
            except Exception as e:
                log.error(f"❌ Error caching OpenAI response: {e}")
        elif cache and form_data.get("stream", False):
            log.debug(f"⚡ Streaming OpenAI response - not caching")
        else:
            log.info(f"⚠️ Cache is None - cannot cache OpenAI response")
        
        return response


chat_completion = generate_chat_completion


async def chat_completed(request: Request, form_data: dict, user: Any):
    if not request.app.state.MODELS:
        await get_all_models(request)
    models = request.app.state.MODELS

    data = form_data
    model_id = data["model"]
    if model_id not in models:
        raise Exception("Model not found")

    model = models[model_id]

    # Add caching logic for completed streaming responses
    if ENABLE_LLM_CACHE:
        try:
            cache = get_cache()
            if cache and "messages" in data:
                messages = data.get("messages", [])
                
                # Extract response content from the last assistant message
                response_content = None
                if messages and len(messages) >= 2:
                    last_message = messages[-1]
                    if last_message.get("role") == "assistant":
                        response_content = last_message.get("content", "")
                
                # Also check if there's a direct content field (fallback)
                if not response_content and "content" in data:
                    response_content = data.get("content", "")
                
                if response_content:
                    # Create cache parameters (use consistent params for storage)
                    cache_params = {
                        "temperature": 0.0,  # Force deterministic for caching
                        "stream": False  # Always use False for consistent cache keys
                    }
                    
                    log.debug(f"💾 Caching completed streaming response for {model_id}")
                    
                    # Cache the completed response using the original messages (minus the assistant response)
                    original_messages = messages[:-1] if len(messages) > 1 else messages
                    cache.cache_response(model_id, original_messages, cache_params, response_content, LLM_CACHE_TTL)
                else:
                    log.debug("No response content found to cache")
            else:
                log.debug("Cache conditions not met for completed response")
        except Exception as e:
            log.error(f"❌ Error caching completed response: {e}")

    try:
        data = process_pipeline_outlet_filter(request, data, user, models)
    except Exception as e:
        return Exception(f"Error: {e}")

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
            "user_id": user.id,
        }
    )

    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
            "user_id": user.id,
        }
    )

    def get_priority(function_id):
        function = Functions.get_function_by_id(function_id)
        if function is not None and hasattr(function, "valves"):
            # TODO: Fix FunctionModel to include vavles
            return (function.valves if function.valves else {}).get("priority", 0)
        return 0

    filter_ids = [function.id for function in Functions.get_global_filter_functions()]
    if "info" in model and "meta" in model["info"]:
        filter_ids.extend(model["info"]["meta"].get("filterIds", []))
        filter_ids = list(set(filter_ids))

    enabled_filter_ids = [
        function.id
        for function in Functions.get_functions_by_type("filter", active_only=True)
    ]
    filter_ids = [
        filter_id for filter_id in filter_ids if filter_id in enabled_filter_ids
    ]

    # Sort filter_ids by priority, using the get_priority function
    filter_ids.sort(key=get_priority)

    for filter_id in filter_ids:
        filter = Functions.get_function_by_id(filter_id)
        if not filter:
            continue

        if filter_id in request.app.state.FUNCTIONS:
            function_module = request.app.state.FUNCTIONS[filter_id]
        else:
            function_module, _, _ = load_function_module_by_id(filter_id)
            request.app.state.FUNCTIONS[filter_id] = function_module

        if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
            valves = Functions.get_function_valves_by_id(filter_id)
            function_module.valves = function_module.Valves(
                **(valves if valves else {})
            )

        if not hasattr(function_module, "outlet"):
            continue
        try:
            outlet = function_module.outlet

            # Get the signature of the function
            sig = inspect.signature(outlet)
            params = {"body": data}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": filter_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
                "__request__": request,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

            if "__user__" in sig.parameters:
                __user__ = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                }

                try:
                    if hasattr(function_module, "UserValves"):
                        __user__["valves"] = function_module.UserValves(
                            **Functions.get_user_valves_by_id_and_user_id(
                                filter_id, user.id
                            )
                        )
                except Exception as e:
                    print(e)

                params = {**params, "__user__": __user__}

            if inspect.iscoroutinefunction(outlet):
                data = await outlet(**params)
            else:
                data = outlet(**params)

        except Exception as e:
            return Exception(f"Error: {e}")

    return data


async def chat_action(request: Request, action_id: str, form_data: dict, user: Any):
    if "." in action_id:
        action_id, sub_action_id = action_id.split(".")
    else:
        sub_action_id = None

    action = Functions.get_function_by_id(action_id)
    if not action:
        raise Exception(f"Action not found: {action_id}")

    if not request.app.state.MODELS:
        await get_all_models(request)
    models = request.app.state.MODELS

    data = form_data
    model_id = data["model"]

    if model_id not in models:
        raise Exception("Model not found")
    model = models[model_id]

    __event_emitter__ = get_event_emitter(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
            "user_id": user.id,
        }
    )
    __event_call__ = get_event_call(
        {
            "chat_id": data["chat_id"],
            "message_id": data["id"],
            "session_id": data["session_id"],
            "user_id": user.id,
        }
    )

    if action_id in request.app.state.FUNCTIONS:
        function_module = request.app.state.FUNCTIONS[action_id]
    else:
        function_module, _, _ = load_function_module_by_id(action_id)
        request.app.state.FUNCTIONS[action_id] = function_module

    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(action_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))

    if hasattr(function_module, "action"):
        try:
            action = function_module.action

            # Get the signature of the function
            sig = inspect.signature(action)
            params = {"body": data}

            # Extra parameters to be passed to the function
            extra_params = {
                "__model__": model,
                "__id__": sub_action_id if sub_action_id is not None else action_id,
                "__event_emitter__": __event_emitter__,
                "__event_call__": __event_call__,
                "__request__": request,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

            if "__user__" in sig.parameters:
                __user__ = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                }

                try:
                    if hasattr(function_module, "UserValves"):
                        __user__["valves"] = function_module.UserValves(
                            **Functions.get_user_valves_by_id_and_user_id(
                                action_id, user.id
                            )
                        )
                except Exception as e:
                    print(e)

                params = {**params, "__user__": __user__}

            if inspect.iscoroutinefunction(action):
                data = await action(**params)
            else:
                data = action(**params)

        except Exception as e:
            return Exception(f"Error: {e}")

    return data
