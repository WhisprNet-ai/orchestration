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

def format_draft_summary(draft):
    """Format a draft for summary display - shows only job_title, job_id, timestamp"""
    job_title = draft.get('job_title', 'Untitled Job')
    job_id = draft.get('job_id', 'unknown')
    timestamp = draft.get('timestamp', '')
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
    except:
        formatted_date = 'Unknown date'
    
    return f"• **{job_title}** (`{job_id}`) - {formatted_date}"

def format_draft_detailed(draft):
    """Format a draft for detailed display - shows all information except description"""
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
    
    return f"""🔹 **{job_title}** at {company}
📋 Job ID: `{job_id}`
💼 Type: {job_type} | 🎯 Experience: {experience}
📍 Location: {location}
🛠️ Skills: {skills}
📅 Created: {formatted_date}"""

def format_draft_with_description(draft):
    """Format a draft with full details including description for hiring-style display"""
    job_title = draft.get('job_title', 'Untitled Job')
    company = draft.get('company', 'Unknown Company')
    job_type = draft.get('job_type', 'Not specified')
    experience = draft.get('experience', 'Not specified')
    location = draft.get('location', 'Not specified')
    skills = draft.get('skills', 'Not specified')
    timestamp = draft.get('timestamp', '')
    job_id = draft.get('job_id', 'unknown')
    description = draft.get('description', 'No description available')
    number_of_people = draft.get('number_of_people', 'Not specified')
    expiration_date = draft.get('expiration_date', 'Not specified')
    education = draft.get('education', 'Not specified')
    mail = draft.get('mail', 'Not specified')
    url = draft.get('url', 'Not specified')
    city = draft.get('city', 'Not specified')
    state = draft.get('state', 'Not specified')
    
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
    except:
        formatted_date = 'Unknown date'
    
    return f"""🚀 **{job_title}** at {company}
📋 Job ID: `{job_id}`

**📄 Job Details:**
💼 Type: {job_type}
🎯 Experience: {experience}
📍 Location: {location} ({city}, {state})
🛠️ Skills: {skills}
👥 Positions: {number_of_people}
🎓 Education: {education}
⏰ Application Deadline: {expiration_date}
📧 Contact: {mail}
🔗 Apply: {url}
📅 Posted: {formatted_date}

**📝 Description:**
{description}"""

def format_draft_for_slack(draft):
    """Backward compatibility function - uses summary format by default"""
    return format_draft_summary(draft)

