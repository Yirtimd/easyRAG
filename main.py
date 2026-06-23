import os
import uuid
import tempfile
from pathlib import Path
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from database import get_history, save_message, create_user, get_user_by_key
from ingest import ingest, ingest_text
from tools import TOOLS, call_tool
from fastapi.responses import JSONResponse


load_dotenv()

app = FastAPI(title="Document Q&A")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ["BASE_URL"],
)

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about documents.
Use search_documents to find relevant content. Use get_session_history when user references past messages.
If the answer is not in the documents, say so honestly."""


# --- Auth ---

async def get_current_user(x_api_key: str = Header(...)):
    user = get_user_by_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register():
    """Создаёт нового пользователя и возвращает api_key."""
    return create_user()


@app.post("/ingest")
async def ingest_pdf(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    named_path = tmp_path.parent / file.filename
    tmp_path.rename(named_path)

    n = ingest(named_path, user_id=user["id"])
    named_path.unlink(missing_ok=True)

    return {"filename": file.filename, "chunks": n}


class TextIngestRequest(BaseModel):
    text: str
    source: str = "clipboard"


@app.post("/ingest/text")
async def ingest_text_endpoint(
    req: TextIngestRequest,
    user=Depends(get_current_user),
):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    n = ingest_text(req.text, req.source, user_id=user["id"])
    return {"source": req.source, "chunks": n}


class ChatRequest(BaseModel):
    question: str
    session_id: str = ""


def stream_agent(question: str, session_id: str, user_id: int):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    while True:
        response = llm.chat.completions.create(
            model=os.environ["BASE_MODEL"],
            messages=messages,
            tools=TOOLS,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            result = call_tool(tc.function.name, tc.function.arguments, session_id, user_id)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    full_answer = []
    stream = llm.chat.completions.create(
        model=os.environ["BASE_MODEL"],
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            full_answer.append(delta)
            yield delta

    save_message(session_id, "user", question)
    save_message(session_id, "assistant", "".join(full_answer))


@app.post("/chat")
async def chat(req: ChatRequest, user=Depends(get_current_user)):
    session_id = req.session_id or str(uuid.uuid4())
    return StreamingResponse(
        stream_agent(req.question, session_id, user["id"]),
        media_type="text/plain",
        headers={"X-Session-Id": session_id},
    )


@app.get("/history/{session_id}")
def history(session_id: str, user=Depends(get_current_user)):
    return get_history(session_id)

@app.get("/export")
async def export_collection(user=Depends(get_current_user)):
    """Экспортирует все документы пользователя в JSON."""
    from ingest import get_collection
    collection = get_collection(user["id"])
    results = collection.get()

    documents = [
        {
            "id": doc_id,
            "text": doc,
            "source": meta["source"],
            "chunk": meta["chunk"],
        }
        for doc_id, doc, meta in zip(
            results["ids"], results["documents"], results["metadatas"]
        )
    ]

    return JSONResponse(
        content={"total_chunks": len(documents), "documents": documents},
        headers={"Content-Disposition": "attachment; filename=rag_export.json"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)