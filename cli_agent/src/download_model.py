"""
Download and cache the embedding model for faster container builds
"""
from sentence_transformers import SentenceTransformer
import os

def download_embedding_model():
    """Download and cache the all-MiniLM-L6-v2 model"""
    print("🔄 Downloading all-MiniLM-L6-v2 model...")
    
    # This will download and cache the model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Test it works
    test_text = "This is a test sentence"
    embedding = model.encode(test_text)
    
    print(f"✅ Model downloaded and cached successfully!")
    print(f"   Embedding dimension: {len(embedding)}")
    print(f"   Cache location: {model.cache_folder}")
    
    return model

if __name__ == "__main__":
    download_embedding_model()
