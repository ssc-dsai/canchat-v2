import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

# ----------- Request Models -----------
class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: Optional[bool] = True
    options: Optional[Dict] = {}

class ChatMessage(BaseModel):
    role: str  # e.g., "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = True
    options: Optional[Dict] = {}

# ----------- Canned Responses -----------
CANNED_RESPONSE = "This is a canned response script. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Responsum hodiernum a raid shadow legends, uno ex optimis ludis mobilibus anni bis millesimi undeviginti, patrocinatur, et omnino gratuitum est."

PROMPT_RESPONSES = {
    "### task:\nyou are an autocompletion system." : "{ \"text\": \"How annoying is this? Blah blah blah.\" } ",
    "### task:\ngenerate 1-3 broad tags" : "{ \"tags\": [\"Fake\", \"Faker\", \"Fakest\"] }\",",
    "create a concise, 3-5 word title with an emoji as a title for the chat history": "😘 Fake title",
    "hello": "Hi! How can I pretend to help you today?",
    "name": "This a canned response script.",
    "weather": "It might be sunny right now, with 25% chance of rain later tonight in your area.",
}

STUB_MODEL = {
    "model": "fauxllama:latest",
    "name": "fauxllama:latest",
    "urls": [0],
}
STUB_MODELS = {"models": [STUB_MODEL]}
STUB_VERSION = {"version": "0.0.1"}
STUB_EMBED = {"embedding": [0.1, 0.2, 0.3], "model": "fauxllama:latest"}
STUB_COMPLETION = {"id": "stub-id", "object": "text_completion", "choices": [{"text": "Canned completion."}], "model": "fauxllama:latest"}
STUB_CHAT = {"id": "stub-id", "object": "chat.completion", "choices": [{"message": {"role": "assistant", "content": "Canned chat response."}}], "model": "fauxllama:latest"}
STUB_PUSH = True
STUB_DELETE = True
STUB_COPY = True
STUB_SHOW = {"model": "fauxllama:latest", "info": "Canned model info."}
STUB_UPLOAD = {"done": True, "blob": "sha256:hash", "name": "stub-file"}
STUB_DOWNLOAD = {"progress": 100, "completed": 123456, "total": 123456, "done": True, "blob": "sha256:hash", "name": "stub-file"}
def get_response_from_prompt(prompt: str) -> str:
    for key, value in PROMPT_RESPONSES.items():
        if key in prompt.lower():
            return value
    return CANNED_RESPONSE

def get_response_from_chat(messages: List[ChatMessage]) -> str:
    last_user_message = next((m.content for m in reversed(messages) if m.role == "user"), "")
    return get_response_from_prompt(last_user_message)

@app.get("/")
@app.head("/")
def get_status():
    html_content = (
        "<html><head><meta name=\"color-scheme\" content=\"light dark\"></head>"
        "<body><pre style=\"word-wrap: break-word; white-space: pre-wrap;\">Fauxllama is running</pre></body></html>"
    )
    return HTMLResponse(content=html_content)

@app.post("/verify")
def verify_connection():
    return STUB_VERSION

@app.get("/config")
def get_config():
    return {"ENABLE_OLLAMA_API": True, "OLLAMA_BASE_URLS": ["http://localhost:11404"], "OLLAMA_API_CONFIGS": {"0": {}}}

@app.post("/config/update")
def update_config():
    return {"ENABLE_OLLAMA_API": True, "OLLAMA_BASE_URLS": ["http://localhost:11404"], "OLLAMA_API_CONFIGS": {"0": {}}}

@app.get("/api/tags")
@app.get("/api/tags/{url_idx}")
def get_ollama_tags(url_idx: Optional[int] = None):
    return STUB_MODELS

@app.get("/api/version")
@app.get("/api/version/{url_idx}")
def get_ollama_versions(url_idx: Optional[int] = None):
    return STUB_VERSION

@app.get("/api/ps")
def get_ollama_loaded_models():
    return {"http://localhost:11404": STUB_MODELS}

