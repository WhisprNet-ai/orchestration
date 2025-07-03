# Slack ML Integration Bot

A Flask-based Slack bot that batches messages and sends them to an ML endpoint for processing.

## Features

### 🔄 **Message Recovery System** (New!)
- **Automatic Detection**: Detects messages dropped by Slack's real-time events
- **Background Recovery**: Uses `conversations.history` API to recover missing messages
- **Complete Batching**: Ensures all messages are processed together
- **Rate Limiting Protection**: Intelligent checking to avoid API limits
- **Duplicate Prevention**: Prevents processing the same message twice

### 📦 **Message Batching**
- Groups messages by channel and thread
- Configurable 20-second timeout (customizable via `BATCH_TIMEOUT_SECONDS`)
- Maximum batch size of 50 messages (customizable via `MAX_BATCH_SIZE`)
- Thread-safe message storage

### 🤖 **ML Integration**
- Sends batched messages to external ML endpoint as JSON
- Automatic fallback to mock processor if ML service unavailable
- Health check monitoring
- Configurable timeout and retry settings

### 🔍 **Monitoring & Debugging**
- Comprehensive logging with emoji indicators
- Multiple health check endpoints
- Debug endpoints for inspecting message store
- Real-time statistics

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-your-bot-token"
   export SLACK_APP_TOKEN="xapp-your-app-token"
   export ML_MODEL_ENDPOINT="http://your-ml-endpoint:5000/process"
   ```

3. **Run the Bot**:
   ```bash
   python slack.py
   ```

## How Message Recovery Works

The message recovery system solves the common issue where Slack's real-time events drop messages during rapid message sequences:

1. **Real-time Processing**: Messages are processed as they arrive via Socket Mode
2. **Background Monitoring**: Every 10 seconds, checks for missing messages using `conversations.history`
3. **Gap Detection**: Compares received messages with actual channel history
4. **Automatic Recovery**: Processes any missing messages through the normal pipeline
5. **Complete Batching**: All messages (real-time + recovered) are batched together

### Example Scenario
```
User sends: "a", "b", "c", "d" (rapidly)
Real-time events: Only "a" and "d" received
Recovery system: Detects and recovers "b" and "c"
Final batch: All 4 messages processed together ✅
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | Required | Slack bot token (xoxb-...) |
| `SLACK_APP_TOKEN` | Required | Slack app token (xapp-...) |
| `ML_MODEL_ENDPOINT` | Required | ML service endpoint URL |
| `BATCH_TIMEOUT_SECONDS` | 20 | Seconds to wait before processing batch |
| `MAX_BATCH_SIZE` | 50 | Maximum messages per batch |
| `ML_MODEL_TIMEOUT` | 10 | ML request timeout in seconds |
| `ML_MODEL_RETRIES` | 3 | Number of retry attempts |
| `PORT` | 5000 | Flask server port |
| `LOG_LEVEL` | INFO | Logging level |

### Message Recovery Settings

The recovery system is automatically configured with:
- **Check Interval**: 10 seconds
- **Lookback Window**: 30 seconds
- **Rate Limiting**: 15 seconds minimum between channel checks
- **Memory Management**: Automatic cleanup of processed message IDs

## API Endpoints

### Health & Monitoring
- `GET /health` - Health check with component status
- `GET /ready` - Readiness check for Kubernetes
- `GET /stats` - Real-time statistics
- `GET /status` - Application status overview

### Debugging
- `GET /debug` - Detailed state inspection
- `GET /outcomes/<channel_id>` - Get processed messages for channel
- `GET /outcomes/<channel_id>/<thread_ts>` - Get processed messages for thread

## Logging

The bot provides detailed logging with emoji indicators:

```
📨 NEW MESSAGE #1: user=john, text='hello', channel=C123, thread=None
🔄 RECOVERING MESSAGE: user=jane, text='world', ts=1234567890
📦 Processing batch of 2 messages for C123/main
🤖 Starting ML processing for 2 messages
✅ ML processing successful
📤 Successfully posted response to Slack
```

## Architecture

### Core Components

1. **SlackHandler**: Manages Slack Socket Mode connection and events
2. **MessageStore**: Thread-safe storage for batched messages
3. **TimerManager**: Handles batch timeout timers
4. **MLProcessor**: Processes messages with ML endpoint
5. **MessageRecovery**: Background service for recovering dropped messages

### Threading Model

- **Main Thread**: Flask web server
- **Slack Thread**: Socket Mode connection handler
- **Recovery Thread**: Background message recovery service
- **Timer Threads**: Individual batch timeout handlers

## Troubleshooting

### Common Issues

1. **Messages Not Batching**: Check if `BATCH_TIMEOUT_SECONDS` is too low
2. **ML Endpoint Unreachable**: Bot automatically falls back to mock processor
3. **Rate Limiting**: Message recovery backs off automatically
4. **Memory Usage**: Processed message IDs are automatically cleaned up

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python slack.py
```

## Testing

Run the test suite:
```bash
pytest tests/
```

The tests cover:
- Message batching logic
- Timer management
- ML processor integration
- Error handling scenarios

## Production Deployment

For production deployment, consider:

1. **Use Gunicorn**: Replace Flask development server
2. **Environment Variables**: Secure configuration management
3. **Monitoring**: Set up application monitoring
4. **Scaling**: Message recovery system is designed for single-instance deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details. 