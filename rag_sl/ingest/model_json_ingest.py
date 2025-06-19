import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import retrieval module
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from langchain_core.documents import Document
from retrieval.vectorstore import get_vectorstore

def ingest_json_data():
    """Ingest job posting data from maya.json into vectorstore."""
    try:
        # Get the path to maya.json
        json_file_path = Path(__file__).parent / "maya.json"
        
        # Step 1: Load the JSON file
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Step 2: Extract entities
        entities = json_data["entities"]

        # Step 3: Prepare the document content
        content = (
            f"Intent: {json_data['intent']}\n"
            f"Company: {entities.get('company_name')}\n"
            f"Title: {entities.get('title')}\n"
            f"Location: {entities.get('location')}\n"
            f"Salary: {entities.get('salary_range')}\n"
            f"Employment: {entities.get('employmentStatus')}\n"
            f"Workplace Type: {', '.join(entities.get('workplaceTypes', []))}\n"
            f"Experience Level: {entities.get('experience_level')}\n"
            f"Skills Required: {', '.join(entities.get('skills_required', []))}\n"
            f"Responsibilities: {', '.join(entities.get('responsibilities', []))}\n"
            f"Qualifications: {', '.join(entities.get('qualifications', []))}\n"
            f"Description: {entities.get('description')}\n"
            f"Apply URL: {entities.get('companyApplyUrl')}"
        )

        # Step 4: Set up metadata for filtering
        metadata = {
            "source": "model",
            "intent": json_data["intent"],
            "company": entities.get("company_name"),
            "title": entities.get("title"),
            "location": entities.get("location"),
            "employmentStatus": entities.get("employmentStatus"),
            "experience_level": entities.get("experience_level"),
            "document_type": "job_posting",
            "external_id": entities.get("externalJobPostingId")
        }

        # Step 5: Create Document and ingest
        doc = Document(page_content=content, metadata=metadata)
        vectorstore = get_vectorstore()
        vectorstore.add_documents([doc])

        print(" maya.json successfully ingested into vectorstore.")
        return True
        
    except Exception as e:
        print(f" Error ingesting JSON data: {e}")
        return False

if __name__ == "__main__":
    ingest_json_data()