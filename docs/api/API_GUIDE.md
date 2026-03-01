# Illness Prediction System API Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Rate Limiting](#rate-limiting)
5. [API Endpoints](#api-endpoints)
6. [Usage Examples](#usage-examples)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [SDKs and Libraries](#sdks-and-libraries)

## Introduction

The Illness Prediction System API provides a conversational interface for collecting symptoms and predicting potential illnesses using machine learning. The API supports multiple communication channels (Web, SMS, WhatsApp) and languages.

### Key Features

- **Conversational Interface**: Natural language symptom collection
- **Multi-Channel Support**: Web, SMS, and WhatsApp
- **Multi-Language**: English, Spanish, French, Hindi, and Mandarin
- **Intelligent Questioning**: AI-driven follow-up questions
- **Explainable Predictions**: SHAP-based explanations
- **Privacy-First**: HIPAA/GDPR compliant

### Base URLs

- **Production**: `https://api.illnessprediction.example.com/v1`
- **Staging**: `https://staging-api.illnessprediction.example.com/v1`
- **Local Development**: `http://localhost:8000`

## Getting Started

### Prerequisites

- API key (optional, but recommended for production)
- HTTP client (curl, Postman, or programming language HTTP library)

### Quick Start

1. **Check API Health**

```bash
curl https://api.illnessprediction.example.com/v1/health
```

2. **Create a Session**

```bash
curl -X POST https://api.illnessprediction.example.com/v1/sessions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "channel": "web",
    "user_id": "user_12345",
    "language": "en"
  }'
```

3. **Send a Message**

```bash
curl -X POST https://api.illnessprediction.example.com/v1/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "message": "I have a fever and headache for 2 days"
  }'
```

## Authentication

### API Key Authentication

The API uses API key authentication via the `X-API-Key` header.

**Header Format:**
```
X-API-Key: your-api-key-here
```

**Example:**
```bash
curl -H "X-API-Key: sk_live_abc123xyz789" \
  https://api.illnessprediction.example.com/v1/sessions
```

### Obtaining an API Key

1. Sign up at the developer portal
2. Navigate to API Keys section
3. Generate a new API key
4. Store the key securely (it won't be shown again)

### Security Best Practices

- **Never expose API keys** in client-side code
- **Use environment variables** to store keys
- **Rotate keys regularly** (every 90 days recommended)
- **Use different keys** for development, staging, and production
- **Revoke compromised keys** immediately

### Authentication Errors

**401 Unauthorized - Missing API Key:**
```json
{
  "error": "API key is required",
  "status_code": 401,
  "path": "/sessions"
}
```

**401 Unauthorized - Invalid API Key:**
```json
{
  "error": "Invalid API key",
  "status_code": 401,
  "path": "/sessions"
}
```

## Rate Limiting

### Limits

All endpoints (except health checks and documentation) are rate limited to:

- **60 requests per minute** per client

Rate limits are applied per API key (if authenticated) or per IP address (if not authenticated).

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
```

- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window

### Rate Limit Exceeded

When the rate limit is exceeded, the API returns HTTP 429:

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

**Response Headers:**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

### Handling Rate Limits

**Exponential Backoff Strategy:**

```python
import time
import requests

def make_request_with_backoff(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            wait_time = retry_after * (2 ** attempt)  # Exponential backoff
            print(f"Rate limited. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

**Check Remaining Requests:**

```python
response = requests.get(url, headers=headers)
remaining = int(response.headers.get('X-RateLimit-Remaining', 0))

if remaining < 10:
    print(f"Warning: Only {remaining} requests remaining")
```

## API Endpoints

### Health Check

**GET /health**

Check API health and service status.

- **Authentication**: Not required
- **Rate Limit**: Not applied

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "api": "operational",
    "database": "operational",
    "ml_model": "operational",
    "cache": "operational"
  }
}
```

### Session Management

#### Create Session

**POST /sessions**

Create a new conversation session.

**Request:**
```json
{
  "channel": "web",
  "user_id": "user_12345",
  "language": "en"
}
```

**Parameters:**
- `channel` (required): Communication channel - `web`, `sms`, or `whatsapp`
- `user_id` (required): Anonymized user identifier
- `language` (optional): Language code - `en`, `es`, `fr`, `hi`, or `zh` (default: `en`)

**Response (201 Created):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_12345",
  "channel": "web",
  "language": "en",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "last_active": "2024-01-15T10:30:00Z",
  "message": "Session created successfully"
}
```

#### Get Session State

**GET /sessions/{session_id}**

Retrieve session state and information.

**Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_12345",
  "channel": "web",
  "language": "en",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "last_active": "2024-01-15T10:35:00Z",
  "message_count": 6,
  "symptom_count": 3,
  "question_count": 2
}
```

#### Delete Session

**DELETE /sessions/{session_id}**

Delete all session data (GDPR/HIPAA compliance).

**Response (204 No Content)**

### Message Processing

#### Send Message

**POST /sessions/{session_id}/messages**

Send a user message in a conversation.

**Request:**
```json
{
  "message": "I have a fever and headache for 2 days"
}
```

**Response - Follow-up Question (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Do you have any difficulty breathing or chest pain?",
  "predictions": null,
  "requires_input": true,
  "session_status": "active"
}
```

**Response - Predictions (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Based on your symptoms, here are the most likely conditions:",
  "predictions": [
    {
      "illness": "Influenza",
      "confidence_score": 0.85,
      "severity": "moderate",
      "explanation": "Your fever, headache, and sore throat are common flu symptoms",
      "treatment_suggestions": {
        "medications": ["Acetaminophen", "Ibuprofen"],
        "non_medication": ["Rest", "Hydration", "Warm liquids"],
        "disclaimer": "These are general suggestions. Consult a healthcare professional.",
        "seek_professional": false
      }
    },
    {
      "illness": "Common Cold",
      "confidence_score": 0.65,
      "severity": "low",
      "explanation": "Similar symptoms but typically milder"
    }
  ],
  "requires_input": false,
  "session_status": "completed"
}
```

### Webhooks

#### SMS Webhook

**POST /webhooks/sms**

Receive SMS messages from Twilio.

**Content-Type**: `application/x-www-form-urlencoded`

**Parameters:**
- `From`: Sender phone number
- `Body`: Message content
- `MessageSid`: Twilio message identifier
- `To`: Recipient phone number

#### WhatsApp Webhook

**POST /webhooks/whatsapp**

Receive WhatsApp messages from WhatsApp Business API.

**Content-Type**: `application/json`

**Request:**
```json
{
  "from": "+1234567890",
  "body": "I have a fever",
  "text": {
    "body": "I have a fever"
  }
}
```

## Usage Examples

### Example 1: Complete Conversation Flow (Python)

```python
import requests

BASE_URL = "https://api.illnessprediction.example.com/v1"
API_KEY = "your-api-key"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Step 1: Create a session
session_response = requests.post(
    f"{BASE_URL}/sessions",
    headers=headers,
    json={
        "channel": "web",
        "user_id": "user_12345",
        "language": "en"
    }
)
session_data = session_response.json()
session_id = session_data["session_id"]
print(f"Created session: {session_id}")

# Step 2: Send initial symptoms
message_response = requests.post(
    f"{BASE_URL}/sessions/{session_id}/messages",
    headers=headers,
    json={
        "message": "I have a fever and headache for 2 days"
    }
)
message_data = message_response.json()
print(f"System: {message_data['response']}")

# Step 3: Continue conversation
while message_data.get("requires_input"):
    user_input = input("You: ")
    
    message_response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/messages",
        headers=headers,
        json={"message": user_input}
    )
    message_data = message_response.json()
    print(f"System: {message_data['response']}")
    
    # Check for predictions
    if message_data.get("predictions"):
        print("\nPredictions:")
        for pred in message_data["predictions"]:
            print(f"  - {pred['illness']}: {pred['confidence_score']*100:.1f}% confidence")
            print(f"    Severity: {pred['severity']}")
            print(f"    {pred['explanation']}")
        break

# Step 4: Get final session state
state_response = requests.get(
    f"{BASE_URL}/sessions/{session_id}",
    headers=headers
)
state_data = state_response.json()
print(f"\nSession completed:")
print(f"  Messages: {state_data['message_count']}")
print(f"  Symptoms: {state_data['symptom_count']}")
print(f"  Questions: {state_data['question_count']}")

# Step 5: Delete session data (optional)
requests.delete(f"{BASE_URL}/sessions/{session_id}", headers=headers)
print("Session data deleted")
```

### Example 2: Multi-Language Support (JavaScript)

```javascript
const axios = require('axios');

const BASE_URL = 'https://api.illnessprediction.example.com/v1';
const API_KEY = 'your-api-key';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
};

