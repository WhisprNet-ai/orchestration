import os
import json
from typing import Dict, Any, Optional
from maya_agent.edit_pipeline import process_edit_feedback, cleanup_edit_workflow

def handle_edit_feedback(user_id: str, username: str, channel_id: str, feedback: str) -> Dict[str, Any]:
    """
    Main function to handle edit feedback from users.
    This integrates the formatter LLM with the Slack poll system.
    """
    try:
        # Process the feedback using the edit pipeline
        result = process_edit_feedback(user_id, username, channel_id, feedback)
        
        if result["status"] == "success":
            action = result.get("action")
            
            if action == "approved":
                # User approved the edited description
                # Return the approved data for LinkedIn posting
                return {
                    "status": "success",
                    "action": "post_to_linkedin",
                    "job_data": result["original_job_data"],
                    "description": result["updated_description"],
                    "job_id": result["job_id"]
                }
                
            elif action == "rejected":
                # User rejected the edit
                # Clean up the edit workflow
                cleanup_edit_workflow(user_id)
                
                return {
                    "status": "success",
                    "action": "edit_rejected",
                    "message": "Edit rejected by user"
                }
                
            elif action == "edit_again":
                # User wants to make more edits
                return {
                    "status": "success",
                    "action": "continue_editing",
                    "message": "User wants to continue editing"
                }
                
            elif action == "drafted":
                # User saved as draft
                return {
                    "status": "success",
                    "action": "saved_as_draft",
                    "job_id": result["job_id"],
                    "message": "Description saved as draft"
                }
            else:
                # Unknown action
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}"
                }
                
        else:
            # Error occurred
            return {
                "status": "error",
                "message": result["message"]
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

def is_edit_feedback(message: str) -> bool:
    """
    Determine if a message is edit feedback based on context and keywords.
    """
    # Simple heuristic - can be improved with more sophisticated NLP
    edit_keywords = [
        "change", "update", "modify", "edit", "revise", "adjust", "fix",
        "title", "skills", "experience", "location", "company", "salary",
        "requirements", "responsibilities", "benefits"
    ]
    
    message_lower = message.lower()
    
    # Check if message contains edit-related keywords
    has_edit_keywords = any(keyword in message_lower for keyword in edit_keywords)
    
    # Check if message seems like feedback (not a new job request)
    is_feedback = (
        has_edit_keywords and
        not any(new_job_indicator in message_lower for new_job_indicator in [
            "new job", "post job", "create job", "hire", "recruit"
        ])
    )
    
    return is_feedback

def extract_edit_intent(message: str) -> Dict[str, Any]:
    """
    Extract edit intent from user message.
    Returns a structured representation of what the user wants to change.
    """
    # This is a simplified version - can be enhanced with more sophisticated NLP
    message_lower = message.lower()
    
    edit_intent = {
        "type": "edit",
        "changes": [],
        "raw_feedback": message
    }
    
    # Simple keyword-based extraction
    if "title" in message_lower:
        edit_intent["changes"].append("job_title")
    if "skills" in message_lower or "technology" in message_lower:
        edit_intent["changes"].append("skills")
    if "experience" in message_lower or "years" in message_lower:
        edit_intent["changes"].append("experience")
    if "location" in message_lower or "remote" in message_lower or "office" in message_lower:
        edit_intent["changes"].append("location")
    if "company" in message_lower:
        edit_intent["changes"].append("company")
    if "salary" in message_lower or "pay" in message_lower:
        edit_intent["changes"].append("salary")
    
    return edit_intent

def validate_edit_feedback(feedback: str) -> Dict[str, Any]:
    """
    Validate edit feedback to ensure it's actionable.
    """
    if not feedback or len(feedback.strip()) < 5:
        return {
            "valid": False,
            "message": "Please provide more specific feedback about what you'd like to change."
        }
    
    # Check if feedback is too vague
    vague_indicators = ["good", "bad", "okay", "fine", "better", "worse"]
    feedback_lower = feedback.lower()
    
    if all(indicator not in feedback_lower for indicator in vague_indicators):
        return {
            "valid": True,
            "message": "Feedback looks good"
        }
    else:
        return {
            "valid": False,
            "message": "Please be more specific about what changes you'd like to make."
        }

def create_edit_summary(original_data: Dict[str, Any], feedback: str, changes_made: str) -> str:
    """
    Create a summary of the edit changes for the user.
    """
    summary = f"📝 *Edit Summary*\n\n"
    summary += f"*Your feedback:* {feedback}\n\n"
    summary += f"*Changes made:* {changes_made}\n\n"
    summary += f"*Original job title:* {original_data.get('job_title', 'N/A')}\n"
    summary += f"*Original skills:* {original_data.get('skills', 'N/A')}\n"
    summary += f"*Original experience:* {original_data.get('experience', 'N/A')}\n"
    
    return summary