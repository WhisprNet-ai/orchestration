# Edit System Integration

This document describes the new edit system implementation for the Slack bot that allows users to edit job descriptions through a clean, modular architecture.

## Overview

The edit system allows users to click an "Edit" button on job descriptions, which puts them in edit mode. When they send their next message, it's treated as edit instructions and processed through a specialized pipeline to update the job description.

## Architecture

### Core Components

1. **Edit State Manager** (`edit_state_manager.py`)
   - Handles JSON read/write operations for `edit_mode.json`
   - Manages user edit states and status
   - Provides clean API for state management

2. **Message Router** (`message_router.py`)
   - Routes messages to appropriate pipeline based on user status
   - Handles both edit mode and normal mode routing
   - Includes bypass logic for special cases

3. **Edit RAG Processor** (`edit_rag_processor.py`)
   - Processes edit instructions using LLM
   - Extracts job descriptions from Slack messages
   - Sends updated descriptions back to Slack

4. **Updated Slack Button Handler** (`maya_agent/slack_button.py`)
   - Uses new state manager for edit mode updates
   - Cleaner integration with state management

## Flow

### Normal Job Description Generation
1. User sends message → Message Router → Normal RAG Pipeline → Job Description posted with buttons

### Edit Flow
1. User clicks "Edit" button → Update `edit_mode.json` with original message
2. User sends edit instructions → Message Router detects edit mode → Edit RAG Pipeline
3. LLM processes edit instructions → Updated job description posted → Edit mode cleared

## File Structure

```
.
├── edit_state_manager.py       # JSON state management
├── message_router.py          # Message routing logic
├── edit_rag_processor.py      # Edit processing pipeline
├── test_edit_system.py        # Integration tests
├── edit_mode.json            # User edit state storage
└── maya_agent/
    └── slack_button.py       # Updated button handler
```

## API Reference

### Edit State Manager

```python
# Load all edit states
state = load_state()

# Set user to edit mode
set_user_edit_mode(user_id, original_message)

# Check if user is in edit mode
is_in_edit = is_user_in_edit_mode(user_id)

# Get original message for editing
original_msg = get_user_original_message(user_id)

# Clear edit mode
clear_user_edit_mode(user_id)
```

### Message Router

```python
# Route message to appropriate pipeline
result = route_user_message(user_id, username, channel_id, messages, slack_handler)

# Check if message should bypass router
should_bypass = should_bypass_router(messages)
```

### Edit RAG Processor

```python
# Process edit instructions
result = edit_rag(user_id, username, channel_id, edit_instructions, original_message, slack_handler)

# Validate edit instructions
is_valid = validate_edit_instructions(edit_instructions)

# Extract job description from Slack message
job_desc = extract_job_description(slack_message)
```

## State File Format

`edit_mode.json`:
```json
{
  "user_id": {
    "status": true,
    "message": "Original job description message"
  }
}
```

## Integration Points

### Modified Files
- `rag_it1/rag_func.py` - Updated to use message router
- `maya_agent/slack_button.py` - Updated button handler

### Key Integration
- Message router is called from `process_messages()` in `rag_func.py`
- Edit button handler uses state manager to update edit mode
- Edit RAG processor handles the complete edit workflow

## Testing

Run the test suite:
```bash
python test_edit_system.py
```

This tests:
- Edit state manager functionality
- Message router logic
- Edit RAG processor components

## Benefits

1. **Modular Design**: Clean separation of concerns
2. **Robust State Management**: Proper JSON handling with error recovery
3. **Comprehensive Routing**: Smart message routing based on user status
4. **Production Ready**: Comprehensive error handling and logging
5. **Maintainable**: Well-documented, testable code

## Future Enhancements

- Add edit history tracking
- Implement edit timeouts
- Add more sophisticated edit instruction parsing
- Support for multi-step editing workflows 