from langchain_community.vectorstores import Chroma
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from dotenv import load_dotenv
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Set environment variable for consistency
os.environ["NVIDIA_API_KEY"] = os.getenv("NVIDIA_API_KEY")

def get_vectorstore(
    model_name: str = "nvidia/embed-qa-4",  # Updated to use full model name from your test
    collection_name: str = "rag_chroma",
    chroma_dir: Optional[str] = None,
    create_new: bool = False
):
    """
    Initialize and return the Chroma vectorstore with NVIDIA embeddings.
    
    Args:
        model_name: NVIDIA embedding model to use (default: nvidia/embed-qa-4)
        collection_name: Name for the Chroma collection
        chroma_dir: Directory to store Chroma data (uses env var or default if None)
        create_new: Whether to create a new collection (deletes existing)
    
    Returns:
        Chroma: Initialized vectorstore
        
    Raises:
        ValueError: If API key is missing
        Exception: If vectorstore initialization fails
    """
    try:
        # Validate API key
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("❌ NVIDIA_API_KEY not found in environment variables")
        
        logger.info(f"🔧 Initializing NVIDIA embeddings with model: {model_name}")
        
        # Initialize embeddings with error handling
        try:
            embeddings = NVIDIAEmbeddings(
                model=model_name,
                api_key=api_key
            )
            logger.info("✅ NVIDIA embeddings initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NVIDIA embeddings: {e}")
            logger.info("🔄 Trying with default model...")
            # Fallback to default model
            embeddings = NVIDIAEmbeddings()
        
        # Set up Chroma directory
        if chroma_dir is None:
            chroma_dir = os.getenv("CHROMA_DIR", "./chroma_store")
        
        # Ensure the directory exists
        os.makedirs(chroma_dir, exist_ok=True)
        logger.info(f"📁 Using Chroma directory: {chroma_dir}")
        
        # Handle collection creation/clearing
        if create_new:
            logger.warning(f"🗑️ Creating new collection (will clear existing): {collection_name}")
            import shutil
            if os.path.exists(chroma_dir):
                shutil.rmtree(chroma_dir)
                os.makedirs(chroma_dir, exist_ok=True)
        
        # Initialize vectorstore
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=chroma_dir
        )
        
        # Get collection info
        try:
            collection = vectorstore._collection
            doc_count = collection.count()
            logger.info(f"✅ Vectorstore initialized successfully")
            logger.info(f"📊 Collection '{collection_name}' contains {doc_count} documents")
        except Exception as info_error:
            logger.warning(f"⚠️ Could not retrieve collection info: {info_error}")
        
        return vectorstore
        
    except ValueError as ve:
        logger.error(f"❌ Configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"❌ Error initializing vectorstore: {e}")
        logger.error(f"   Model: {model_name}")
        logger.error(f"   Directory: {chroma_dir}")
        logger.error(f"   Collection: {collection_name}")
        raise

def test_vectorstore_connection(vectorstore: Chroma) -> bool:
    """
    Test the vectorstore with a simple embedding operation.
    
    Args:
        vectorstore: The Chroma vectorstore to test
        
    Returns:
        bool: True if test passes, False otherwise
    """
    try:
        logger.info("🧪 Testing vectorstore connection...")
        
        # Test embedding
        test_text = "This is a test document for vectorstore validation."
        embeddings = vectorstore._embedding_function.embed_query(test_text)
        
        logger.info(f"✅ Vectorstore test passed")
        logger.info(f"   Embedding dimension: {len(embeddings)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Vectorstore test failed: {e}")
        return False

def get_vectorstore_info(vectorstore: Chroma) -> dict:
    """
    Get detailed information about the vectorstore collection.
    
    Args:
        vectorstore: The Chroma vectorstore
        
    Returns:
        dict: Collection information including stats and sample data
    """
    try:
        collection = vectorstore._collection
        
        info = {
            "collection_name": collection.name,
            "document_count": collection.count(),
            "persist_directory": vectorstore._persist_directory,
            "embedding_dimension": None,
            "sample_metadata": None
        }
        
        # Get embedding dimension and sample metadata if documents exist
        if info["document_count"] > 0:
            try:
                sample_results = collection.peek(limit=1)
                if sample_results:
                    # Get embedding dimension
                    if "embeddings" in sample_results and sample_results["embeddings"]:
                        info["embedding_dimension"] = len(sample_results["embeddings"][0])
                    
                    # Get sample metadata
                    if "metadatas" in sample_results and sample_results["metadatas"]:
                        info["sample_metadata"] = sample_results["metadatas"][0]
            except Exception as sample_error:
                logger.warning(f"⚠️ Could not retrieve sample data: {sample_error}")
        
        return info
        
    except Exception as e:
        logger.error(f"❌ Error getting collection info: {e}")
        return {"error": str(e)}

def print_vectorstore_info(vectorstore: Chroma):
    """
    Print formatted information about the vectorstore.
    
    Args:
        vectorstore: The Chroma vectorstore
    """
    info = get_vectorstore_info(vectorstore)
    
    print(f"\n📋 Vectorstore Information:")
    print(f"{'='*50}")
    
    if "error" in info:
        print(f"❌ Error: {info['error']}")
        return
    
    print(f"📁 Collection Name: {info['collection_name']}")
    print(f"📊 Document Count: {info['document_count']}")
    print(f"💾 Directory: {info['persist_directory']}")
    
    if info['embedding_dimension']:
        print(f"🔢 Embedding Dimension: {info['embedding_dimension']}")
    
    if info['sample_metadata']:
        print(f"🏷️  Sample Metadata: {info['sample_metadata']}")

# Example usage functions
def main():
    """Example usage of the vectorstore functions."""
    try:
        # Initialize vectorstore
        print("🚀 Initializing vectorstore...")
        vectorstore = get_vectorstore()
        
        # Test the connection
        if test_vectorstore_connection(vectorstore):
            print("✅ Vectorstore is working correctly")
            
            # Print information
            print_vectorstore_info(vectorstore)
        else:
            print("❌ Vectorstore test failed")
            
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}")

if __name__ == "__main__":
    main()