def handle_specific_job_action(message_text, user_data, slack_handler):
    """Enhanced handler for specific job actions with different display formats"""
    user_id = user_data.get('user_id')
    username = user_data.get('username', 'there')
    channel_id = user_data.get('channel_id')
    
    print(f"🔍 Checking specific job action for message: '{message_text}'")
    
    # Patterns that match both job_xxx and xxx formats, with optional space or underscore
    edit_pattern = r'edit[\s_]+(job_)?([a-zA-Z0-9_]{4,})'
    delete_pattern = r'delete[\s_]+(job_)?([a-zA-Z0-9_]{4,})'
    show_pattern = r'show[\s_]+(job_)?([a-zA-Z0-9_]{4,})'  # Pattern for showing specific jobs
    
    edit_match = re.search(edit_pattern, message_text.lower())
    delete_match = re.search(delete_pattern, message_text.lower())
    show_match = re.search(show_pattern, message_text.lower())
    
    print(f"🔍 Pattern matches - Edit: {edit_match}, Delete: {delete_match}, Show: {show_match}")
    
    try:
        if delete_match:
            job_id = delete_match.group(2)  # Get the actual job_id (second group)
            print(f"🗑️ Delete request for job_id: {job_id}")
            
            success = delete_user_draft(job_id, user_id)
            
            if success:
                message = f"✅ **Job Deleted Successfully**\n\n" \
                         f"Job `{job_id}` has been permanently deleted, {username}.\n" \
                         f"This action cannot be undone."
            else:
                message = f"❌ **Delete Failed**\n\n" \
                         f"Could not delete job `{job_id}`. Possible reasons:\n" \
                         f"• Job ID doesn't exist\n" \
                         f"• Job doesn't belong to you\n" \
                         f"• Database error\n\n" \
                         f"Try `show my posts` to see your available jobs."
            
            slack_handler._post_response(
                channel_id=channel_id,
                thread_ts=user_data.get('thread_ts'),
                text=message
            )
            return True
            
        elif show_match:
            job_id = show_match.group(2)  # Get the actual job_id (second group)
            print(f"👁️ Show request for job_id: {job_id}")
            
            drafts = get_user_drafts(user_id, limit=100)
            target_job = next((draft for draft in drafts if draft.get('job_id') == job_id), None)
            
            if target_job:
                # Get the job description
                description = target_job.get('description', 'No description available')
                
                # Call send_job_desc to show the job with approval buttons
                try:
                    from maya_agent.slack_button import send_job_desc
                    action = send_job_desc(channel_id, description, job_id, username, user_id)
                    
                    # Handle the user's response - same logic as in naveens_agent.py
                    if action == "approve":
                        print("✅ Approved by user. Proceeding to LinkedIn...")
                        # Delete user data from vectorstore
                        try:
                            from maya_agent.naveens_agent import delete_user_data
                            delete_user_data(user_id)
                        except Exception as e:
                            print(f"❌ Error deleting user data: {e}")
                        
                        # Post to LinkedIn
                        try:
                            from maya_agent.naveens_agent import post_job_to_linkedin
                            # Create a state object similar to what post_job_to_linkedin expects
                            job_data = target_job.copy()
                            job_data["llm_description"] = description
                            
                            # Call LinkedIn posting function
                            post_result = post_job_to_linkedin({"job_data": job_data, "error": None, "job_result": "", "edit_workflow_active": None})
                            
                            job_result = post_result.get("job_result", "")
                            if "✅ Posted:" in job_result:
                                # Extract the LinkedIn URL from the result
                                if "https://www.linkedin.com/feed/update/" in job_result:
                                    # Extract the URL from the result
                                    url_match = re.search(r'https://www\.linkedin\.com/feed/update/[^\s]+', job_result)
                                    if url_match:
                                        linkedin_url = url_match.group(0)
                                        message = f"✅ <@{user_id}>, your job has been posted to LinkedIn successfully!\n\n🔗 **LinkedIn Post:** {linkedin_url}"
                                    else:
                                        message = f"✅ <@{user_id}>, your job has been posted to LinkedIn successfully!"
                                else:
                                    message = f"✅ <@{user_id}>, your job has been posted to LinkedIn successfully!"
                            else:
                                message = f"❌ <@{user_id}>, there was an error posting to LinkedIn: {job_result}"
                        except Exception as e:
                            print(f"❌ Error posting to LinkedIn: {e}")
                            message = f"❌ <@{user_id}>, there was an error posting to LinkedIn."
                        
                        slack_handler._post_response(
                            channel_id=channel_id,
                            thread_ts=user_data.get('thread_ts'),
                            text=message
                        )
                        
                    elif action == "reject":
                        print("🧹 User rejected. Resetting memory and halting job.")
                        # Delete user data from vectorstore
                        try:
                            from maya_agent.naveens_agent import delete_user_data
                            delete_user_data(user_id)
                        except Exception as e:
                            print(f"❌ Error deleting user data: {e}")
                        
                        message = f"❌ <@{user_id}>, I've canceled the posting and cleared your data."
                        slack_handler._post_response(
                            channel_id=channel_id,
                            thread_ts=user_data.get('thread_ts'),
                            text=message
                        )
                        
                    elif action == "edit":
                        print("User clicked edit, initiating edit workflow")
                        try:
                            from maya_agent.edit_pipeline import initiate_edit_workflow
                            edit_result = initiate_edit_workflow(
                                job_id=job_id,
                                user_id=user_id,
                                username=username,
                                channel_id=channel_id,
                                job_data=target_job,
                                description=description
                            )
                            
                            if edit_result["status"] == "success":
                                message = f"✏️ <@{user_id}>, I'm ready to help you edit the job description. Please tell me what changes you'd like to make (e.g., 'Change the title to Senior Developer' or 'Update skills to include React')."
                            else:
                                message = f"❌ <@{user_id}>, failed to initiate edit: {edit_result['message']}"
                        except Exception as e:
                            print(f"❌ Error initiating edit workflow: {e}")
                            message = f"❌ <@{user_id}>, there was an error setting up the edit workflow."
                        
                        slack_handler._post_response(
                            channel_id=channel_id,
                            thread_ts=user_data.get('thread_ts'),
                            text=message
                        )
                        
                    elif action == "draft":
                        print("User selected draft, saving as draft")
                        try:
                            from maya_agent.database import insert_draft
                            # The job is already in the database, so we just need to confirm
                            draft_confirmation = f"✅ <@{user_id}>, this job is already saved as a draft!\n\n" \
                                               f"📋 **Draft Details:**\n" \
                                               f"• Job Title: {target_job.get('job_title', 'N/A')}\n" \
                                               f"• Company: {target_job.get('company', 'N/A')}\n" \
                                               f"• Job ID: `{job_id}`\n\n" \
                                               f"💡 **To manage your drafts:**\n" \
                                               f"• Say \"show my posts\" to view all your drafts\n" \
                                               f"• Say \"edit {job_id}\" to modify this draft\n" \
                                               f"• Say \"delete {job_id}\" to remove this draft"
                        except Exception as e:
                            print(f"❌ Error handling draft action: {e}")
                            draft_confirmation = f"📋 <@{user_id}>, this job is already saved as a draft with ID `{job_id}`."
                        
                        slack_handler._post_response(
                            channel_id=channel_id,
                            thread_ts=user_data.get('thread_ts'),
                            text=draft_confirmation
                        )
                        
                    else:
                        message = f"ℹ️ <@{user_id}>, job `{job_id}` displayed successfully."
                        slack_handler._post_response(
                            channel_id=channel_id,
                            thread_ts=user_data.get('thread_ts'),
                            text=message
                        )
                except Exception as e:
                    print(f"❌ Error calling send_job_desc: {e}")
                    # Fallback to direct message if send_job_desc fails
                    message = f"📋 **Job Details for {job_id}**\n\n"
                    message += format_draft_with_description(target_job)
                    message += f"\n\n💡 **Actions Available:**\n"
                    message += f"• `edit {job_id}` - Modify this job\n"
                    message += f"• `delete {job_id}` - Remove this job"
                    
                    slack_handler._post_response(
                        channel_id=channel_id,
                        thread_ts=user_data.get('thread_ts'),
                        text=message
                    )
            else:
                message = f"❌ **Job Not Found**\n\n" \
                         f"Could not find job `{job_id}` in your postings.\n" \
                         f"Try `show my posts` to see your available jobs."
                
                slack_handler._post_response(
                    channel_id=channel_id,
                    thread_ts=user_data.get('thread_ts'),
                    text=message
                )
            return True
            
        elif edit_match:
            job_id = edit_match.group(2)  # Get the actual job_id (second group)
            print(f"✏️ Edit request for job_id: {job_id}")
            
            drafts = get_user_drafts(user_id, limit=100)
            target_job = next((draft for draft in drafts if draft.get('job_id') == job_id), None)
            
            if target_job:
                # Use detailed format for edit preview
                message = f"✏️ **Edit Job: {target_job.get('job_title', 'Untitled')}**\n\n"
                message += format_draft_detailed(target_job)
                message += f"\n\n💡 **To edit this job:**\n"
                message += f"Please tell me what you'd like to change. For example:\n"
                message += f"• \"Change the title to Senior Developer\"\n"
                message += f"• \"Update location to Remote\"\n"
                message += f"• \"Add React to required skills\"\n\n"
                message += f"I'll help you update job `{job_id}`!"
            else:
                message = f"❌ **Job Not Found**\n\n" \
                         f"Could not find job `{job_id}` in your postings.\n" \
                         f"Try `show my posts` to see your available jobs."
            
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

