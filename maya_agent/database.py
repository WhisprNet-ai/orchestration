# draft_db.py
import sqlite3
from datetime import datetime
import os




DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'job_drafts.db'))
def create_draft_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,     -- You supply this
            user_id TEXT NOT NULL,
            username TEXT,
            channel_id TEXT,
            job_title TEXT,
            company TEXT,
            job_type TEXT,
            experience TEXT,
            location TEXT,
            skills TEXT,
            expiration_date TEXT,
            number_of_people TEXT,
            url TEXT,
            city TEXT,
            state TEXT,
            mail TEXT,
            education TEXT,
            description TEXT,
            timestamp TEXT
        )
    """)

    # Create edit_requests table for tracking edit workflows
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS edit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT,
            channel_id TEXT,
            original_job_data TEXT,  -- JSON string of original job data
            original_description TEXT,
            edit_status TEXT DEFAULT 'pending',  -- pending, processing, completed
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

def insert_draft(job_id, user_id, username, channel_id, job_data, description):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO drafts (
            job_id, user_id, username, channel_id, job_title, company, job_type,
            experience, location, skills, expiration_date, number_of_people,
            url, city, state, mail, education, description, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        user_id,
        username,
        channel_id,
        job_data.get("job_title"),
        job_data.get("company"),
        job_data.get("job_type"),
        job_data.get("experience"),
        job_data.get("location"),
        job_data.get("skills"),
        job_data.get("expiration_date"),
        str(job_data.get("number_of_people")),
        job_data.get("url"),
        job_data.get("city"),
        job_data.get("state"),
        job_data.get("mail"),
        job_data.get("education"),
        description,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()

def insert_edit_request(job_id, user_id, username, channel_id, job_data, description):
    """Insert an edit request into the database"""
    import json
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO edit_requests (
            job_id, user_id, username, channel_id, original_job_data, 
            original_description, edit_status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        user_id,
        username,
        channel_id,
        json.dumps(job_data),  # Store job_data as JSON string
        description,
        'pending',
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()

def get_edit_request(job_id):
    """Retrieve an edit request by job_id"""
    import json
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM edit_requests WHERE job_id = ?", (job_id,))
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

def update_edit_status(job_id, status):
    """Update the status of an edit request"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE edit_requests 
        SET edit_status = ? 
        WHERE job_id = ?
    """, (status, job_id))

    conn.commit()
    conn.close()

def delete_edit_request(job_id):
    """Delete an edit request"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM edit_requests WHERE job_id = ?", (job_id,))
    
    conn.commit()
    conn.close()


# create_draft_table()


# # Step 2: Sample job_data and description
# sample_job_data = {
#     "job_title": "AI Research Engineer",
#     "company": "whisprnet.ai",
#     "job_type": "full-time",
#     "experience": "3 years",
#     "location": "Remote",
#     "skills": "Python, Deep Learning",
#     "expiration_date": "2025-08-01",
#     "number_of_people": 2,
#     "url": "http://linkedin.com",
#     "city": "Pondicherry",
#     "state": "Pondicherry",
#     "mail": "careers@whisprnet.ai",
#     "education": "BTech/MTech"
# }

# # Step 3: Call the insert_draft function
# insert_draft(
#     job_id="job_001",
#     user_id="U123456",
#     username="naveen_k",
#     channel_id="C123456",
#     job_data=sample_job_data,
#     description="This is a sample LinkedIn job description generated by LLM."
# )

# print("✅ Draft inserted successfully!")



# def get_draft_by_job_id(job_id):
#     """
#     Fetch a single draft using its job_id.
#     """
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM drafts WHERE job_id = ?", (job_id,))
#     row = cursor.fetchone()

#     conn.close()

#     if row:
#         # Convert row to dictionary using column names
#         columns = [desc[0] for desc in cursor.description]
#         return dict(zip(columns, row))
#     else:
#         return None



# job_id = "job_001"

# draft = get_draft_by_job_id(job_id)

# if draft:
#     print("✅ Draft found:")
#     for key, value in draft.items():
#         print(f"{key}: {value}")
# else:
#     print("❌ No draft found with that job_id.")