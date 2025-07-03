# Project Structure

This project has been refactored from a monolithic `slack.py` file into a clean, modular architecture. Here's how the code is organized:

## 📁 File Structure

```
slack_integration/
├── config.py              # Configuration management
├── models.py              # Data models and exceptions
├── message_store.py       # Thread-safe message storage
├── timer_manager.py       # Batch timeout timer management
├── ml_processor.py        # ML integration (real + mock)
├── message_recovery.py    # Background message recovery system
├── slack_handler.py       # Main Slack event handling
├── app.py                # Flask application and API routes
├── main.py               # Main entry point
├── slack.py              # Backward compatibility entry point
└── README.md             # Documentation
```

## 🔧 Module Responsibilities

### `config.py`
- Environment variable management
- Configuration validation
- Provides configuration dictionaries for different components

### `models.py`
- `SlackMessage` dataclass with message data and metadata
- `MLProcessorError` custom exception
- Data transformation methods

### `message_store.py`
- Thread-safe message storage using `threading.RLock()`
- Groups messages by channel and thread
- Provides statistics and cleanup methods

### `timer_manager.py`
- Manages batch timeout timers using `threading.Timer`
- Thread-safe timer operations
- Handles timer callbacks for batch processing

### `ml_processor.py`
- `MLProcessor`: Real ML endpoint integration with retry logic
- `MockMLProcessor`: Fallback for testing/development
- Health checking and connection management

### `message_recovery.py`
- Background service to recover dropped messages
- Uses Slack's `conversations.history` API
- Rate limiting and duplicate prevention
- Automatic integration with main message processing pipeline

### `slack_handler.py`
- Main Slack Socket Mode connection handling
- Event processing and message filtering
- Bot identification and user lookup
- Integration of all components (store, timers, ML, recovery)

### `app.py`
- Flask application setup
- All HTTP API endpoints:
  - `/health` - Health check
  - `/stats` - Runtime statistics  
  - `/ready` - Readiness probe
  - `/status` - Application status
  - `/debug` - Debug information
  - `/outcomes/<channel_id>` - Message outcomes

### `main.py`
- Application entry point
- Logging configuration
- Signal handling for graceful shutdown
- Flask server startup

### `slack.py`
- Backward compatibility entry point
- Simply imports and runs `main.py`

## 🏃‍♂️ Running the Application

### Option 1: Use main.py (recommended)
```bash
python main.py
```

### Option 2: Use slack.py (backward compatibility)
```bash
python slack.py
```

### Option 3: Specify port
```bash
PORT=5001 python main.py
```

## ✅ Benefits of Modular Structure

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Testability**: Components can be tested independently
3. **Maintainability**: Changes are isolated to specific modules
4. **Reusability**: Components can be reused or replaced easily
5. **Readability**: Code is much easier to understand and navigate
6. **Debugging**: Issues can be isolated to specific modules
7. **Development**: Multiple developers can work on different modules

## 🔄 Import Dependencies

```
config.py               (no internal dependencies)
models.py               (no internal dependencies)
message_store.py        → models
timer_manager.py        (no internal dependencies)
ml_processor.py         → config, models
message_recovery.py     (no internal dependencies - gets slack_handler via constructor)
slack_handler.py        → config, message_store, timer_manager, ml_processor, message_recovery
app.py                  → config, slack_handler
main.py                 → config, app
slack.py                → main
```

## 🧪 Testing Individual Components

You can now test individual components in isolation:

```python
# Test configuration
from config import Config
print(Config.BATCH_TIMEOUT_SECONDS)

# Test message store
from message_store import MessageStore
store = MessageStore()
store.add_message("channel", None, "user", "name", "hello")

# Test ML processor
from ml_processor import MockMLProcessor
processor = MockMLProcessor()
# ... and so on
```

## 🚀 Production Deployment

The modular structure makes it easier to:
- Replace components (e.g., use Redis instead of in-memory storage)
- Add monitoring to specific components
- Scale individual components if needed
- Deploy with different configurations

## 🔧 Extending the Application

To add new functionality:
1. Create a new module with clear responsibilities
2. Add imports to the appropriate files
3. Update `slack_handler.py` or `app.py` to integrate the new component
4. Update this documentation

The modular structure makes the codebase much more maintainable and easier to extend! 