@app.post("/api/pull")
@app.post("/api/pull/{url_idx}")
def pull_model(url_idx: Optional[int] = None):
    return JSONResponse(content={"status": "pulled"})

@app.delete("/api/push")
@app.delete("/api/push/{url_idx}")
def push_model(url_idx: Optional[int] = None):
    return STUB_PUSH

@app.post("/api/create")
@app.post("/api/create/{url_idx}")
def create_model(url_idx: Optional[int] = None):
    return JSONResponse(content={"status": "created"})

@app.post("/api/copy")
@app.post("/api/copy/{url_idx}")
def copy_model(url_idx: Optional[int] = None):
    return STUB_COPY

@app.delete("/api/delete")
@app.delete("/api/delete/{url_idx}")
def delete_model(url_idx: Optional[int] = None):
    return STUB_DELETE

@app.post("/api/show")
def show_model_info():
    return STUB_SHOW

@app.post("/api/embed")
@app.post("/api/embed/{url_idx}")
def embed(url_idx: Optional[int] = None):
    return STUB_EMBED

@app.post("/api/embeddings")
@app.post("/api/embeddings/{url_idx}")
def embeddings(url_idx: Optional[int] = None):
    return STUB_EMBED

@app.post("/v1/completions")
@app.post("/v1/completions/{url_idx}")
def generate_openai_completion(url_idx: Optional[int] = None):
    return STUB_COMPLETION

@app.post("/v1/chat/completions")
@app.post("/v1/chat/completions/{url_idx}")
def generate_openai_chat_completion(url_idx: Optional[int] = None):
    return STUB_CHAT

@app.get("/v1/models")
@app.get("/v1/models/{url_idx}")
def get_openai_models(url_idx: Optional[int] = None):
    return {"data": [STUB_MODEL], "object": "list"}

@app.post("/models/download")
@app.post("/models/download/{url_idx}")
def download_model(url_idx: Optional[int] = None):
    def event_stream():
        yield f"{json.dumps(STUB_DOWNLOAD)}\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/models/upload")
@app.post("/models/upload/{url_idx}")
def upload_model(url_idx: Optional[int] = None, file: UploadFile = File(...)):
    def event_stream():
        yield f"{json.dumps(STUB_UPLOAD)}\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ----------- /api/generate -----------
@app.post("/api/generate")
async def generate(request: GenerateRequest):
    response_text = get_response_from_prompt(request.prompt)

    if request.stream:
        async def generate_stream():
            for word in response_text.split():
                chunk = {
                    "response": word + " ",
                    "done": False
                }
                line = f"data: {json.dumps(chunk)}\n"
                logging.info(f"[generate] Streaming chunk: {line.strip()}")
                yield line
                await asyncio.sleep(0.05)

            done_line = f"data: {json.dumps({'done': True})}\n"
            logging.info(f"[generate] Final chunk: {done_line.strip()}")
            yield done_line

        return StreamingResponse(generate_stream(), media_type="text/event-stream")

    return JSONResponse({
        "response": response_text,
        "done": True
    })

# ----------- /api/chat -----------
@app.post("/api/chat")
async def chat(request: ChatRequest):
    response_text = get_response_from_chat(request.messages)

    if request.stream:
        async def chat_stream():
            for word in response_text.split():
                chunk = {
                    "message": {
                        "role": "assistant",
                        "content": word + " "
                    },
                    "done": False
                }
                line = f"{json.dumps(chunk)}\n"
                logging.info(f"[chat] Streaming chunk: {line.strip()}")
                yield line
                await asyncio.sleep(0.05)

            done_line = f"{json.dumps({'done': True})}\n"
            logging.info(f"[chat] Final chunk: {done_line.strip()}")
            yield done_line

        return StreamingResponse(chat_stream(), media_type="text/event-stream")

    return JSONResponse({
        "message": {
            "role": "assistant",
            "content": response_text
        },
        "done": True
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=11404)
