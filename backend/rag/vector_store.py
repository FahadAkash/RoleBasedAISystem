"""ChromaDB vector store wrapper — persistent, local."""

import logging
from typing import Optional

import chromadb

from backend.config import CHROMA_DIR

logger = logging.getLogger(__name__)

_client: Optional[chromadb.PersistentClient] = None
COLLECTION_NAME = "knowledge_base"


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create the persistent ChromaDB client."""
    global _client
    if _client is None:
        logger.info(f"Initializing ChromaDB at {CHROMA_DIR}")
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_collection() -> chromadb.Collection:
    """Get or create the knowledge-base collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    """Add documents (chunked) to the vector store."""
    collection = get_collection()
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info(f"Added {len(ids)} chunks to ChromaDB")


def search(
    query_embedding: list[float],
    top_k: int = 5,
    where: Optional[dict] = None,
) -> dict:
    """Search the vector store by embedding similarity."""
    collection = get_collection()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def get_collection_count() -> int:
    """Return total number of chunks in the collection."""
    return get_collection().count()


def reset_collection() -> None:
    """Delete and recreate the collection."""
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    get_collection()
    logger.info("ChromaDB collection reset")
