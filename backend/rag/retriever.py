"""RAG retriever — combines embedding search with access-level filtering."""

import logging
from typing import Optional

from backend.rag.embedder import embed_query
from backend.rag.vector_store import search

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    top_k: int = 5,
    access_levels: Optional[list[str]] = None,
) -> list[dict]:
    """
    Retrieve the top-k most relevant document chunks for a query.
    Filters by access_level metadata when provided.
    """
    query_embedding = embed_query(query)

    # Build ChromaDB where filter for access levels
    where_filter = None
    if access_levels:
        if len(access_levels) == 1:
            where_filter = {"access_level": access_levels[0]}
        else:
            where_filter = {"access_level": {"$in": access_levels}}

    raw = search(
        query_embedding=query_embedding,
        top_k=top_k,
        where=where_filter,
    )

    # Parse ChromaDB results into a clean list
    results = []
    if raw and raw.get("documents") and raw["documents"][0]:
        documents = raw["documents"][0]
        metadatas = raw["metadatas"][0] if raw.get("metadatas") else [{}] * len(documents)
        distances = raw["distances"][0] if raw.get("distances") else [0.0] * len(documents)

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            similarity = 1 - (dist / 2)
            results.append(
                {
                    "text": doc,
                    "source": meta.get("title", "unknown"),
                    "filename": meta.get("source", "unknown"),
                    "access_level": meta.get("access_level", "all"),
                    "category": meta.get("category", "general"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "score": round(similarity, 4),
                }
            )

    return results
