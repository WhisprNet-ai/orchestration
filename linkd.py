import requests
import json

# Load job input
with open("job_in.json", "r") as file:
    job_data = json.load(file)

# Step 1: Generate job description from Flask API
response = requests.post("http://localhost:5000/generate-job-description", json=job_data)
if response.status_code != 200:
    print("❌ Failed to generate job description")
    print(response.text)
    exit()

data = response.json()
generated_description = data["job_description"]
job_title = data["job_title"]
location = data["location"]
company = data["company"]

# Step 2: LinkedIn API POST
access_token = "AQXguRLENdE8B3HDiIDd8YyUDfsMxUjdV-F1tM9e2ZwzWyi-vTeWLo9AuYqOu86AC-A3W_5fYOBmi7c8BbFKq90UZUOuyhMmDtNcxUtHCkmMTGUnJY-vK4woS-XqPi5g16Xm6wOQWYX80dp2n3Di013oZnSMiNOkXhGElCsdapS4_tUBMptCwDCsF8sR13sqoxIVgXIaIYWidGO3JvUbFzpjWSejfnWU_iZhx5vYq8j-AVqoDGfXZ36sVlnOpZWqAqVYUa9Wo-Rut1ep4vHo-XVqD38SswYrkOumJsjOkqrPuR_YwXsTYbJD2nF_zu4xfcMdlG5tv2Xgl3g5rkTlVnWn8PCgzQ"
person_urn = "urn:li:person:f-rqHhOZHA"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0"
}

post_payload = {
    "author": person_urn,
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": f"🚀 New Job Opportunity at {company}!\n\n"
                        f"📌 Title: {job_title}\n"
                        f"📍 Location: {location}\n\n"
                        f"{generated_description}\n"
                        f"#Hiring #Careers #JobOpening #SoftwareEngineer"
            },
            "shareMediaCategory": "NONE"
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

post_response = requests.post(
    "https://api.linkedin.com/v2/ugcPosts",
    headers=headers,
    data=json.dumps(post_payload)
)

print("✅ Status Code:", post_response.status_code)
try:
    print(post_response.json())
except Exception:
    print("No JSON response received")
