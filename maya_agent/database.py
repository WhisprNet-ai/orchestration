# database.py - Complete job drafts database management
import sqlite3
from datetime import datetime
import os
import json
import logging

logger = logging.getLogger(__name__)

# Database configuration
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'job_drafts.db'))

def ensure_database_directory():
    """Ensure the database directory exists"""
    db_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"✅ Created database directory: {db_dir}")

def create_draft_table():
    """Create the drafts and edit_requests tables if they don't exist"""
    ensure_database_directory()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create drafts table
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
            timestamp TEXT,
            status TEXT DEFAULT 'active'     -- active, deleted, archived
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
            timestamp TEXT,
            FOREIGN KEY (job_id) REFERENCES drafts(job_id)
        )
    """)

    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_drafts_user_id ON drafts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_drafts_timestamp ON drafts(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edit_requests_user_id ON edit_requests(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edit_requests_job_id ON edit_requests(job_id)")

    conn.commit()
    conn.close()
    print("✅ Database tables created/verified successfully")

def insert_draft(job_id, user_id, username, channel_id, job_data, description):
    """Insert a new job draft into the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO drafts (
                job_id, user_id, username, channel_id, job_title, company, job_type,
                experience, location, skills, expiration_date, number_of_people,
                url, city, state, mail, education, description, timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            datetime.utcnow().isoformat(),
            'active'
        ))

        conn.commit()
        conn.close()
        print(f"✅ Draft inserted successfully: {job_id}")
        return True
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Draft insertion failed - job_id already exists: {job_id}")
        logger.error(f"Draft insertion integrity error: {e}")
        return False
    except Exception as e:
        print(f"❌ Draft insertion failed: {e}")
        logger.error(f"Draft insertion error: {e}")
        return False

def get_draft_by_job_id(job_id):
    """Fetch a single draft using its job_id"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM drafts WHERE job_id = ? AND status = 'active'", (job_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            # Convert row to dictionary using column names
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error fetching draft by job_id {job_id}: {e}")
        logger.error(f"Get draft error: {e}")
        return None

def get_user_drafts(user_id, limit=10, include_deleted=False):
    """Fetch user's job drafts from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if include_deleted:
            status_condition = ""
            params = (user_id, limit)
        else:
            status_condition = "AND status = 'active'"
            params = (user_id, limit)
        
        cursor.execute(f"""
            SELECT * FROM drafts 
            WHERE user_id = ? {status_condition}
            ORDER BY timestamp DESC 
            LIMIT ?
        """, params)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        conn.close()
        
        # Convert to list of dictionaries
        drafts = []
        for row in rows:
            draft = dict(zip(columns, row))
            drafts.append(draft)
        
        return drafts
        
    except Exception as e:
        print(f"❌ Error fetching user drafts for {user_id}: {e}")
        logger.error(f"Get user drafts error: {e}")
        return []

def get_all_user_drafts(user_id):
    """Get all drafts for a user (no limit)"""
    return get_user_drafts(user_id, limit=1000, include_deleted=False)

