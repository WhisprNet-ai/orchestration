from langchain.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from maya_agent.naveens_agent import naveen
import json
import logging
import sqlite3
from datetime import datetime, timedelta
import os
import re

# Initialize logger
logger = logging.getLogger(__name__)

# Database configuration
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'job_drafts.db'))

# Database utility functions
def get_user_drafts(user_id, limit=10):
    """Fetch user's job drafts from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM drafts 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
        
    except Exception as e:
        logger.error(f"Error fetching user drafts: {e}")
        return []

def get_user_edit_requests(user_id, limit=5):
    """Fetch user's edit requests from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM edit_requests 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        edit_requests = []
        for row in rows:
            edit_request = dict(zip(columns, row))
            if edit_request.get('original_job_data'):
                try:
                    edit_request['original_job_data'] = json.loads(edit_request['original_job_data'])
                except:
                    pass
            edit_requests.append(edit_request)
        
        return edit_requests
        
    except Exception as e:
        logger.error(f"Error fetching user edit requests: {e}")
        return []

def delete_user_draft(job_id, user_id):
    """Delete a specific user's draft"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT job_id FROM drafts WHERE job_id = ? AND user_id = ?", (job_id, user_id))
        
        if cursor.fetchone():
            cursor.execute("DELETE FROM drafts WHERE job_id = ? AND user_id = ?", (job_id, user_id))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"Error deleting user draft: {e}")
        return False

def format_draft_for_slack(draft):
    """Format a single draft for display in Slack"""
    job_title = draft.get('job_title', 'Untitled Job')
    company = draft.get('company', 'Unknown Company')
    job_type = draft.get('job_type', 'Not specified')
    experience = draft.get('experience', 'Not specified')
    location = draft.get('location', 'Not specified')
    skills = draft.get('skills', 'Not specified')
    timestamp = draft.get('timestamp', '')
    job_id = draft.get('job_id', 'unknown')
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
    except:
        formatted_date = 'Unknown date'
    
    return f"""🔹 *{job_title}* at {company}
