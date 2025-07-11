import os
import json
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.prompts import ChatPromptTemplate

from edit_rag.slack_button import send_job_desc
load_dotenv()


def load_job_store(file_path="job_store.json"):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_job_store(data, file_path="job_store.json"):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def store_job_description(job_json_path="job_descp.json"):
    if not os.path.exists(job_json_path):
        return {"error": f"{job_json_path} not found"}

    with open(job_json_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)

    user_id = job_data.get("user_id")
    job_desc = job_data.get("job_desc", "").strip()

    if not user_id or not job_desc:
        return {"error": "Missing user_id or job_desc"}

    job_store = load_job_store()
    job_store[user_id] = job_desc
    save_job_store(job_store)
    return {"status": "stored", "user_id": user_id}


def alter_job_description( reply,job_desc):
   
    reply_text = reply.strip()
    if not reply_text:
        return {"error": "Empty reply"}

    llm = ChatNVIDIA(
        model="meta/llama3-70b-instruct",
        api_key=os.getenv("NVIDIA_API_KEY")
    )

    prompt = ChatPromptTemplate.from_template("""You are a smart rewriting assistant.

Use the user's reply to update the given job description accordingly.

Instructions:
- ONLY update fields like title, skills, experience, or location based on the reply.
- DO NOT add fictional or speculative information.
- MAINTAIN original job formatting, professionalism, and clarity.
- Your output should start directly with the revised job description. Do NOT include introductory text.

User's Reply:
{reply}

Original Job Description:
{job_desc}

Updated Job Description:
""")

    result = llm.invoke(
        prompt.format(reply=reply_text, job_desc=job_desc)
    ).content
     
    return {"new_job_description": result}


# ========================
# MAIN EXECUTION
# ========================

    
def run_job_rewrite_pipeline(user_id, reply,job_desc,user_name):
    

    result = alter_job_description(reply,job_desc)
    
    result=result["new_job_description"]
    print("\n Altered job description processed")
    import uuid
    job_id = str(uuid.uuid4())[:8] 
    channel_id='C094K04Q5ED'
    # Fix file path to access edit_mode.json from root directory
    edit_mode_path = os.path.join(os.path.dirname(__file__), '..', 'edit_mode.json')
    
    try:
        with open(edit_mode_path, 'r') as f:
            content = f.read().strip()
            if not content:
                edit_mode = {}
            else:
                edit_mode = json.loads(content)
    except FileNotFoundError:
        edit_mode = {}
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in edit_mode.json: {e}")
        edit_mode = {}
    
    # Reset user's edit mode
    if user_id in edit_mode:
        edit_mode[user_id]["status"] = False
        edit_mode[user_id]["message"] = "null"
    
    # Write back to file
    with open(edit_mode_path, 'w') as f:
        json.dump(edit_mode, f, indent=2)
    send_edited_job_to_slack(channel_id, result, job_id, user_name, user_id)


# ========================
# SEND EDITED JOB TO SLACK
# ========================
def send_edited_job_to_slack(channel_id, updated_job_desc, job_id, user_name, user_id):
    """
    Function similar to send_job_desc but for edited job descriptions
    Posts the updated job description to Slack with approval buttons
    """
    try:
        
        
        print(f"📤 Sending updated job description to Slack | job_id: {job_id}")
        
        # Call the existing send_job_desc function with updated description
        action = send_job_desc(channel_id, updated_job_desc, job_id, user_name, user_id)
        
        print(f"✅ User response for updated job_id {job_id}: {action}")
        return action
        
    except Exception as e:
        print(f"❌ Error sending edited job to Slack: {e}")
        return "error"
   

# Run only if script is executed directly
if __name__ == "__main__":
    user_id='12122'
    user_name='manoj'
    reply='change year of experience to 3 years'
    job_desc="Hey <@U09359UUX8X>, here's your job description:\n\n**Senior Backend Developer**\nWe are looking for a skilled Backend Developer with 5 years of experience in Python.\n**Requirements:**\n- Python programming\n- Database management\n- API development\n\n**Job Type:** Full-time\n\nDoes this look okay?"
    output = run_job_rewrite_pipeline(user_id, reply,job_desc,user_name)
    if output:
        print("\n Final Output:\n")
        print(output)