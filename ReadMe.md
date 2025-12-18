# Customer Support Chatbot

A prototype customer support chatbot for a computer products company, built with OpenAI and MCP (Model Context Protocol).

## 🎨 Chat UI

**NEW!** A beautiful, modern web-based chat interface is now available!

### Quick Start:
```bash
# Start the server
uv run python run_server.py
# Or: python run_server.py

# Open in browser
http://localhost:8000
```

### Features:
- 💬 **Modern Chat Interface** - Beautiful Tailwind CSS design
- 🔒 **Customer Authentication** - Secure login with email and PIN
- 🔄 **Session Management** - Maintains conversation context
- 📱 **Responsive Design** - Works on all devices
- ⚡ **Real-time Status** - Connection and processing indicators
- 🎯 **Easy to Use** - Just type and send messages
- 🛒 **Order Management** - Place and track orders (authenticated users)

**See `CHAT-UI-SUMMARY.md` for complete details and `UI-SETUP.md` for setup guide.**

### 🔐 New: Customer Authentication Flow

The chatbot now includes a proper customer authentication system:
- **First-time users** are greeted and asked for their email and 4-digit PIN
- **Authenticated users** can place orders and view order history
- **Unauthenticated users** can still browse products and get information
- Each session maintains its own authentication state

**See `CUSTOMER-FLOW.md` for detailed documentation and `AUTH-IMPLEMENTATION-SUMMARY.md` for technical details.**

## Setup

### Prerequisites

- Python 3.11 or higher
- OpenAI API key

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file in the root directory:
```
OPENAI_API_KEY=your_openai_api_key_here
MCP_SERVER_URL=https://vipfapwm3x.us-east-1.awsapprunner.com/mcp
```

3. Test the integrated chat system:
```bash
python main.py
```

## Project Structure

- `app.py` - **FastAPI server with REST API endpoints**
- `llm_client.py` - OpenAI LLM client for all LLM interactions
- `mcp_client.py` - MCP server client for accessing company features
- `chat_util.py` - **Chat module that integrates LLM + MCP with automatic tool calling**
- `main.py` - Main entry point with demo examples
- `run_server.py` - Script to run the FastAPI server
- `requirements.txt` - Python dependencies

## LLM Client Usage

The LLM client is configured to use `gpt-4o-mini` by default for cost efficiency.

### Basic Usage

```python
from llm_client import get_llm_client

# Get client instance
llm = get_llm_client()

# Simple chat completion
response = await llm.chat_completion_simple(
    user_message="Hello!",
    system_message="You are a helpful assistant."
)
```

### Advanced Usage

```python
# With conversation history
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"}
]

response = await llm.chat_completion(
    messages=messages,
    temperature=0.7,
    max_tokens=500
)

# Streaming responses
async for chunk in llm.chat_completion_stream(messages=messages):
    print(chunk, end="", flush=True)
```

## Chat Module Usage (Recommended)

The `chat_util.py` module integrates the LLM client with the MCP client, automatically handling tool calls.

### Basic Chat Usage

```python
from chat_util import get_chat_session

# Create or get a chat session
session = await get_chat_session(session_id="user-123")

# Chat with automatic tool calling
response = await session.chat("Show me all available monitors")
print(response)
```

### Streaming Chat

```python
# Stream responses (tool calls handled automatically)
async for chunk in session.chat_stream("What printers do you have?"):
    print(chunk, end="", flush=True)
```

### Session Management

```python
# Get conversation history
history = session.get_history()

# Reset conversation
session.reset()

# Delete session
from chat_util import delete_session
delete_session("user-123")
```

### Features

- **Automatic Tool Calling**: When the LLM needs to call MCP tools, it happens automatically
- **Conversation History**: Maintains context across multiple messages
- **Session Management**: Multiple concurrent chat sessions supported
- **Streaming Support**: Real-time response streaming available

## Running the API Server

Start the FastAPI server:

```bash
python run_server.py
# or
python app.py
# or
uvicorn app:app --reload
```

The server will start on `http://localhost:8000` by default.

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Session Management

### How Session IDs Work

The API uses session IDs to maintain conversation context across multiple messages:

**Option 1: Auto-generate on first message (Recommended)**
1. Send first message WITHOUT `session_id`
2. Server generates a UUID and returns it
3. Save the `session_id` from response
4. Include it in all subsequent messages

```javascript
// First message - no session_id
const response1 = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message: 'Hello' })
});
const data1 = await response1.json();
const sessionId = data1.session_id; // Save this!

// Second message - include session_id
const response2 = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ 
    message: 'Show me monitors',
    session_id: sessionId  // Use saved session_id
  })
});
```

