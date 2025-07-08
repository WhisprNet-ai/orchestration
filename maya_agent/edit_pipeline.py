import os
import json
import uuid
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from maya_agent.database import insert_edit_request, get_edit_request, update_edit_status, delete_edit_request
from maya_agent.slack_button import send_job_desc

# Load environment variables
load_dotenv()

def get_vectorstore():
    """Get the Chroma vectorstore instance"""
    embeddings = NVIDIAEmbeddings(
        model="nvidia/embed-qa-4",
        api_key=os.getenv("NVIDIA_API_KEY")
    )
    persist_directory = os.getenv("CHROMA_DIR", "./chroma_store")
    return Chroma(
        collection_name="rag_chroma",
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

def store_job_description_for_edit(user_id: str, job_description: str):
    """Store job description in vectorstore for editing"""
    try:
        vectorstore = get_vectorstore()
        
        # Wrap the job description in a Document with metadata
        doc = Document(page_content=job_description, metadata={"user_id": user_id})
        vectorstore.add_documents([doc])
        
        return {"status": "success", "message": "Job description stored for editing"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_job_description_from_vectorstore(user_id: str) -> Optional[str]:
    """Retrieve job description from vectorstore"""
    try:
        vectorstore = get_vectorstore()
        job_docs = vectorstore.get(where={"user_id": user_id})
        
        if job_docs['documents']:
            return job_docs['documents'][0]
        else:
            return None
    except Exception as e:
        print(f"Error retrieving job description: {e}")
        return None

def format_job_description_with_llm(original_description: str, user_feedback: str) -> str:
    """Use the formatter LLM to update job description based on user feedback"""
    try:
        formatter_llm = ChatNVIDIA(
            model="meta/llama3-70b-instruct",
            api_key=os.getenv("NVIDIA_API_KEY")
        )

        # Prompt template for editing
        edit_prompt = ChatPromptTemplate.from_template("""You are a smart rewriting assistant.

Use the user's feedback to update the given job description accordingly.

Instructions:
- ONLY update fields like title, skills, experience, or location based on the feedback.
- DO NOT add fictional or speculative information.
- MAINTAIN original job formatting, professionalism, and clarity.
- Your output should start *directly with the revised job description*. Do NOT include introductory text.

User's Feedback:
{feedback}

Original Job Description:
{job_desc}

Updated Job Description:
""")

        # Generate updated description
        updated_description = formatter_llm.invoke(
            edit_prompt.format(feedback=user_feedback, job_desc=original_description)
        ).content

        return str(updated_description).strip()

    except Exception as e:
        print(f"Error in LLM formatting: {e}")
        return original_description

def initiate_edit_workflow(job_id: str, user_id: str, username: str, channel_id: str, 
                          job_data: Dict[str, Any], description: str) -> Dict[str, Any]:
    """Initiate the edit workflow"""
    try:
        # Store original data in database
        insert_edit_request(job_id, user_id, username, channel_id, job_data, description)
        
        # Store job description in vectorstore
        store_result = store_job_description_for_edit(user_id, description)
        
        if store_result["status"] == "success":
            # Send message to user asking for feedback
            message = f"✏ <@{user_id}>, I'm ready to help you edit the job description. Please tell me what changes you'd like to make (e.g., 'Change the title to Senior Developer' or 'Update skills to include React')."
            # Note: send_slack_message will be handled by the main agent
            
            return {
                "status": "success",
                "message": "Edit workflow initiated",
                "job_id": job_id
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to store job description: {store_result['message']}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initiate edit workflow: {str(e)}"
        }

def process_edit_feedback(user_id: str, username: str, channel_id: str, feedback: str) -> Dict[str, Any]:
    """Process user feedback and generate updated job description"""
    try:
        # Get original job description from vectorstore
        original_description = get_job_description_from_vectorstore(user_id)
        
        if not original_description:
            return {
                "status": "error",
                "message": "No job description found for editing"
            }
        
        # Get edit request from database
        edit_request = get_edit_request_by_user_id(user_id)
        if not edit_request:
            return {
                "status": "error",
                "message": "No edit request found"
            }
        
        # Update status to processing
        update_edit_status(edit_request['job_id'], 'processing')
        
        # Generate updated description using LLM
        updated_description = format_job_description_with_llm(original_description, feedback)
        
        # Create new job_id for the updated version
        new_job_id = str(uuid.uuid4())[:8]
        
        # Send updated description to Slack for approval
        action = send_job_desc(channel_id, updated_description, new_job_id, username, user_id)
        
        if action == "approve":
            # User approved the edit
            update_edit_status(edit_request['job_id'], 'completed')
            delete_edit_request(edit_request['job_id'])
            
            return {
                "status": "success",
                "action": "approved",
                "job_id": new_job_id,
                "updated_description": updated_description,
                "original_job_data": edit_request['original_job_data']
            }
            
        elif action == "reject":
            # User rejected the edit
            update_edit_status(edit_request['job_id'], 'pending')
            delete_edit_request(edit_request['job_id'])
            
            return {
                "status": "success",
                "action": "rejected",
                "message": "Edit rejected by user"
            }
            
        elif action == "edit":
            # User wants to edit further
            update_edit_status(edit_request['job_id'], 'pending')
            
            return {
                "status": "success",
                "action": "edit_again",
                "message": "User wants to edit further"
            }
            
        elif action == "draft":
            # User wants to save as draft
            from maya_agent.database import insert_draft
            insert_draft(
                job_id=new_job_id,
                user_id=user_id,
                username=username,
                channel_id=channel_id,
                job_data=edit_request['original_job_data'],
                description=updated_description
            )
            update_edit_status(edit_request['job_id'], 'completed')
            delete_edit_request(edit_request['job_id'])
            
            return {
                "status": "success",
                "action": "drafted",
                "job_id": new_job_id,
                "message": "Updated description saved as draft"
            }
        else:
            # Default case for unknown action
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process edit feedback: {str(e)}"
        }

def get_edit_request_by_user_id(user_id: str):
    """Get edit request by user_id (assuming one active edit per user)"""
    import sqlite3
    import json
    from maya_agent.database import DB_FILE
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM edit_requests WHERE user_id = ? AND edit_status IN ('pending', 'processing') ORDER BY timestamp DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
        # Parse the JSON string back to dict
        result['original_job_data'] = json.loads(result['original_job_data'])
        return result
    else:
        return None

def cleanup_edit_workflow(user_id: str):
    """Clean up edit workflow data"""
    try:
        # Delete from vectorstore
        vectorstore = get_vectorstore()
        collection = vectorstore._collection
        collection.delete(where={"user_id": user_id})
        
        # Delete from database
        edit_request = get_edit_request_by_user_id(user_id)
        if edit_request:
            delete_edit_request(edit_request['job_id'])
        
        return {"status": "success", "message": "Edit workflow cleaned up"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to cleanup: {str(e)}"}