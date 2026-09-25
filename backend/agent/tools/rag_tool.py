"""RAG search tool — searches ChromaDB for relevant document chunks."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import Document
from backend.rag.retriever import retrieve

logger = logging.getLogger(__name__)


def rag_search(
    query: str,
    user_role: str,
    db: Session,
    top_k: int = 5,
) -> dict:
    """
    Search the vector store for relevant document chunks.
    Filters by access level based on the user's role.
    """
    # Determine which access levels this role can see
    access_levels = ["all"]
    if user_role in ("staff", "admin"):
        access_levels.append("staff")
    if user_role == "admin":
        access_levels.append("admin")

    try:
        results = retrieve(query=query, top_k=top_k, access_levels=access_levels)

        if not results:
            return {
                "found": False,
                "message": "No relevant documents found for your query.",
                "sources": [],
                "chunks": [],
            }

        return {
            "found": True,
            "message": f"Found {len(results)} relevant passages.",
            "sources": list({r["source"] for r in results}),
            "chunks": [
                {
                    "text": r["text"],
                    "source": r["source"],
                    "score": round(r.get("score", 0.0), 3),
                }
                for r in results
            ],
        }

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return {
            "found": False,
            "message": f"Search error: {str(e)}",
            "sources": [],
            "chunks": [],
        }
