import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from ingest.model_json_ingest import ingest_json_data
from ingest.slack_ingest import ingest_slack_data

def main():
    """Run all ingestion processes."""
    print("🚀 Starting data ingestion process...")
    
    # Ingest JSON data
    print("\n Ingesting JSON job posting data...")
    json_success = ingest_json_data()
    
    # Ingest Slack data
    print("\n Ingesting Slack messages...")
    slack_success = ingest_slack_data()
    
    # Summary
    print(f"\n Ingestion Summary:")
    print(f"   JSON Data: {' Success' if json_success else '❌ Failed'}")
    print(f"   Slack Data: {' Success' if slack_success else '❌ Failed'}")
    
    if json_success and slack_success:
        print("\n All data ingested ")
    else:
        print("\n⚠️  Some ingestion processes failed. Check the errors above.")

if __name__ == "__main__":
    main()