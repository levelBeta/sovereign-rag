"""Local vector store for Sovereign RAG. ALL DATA IS SYNTHETIC.
Embeddings come from Ollama (nomic-embed-text). Chroma's default embedder is never used.
Role access is stored as boolean metadata flags so the role filter runs inside the query.
"""
import chromadb
import ollama
from chromadb.config import Settings

EMBED_MODEL = "nomic-embed-text"
ROLES = ("analyst", "manager", "ciso")


def embed(texts):
    return ollama.embed(model=EMBED_MODEL, input=list(texts))["embeddings"]


def _meta(c):
    m = {"doc_id": c["doc_id"], "classification": c["classification"]}
    for r in ROLES:
        m["role_" + r] = r in c["roles"]
    return m


def build_index(chunks, name="syn_corpus"):
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.create_collection(name, metadata={"hnsw:space": "cosine"})
    col.add(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed([c["text"] for c in chunks]),
        metadatas=[_meta(c) for c in chunks],
    )
    return col