async function createSpanishSession() {
  try {
    // Create session in Spanish
    const sessionResponse = await axios.post(
      `${BASE_URL}/sessions`,
      {
        channel: 'web',
        user_id: 'user_67890',
        language: 'es'  // Spanish
      },
      { headers }
    );
    
    const sessionId = sessionResponse.data.session_id;
    console.log(`Sesión creada: ${sessionId}`);
    
    // Send message in Spanish
    const messageResponse = await axios.post(
      `${BASE_URL}/sessions/${sessionId}/messages`,
      {
        message: 'Tengo fiebre y dolor de cabeza desde hace 2 días'
      },
      { headers }
    );
    
    console.log(`Sistema: ${messageResponse.data.response}`);
    
    return sessionId;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

createSpanishSession();
```

### Example 3: Error Handling (Python)

```python
import requests
from requests.exceptions import RequestException

def safe_api_call(url, method='GET', **kwargs):
    """Make API call with comprehensive error handling."""
    try:
        response = requests.request(method, url, **kwargs)
        
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retry after {retry_after} seconds")
            return None
        
        # Check for authentication errors
        if response.status_code == 401:
            print("Authentication failed. Check your API key.")
            return None
        
        # Check for not found
        if response.status_code == 404:
            print("Resource not found")
            return None
        
        # Check for bad request
        if response.status_code == 400:
            error_data = response.json()
            print(f"Bad request: {error_data.get('error')}")
            return None
        
        # Check for server errors
        if response.status_code >= 500:
            print("Server error. Please try again later.")
            return None
        
        # Success
        response.raise_for_status()
        return response.json()
    
    except RequestException as e:
        print(f"Network error: {str(e)}")
        return None

# Usage
data = safe_api_call(
    f"{BASE_URL}/sessions",
    method='POST',
    headers=headers,
    json={"channel": "web", "user_id": "user_123"}
)

if data:
    print(f"Session created: {data['session_id']}")
```

### Example 4: Session Management (cURL)

```bash
#!/bin/bash

BASE_URL="https://api.illnessprediction.example.com/v1"
API_KEY="your-api-key"

# Create session
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "channel": "web",
    "user_id": "user_12345",
    "language": "en"
  }')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Created session: $SESSION_ID"

# Send message
MESSAGE_RESPONSE=$(curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "message": "I have a fever and headache"
  }')

echo "Response: $(echo $MESSAGE_RESPONSE | jq -r '.response')"

# Get session state
STATE_RESPONSE=$(curl -s -X GET "$BASE_URL/sessions/$SESSION_ID" \
  -H "X-API-Key: $API_KEY")

echo "Session state: $(echo $STATE_RESPONSE | jq '.')"

# Delete session
curl -s -X DELETE "$BASE_URL/sessions/$SESSION_ID" \
  -H "X-API-Key: $API_KEY"

echo "Session deleted"
```

### Example 5: Webhook Integration (Python/Flask)

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_BASE_URL = "https://api.illnessprediction.example.com/v1"
API_KEY = "your-api-key"

@app.route('/webhooks/sms', methods=['POST'])
def handle_sms():
    """Handle incoming SMS from Twilio."""
    from_number = request.form.get('From')
    message_body = request.form.get('Body')
    
    # Forward to illness prediction API
    response = requests.post(
        f"{API_BASE_URL}/webhooks/sms",
        data={
            'From': from_number,
            'Body': message_body,
            'MessageSid': request.form.get('MessageSid'),
            'To': request.form.get('To')
        }
    )
    
    return jsonify(response.json())

@app.route('/webhooks/whatsapp', methods=['POST'])
def handle_whatsapp():
    """Handle incoming WhatsApp messages."""
    data = request.json
    
    # Forward to illness prediction API
    response = requests.post(
        f"{API_BASE_URL}/webhooks/whatsapp",
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(port=5000)
```

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request succeeded, no content to return |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Invalid or missing API key |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

All errors return a JSON object:

```json
{
  "error": "Error message",
  "status_code": 400,
  "path": "/sessions"
}
```

### Common Errors

**Invalid Channel:**
```json
{
  "error": "Invalid channel. Must be one of: sms, whatsapp, web",
  "status_code": 400,
  "path": "/sessions"
}
```

**Session Not Found:**
```json
{
  "error": "Session 550e8400-e29b-41d4-a716-446655440000 not found",
  "status_code": 404,
  "path": "/sessions/550e8400-e29b-41d4-a716-446655440000"
}
```

**Session Expired:**
```json
{
  "error": "Session has expired (inactive for >24 hours)",
  "status_code": 400,
  "path": "/sessions/550e8400-e29b-41d4-a716-446655440000/messages"
}
```

## Best Practices

### 1. Session Management

- **Create one session per user conversation**
- **Store session IDs** securely on the client side
- **Resume sessions** when users return within 24 hours
- **Delete sessions** when conversation is complete (GDPR compliance)

### 2. Message Processing

- **Send complete messages** - include all relevant information
- **Wait for responses** before sending next message
- **Handle predictions gracefully** - check for `predictions` field
- **Respect `requires_input` flag** - don't send messages when false

### 3. Error Handling

- **Implement retry logic** with exponential backoff
- **Handle rate limits** gracefully
- **Log errors** for debugging
- **Provide user feedback** for errors

### 4. Security

- **Never expose API keys** in client-side code
- **Use HTTPS** for all requests
- **Validate user input** before sending to API
- **Implement CSRF protection** for webhooks

### 5. Performance

- **Reuse HTTP connections** (connection pooling)
- **Cache session IDs** to avoid repeated lookups
- **Monitor rate limits** to avoid throttling
- **Use async/await** for non-blocking operations

### 6. Privacy

- **Anonymize user identifiers** before sending to API
- **Don't include PII** in messages
- **Delete sessions** when no longer needed
- **Comply with GDPR/HIPAA** requirements

## SDKs and Libraries

### Official SDKs

Coming soon:
- Python SDK
- JavaScript/TypeScript SDK
- Java SDK
- Ruby SDK

### Community Libraries

Check our GitHub organization for community-contributed libraries.

### HTTP Clients

The API works with any HTTP client:

**Python:**
- `requests`
- `httpx`
- `aiohttp`

**JavaScript:**
- `axios`
- `fetch`
- `node-fetch`

**Java:**
- `OkHttp`
- `Apache HttpClient`

**Ruby:**
- `httparty`
- `faraday`

## Support

### Documentation

- **API Reference**: `/docs` (Swagger UI)
- **OpenAPI Spec**: `/openapi.json`
- **ReDoc**: `/redoc`

### Contact

- **Email**: support@illnessprediction.example.com
- **GitHub**: https://github.com/illness-prediction/api
- **Status Page**: https://status.illnessprediction.example.com

### Rate Limit Increases

For higher rate limits, contact our sales team at sales@illnessprediction.example.com
