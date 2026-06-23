import os
import chromadb
from pathlib import Path
from pypdf import PdfReader
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DB_PATH = str(Path(__file__).parent / 'chromadb')
COLLECTION_PREFIX = 'docs_'

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name='all-MiniLM-L6-v2'
)

client = chromadb.PersistentClient(path=DB_PATH)

def get_collection(user_id: int):
    return client.get_or_create_collection(
        name=f'{COLLECTION_PREFIX}{user_id}',
        embedding_function=embedding_function,
    )

def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return '\n'.join(page.extract_text() or '' for page in reader.pages)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start: start + chunk_size])
        start += chunk_size - overlap
    return [c for c in chunks if c.strip()]

def ingest(pdf_path: Path, user_id: int) -> int:
    collection = get_collection(user_id)

    existing = collection.get(where={"source": pdf_path.name})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    text = extract_text(pdf_path)
    chunks = chunk_text(text)

    collection.upsert(
        documents=chunks,
        ids=[f"{pdf_path.stem}_chunk_{i}" for i in range(len(chunks))],
        metadatas=[{"source": pdf_path.name, "chunk": i} for i in range(len(chunks))],
    )
    return len(chunks)


def ingest_text(text: str, source: str = "clipboard", user_id: int = 0) -> int:
    collection = get_collection(user_id)

    existing = collection.get(where={"source": source})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    chunks = chunk_text(text)
    if not chunks:
        return 0

    safe_source = source.replace("://", "_").replace("/", "_")[:50]
    collection.upsert(
        documents=chunks,
        ids=[f"{safe_source}_chunk_{i}" for i in range(len(chunks))],
        metadatas=[{"source": source, "chunk": i} for i in range(len(chunks))],
    )
    return len(chunks)