📋 Job ID: {job_id}
💼 Type: {job_type} | 🎯 Experience: {experience}
📍 Location: {location}
🛠 Skills: {skills}
📅 Created: {formatted_date}"""

def handle_past_request(response_dict, user_data, slack_handler):
    """
    Enhanced handle past request pipeline - ONLY displays job titles, no automatic description generation
    """
    print(f"📋 PAST REQUEST detected for user: {user_data.get('username')}")
    
    entities = response_dict.get('entities', {})
    # Remove request_type logic - always show simple job list
    
    channel_id = user_data.get('channel_id')
    user_id = user_data.get('user_id')
    username = user_data.get('username', 'there')
    
    print(f"Channel: {channel_id}, User: {username}")
    
    if not slack_handler or not channel_id:
        print("⚠ No Slack handler available or missing channel_id - cannot post response")
        return
    
    try:
        # Always show simple job list when user asks for past requests
        print(f"📊 Fetching drafts for user {user_id}...")
        drafts = get_user_drafts(user_id, limit=20)  # Get more jobs for better overview
        
        if drafts:
            # Simple job title list format
            message = f"📋 *Your Job Postings* ({len(drafts)} found)\n\n"
            
            for i, draft in enumerate(drafts, 1):
                job_title = draft.get('job_title', 'Untitled Job')
                job_id = draft.get('job_id', 'unknown')
                company = draft.get('company', 'whisprnet.ai')
                job_type = draft.get('job_type', 'Not specified')
                timestamp = draft.get('timestamp', '')
                
                # Format date
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%m/%d/%Y')
                except:
                    formatted_date = 'Unknown'
                
                # Simple one-line format for each job
                message += f"{i}. *{job_title}* ({job_type}) - {job_id} - {formatted_date}\n"
            
            message += f"\n💡 *What you can do:*\n"
            message += f"• Say generate job_id to create job description for a specific posting\n"
            message += f"• Say edit job_id to modify a job posting\n"
            message += f"• Say delete job_id to remove a job posting\n"
            message += f"• Say details job_id to see full job details\n\n"
            message += f"Note: Job descriptions are generated only when you specifically request them."
            
        else:
            message = f"📭 *No Job Postings Found*\n\n" \
                     f"Hi {username}! You don't have any job postings yet.\n\n" \
                     "🚀 *Get Started:*\n" \
                     "• Say something like: \"I need to hire a Python developer\"\n" \
                     "• I'll help you create your first job posting!"
        
        # Post message to Slack
        slack_handler._post_response(
            channel_id=channel_id,
            thread_ts=user_data.get('thread_ts'),
            text=message
        )
        
        print(f"✅ Posted simple job list to Slack for {username}")
        
    except Exception as e:
        print(f"❌ Error in past request handling: {e}")
        logger.error(f"Past request error: {e}")
        
        # Fallback message
        try:
            fallback_msg = f"Hey {username}! I'm having trouble accessing your job posting history right now. " \
                          f"Please try again in a moment! 📋"
            
            slack_handler._post_response(
                channel_id=channel_id,
                thread_ts=user_data.get('thread_ts'),
                text=fallback_msg
            )
        except Exception as fallback_error:
            print(f"❌ Even fallback message failed: {fallback_error}")

def handle_specific_job_action(message_text, user_data, slack_handler):
    """
    Handle specific job actions including new 'generate' and 'details' commands
    """
    user_id = user_data.get('user_id')
    username = user_data.get('username', 'there')
    channel_id = user_data.get('channel_id')
    
    # Updated patterns to include generate and details
    edit_pattern = r'edit\s+([a-zA-Z0-9_]+)'
    delete_pattern = r'delete\s+([a-zA-Z0-9_]+)'
    generate_pattern = r'generate\s+([a-zA-Z0-9_]+)'
    details_pattern = r'details\s+([a-zA-Z0-9_]+)'
    
    edit_match = re.search(edit_pattern, message_text.lower())
    delete_match = re.search(delete_pattern, message_text.lower())
    generate_match = re.search(generate_pattern, message_text.lower())
    details_match = re.search(details_pattern, message_text.lower())
    
    try:
        if generate_match:
            job_id = generate_match.group(1)
            print(f"📝 Generate description request for job_id: {job_id}")
            
            # Get job details first
            drafts = get_user_drafts(user_id, limit=100)
            target_job = next((draft for draft in drafts if draft.get('job_id') == job_id), None)
            
            if target_job:
                # Generate job description using existing naveen system
                job_data = {
                    'job_title': target_job.get('job_title'),
                    'company': target_job.get('company'),
                    'job_type': target_job.get('job_type'),
                    'experience': target_job.get('experience'),
                    'location': target_job.get('location'),
                    'skills': target_job.get('skills'),
                    'expiration_date': target_job.get('expiration_date'),
                    'number_of_people': target_job.get('number_of_people'),
                    'url': target_job.get('url'),
                    'city': target_job.get('city'),
                    'state': target_job.get('state'),
                    'mail': target_job.get('mail'),
                    'education': target_job.get('education')
                }
                
                # Create request dict for naveen system
                request_dict = {
                    'intent': 'hiring_request',
                    'entities': job_data,
                    'user_id': user_data['user_id'],
                    'username': user_data['username'],
                    'app_id': user_data.get('app_id'),
                    'channel_id': user_data['channel_id'],
                    'session_id': user_data.get('session_id', 'default')
                }
                
                # Generate description
                naveen(request_dict)
                
                message = f"✅ *Generating Job Description*\n\n" \
                         f"Creating LinkedIn job description for: *{target_job.get('job_title')}* ({job_id})\n" \
                         f"Please wait a moment..."
            else:
                message = f"❌ *Job Not Found*\n\n" \
                         f"Could not find job {job_id} in your postings.\n" \
                         f"Use show my posts to see available jobs."
            
            slack_handler._post_response(
                channel_id=channel_id,
                thread_ts=user_data.get('thread_ts'),
                text=message
            )
            return True
            
        elif details_match:
            job_id = details_match.group(1)
            print(f"📋 Details request for job_id: {job_id}")
            
            drafts = get_user_drafts(user_id, limit=100)
            target_job = next((draft for draft in drafts if draft.get('job_id') == job_id), None)
            
            if target_job:
                message = f"📋 *Job Details: {target_job.get('job_title', 'Untitled')}*\n\n"
                message += format_draft_for_slack(target_job)
                message += f"\n\n💡 *Available Actions:*\n"
                message += f"• generate {job_id} - Create LinkedIn job description\n"
                message += f"• edit {job_id} - Modify this job posting\n"
                message += f"• delete {job_id} - Remove this job posting"
            else:
                message = f"❌ *Job Not Found*\n\n" \
                         f"Could not find job {job_id} in your postings.\n" \
                         f"Use show my posts to see available jobs."
            
            slack_handler._post_response(
                channel_id=channel_id,
                thread_ts=user_data.get('thread_ts'),
                text=message
            )
            return True
            
        elif delete_match:
            job_id = delete_match.group(1)
            print(f"🗑 Delete request for job_id: {job_id}")
            
            success = delete_user_draft(job_id, user_id)
            
            if success:
                message = f"✅ *Job Deleted Successfully*\n\n" \
                         f"Job {job_id} has been permanently deleted, {username}.\n" \
                         f"This action cannot be undone."
            else:
                message = f"❌ *Delete Failed*\n\n" \
                         f"Could not delete job {job_id}. Possible reasons:\n" \
                         f"• Job ID doesn't exist\n" \
                         f"• Job doesn't belong to you\n" \
                         f"• Database error\n\n" \
                         f"Try show my posts to see your available jobs."
            
            slack_handler._post_response(
                channel_id=channel_id,
                thread_ts=user_data.get('thread_ts'),
                text=message
            )
            return True
            
        elif edit_match:
            job_id = edit_match.group(1)
            print(f"✏ Edit request for job_id: {job_id}")
            
            drafts = get_user_drafts(user_id, limit=100)
            target_job = next((draft for draft in drafts if draft.get('job_id') == job_id), None)
            
            if target_job:
                message = f"✏ *Edit Job: {target_job.get('job_title', 'Untitled')}*\n\n"
                message += format_draft_for_slack(target_job)
                message += f"\n\n💡 *To edit this job:*\n"
                message += f"Please tell me what you'd like to change. For example:\n"
                message += f"• \"Change the title to Senior Developer\"\n"
                message += f"• \"Update location to Remote\"\n"
                message += f"• \"Add React to required skills\"\n\n"
                message += f"I'll help you update job {job_id}!"
            else:
                message = f"❌ *Job Not Found*\n\n" \
                         f"Could not find job {job_id} in your postings.\n" \
                         f"Try show my posts to see your available jobs."
            
            slack_handler._post_response(
                channel_id=channel_id,
                thread_ts=user_data.get('thread_ts'),
                text=message
            )
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error handling specific job action: {e}")
        logger.error(f"Specific job action error: {e}")
        return False



def handle_hiring_request(response_dict, user_data, slack_handler):
    """Handle new hiring request (existing logic with enhancements)"""
    print(f"💼 HIRING REQUEST detected for user: {user_data.get('username')}")
    
    try:
        # Add company details (existing logic)
        response_dict['entities']['company'] = 'whisprnet.ai'
        response_dict['entities']['url'] = 'http://linkedin.com'
        response_dict['entities']['city'] = 'pondicherry'
        response_dict['entities']['state'] = 'pondicherry'
        response_dict['entities']['mail'] = 'careers@whisprnet.ai'
        response_dict['entities']['education'] = 'btech/mtech'
        
        # Add user metadata
        response_dict["user_id"] = user_data["user_id"]
        response_dict["username"] = user_data["username"]
        response_dict["app_id"] = user_data["app_id"]
        response_dict["channel_id"] = user_data["channel_id"]
        response_dict["session_id"] = user_data.get("session_id", "default")
        
        print(f"📤 Sending to job posting system for {user_data.get('username')}")
        
        # Send to job posting system
        naveen(response_dict)
        
        # Send confirmation to Slack
        if slack_handler and user_data.get('channel_id'):
            confirmation_msg = f"✅ Got it {user_data.get('username')}! I'm processing your job posting request..."
            slack_handler._post_response(
                channel_id=user_data['channel_id'],
                thread_ts=user_data.get('thread_ts'),
                text=confirmation_msg
            )
        
        print(f"✅ Hiring request processed successfully for {user_data.get('username')}")
        
    except Exception as e:
        print(f"❌ Error processing hiring request: {e}")
        logger.error(f"Hiring request processing error: {e}")
        
        # Send error message to user
        if slack_handler and user_data.get('channel_id'):
            error_msg = f"Sorry {user_data.get('username', '')}, I encountered an issue processing your job posting. Please try again!"
            slack_handler._post_response(
                channel_id=user_data['channel_id'],
                thread_ts=user_data.get('thread_ts'),
                text=error_msg
            )

def handle_non_hiring_request(response_dict, user_data, slack_handler):
    """Handle non-hiring requests - general questions, support, etc."""
    username = user_data.get('username', 'there')
    print(f"ℹ NON-HIRING request from {username}")
    
    # Send a helpful response for non-hiring requests
    if slack_handler and user_data.get('channel_id'):
        try:
            help_msg = f"Hi {username}! 👋\n\n" \
                      "I'm here to help with job posting requests. I can:\n" \
                      "• 💼 Create new job postings\n" \
                      "• 📋 Show your past job requests\n" \
                      "• ✏ Edit existing postings\n" \
                      "• 🗑 Delete old postings\n\n" \
                      "How can I assist you with your hiring needs?"
            
            slack_handler._post_response(
                channel_id=user_data['channel_id'],
                thread_ts=user_data.get('thread_ts'),
                text=help_msg
            )
            
            print(f"✅ Sent help message to {username}")
            
        except Exception as e:
            print(f"❌ Error sending help message: {e}")

def intent_entity_processor(data, slack_handler=None): 
    """Enhanced intent entity processor that handles hiring requests, past requests, and non-hiring intents"""
    for list_item in data:
        message = list_item['response']
        
        # First check for specific job actions (edit job_123, delete job_456)
        if slack_handler and handle_specific_job_action(message, list_item, slack_handler):
            print(f"✅ Handled specific job action for: {message}")
            continue
        
        print(f"\nProcessing user: {list_item.get('username', 'Unknown')}")
        print(f"Message: {message}")
        
        intent_entity_response = intent_entity_extractor(message)
        print(f"Raw intent extraction: {intent_entity_response}")
        
        try:
            response_dict = json.loads(intent_entity_response)
            print(f"Parsed entities: {response_dict.get('entities', {})}")
            
            intent = response_dict.get('intent', 'non_hiring')
            print(f"Detected intent: {intent}")
            
            if intent == 'past_request':
                print("🔄 Routing to database-powered past request handler...")
                handle_past_request(response_dict, list_item, slack_handler)
                
            elif intent == 'hiring_request':
                print("💼 Routing to hiring request handler...")
                handle_hiring_request(response_dict, list_item, slack_handler)
                
            else:
                print(f"ℹ Non-hiring intent detected for user {list_item.get('username')}")
                handle_non_hiring_request(response_dict, list_item, slack_handler)
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse intent extraction JSON: {e}")
            print(f"Raw response: {intent_entity_response}")
            
            if slack_handler and list_item.get('channel_id'):
                slack_handler._post_response(
                    channel_id=list_item['channel_id'],
                    thread_ts=None,
                    text=f"Sorry {list_item.get('username', '')}, I had trouble understanding your request. Could you please rephrase it?"
                )
                
        except Exception as e:
            print(f"❌ Error in intent processing: {e}")
            logger.error(f"Intent processing error: {e}")
    
    print("="*80)
    print("INTENT ENTITY PROCESSOR - Completed")
    print("="*80)

def intent_entity_extractor(message):
    """Extract intent and entities from user message - simplified for job title display"""
    print("🔍 Processing intent entity extraction...")
    print(f"Input message: {message}")
    print("####")
    
    # Simplified prompt template - removed request_type complexity
    prompt = ChatPromptTemplate.from_template("""
    CONVERSATION:
    {message_batch}

    TASK: Analyze the conversation and extract the following information in JSON format:

    {{
     "intent": "hiring_request" | "past_request" | "non_hiring",
     "entities": {{
         "job_title": "exact job title mentioned or null",
         "skills": "comma-separated list of required skills or null",
         "experience": "experience requirement (e.g., '3+ years', 'Senior level') or null",
         "location": "job location (city, state, hybrid) or null",
         "job_type": "employment type (full-time, part-time, remote, contract, internship) or null",
         "expiration_date": "application deadline if mentioned or null",
         "number_of_people": "number of positions to fill or null"
     }}
     }}

    GUIDELINES:
    - Set intent to "hiring_request" if discussing NEW job postings, recruitment, or hiring needs
    - Set intent to "past_request" if asking about PREVIOUS/OLD job postings, viewing history, or retrieving past requests
    - Set intent to "non_hiring" for general questions, support issues, or non-recruitment topics
    
    - Extract entities ONLY if explicitly mentioned - use null for missing information
    - For skills, include both technical and soft skills mentioned
    - For experience, capture years, level (junior/senior), or specific requirements
    - For location, include remote work arrangements if mentioned
    - Be precise - don't infer or assume information not explicitly stated

    PAST REQUEST INDICATORS (should trigger "past_request" intent):
    - "show me my old posts", "previous job postings", "past requests"
    - "my previous", "old job postings", "earlier requests"
    - "view my drafts", "see my posted jobs", "job history"
    - "show my posts", "list my jobs"

    HIRING REQUEST INDICATORS (should trigger "hiring_request" intent):
    - "I need to hire", "looking for", "recruiting", "job opening"
    - "need someone for", "hiring for position", "post a job"
    - Mentioning specific job titles, skills, requirements
    - "full-time", "part-time", "remote work", "contract position"

    NON-HIRING INDICATORS (should trigger "non_hiring" intent):
    - General greetings: "hello", "hi", "how are you"
    - Support questions: "help", "how does this work", "what can you do"
    - Unrelated topics that don't involve jobs or hiring

    RESPONSE: Return only valid JSON, no additional text:
    """)

    # Setup NVIDIA LLM
    formatter_llm = ChatNVIDIA(
        model="meta/llama3-70b-instruct",
        api_key="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"
    )

    try:
        # Format the prompt
        formatted_prompt = prompt.format_messages(message_batch=message)

        # Invoke the model
        response = formatter_llm.invoke(formatted_prompt)

        print("🤖 LLM Response:")
        print(response.content)
        
        return response.content
        
    except Exception as e:
        print(f"❌ Error in LLM processing: {e}")
        logger.error(f"LLM processing error: {e}")
        
        # Return fallback response
        fallback_response = {
            "intent": "non_hiring",
            "entities": {
                "job_title": None,
                "skills": None,
                "experience": None,
                "location": None,
                "job_type": None,
                "expiration_date": None,
                "number_of_people": None
            }
        }
        return json.dumps(fallback_response)

# Integration function for SlackHandler
def integrate_with_slack_handler():
    """Returns a function that can replace the _process_messages method in SlackHandler"""
    def enhanced_process_messages(self, channel_id: str, thread_ts, messages: list) -> None:
        """Enhanced process messages with past request handling"""
        try:
            from typing import Optional
            thread_display = thread_ts or 'main'
            print(f"🚀 Starting enhanced processing for {len(messages)} messages in {channel_id}/{thread_display}")
            
            # Convert messages to the format expected by intent_entity_processor
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    'username': msg.username,
                    'user_id': msg.user_id,
                    'channel_id': channel_id,
                    'thread_ts': thread_ts,
                    'app_id': getattr(msg, 'app_id', None),
                    'session_id': getattr(msg, 'session_id', 'default'),
                    'response': msg.text
                }
                formatted_messages.append(formatted_msg)
            
            print(f"📤 Processing {len(formatted_messages)} formatted messages through intent detector...")
            
            # Process through enhanced intent detector
            intent_entity_processor(formatted_messages, slack_handler=self)
            
            # Continue with existing ML processing if needed (optional)
            try:
                if hasattr(self, 'ml_processor') and self.ml_processor:
                    ml_response = self.ml_processor.process_messages(messages)
                    print(f"✅ ML processing successful for {channel_id}/{thread_display}")
                    
                    # Update message store with ML output
                    if hasattr(self, 'message_store') and self.message_store:
                        self.message_store.update_ml_output(channel_id, thread_ts, ml_response)
                
            except Exception as e:
                print(f"⚠ ML processing failed for {channel_id}/{thread_display}: {e}")
                # Don't fail the entire process if ML fails
            
            # Remove processed messages from store
            if hasattr(self, 'message_store') and self.message_store:
                removed_messages = self.message_store.remove_messages(channel_id, thread_ts)
                print(f"🧹 Removed {len(removed_messages)} messages from store after processing")
            
            print(f"✅ Enhanced processing completed for {channel_id}/{thread_display}")
            
        except Exception as e:
            print(f"❌ Error in enhanced processing for {channel_id}/{thread_ts}: {e}")
            logger.error(f"Enhanced processing error: {e}")
    
    return enhanced_process_messages

# Test function for database integration
def test_database_integration():
    """Test function to verify database integration works correctly"""
    test_user_id = "test_user_123"
    
    print("\n" + "="*60)
    print("TESTING DATABASE INTEGRATION")
    print("="*60)
    
    # Test fetching drafts
    drafts = get_user_drafts(test_user_id, limit=5)
    print(f"Found {len(drafts)} drafts for test user")
    
    for draft in drafts:
        print(f"- {draft.get('job_title', 'Unknown')} ({draft.get('job_id', 'unknown')})")
    
    # Test edit requests
    edit_requests = get_user_edit_requests(test_user_id, limit=3)
    print(f"Found {len(edit_requests)} edit requests for test user")
    
    print("Database integration test completed")

# Test function for intent extraction
def test_intent_extraction():
    """Test function to verify intent extraction works correctly"""
    test_messages = [
        "I need to hire a Python developer",
        "Show me my old job posts",
        "Edit my last job posting",
        "Hello, how are you?",
        "Delete my previous job",
        "Looking for a full-time React developer with 3 years experience",
        "List all my jobs",
        "edit job_123",
        "delete job_456"
    ]
    
    print("\n" + "="*60)
    print("TESTING INTENT EXTRACTION")
    print("="*60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: '{message}'")
        result = intent_entity_extractor(message)
        try:
            parsed = json.loads(result)
            print(f"Intent: {parsed.get('intent')}")
            print(f"Request Type: {parsed.get('entities', {}).get('request_type')}")
        except:
            print("Failed to parse result")
        print("-" * 40)

# Example usage and module initialization
if __name__ == "__main__":
    print("Enhanced Extractor with Database Integration loaded!")
    print("Features:")
    print("• Intent detection (hiring_request, past_request, non_hiring)")
    print("• Database integration for job postings")
    print("• Specific job actions (edit job_123, delete job_456)")
    print("• Smart Slack responses with real data")
    
    # Uncomment to test
    # test_database_integration()
    # test_intent_extraction()
else:
    # Module loaded via import
    print("📋 Extractor module imported successfully")
    print("✅ Ready to process intents and manage job postings")