**Option 2: Pre-create session**
1. Call `POST /api/session/new` to get a session_id upfront
2. Use that session_id in all chat requests

```javascript
// Pre-create session
const newSession = await fetch('/api/session/new', { method: 'POST' });
const { session_id } = await newSession.json();

// Use in chat requests
await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message: 'Hello', session_id })
});
```

## API Endpoints

### Core Endpoints (from Plan.md)

#### `POST /api/chat`
Send a chat message and get a response.

**Request Body:**
```json
{
  "message": "Show me all monitors",
  "session_id": "optional-session-id",
  "stream": false
}
```

**Note:** `temperature` and `max_tokens` are configured server-side for consistent, professional responses and cost control. They cannot be set by users.

**Response:**
```json
{
  "response": "Here are the available monitors...",
  "session_id": "uuid-here",
  "tool_calls": null
}
```

#### `GET /api/chat/stream`
Streaming chat endpoint (alternative to POST with stream=true).

**Query Parameters:**
- `message` (required): User message
- `session_id` (optional): Session ID

**Response:** Server-Sent Events (SSE) stream

#### `GET /api/tools`
Get list of available MCP tools.

**Response:**
```json
{
  "tools": [
    {
      "name": "list_products",
      "description": "List products...",
      "parameters": {...}
    }
  ]
}
```

#### `POST /api/reset/{session_id}`
Reset a chat session (clear conversation history).

**Response:**
```json
{
  "status": "success",
  "message": "Session reset",
  "session_id": "uuid-here"
}
```

### Additional Helpful Endpoints

#### `POST /api/session/new`
Create a new session ID upfront (before sending any messages).

**Response:**
```json
{
  "status": "success",
  "message": "New session created",
  "session_id": "abc-123-def-456"
}
```

**Use Case:** If you want to get a session ID before the user types their first message.

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### `GET /api/session/{session_id}`
Get information about a chat session (history, message count, authentication status).

**Response:**
```json
{
  "session_id": "uuid-here",
  "message_count": 5,
  "history": [...],
  "is_authenticated": true,
  "customer_info": {
    "customer_id": "uuid",
    "name": "Alice Johnson",
    "email": "alice@example.com"
  }
}
```

#### `GET /api/sessions`
List all active chat sessions (useful for debugging/admin).

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "uuid-1",
      "message_count": 3,
      "last_message": {...}
    }
  ],
  "count": 1
}
```

#### `DELETE /api/reset/{session_id}`
Delete a chat session completely (alternative to POST reset).

### Static Files

#### `GET /static/*`
Serve static files (HTML, CSS, JS) for the UI.

## API Usage Examples

### Python Example

```python
import requests

# Send a chat message
response = requests.post(
    "http://localhost:8000/api/chat",
    json={
        "message": "What monitors do you have?",
        "session_id": "my-session-123"
    }
)
print(response.json())
```

### JavaScript/Fetch Example

```javascript
const response = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Show me all products',
    session_id: 'user-123'
  })
});
const data = await response.json();
console.log(data.response);
```

### Streaming Example (JavaScript)

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/chat/stream?message=Hello&session_id=user-123`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.chunk) {
    console.log(data.chunk); // Stream chunk
  } else if (data.done) {
    eventSource.close();
  }
};
```

## Testing

### Test Authentication Flow

Run the automated test script:
```bash
python test_auth_flow.py
```

This will test:
- Session creation
- Initial greeting
- Product browsing (without auth)
- Customer authentication
- Order placement (with auth)
- Session isolation

### Test Credentials

To test the authentication system, you'll need valid customer credentials from your database. See `GET-TEST-CREDENTIALS.md` for instructions on obtaining test customer data.

Example test conversation:
```
User: Hello
Assistant: [Greets and asks for credentials]

User: My email is alice@example.com and PIN is 1234
Assistant: [Authenticates and welcomes by name]

User: Show me monitors
Assistant: [Lists monitors]

User: I want to order MON-0054
Assistant: [Places order - works because user is authenticated]
```

## Development

The project uses:
- **OpenAI API** for LLM interactions
- **FastAPI** for the web server
- **MCP** for accessing company product data

## Documentation

- `ReadMe.md` - This file, main project documentation
- `CUSTOMER-FLOW.md` - Detailed customer authentication flow documentation
- `AUTH-IMPLEMENTATION-SUMMARY.md` - Technical implementation details
- `GET-TEST-CREDENTIALS.md` - Guide to obtaining test customer credentials
- `CHAT-UI-SUMMARY.md` - Chat UI documentation
- `UI-SETUP.md` - UI setup guide
- `docs/Assessment.md` - Project requirements
- `docs/Plan.md` - Implementation plan

