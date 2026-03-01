# API Quick Reference

## Base URLs

- **Production**: `https://api.illnessprediction.example.com/v1`
- **Staging**: `https://staging-api.illnessprediction.example.com/v1`
- **Local**: `http://localhost:8000`

## Authentication

```http
X-API-Key: your-api-key-here
```

## Rate Limits

- **60 requests per minute** per client
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- 429 response when exceeded

## Quick Start

### 1. Create Session

```bash
curl -X POST $BASE_URL/sessions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "user_id": "user_123",
    "language": "en"
  }'
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "message": "Session created successfully"
}
```

### 2. Send Message

```bash
curl -X POST $BASE_URL/sessions/$SESSION_ID/messages \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have a fever and headache"
  }'
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Do you have any other symptoms?",
  "predictions": null,
  "requires_input": true,
  "session_status": "active"
}
```

### 3. Get Session State

```bash
curl -X GET $BASE_URL/sessions/$SESSION_ID \
  -H "X-API-Key: $API_KEY"
```

### 4. Delete Session

```bash
curl -X DELETE $BASE_URL/sessions/$SESSION_ID \
  -H "X-API-Key: $API_KEY"
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | API information |
| POST | `/sessions` | Create session |
| GET | `/sessions/{id}` | Get session state |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/messages` | Send message |
| POST | `/webhooks/sms` | SMS webhook |
| POST | `/webhooks/whatsapp` | WhatsApp webhook |

## Request Examples

### Python

```python
import requests

headers = {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
}

# Create session
response = requests.post(
    'https://api.illnessprediction.example.com/v1/sessions',
    headers=headers,
    json={
        'channel': 'web',
        'user_id': 'user_123',
        'language': 'en'
    }
)

session_id = response.json()['session_id']

# Send message
response = requests.post(
    f'https://api.illnessprediction.example.com/v1/sessions/{session_id}/messages',
    headers=headers,
    json={'message': 'I have a fever'}
)

print(response.json())
```

### JavaScript

```javascript
const axios = require('axios');

const headers = {
  'X-API-Key': 'your-api-key',
  'Content-Type': 'application/json'
};

// Create session
const sessionResponse = await axios.post(
  'https://api.illnessprediction.example.com/v1/sessions',
  {
    channel: 'web',
    user_id: 'user_123',
    language: 'en'
  },
  { headers }
);

const sessionId = sessionResponse.data.session_id;

// Send message
const messageResponse = await axios.post(
  `https://api.illnessprediction.example.com/v1/sessions/${sessionId}/messages`,
  { message: 'I have a fever' },
  { headers }
);

console.log(messageResponse.data);
```

### cURL

```bash
# Set variables
export API_KEY="your-api-key"
export BASE_URL="https://api.illnessprediction.example.com/v1"

# Create session
SESSION_ID=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"channel":"web","user_id":"user_123","language":"en"}' \
  | jq -r '.session_id')

# Send message
curl -X POST "$BASE_URL/sessions/$SESSION_ID/messages" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"I have a fever"}'
```

## Response Formats

### Session Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "channel": "web",
  "language": "en",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "last_active": "2024-01-15T10:30:00Z",
  "message": "Session created successfully"
}
```

### Message Response (Question)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Do you have any difficulty breathing?",
  "predictions": null,
  "requires_input": true,
  "session_status": "active"
}
```

### Message Response (Predictions)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Based on your symptoms, here are the most likely conditions:",
  "predictions": [
    {
      "illness": "Influenza",
      "confidence_score": 0.85,
      "severity": "moderate",
      "explanation": "Your fever and headache are common flu symptoms",
      "treatment_suggestions": {
        "medications": ["Acetaminophen", "Ibuprofen"],
        "non_medication": ["Rest", "Hydration"],
        "disclaimer": "Consult a healthcare professional",
        "seek_professional": false
      }
    }
  ],
  "requires_input": false,
  "session_status": "completed"
}
```

### Session State Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
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

## Error Responses

### 400 Bad Request

```json
{
  "error": "Invalid channel. Must be one of: sms, whatsapp, web",
  "status_code": 400,
  "path": "/sessions"
}
```

### 401 Unauthorized

```json
{
  "error": "API key is required",
  "status_code": 401,
  "path": "/sessions"
}
```

### 404 Not Found

```json
{
  "error": "Session 550e8400-e29b-41d4-a716-446655440000 not found",
  "status_code": 404,
  "path": "/sessions/550e8400-e29b-41d4-a716-446655440000"
}
```

### 429 Too Many Requests

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred. Please try again later.",
  "path": "/sessions"
}
```

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

## Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `hi` | Hindi |
| `zh` | Mandarin |

## Supported Channels

| Channel | Description |
|---------|-------------|
| `web` | Web interface |
| `sms` | SMS messaging |
| `whatsapp` | WhatsApp messaging |

## Session Statuses

| Status | Description |
|--------|-------------|
| `active` | Session is active and accepting messages |
| `completed` | Session has completed with predictions |
| `expired` | Session has expired (>24 hours inactive) |

## Severity Levels

| Level | Description |
|-------|-------------|
| `low` | Minor condition, self-care appropriate |
| `moderate` | May require medical consultation |
| `high` | Should seek medical attention soon |
| `critical` | Seek immediate medical attention |

## Best Practices

1. **Store session IDs** - Save session_id for resuming conversations
2. **Check requires_input** - Don't send messages when false
3. **Handle rate limits** - Implement exponential backoff
4. **Monitor remaining requests** - Check X-RateLimit-Remaining header
5. **Delete sessions** - Clean up when done (GDPR compliance)
6. **Use HTTPS** - Always use secure connections
7. **Secure API keys** - Never expose in client-side code

## Common Patterns

### Complete Conversation

```python
# 1. Create session
session = create_session()

# 2. Send initial symptoms
response = send_message(session['session_id'], "I have a fever")

# 3. Continue until predictions received
while response['requires_input']:
    user_input = input("You: ")
    response = send_message(session['session_id'], user_input)

# 4. Display predictions
for pred in response['predictions']:
    print(f"{pred['illness']}: {pred['confidence_score']*100:.1f}%")

# 5. Clean up
delete_session(session['session_id'])
```

### Error Handling

```python
try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        # Rate limited - wait and retry
        time.sleep(60)
        return make_request(url, headers, data)
    elif e.response.status_code == 401:
        # Authentication failed
        print("Invalid API key")
    else:
        # Other error
        print(f"Error: {e.response.json()}")
```

### Rate Limit Handling

```python
response = requests.post(url, headers=headers, json=data)

# Check remaining requests
remaining = int(response.headers.get('X-RateLimit-Remaining', 0))

if remaining < 10:
    print(f"Warning: Only {remaining} requests remaining")
    time.sleep(5)  # Slow down
```

## Resources

- **API Documentation**: https://api.illnessprediction.example.com/docs
- **OpenAPI Spec**: https://api.illnessprediction.example.com/openapi.json
- **ReDoc**: https://api.illnessprediction.example.com/redoc
- **Status Page**: https://status.illnessprediction.example.com
- **Support**: support@illnessprediction.example.com

## SDK Support

Coming soon:
- Python SDK
- JavaScript/TypeScript SDK
- Java SDK
- Ruby SDK

## Changelog

### v1.0.0 (2024-01-15)
- Initial release
- Session management endpoints
- Message processing
- SMS and WhatsApp webhooks
- Multi-language support
- Rate limiting
- API key authentication
