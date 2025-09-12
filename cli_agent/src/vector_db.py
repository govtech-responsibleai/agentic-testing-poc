"""
Vector database setup using Chroma for meeting minutes and document search
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
import json
from typing import List, Dict, Any
import uuid

# Paths
DOCS_DIR = Path(__file__).parent / "docs"
MINUTES_DIR = DOCS_DIR / "meeting_minutes"
CHROMA_DIR = Path(__file__).parent / "chroma_db"


class VectorDB:
    def __init__(self, persist_directory: str = None):
        """Initialize Chroma vector database"""
        if persist_directory is None:
            persist_directory = str(CHROMA_DIR)

        # Create Chroma client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="business_documents", metadata={"hnsw:space": "cosine"}
        )

    def add_meeting_minutes(self):
        """Load and index all meeting minutes"""
        if not MINUTES_DIR.exists():
            print(f"Meeting minutes directory not found: {MINUTES_DIR}")
            return

        documents = []
        metadatas = []
        ids = []

        for file_path in MINUTES_DIR.glob("*.md"):
            with open(file_path, "r") as f:
                content = f.read()

            # Extract metadata from filename and content
            filename = file_path.name
            parts = filename.split("_")
            meeting_num = parts[1]
            meeting_type = "_".join(parts[2:-1])
            date_str = parts[-1].replace(".md", "")

            # Parse basic info from content
            lines = content.split("\n")
            meeting_title = lines[0].replace("# ", "") if lines else "Unknown Meeting"

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

        # Add to collection
        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            print(f"✅ Added {len(documents)} meeting minutes to vector database")
        else:
            print("❌ No meeting minutes found to add")

    def search_documents(
        self, query: str, n_results: int = 5, doc_type: str = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        where_filter = {}
        if doc_type:
            where_filter["document_type"] = doc_type

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None,
        )

        # Format results
        formatted_results = []
        for i in range(len(results["documents"][0])):
            formatted_results.append(
                {
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": (
                        results["distances"][0][i] if "distances" in results else None
                    ),
                }
            )

        return formatted_results

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        count = self.collection.count()
        return {"total_documents": count, "collection_name": self.collection.name}

    def search_by_meeting_type(
        self, meeting_type: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for documents by meeting type"""
        results = self.collection.query(
            query_texts=[meeting_type],
            n_results=n_results,
            where={"document_type": "meeting_minutes"},
        )

        formatted_results = []
        for i in range(len(results["documents"][0])):
            formatted_results.append(
                {
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": (
                        results["distances"][0][i] if "distances" in results else None
                    ),
                }
            )

        return formatted_results


def initialize_vector_db():
    """Initialize vector database with meeting minutes"""
    print("🔄 Initializing vector database...")

    # Create vector DB instance
    vector_db = VectorDB()

    # Add meeting minutes
    vector_db.add_meeting_minutes()

    # Print collection info
    info = vector_db.get_collection_info()
    print(f"📊 Vector database initialized: {info['total_documents']} documents")

    return vector_db


def search_meeting_minutes(query: str, n_results: int = 5):
    """Convenience function to search meeting minutes"""
    vector_db = VectorDB()
    results = vector_db.search_documents(query, n_results, doc_type="meeting_minutes")

    print(f"🔍 Search results for '{query}':")
    for i, result in enumerate(results, 1):
        metadata = result["metadata"]
        print(f"\n{i}. {metadata['title']} ({metadata['meeting_type']})")
        print(f"   Date: {metadata['date']}, File: {metadata['filename']}")
        print(f"   Preview: {result['content'][:200]}...")


if __name__ == "__main__":
    # Initialize the vector database
    db = initialize_vector_db()

    # Example searches
    print("\n" + "=" * 50)
    search_meeting_minutes("sales performance and revenue", 3)

    print("\n" + "=" * 50)
    search_meeting_minutes("product development and roadmap", 3)

    print("\n" + "=" * 50)
    search_meeting_minutes("budget and financial planning", 3)
