#!/usr/bin/env python3
"""
Test the complete edit flow from setting edit mode to processing edit instructions.
"""

from edit_state_manager import set_user_edit_mode, is_user_in_edit_mode, clear_user_edit_mode
from message_router import route_user_message
from rag_it1.rag_func import process_messages


def test_complete_edit_flow():
    """Test the complete edit flow"""
    print('=== Testing Complete Edit Flow ===')
    
    # Step 1: Set user in edit mode with original job description
    user_id = 'U09359UUX8X'
    original_job = '''Hey @test_user, here's your job description:

**Backend Developer**

We are looking for a skilled Backend Developer with 5 years of experience in Python.

**Requirements:**
- Python programming
- Database management
- API development

Does this look okay?'''
    
    print('Step 1: Setting user in edit mode...')
    set_user_edit_mode(user_id, original_job)
    print(f'User in edit mode: {is_user_in_edit_mode(user_id)}')
    
    # Step 2: Test routing edit instructions
    print('\nStep 2: Routing edit instructions...')
    edit_instructions = ['change the title to Senior Backend Developer and add React to skills']
    
    routing_result = route_user_message(
        user_id=user_id,
        username='test_user',
        channel_id='C094K04Q5ED',
        user_messages=edit_instructions,
        slack_handler=None
    )
    
    print(f'Routing result: {routing_result.get("route", "unknown")}')
    print(f'Status: {routing_result.get("status", "unknown")}')
    print(f'Message: {routing_result.get("message", "No message")}')
    
    # Step 3: Check if user is still in edit mode (should be cleared after processing)
    print(f'\nStep 3: User in edit mode after processing: {is_user_in_edit_mode(user_id)}')
    
    # Step 4: Test normal routing after edit is complete
    print('\nStep 4: Testing normal routing after edit...')
    normal_messages = ['I need a frontend developer']
    
    normal_routing = route_user_message(
        user_id=user_id,
        username='test_user',
        channel_id='C094K04Q5ED',
        user_messages=normal_messages,
        slack_handler=None
    )
    
    print(f'Normal routing result: {normal_routing.get("route", "unknown")}')
    print(f'Normal status: {normal_routing.get("status", "unknown")}')
    
    print('\n=== Edit Flow Test Complete ===')


def test_edit_mode_detection():
    """Test edit mode detection in the process_messages function"""
    print('\n=== Testing Edit Mode Detection in process_messages ===')
    
    # Set user in edit mode
    user_id = 'U09359UUX8X'
    original_job = 'Test job description for editing'
    set_user_edit_mode(user_id, original_job)
    
    # Create test payload
    test_payload = {
        'messages': [{
            'user_id': user_id,
            'username': 'test_user',
            'text': 'change title to Lead Developer',
            'channel_id': 'C094K04Q5ED',
            'session_id': 'default'
        }]
    }
    
    print('Processing message with user in edit mode...')
    try:
        result = process_messages(test_payload)
        print(f'Process result: {len(result)} messages processed')
        
        # Check if user is still in edit mode
        print(f'User still in edit mode: {is_user_in_edit_mode(user_id)}')
        
    except Exception as e:
        print(f'Error during processing: {e}')
    
    # Clean up
    clear_user_edit_mode(user_id)
    
    print('=== Edit Mode Detection Test Complete ===')


if __name__ == '__main__':
    test_complete_edit_flow()
    test_edit_mode_detection() 