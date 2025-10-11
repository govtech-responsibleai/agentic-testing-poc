"""Vector database setup using Chroma for meeting minutes and document search."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import chromadb

# Paths
DOCS_DIR = Path(__file__).parent / "docs"
MINUTES_DIR = DOCS_DIR / "meeting_minutes"
CHROMA_DIR = Path(__file__).parent / "chroma_db"

logger = logging.getLogger(__name__)


class VectorDB:
    """Wrapper around a persistent Chroma collection."""

    def __init__(self, persist_directory: str | None = None) -> None:
        if persist_directory is None:
            persist_directory = str(CHROMA_DIR)

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="business_documents", metadata={"hnsw:space": "cosine"}
        )

    def add_meeting_minutes(self) -> None:
        """Load and index all meeting minutes located in the docs directory."""

        if not MINUTES_DIR.exists():
            logger.warning("Meeting minutes directory not found: %s", MINUTES_DIR)
            return

        documents: list[str] = []
        metadatas: list[dict[str, str]] = []
        ids: list[str] = []

        for file_path in MINUTES_DIR.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            filename = file_path.name
            parts = filename.split("_")
            meeting_num = parts[1]
            meeting_type = "_".join(parts[2:-1])
            date_str = parts[-1].removesuffix(".md")

            lines = content.splitlines()
            meeting_title = lines[0].removeprefix("# ") if lines else "Unknown Meeting"

            metadata = {
                "filename": filename,
                "meeting_number": meeting_num,
                "meeting_type": meeting_type.replace("_", " ").title(),
                "date": date_str,
                "document_type": "meeting_minutes",
                "title": meeting_title,
            }

            documents.append(content)
            metadatas.append(metadata)
            ids.append(str(uuid.uuid4()))

        if not documents:
            logger.info("No meeting minutes found to add to vector database")
            return

        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info("Added %s meeting minutes to vector database", len(documents))

    def search_documents(
        self, query: str, n_results: int = 5, doc_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar documents using semantic similarity."""

        where_filter: dict[str, str] | None = None
        if doc_type:
            where_filter = {"document_type": doc_type}

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        formatted_results: list[dict[str, Any]] = []
        for index, document in enumerate(results["documents"][0]):
            formatted_results.append(
                {
                    "content": document,
                    "metadata": results["metadatas"][0][index],
                    "similarity": (
                        results["distances"][0][index]
                        if "distances" in results
                        else None
                    ),
                }
            )

        return formatted_results

    def get_collection_info(self) -> dict[str, Any]:
        """Return simple metadata about the managed collection."""

        count = self.collection.count()
        return {"total_documents": count, "collection_name": self.collection.name}

    def search_by_meeting_type(
        self, meeting_type: str, n_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search for documents filtered by meeting type."""

        results = self.collection.query(
            query_texts=[meeting_type],
            n_results=n_results,
            where={"document_type": "meeting_minutes"},
        )

        formatted_results: list[dict[str, Any]] = []
        for index, document in enumerate(results["documents"][0]):
            formatted_results.append(
                {
                    "content": document,
                    "metadata": results["metadatas"][0][index],
                    "similarity": (
                        results["distances"][0][index]
                        if "distances" in results
                        else None
                    ),
                }
            )

        return formatted_results


def initialize_vector_db() -> VectorDB:
    """Initialise the vector database with meeting minutes content."""

    logger.info("Initialising vector database")
    vector_db = VectorDB()
    vector_db.add_meeting_minutes()
    info = vector_db.get_collection_info()
    logger.info(
        "Vector database initialised with %s documents", info.get("total_documents", 0)
    )
    return vector_db


def search_meeting_minutes(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Convenience helper to search meeting minutes and log the results."""

    vector_db = VectorDB()
    results = vector_db.search_documents(query, n_results, doc_type="meeting_minutes")

    for index, result in enumerate(results, 1):
        metadata = result["metadata"]
        logger.info(
            "%s. %s (%s) - %s",
            index,
            metadata.get("title"),
            metadata.get("meeting_type"),
            metadata.get("filename"),
        )
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    initialize_vector_db()
    logger.info("%s", "=" * 50)
    search_meeting_minutes("sales performance and revenue", 3)
    logger.info("%s", "=" * 50)
    search_meeting_minutes("product development and roadmap", 3)
    logger.info("%s", "=" * 50)
    search_meeting_minutes("budget and financial planning", 3)