def update_draft(job_id, user_id, updated_data):
    """Update an existing draft"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Build dynamic update query based on provided data
        update_fields = []
        values = []
        
        field_mapping = {
            'job_title': 'job_title',
            'company': 'company',
            'job_type': 'job_type',
            'experience': 'experience',
            'location': 'location',
            'skills': 'skills',
            'expiration_date': 'expiration_date',
            'number_of_people': 'number_of_people',
            'url': 'url',
            'city': 'city',
            'state': 'state',
            'mail': 'mail',
            'education': 'education',
            'description': 'description'
        }
        
        for key, db_field in field_mapping.items():
            if key in updated_data:
                update_fields.append(f"{db_field} = ?")
                values.append(updated_data[key])
        
        if not update_fields:
            print("⚠ No valid fields to update")
            return False
        
        # Add timestamp update
        update_fields.append("timestamp = ?")
        values.append(datetime.utcnow().isoformat())
        
        # Add WHERE conditions
        values.extend([job_id, user_id])
        
        query = f"""
            UPDATE drafts 
            SET {', '.join(update_fields)}
            WHERE job_id = ? AND user_id = ? AND status = 'active'
        """
        
        cursor.execute(query, values)
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            print(f"✅ Draft updated successfully: {job_id}")
            return True
        else:
            conn.close()
            print(f"❌ No draft found to update: {job_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating draft {job_id}: {e}")
        logger.error(f"Update draft error: {e}")
        return False

def delete_user_draft(job_id, user_id, soft_delete=True):
    """Delete a specific user's draft (soft delete by default)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if soft_delete:
            # Soft delete - mark as deleted
            cursor.execute("""
                UPDATE drafts 
                SET status = 'deleted', timestamp = ?
                WHERE job_id = ? AND user_id = ? AND status = 'active'
            """, (datetime.utcnow().isoformat(), job_id, user_id))
        else:
            # Hard delete - actually remove from database
            cursor.execute("""
                DELETE FROM drafts 
                WHERE job_id = ? AND user_id = ?
            """, (job_id, user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            delete_type = "soft deleted" if soft_delete else "permanently deleted"
            print(f"✅ Draft {delete_type} successfully: {job_id}")
            return True
        else:
            conn.close()
            print(f"❌ No draft found to delete: {job_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting draft {job_id}: {e}")
        logger.error(f"Delete draft error: {e}")
        return False

def restore_draft(job_id, user_id):
    """Restore a soft-deleted draft"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE drafts 
            SET status = 'active', timestamp = ?
            WHERE job_id = ? AND user_id = ? AND status = 'deleted'
        """, (datetime.utcnow().isoformat(), job_id, user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            print(f"✅ Draft restored successfully: {job_id}")
            return True
        else:
            conn.close()
            print(f"❌ No deleted draft found to restore: {job_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error restoring draft {job_id}: {e}")
        logger.error(f"Restore draft error: {e}")
        return False

# Edit Requests Functions
def insert_edit_request(job_id, user_id, username, channel_id, job_data, description):
    """Insert an edit request into the database"""
    try:
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
        print(f"✅ Edit request inserted successfully: {job_id}")
        return True
        
    except Exception as e:
        print(f"❌ Edit request insertion failed: {e}")
        logger.error(f"Edit request insertion error: {e}")
        return False

def get_edit_request(job_id):
    """Retrieve an edit request by job_id"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM edit_requests WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            # Parse the JSON string back to dict
            try:
                result['original_job_data'] = json.loads(result['original_job_data'])
            except:
                result['original_job_data'] = {}
            return result
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error fetching edit request for {job_id}: {e}")
        logger.error(f"Get edit request error: {e}")
        return None

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
        
        # Convert to list of dictionaries
        edit_requests = []
        for row in rows:
            edit_request = dict(zip(columns, row))
            # Parse JSON data
            if edit_request.get('original_job_data'):
                try:
                    edit_request['original_job_data'] = json.loads(edit_request['original_job_data'])
                except:
                    edit_request['original_job_data'] = {}
            edit_requests.append(edit_request)
        
        return edit_requests
        
    except Exception as e:
        print(f"❌ Error fetching edit requests for {user_id}: {e}")
        logger.error(f"Get user edit requests error: {e}")
        return []

def update_edit_status(job_id, status):
    """Update the status of an edit request"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE edit_requests 
            SET edit_status = ?, timestamp = ?
            WHERE job_id = ?
        """, (status, datetime.utcnow().isoformat(), job_id))

        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            print(f"✅ Edit request status updated: {job_id} -> {status}")
            return True
        else:
            conn.close()
            print(f"❌ No edit request found to update: {job_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating edit status for {job_id}: {e}")
        logger.error(f"Update edit status error: {e}")
        return False

def delete_edit_request(job_id):
    """Delete an edit request"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM edit_requests WHERE job_id = ?", (job_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            print(f"✅ Edit request deleted successfully: {job_id}")
            return True
        else:
            conn.close()
            print(f"❌ No edit request found to delete: {job_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting edit request for {job_id}: {e}")
        logger.error(f"Delete edit request error: {e}")
        return False

# Search and Filter Functions
def search_drafts_by_title(user_id, search_term, limit=10):
    """Search drafts by job title"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM drafts 
            WHERE user_id = ? AND status = 'active' 
            AND job_title LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, f"%{search_term}%", limit))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
        
    except Exception as e:
        print(f"❌ Error searching drafts: {e}")
        logger.error(f"Search drafts error: {e}")
        return []

def get_drafts_by_date_range(user_id, start_date, end_date, limit=50):
    """Get drafts within a date range"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM drafts 
            WHERE user_id = ? AND status = 'active'
            AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_id, start_date, end_date, limit))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
        
    except Exception as e:
        print(f"❌ Error getting drafts by date range: {e}")
        logger.error(f"Get drafts by date range error: {e}")
        return []

# Statistics Functions
def get_user_stats(user_id):
    """Get comprehensive statistics for a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Total drafts
        cursor.execute("SELECT COUNT(*) FROM drafts WHERE user_id = ? AND status = 'active'", (user_id,))
        total_active = cursor.fetchone()[0]
        
        # Deleted drafts
        cursor.execute("SELECT COUNT(*) FROM drafts WHERE user_id = ? AND status = 'deleted'", (user_id,))
        total_deleted = cursor.fetchone()[0]
        
        # Edit requests
        cursor.execute("SELECT COUNT(*) FROM edit_requests WHERE user_id = ?", (user_id,))
        total_edit_requests = cursor.fetchone()[0]
        
        # Recent drafts (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM drafts 
            WHERE user_id = ? AND status = 'active' AND timestamp > ?
        """, (user_id, thirty_days_ago))
        recent_drafts = cursor.fetchone()[0]
        
        # Most common job types
        cursor.execute("""
            SELECT job_type, COUNT(*) as count FROM drafts 
            WHERE user_id = ? AND status = 'active' AND job_type IS NOT NULL
            GROUP BY job_type 
            ORDER BY count DESC 
            LIMIT 5
        """, (user_id,))
        job_types = cursor.fetchall()
        
        conn.close()
        
        stats = {
            'total_active_drafts': total_active,
            'total_deleted_drafts': total_deleted,
            'total_edit_requests': total_edit_requests,
            'recent_drafts_30_days': recent_drafts,
            'most_common_job_types': [{'type': jt[0], 'count': jt[1]} for jt in job_types]
        }
        
        return stats
        
    except Exception as e:
        print(f"❌ Error getting user stats: {e}")
        logger.error(f"Get user stats error: {e}")
        return {
            'total_active_drafts': 0,
            'total_deleted_drafts': 0,
            'total_edit_requests': 0,
            'recent_drafts_30_days': 0,
            'most_common_job_types': []
        }

# Database Maintenance Functions
def cleanup_old_edit_requests(days_old=30):
    """Clean up old completed edit requests"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        cursor.execute("""
            DELETE FROM edit_requests 
            WHERE edit_status = 'completed' AND timestamp < ?
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Cleaned up {deleted_count} old edit requests")
        return deleted_count
        
    except Exception as e:
        print(f"❌ Error cleaning up edit requests: {e}")
        logger.error(f"Cleanup edit requests error: {e}")
        return 0

def get_database_stats():
    """Get overall database statistics"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Count of drafts by status
        cursor.execute("SELECT status, COUNT(*) FROM drafts GROUP BY status")
        draft_counts = dict(cursor.fetchall())
        
        # Count of edit requests by status
        cursor.execute("SELECT edit_status, COUNT(*) FROM edit_requests GROUP BY edit_status")
        edit_counts = dict(cursor.fetchall())
        
        # Unique users
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM drafts")
        unique_users = cursor.fetchone()[0]
        
        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM drafts WHERE timestamp > ?", (seven_days_ago,))
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'draft_counts': draft_counts,
            'edit_request_counts': edit_counts,
            'unique_users': unique_users,
            'recent_activity_7_days': recent_activity
        }
        
    except Exception as e:
        print(f"❌ Error getting database stats: {e}")
        logger.error(f"Get database stats error: {e}")
        return {}

# Initialize database on import
def initialize_database():
    """Initialize the database with tables"""
    try:
        create_draft_table()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        logger.error(f"Database initialization error: {e}")
        return False

# Example/Test Functions
def create_sample_data():
    """Create sample data for testing"""
    sample_job_data = {
        "job_title": "AI Research Engineer",
        "company": "whisprnet.ai",
        "job_type": "full-time",
        "experience": "3 years",
        "location": "Remote",
        "skills": "Python, Deep Learning",
        "expiration_date": "2025-08-01",
        "number_of_people": 2,
        "url": "http://linkedin.com",
        "city": "Pondicherry",
        "state": "Pondicherry",
        "mail": "careers@whisprnet.ai",
        "education": "BTech/MTech"
    }

    # Insert sample draft
    success = insert_draft(
        job_id="job_001",
        user_id="U123456",
        username="naveen_k",
        channel_id="C123456",
        job_data=sample_job_data,
        description="This is a sample LinkedIn job description generated by LLM."
    )
    
    if success:
        print("✅ Sample data created successfully!")
    else:
        print("❌ Failed to create sample data")

def test_all_functions():
    """Test all database functions"""
    print("\n" + "="*60)
    print("TESTING ALL DATABASE FUNCTIONS")
    print("="*60)
    
    # Test user
    test_user_id = "test_user_123"
    test_username = "test_user"
    test_channel = "C123TEST"
    
    # Test draft operations
    print("\n1. Testing draft operations...")
    
    test_job_data = {
        "job_title": "Test Developer",
        "company": "Test Company",
        "job_type": "full-time",
        "experience": "2 years",
        "location": "Remote",
        "skills": "Python, Testing"
    }
    
    # Insert
    insert_draft("test_job_001", test_user_id, test_username, test_channel, test_job_data, "Test description")
    
    # Get by ID
    draft = get_draft_by_job_id("test_job_001")
    print(f"Retrieved draft: {draft.get('job_title') if draft else 'None'}")
    
    # Get user drafts
    user_drafts = get_user_drafts(test_user_id)
    print(f"User has {len(user_drafts)} drafts")
    
    # Update draft
    update_draft("test_job_001", test_user_id, {"job_title": "Updated Test Developer"})
    
    # Test edit requests
    print("\n2. Testing edit requests...")
    insert_edit_request("test_job_001", test_user_id, test_username, test_channel, test_job_data, "Original description")
    
    edit_req = get_edit_request("test_job_001")
    print(f"Edit request status: {edit_req.get('edit_status') if edit_req else 'None'}")
    
    # Test statistics
    print("\n3. Testing statistics...")
    stats = get_user_stats(test_user_id)
    print(f"User stats: {stats}")
    
    db_stats = get_database_stats()
    print(f"Database stats: {db_stats}")
    
    # Cleanup test data
    print("\n4. Cleaning up test data...")
    delete_user_draft("test_job_001", test_user_id)
    delete_edit_request("test_job_001")
    
    print("✅ All tests completed!")

# Run initialization when module is imported
if __name__ == "__main__":
    print("Database module loaded!")
    print("Initializing database...")
    initialize_database()
    
    # Uncomment to run tests
    # test_all_functions()
    
    # Uncomment to create sample data
    # create_sample_data()
else:
    # Auto-initialize when imported
    initialize_database()