def handle_past_request(response_dict, user_data, slack_handler):
    """Enhanced handle past request with different formatting based on request type"""
    print(f"📋 PAST REQUEST detected for user: {user_data.get('username')}")
    
    entities = response_dict.get('entities', {})
    request_type = entities.get('request_type', 'show')
    
    channel_id = user_data.get('channel_id')
    user_id = user_data.get('user_id')
    username = user_data.get('username', 'there')
    
    print(f"Request type: {request_type}")
    print(f"Channel: {channel_id}, User: {username}")
    
    if not slack_handler or not channel_id:
        print("⚠️ No Slack handler available or missing channel_id - cannot post response")
        return
    
    try:
        if request_type == 'show' or request_type is None:
            # Fetch and display user's drafts - USE SUMMARY FORMAT
            print(f"📊 Fetching drafts for user {user_id}...")
            drafts = get_user_drafts(user_id, limit=10)
            
            if drafts:
                message = f"📋 **Your Job Postings** ({len(drafts)} found)\n\n"
                
                # Use summary format for listing
                for draft in drafts:
                    message += format_draft_summary(draft) + "\n"
                
                message += f"\n💡 **What you can do:**\n"
                message += f"• `show job_123` - View full details of a specific job\n"
                message += f"• `edit job_123` - Edit a specific job\n"
                message += f"• `delete job_123` - Remove a job\n"
                message += f"• `show more` - See additional jobs"
                
            else:
                message = f"📭 **No Job Postings Found**\n\n" \
                         f"Hi {username}! You don't have any job postings yet.\n\n" \
                         "🚀 **Get Started:**\n" \
                         "• Say something like: \"I need to hire a Python developer\"\n" \
                         "• I'll help you create your first job posting!"
        
        elif request_type == 'edit':
            # Show drafts with edit instructions - USE SUMMARY FORMAT
            drafts = get_user_drafts(user_id, limit=5)
            edit_requests = get_user_edit_requests(user_id, limit=3)
            
            message = f"✏️ **Edit Your Job Postings**\n\n"
            
            if drafts:
                message += f"📋 **Your Recent Jobs:**\n"
                for draft in drafts:
                    message += format_draft_summary(draft) + "\n"
                
                message += f"\n💡 **To edit:** Say `edit {drafts[0].get('job_id', 'job_id')}` with your changes\n"
            
            if edit_requests:
                message += f"\n🔄 **Pending Edit Requests:**\n"
                for edit_req in edit_requests:
                    job_id = edit_req.get('job_id', 'unknown')
                    status = edit_req.get('edit_status', 'unknown')
                    status_emoji = {'pending': '⏳', 'processing': '🔄', 'completed': '✅'}.get(status, '❓')
                    message += f"• {status_emoji} {job_id} - {status.title()}\n"
            
            if not drafts and not edit_requests:
                message += "📭 No job postings found to edit.\n"
                message += "Create a job posting first, then you can edit it!"
        
        elif request_type == 'delete':
            # Show drafts with delete instructions - USE SUMMARY FORMAT
            drafts = get_user_drafts(user_id, limit=10)
            
            if drafts:
                message = f"🗑️ **Delete Job Postings**\n\n"
                message += f"📋 **Your Jobs** ({len(drafts)} total):\n\n"
                
                for draft in drafts:
                    message += format_draft_summary(draft) + "\n"
                
                message += f"\n⚠️ **To delete:** Say `delete {drafts[0].get('job_id', 'job_id')}`\n"
                message += "⚠️ **Warning:** Deleted posts cannot be recovered!"
                
            else:
                message = f"📭 **No Job Postings Found**\n\n" \
                         f"{username}, you don't have any job postings to delete."
        
        elif request_type == 'list':
            # Show comprehensive list with statistics - USE SUMMARY FORMAT
            drafts = get_user_drafts(user_id, limit=20)
            edit_requests = get_user_edit_requests(user_id, limit=5)
            
            # Calculate statistics
            total_jobs = len(drafts)
            recent_jobs = len([d for d in drafts if d.get('timestamp', '') > (datetime.now() - timedelta(days=30)).isoformat()])
            
            message = f"📊 **Your Job Posting Summary**\n\n"
            message += f"📈 **Statistics:**\n"
            message += f"• Total job postings: {total_jobs}\n"
            message += f"• Recent (last 30 days): {recent_jobs}\n"
            message += f"• Pending edits: {len(edit_requests)}\n\n"
            
            if drafts:
                message += f"📋 **Recent Job Postings:**\n"
                for draft in drafts[:10]:  # Show more in list view
                    message += format_draft_summary(draft) + "\n"
                
                if len(drafts) > 10:
                    message += f"• ... and {len(drafts) - 10} more\n"
            
            message += f"\n💡 **Quick Actions:**\n"
            message += f"• `show job_id` - View full details\n"
            message += f"• `edit job_id` - Modify a posting\n"
            message += f"• `delete job_id` - Remove a posting"
        
        else:
            # General past request help
            drafts_count = len(get_user_drafts(user_id, limit=1))
            
            message = f"🤔 **Past Requests Help**\n\n"
            message += f"Hi {username}! You currently have {drafts_count} job posting(s).\n\n"
            message += f"🎯 **What I can help you with:**\n"
            message += f"• 👀 **View** - `show my posts`\n"
            message += f"• 📄 **Details** - `show job_123`\n"
            message += f"• ✏️ **Edit** - `edit job_123`\n" 
            message += f"• 🗑️ **Delete** - `delete job_123`\n"
            message += f"• 📋 **List** - `list all jobs`\n\n"
            message += f"Just tell me what you'd like to do!"
        
        # Post message to Slack
        slack_handler._post_response(
            channel_id=channel_id,
            thread_ts=user_data.get('thread_ts'),
            text=message
        )
        
        print(f"✅ Posted enhanced response to Slack for {username}")
        
    except Exception as e:
        print(f"❌ Error in enhanced past request handling: {e}")
        logger.error(f"Enhanced past request error: {e}")
        
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
    print(f"ℹ️ NON-HIRING request from {username}")
    
    # Send a helpful response for non-hiring requests
    if slack_handler and user_data.get('channel_id'):
        try:
            help_msg = f"Hi {username}! 👋\n\n" \
                      "I'm here to help with job posting requests. I can:\n" \
                      "• 💼 Create new job postings\n" \
                      "• 📋 Show your past job requests\n" \
                      "• ✏️ Edit existing postings\n" \
                      "• 🗑️ Delete old postings\n" \
                      "• 📄 View detailed job information\n\n" \
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
        original_message = list_item.get('text', message)  # Get original message if available
        is_specific_job_action = list_item.get('is_specific_job_action', False)
        
        # First check for specific job actions (edit job_123, delete job_456, show job_789)
        # Use original message for pattern matching, not the processed response
        if slack_handler and (is_specific_job_action or handle_specific_job_action(original_message, list_item, slack_handler)):
            print(f"✅ Handled specific job action for: {original_message}")
            continue
        
        print(f"\nProcessing user: {list_item.get('username', 'Unknown')}")
        print(f"Message: {message}")
        
        intent_entity_response = intent_entity_extractor(message)
        print(f"Raw intent extraction: {intent_entity_response}")
        
        try:
            # Ensure intent_entity_response is a string before parsing
            if isinstance(intent_entity_response, list):
                intent_entity_response = intent_entity_response[0] if intent_entity_response else "{}"
            elif isinstance(intent_entity_response, dict):
                intent_entity_response = json.dumps(intent_entity_response)
            elif not isinstance(intent_entity_response, str):
                intent_entity_response = str(intent_entity_response)
            
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
                print(f"ℹ️ Non-hiring intent detected for user {list_item.get('username')}")
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

