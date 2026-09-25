"""Document loader and chunker — reads documents and splits them for RAG."""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE, DOCUMENTS_DIR
from backend.rag.embedder import embed_texts
from backend.rag.vector_store import add_documents, get_collection_count

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def load_and_index_text(
    title: str,
    content: str,
    access_level: str = "all",
    category: str = "general",
    source_filename: str = "inline",
) -> int:
    """
    Chunk a text document and add it to the vector store.
    Returns the number of chunks indexed.
    """
    chunks = chunk_text(content)
    if not chunks:
        return 0

    # Generate stable IDs based on content hash
    ids = []
    metadatas = []
    for i, chunk in enumerate(chunks):
        doc_hash = hashlib.md5(f"{title}:{i}:{chunk[:50]}".encode()).hexdigest()
        ids.append(f"doc_{doc_hash}")
        metadatas.append(
            {
                "title": title,
                "source": source_filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "access_level": access_level,
                "category": category,
            }
        )

    embeddings = embed_texts(chunks)
    add_documents(ids=ids, texts=chunks, embeddings=embeddings, metadatas=metadatas)
    logger.info(f"Indexed '{title}': {len(chunks)} chunks")
    return len(chunks)


def load_documents_from_directory(directory: Optional[Path] = None) -> int:
    """Load all .txt and .md files from the documents directory."""
    doc_dir = directory or DOCUMENTS_DIR
    total = 0
    for filepath in doc_dir.iterdir():
        if filepath.suffix in (".txt", ".md"):
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            count = load_and_index_text(
                title=filepath.stem,
                content=content,
                source_filename=filepath.name,
            )
            total += count
    logger.info(f"Loaded {total} total chunks from {doc_dir}")
    return total
