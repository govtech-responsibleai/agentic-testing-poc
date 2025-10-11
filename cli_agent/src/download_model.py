"""Download and cache the embedding model for faster container builds."""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)


def download_embedding_model() -> SentenceTransformer:
    """Download and cache the all-MiniLM-L6-v2 model."""

    logger.info("Downloading all-MiniLM-L6-v2 model")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = model.encode("This is a test sentence")
    logger.info("Model cached successfully (dim=%s)", len(embedding))
    logger.info("Cache location: %s", model.cache_folder)
    return model


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    download_embedding_model()