def intent_entity_extractor(message) -> str:
    """Extract intent and entities from user message using enhanced prompt"""
    print("🔍 Processing intent entity extraction...")
    print(f"Input message: {message}")
    print("####")
    
    # Enhanced prompt template with past_request detection
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
         "number_of_people": "number of positions to fill or null",
         "request_type": "show | edit | delete | list | null"
     }}
     }}

    GUIDELINES:
    - Set intent to "hiring_request" if discussing NEW job postings, recruitment, or hiring needs
    - Set intent to "past_request" if asking about PREVIOUS/OLD job postings, viewing history, editing existing posts, or retrieving past requests
    - Set intent to "non_hiring" for general questions, support issues, or non-recruitment topics
    
    For "past_request", set request_type to:
      * "show" - if asking to view/display past requests
      * "edit" - if asking to modify existing job posts
      * "delete" - if asking to remove job posts
      * "list" - if asking for a list of all past requests
      * null - if unclear what they want to do with past requests
    
    - Extract entities ONLY if explicitly mentioned - use null for missing information
    - For skills, include both technical and soft skills mentioned
    - For experience, capture years, level (junior/senior), or specific requirements
    - For location, include remote work arrangements if mentioned
    - Be precise - don't infer or assume information not explicitly stated

    PAST REQUEST INDICATORS (should trigger "past_request" intent):
    - "show me my old posts", "previous job postings", "past requests"
    - "edit my last job", "modify existing post", "update previous"
    - "delete old posting", "remove my job post"
    - "list all my jobs", "show history", "what jobs did I post"
    - "my previous", "old job postings", "earlier requests"
    - "view my drafts", "see my posted jobs", "job history"

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
        api_key=os.getenv("NVIDIA_API_KEY")
    )

    try:
        # Format the prompt
        formatted_prompt = prompt.format_messages(message_batch=message)

        # Invoke the model
        response = formatter_llm.invoke(formatted_prompt)

        # Print just the content
        print("🤖 LLM Response:")
        print(response.content)
        
        # Ensure we return a string
        content = response.content
        if isinstance(content, list):
            content = content[0] if content else "{}"
        elif isinstance(content, dict):
            content = json.dumps(content)
        return str(content)
        
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
                "number_of_people": None,
                "request_type": None
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
                print(f"⚠️ ML processing failed for {channel_id}/{thread_display}: {e}")
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
        "delete job_456",
        "show job_789"
    ]
    
    print("\n" + "="*60)
    print("TESTING INTENT EXTRACTION")
    print("="*60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: '{message}'")
        result = intent_entity_extractor(message)
        try:
            # Ensure result is a string before parsing
            if isinstance(result, list):
                result = result[0] if result else "{}"
            elif isinstance(result, dict):
                result = json.dumps(result)
            elif not isinstance(result, str):
                result = str(result)
            
            parsed = json.loads(result)
            print(f"Intent: {parsed.get('intent')}")
            print(f"Request Type: {parsed.get('entities', {}).get('request_type')}")
        except:
            print("Failed to parse result")
        print("-" * 40)

# Test function for specific job actions
def test_specific_job_actions():
    """Test specific job action detection and handling"""
    test_cases = [
        "show job_123",
        "edit job_456", 
        "delete job_789",
        "SHOW job_abc",
        "Edit job_def",
        "DELETE job_ghi",
        "show my posts",  # Should not match
        "edit this job",  # Should not match
        "delete that",    # Should not match
    ]
    
    print("\n" + "="*60)
    print("TESTING SPECIFIC JOB ACTIONS")
    print("="*60)
    
    for test_message in test_cases:
        print(f"\nTesting: '{test_message}'")
        
        # Test pattern matching
        edit_pattern = r'edit[\s_]+(job_)?([a-zA-Z0-9_]{4,})'
        delete_pattern = r'delete[\s_]+(job_)?([a-zA-Z0-9_]{4,})'
        show_pattern = r'show[\s_]+(job_)?([a-zA-Z0-9_]{4,})'
        
        edit_match = re.search(edit_pattern, test_message.lower())
        delete_match = re.search(delete_pattern, test_message.lower())
        show_match = re.search(show_pattern, test_message.lower())
        
        if edit_match:
            print(f"✅ Edit match: {edit_match.group(2)}")
        elif delete_match:
            print(f"✅ Delete match: {delete_match.group(2)}")
        elif show_match:
            print(f"✅ Show match: {show_match.group(2)}")
        else:
            print("❌ No specific job action match")
    
    print("\nSpecific job action tests completed")

# Test function for formatting
def test_formatting_functions():
    """Test all formatting functions with sample data"""
    sample_draft = {
        'job_id': 'job_12345',
        'job_title': 'Senior Python Developer',
        'company': 'whisprnet.ai',
        'job_type': 'full-time',
        'experience': '5+ years',
        'location': 'Remote',
        'skills': 'Python, Django, REST APIs, PostgreSQL',
        'timestamp': '2025-01-15T10:30:00',
        'description': 'We are looking for an experienced Python developer to join our AI team...',
        'number_of_people': '2',
        'expiration_date': '2025-02-15',
        'education': 'BTech/MTech',
        'mail': 'careers@whisprnet.ai',
        'url': 'http://linkedin.com',
        'city': 'Pondicherry',
        'state': 'Pondicherry'
    }
    
    print("\n" + "="*60)
    print("TESTING FORMATTING FUNCTIONS")
    print("="*60)
    
    print("\n1. Summary Format:")
    print(format_draft_summary(sample_draft))
    
    print("\n2. Detailed Format:")
    print(format_draft_detailed(sample_draft))
    
    print("\n3. Full Description Format:")
    print(format_draft_with_description(sample_draft))
    
    print("\nFormatting tests completed")

# Command pattern matching functions
def extract_job_id_from_command(message):
    """Extract job ID from various command patterns"""
    patterns = [
        r'edit\s+([a-zA-Z0-9_]+)',
        r'delete\s+([a-zA-Z0-9_]+)',
        r'show\s+([a-zA-Z0-9_]+)',
        r'view\s+([a-zA-Z0-9_]+)',
        r'update\s+([a-zA-Z0-9_]+)',
        r'remove\s+([a-zA-Z0-9_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            return match.group(1)
    
    return None

def get_command_type(message):
    """Determine the command type from message"""
    message_lower = message.lower()
    
    if re.search(r'\bedit\b', message_lower):
        return 'edit'
    elif re.search(r'\bdelete\b|\bremove\b', message_lower):
        return 'delete'
    elif re.search(r'\bshow\b|\bview\b|\bdisplay\b', message_lower):
        return 'show'
    elif re.search(r'\blist\b|\ball\b', message_lower):
        return 'list'
    
    return None

# Statistics and analytics functions
def get_user_job_statistics(user_id):
    """Get comprehensive job posting statistics for a user"""
    try:
        drafts = get_user_drafts(user_id, limit=1000)  # Get all drafts
        edit_requests = get_user_edit_requests(user_id, limit=100)
        
        # Basic counts
        total_jobs = len(drafts)
        total_edits = len(edit_requests)
        
        # Time-based analysis
        now = datetime.now()
        recent_jobs = len([d for d in drafts if d.get('timestamp', '') > (now - timedelta(days=30)).isoformat()])
        this_week = len([d for d in drafts if d.get('timestamp', '') > (now - timedelta(days=7)).isoformat()])
        
        # Job type analysis
        job_types = {}
        locations = {}
        companies = {}
        
        for draft in drafts:
            # Count job types
            job_type = draft.get('job_type', 'Unknown')
            job_types[job_type] = job_types.get(job_type, 0) + 1
            
            # Count locations
            location = draft.get('location', 'Unknown')
            locations[location] = locations.get(location, 0) + 1
            
            # Count companies
            company = draft.get('company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1
        
        return {
            'total_jobs': total_jobs,
            'total_edits': total_edits,
            'recent_jobs_30_days': recent_jobs,
            'jobs_this_week': this_week,
            'most_common_job_types': sorted(job_types.items(), key=lambda x: x[1], reverse=True)[:5],
            'most_common_locations': sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5],
            'most_common_companies': sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        return {}

# Advanced search functions
def search_user_jobs(user_id, search_query, limit=10):
    """Search user's jobs by title, skills, or company"""
    try:
        all_drafts = get_user_drafts(user_id, limit=1000)
        search_terms = search_query.lower().split()
        
        matching_jobs = []
        
        for draft in all_drafts:
            # Create searchable text from job details
            searchable_text = f"{draft.get('job_title', '')} {draft.get('company', '')} {draft.get('skills', '')} {draft.get('location', '')}".lower()
            
            # Check if any search term matches
            if any(term in searchable_text for term in search_terms):
                matching_jobs.append(draft)
        
        return matching_jobs[:limit]
    
    except Exception as e:
        logger.error(f"Error searching user jobs: {e}")
        return []

# Export functions
def export_user_jobs_to_text(user_id):
    """Export all user jobs to a formatted text string"""
    try:
        drafts = get_user_drafts(user_id, limit=1000)
        
        if not drafts:
            return "No job postings found for export."
        
        export_text = f"JOB POSTINGS EXPORT\n"
        export_text += f"User ID: {user_id}\n"
        export_text += f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_text += f"Total Jobs: {len(drafts)}\n"
        export_text += "="*80 + "\n\n"
        
        for i, draft in enumerate(drafts, 1):
            export_text += f"JOB #{i}\n"
            export_text += f"ID: {draft.get('job_id', 'N/A')}\n"
            export_text += f"Title: {draft.get('job_title', 'N/A')}\n"
            export_text += f"Company: {draft.get('company', 'N/A')}\n"
            export_text += f"Type: {draft.get('job_type', 'N/A')}\n"
            export_text += f"Experience: {draft.get('experience', 'N/A')}\n"
            export_text += f"Location: {draft.get('location', 'N/A')}\n"
            export_text += f"Skills: {draft.get('skills', 'N/A')}\n"
            export_text += f"Posted: {draft.get('timestamp', 'N/A')}\n"
            export_text += f"Description: {draft.get('description', 'N/A')}\n"
            export_text += "-"*40 + "\n\n"
        
        return export_text
    
    except Exception as e:
        logger.error(f"Error exporting user jobs: {e}")
        return f"Error exporting jobs: {str(e)}"

# Example usage and module initialization
if __name__ == "__main__":
    print("Enhanced Extractor with Complete Database Integration loaded!")
    print("\n🌟 FEATURES:")
    print("• Intent detection (hiring_request, past_request, non_hiring)")
    print("• Database integration for job postings")
    print("• Specific job actions (edit/delete/show job_123)")
    print("• Smart Slack responses with real data")
    print("• Multiple formatting options (summary, detailed, full)")
    print("• Advanced search and statistics")
    print("• Export functionality")
    
    print("\n🔧 AVAILABLE COMMANDS:")
    print("• show my posts - List all job postings (summary format)")
    print("• show job_123 - View full details of specific job")
    print("• edit job_123 - Edit a specific job posting")
    print("• delete job_123 - Delete a specific job posting")
    print("• list all jobs - Comprehensive job list with stats")
    
    # Uncomment to test various functions
    # test_database_integration()
    # test_intent_extraction()
    # test_specific_job_actions()
    # test_formatting_functions()
    
else:
    # Module loaded via import
    print("📋 Enhanced Extractor module imported successfully")
    print("✅ Ready to process intents and manage job postings with advanced features")