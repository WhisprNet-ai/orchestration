import sys
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import retrieval module
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from retrieval.vectorstore import get_vectorstore
from langchain_core.documents import Document

def ingest_slack_data():
    """Ingest Slack messages from the API into vectorstore."""
    try:
        load_dotenv()
        
        url = os.getenv("SLACK_DATA_URL")
        if not url:
            print(" SLACK_DATA_URL not found in environment variables")
            return False
            
        vectorstore = get_vectorstore()

        print(" Fetching Slack data...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()  # Raise an exception for bad status codes
        
        data = resp.json()
        
        if "messages" not in data:
            print(" No 'messages' key found in response")
            return False

        docs = []
        for i, msg in enumerate(data["messages"]):
            content = msg.get("text", "")
            if not content.strip():  # Skip empty messages
                continue
                
            metadata = {
    "source": "slack",
    "username": msg.get("username", "unknown"),
    "user_id": msg.get("user_id", ""),
    "app_id": msg.get("app_id", ""),
    "ml_output": msg.get("ml_output", ""),
    "message_index": i,
    "document_type": "slack_message"
}

            docs.append(Document(page_content=content, metadata=metadata))

        if docs:
            vectorstore.add_documents(docs)
            print(f" Ingested {len(docs)} Slack messages.")
            return True
        else:
            print("  No valid messages found to ingest.")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Error fetching Slack data: {e}")
        return False
    except Exception as e:
        print(f"❌ Error ingesting Slack data: {e}")
        return False

if __name__ == "__main__":
    ingest_slack_data()