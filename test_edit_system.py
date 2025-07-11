#!/usr/bin/env python3
"""
Test script for the edit system integration
"""
import json
import os
from edit_state_manager import (
    load_state, save_state, set_user_edit_mode, 
    clear_user_edit_mode, is_user_in_edit_mode, 
    get_user_original_message
)
from message_router import should_bypass_router_for_user

def test_edit_state_manager():
    """Test the edit state manager functions"""
    print("Testing Edit State Manager...")
    
    # Test user ID and message
    test_user_id = "TEST_USER_123"
    test_message = "Test job description for editing"
    
    # Test setting edit mode
    print(f"Setting edit mode for user {test_user_id}")
    result = set_user_edit_mode(test_user_id, test_message)
    print(f"Set edit mode result: {result}")
    
    # Test checking edit mode
    print(f"Checking if user {test_user_id} is in edit mode")
    in_edit_mode = is_user_in_edit_mode(test_user_id)
    print(f"User in edit mode: {in_edit_mode}")
    
    # Test getting original message
    print(f"Getting original message for user {test_user_id}")
    original_message = get_user_original_message(test_user_id)
    print(f"Original message: {original_message}")
    
    # Test clearing edit mode
    print(f"Clearing edit mode for user {test_user_id}")
    clear_result = clear_user_edit_mode(test_user_id)
    print(f"Clear edit mode result: {clear_result}")
    
    # Test checking edit mode after clearing
    print(f"Checking if user {test_user_id} is in edit mode after clearing")
    in_edit_mode_after = is_user_in_edit_mode(test_user_id)
    print(f"User in edit mode after clearing: {in_edit_mode_after}")
    
    print("Edit State Manager tests completed!\n")


def test_bypass_router():
    """Test the router bypass functionality"""
    print("Testing Router Bypass Logic...")
    
    # Test normal messages (should not bypass)
    normal_messages = ["I need a developer", "hiring python engineer"]
    test_user_id = "U12345"
    should_bypass = should_bypass_router_for_user(test_user_id, normal_messages)
    print(f"Normal messages bypass: {should_bypass}")
    
    # Test past request messages (should bypass)
    past_messages = ["show me my past jobs", "what are my drafts"]
    should_bypass_past = should_bypass_router_for_user(test_user_id, past_messages)
    print(f"Past request messages bypass: {should_bypass_past}")
    
    # Test specific job action messages (should bypass)
    job_action_messages = ["edit job_abc123", "delete job_xyz789"]
    should_bypass_action = should_bypass_router_for_user(test_user_id, job_action_messages)
    print(f"Job action messages bypass: {should_bypass_action}")
    
    print("Router bypass tests completed!\n")


def test_edit_rag_processor():
    """Test the edit RAG processor functionality"""
    print("Testing Edit RAG Processor...")
    
    from edit_rag_processor import validate_edit_instructions, extract_job_description
    
    # Test validation
    valid_instructions = "Change the title to Senior Developer"
    invalid_instructions = ""
    
    is_valid = validate_edit_instructions(valid_instructions)
    is_invalid = validate_edit_instructions(invalid_instructions)
    
    print(f"Valid instructions '{valid_instructions}': {is_valid}")
    print(f"Invalid instructions '{invalid_instructions}': {is_invalid}")
    
    # Test job description extraction
    sample_message = """Hey @U12345, here's your job description:

**Backend Developer**

We are looking for a skilled Backend Developer with 5 years of experience.

**Requirements:**
- Python programming
- Database management
- API development

Does this look okay?"""
    
    extracted_desc = extract_job_description(sample_message)
    print(f"Extracted job description: {extracted_desc[:100]}...")
    
    print("Edit RAG Processor tests completed!\n")


if __name__ == "__main__":
    print("🧪 Starting Edit System Integration Tests\n")
    
    try:
        test_edit_state_manager()
        test_bypass_router()
        test_edit_rag_processor()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 