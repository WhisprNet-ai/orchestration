"""
Script to check available NVIDIA AI models for embeddings and chat
"""
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, ChatNVIDIA
from dotenv import load_dotenv
import os

def check_available_models():
    """Check and display available NVIDIA models"""
    load_dotenv()
    
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("❌ NVIDIA_API_KEY not found in environment variables")
        return
    
    print("🔍 Checking available NVIDIA models...")
    print("=" * 50)
    
    try:
        # Check available embedding models
        print("\n📊 Available Embedding Models:")
        print("-" * 30)
        
        # Try to get available models for embeddings
        try:
            embedding_models = NVIDIAEmbeddings.get_available_models()
            for i, model in enumerate(embedding_models, 1):
                print(f"{i}. {model}")
        except Exception as e:
            print(f"Could not fetch embedding models: {e}")
            
        # Check available chat models
        print("\n💬 Available Chat Models:")
        print("-" * 30)
        
        try:
            chat_models = ChatNVIDIA.get_available_models()
            for i, model in enumerate(chat_models, 1):
                print(f"{i}. {model}")
        except Exception as e:
            print(f"Could not fetch chat models: {e}")
            
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        
    # Test some common embedding models
    print("\n🧪 Testing Common Embedding Models:")
    print("-" * 40)
    
    common_embedding_models = [
        "nvidia/embed-qa-4",
        "nvidia/nv-embed-v1",
        "nvidia/nv-embedqa-e5-v5",
        "NV-Embed-QA",
        "nvolveqa_40k",
        "nv-embed-v1"
    ]
    
    for model in common_embedding_models:
        try:
            embeddings = NVIDIAEmbeddings(model=model, api_key=api_key)
            print(f"✅ {model} - Working")
            # Test with a simple embedding
            test_result = embeddings.embed_query("test")
            print(f"   Embedding dimension: {len(test_result)}")
            break  # Stop at first working model
        except Exception as e:
            print(f"❌ {model} - Error: {str(e)[:100]}...")
    
    # Test some common chat models
    print("\n🧪 Testing Common Chat Models:")
    print("-" * 40)
    
    common_chat_models = [
        "meta/llama3-8b-instruct",
        "meta/llama-3.1-8b-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1",
        "nvidia/llama3-chatqa-1.5-8b"
    ]
    
    for model in common_chat_models:
        try:
            llm = ChatNVIDIA(model=model, api_key=api_key)
            print(f"✅ {model} - Working")
            # Test with a simple query
            response = llm.invoke("Hello")
            print(f"   Response: {str(response.content)[:50]}...")
            break  # Stop at first working model
        except Exception as e:
            print(f"❌ {model} - Error: {str(e)[:100]}...")

if __name__ == "__main__":
    check_available_models()