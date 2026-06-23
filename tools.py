import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from database import get_history
from ingest import get_collection

load_dotenv()

llm = OpenAI(
    api_key=os.environ['OPENROUTER_API_KEY'],
    base_url=os.environ['BASE_URL'],
)


def search_documents(question: str, user_id: int, n_results: int = 3) -> str:
    """Finds relevant fragments in docs user"""
    collection = get_collection(user_id)
    results = collection.query(query_texts=[question], n_results=n_results)
    chunks = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]

    if not chunks:
        return 'Documents not found'

    parts = []
    for chunk, meta, dist in zip(chunks, metadatas, distances):
        parts.append(f"[{meta['source']}, distance={round(dist, 3)}]\n{chunk}")
    return "\n\n---\n\n".join(parts)


def get_session_history(session_id: str) -> str:
    """Returns history by session"""
    messages = get_history(session_id, limit=10)
    if not messages:
        return 'History empty'
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)


def summarize_history(history_text: str) -> str:
    """Compresses a long conversation history into a concise summary."""
    resp = llm.chat.completions.create(
        model=os.environ["BASE_MODEL"],
        messages=[{
            "role": "user",
            "content": f"Summarize this conversation briefly:\n\n{history_text}",
        }],
    )
    return resp.choices[0].message.content or ""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search indexed documents for relevant content",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Search query"}
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_history",
            "description": "Get the conversation history for a session",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"}
                },
                "required": ["session_id"],
            },
        },
    },
]


def call_tool(name: str, arguments: str, session_id: str, user_id: int) -> str:
    args = json.loads(arguments)
    if name == "search_documents":
        return search_documents(args["question"], user_id)
    if name == "get_session_history":
        history = get_session_history(session_id)
        if len(history) > 2000:
            history = summarize_history(history)
        return history
    return f"Unknown tool: {name}"