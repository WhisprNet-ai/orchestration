#gives warning


import os
import time
import uuid
import sys
from threading import Thread
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from threading import Event
import json
from dotenv import load_dotenv

# Step 1: go up one directory level from this script's location
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Step 2: load the .env file
load_dotenv(dotenv_path=env_path)
# ====== Slack Tokens ======
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")


# ====== Init Slack App ======
app = App(token=SLACK_BOT_TOKEN)
 # job_id → "approve"/"reject"/"edit"


response_events = {}   # job_id → Event object
response_values = {}   # job_id → "approve" / "reject" / "edit"

# ====== Button Click Handler ======
@app.action("approve_click")
@app.action("reject_click")
@app.action("edit_click")
@app.action("draft_click")
def handle_button_click(ack, body, client, action):
    ack()

    # 🔍 Decode block_id JSON to extract job_id and user_name
    try:
        block_metadata = json.loads(action.get("block_id", "{}"))
        job_id = block_metadata.get("job_id")
        user_name = block_metadata.get("user_name", "user")
        user_id= block_metadata.get("user_id","123")
    except Exception as e:
        print("⚠ Failed to parse block_id metadata:", e)
        job_id = "unknown"
        user_name = "user"

    clicked_action = action["action_id"]
    message_ts = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    print(f"🖱 Button clicked: {clicked_action} for job_id: {job_id} by @{user_name}")

    if clicked_action == "approve_click":
        result_text = f"✅ Thanks for the confirmation, <@{user_id}>. I'm now posting the job on LinkedIn."
        response_values[job_id] = "approve"
    elif clicked_action == "reject_click":
        result_text = f"❌ No worries <@{user_id}>, I’ve canceled the posting."
        response_values[job_id] = "reject"
    elif clicked_action == "edit_click":
        result_text = f"✏️ Got it <@{user_id}>, I've marked this for editing. Please provide the necessary changes."
        response_values[job_id] = "edit"
    else:
        result_text = f" Fine <@{user_id}>, I've put this in draft. Please ping me if want to post it again."
        response_values[job_id] = "draft"

    # Unblock the waiting thread
    if job_id in response_events:
        response_events[job_id].set()

    # Update Slack message
    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        text="Response recorded.",
        blocks=[{
            "type": "section",
            "text": {"type": "mrkdwn", "text": result_text}
        }]
    )

# ====== Send Job Description to Slack ======
def send_job_desc(CHANNEL_ID, JOB_DESC, job_id, user_name, user_id):
    client = app.client

    event = Event()
    response_events[job_id] = event
    response_values[job_id] = None

    # 👉 Encode user info into block_id as JSON
    block_metadata = json.dumps({"job_id": job_id, "user_name": user_name,"user_id": user_id})

    print(f"📤 Posting to Slack | job_id: {job_id}")
    client.chat_postMessage(
        channel=CHANNEL_ID,
        text="Choose an action:",
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey @{user_name}, here's your job description:\n\n{JOB_DESC}\n\nDoes this look okay?"}
            },
            {
                "type": "actions",
                "block_id": block_metadata,  # embedded job_id + user_name
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Yes"}, "action_id": "approve_click"},
                    {"type": "button", "text": {"type": "plain_text", "text": "No"}, "action_id": "reject_click"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Edit"}, "action_id": "edit_click"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Draft"}, "action_id": "draft_click"},

                ]
            }
        ]
    )

    print(f"⏳ Waiting for user response for job_id: {job_id}")
    event.wait()  # Block until user responds

    action = response_values.get(job_id, None)
    print(f"✅ Response for job_id {job_id}: {action}")
    return action

