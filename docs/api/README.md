# Illness Prediction System API Documentation

Welcome to the Illness Prediction System API documentation. This directory contains comprehensive documentation for integrating with our AI-powered illness prediction API.

## 📚 Documentation Files

### [API Guide](./API_GUIDE.md)
Complete guide to using the API, including:
- Getting started
- Authentication
- Rate limiting
- All endpoints with examples
- Error handling
- Best practices
- Multi-language code examples (Python, JavaScript, Java, cURL)

### [OpenAPI Specification](./openapi.yaml)
Machine-readable API specification in OpenAPI 3.0 format:
- Complete endpoint definitions
- Request/response schemas
- Authentication schemes
- Error responses
- Can be imported into Postman, Insomnia, or other API tools

### [Authentication and Rate Limiting](./AUTHENTICATION_AND_RATE_LIMITING.md)
Detailed documentation on:
- API key authentication
- Obtaining and managing API keys
- Rate limiting policies
- Handling rate limits
- Security best practices
- Troubleshooting

### [Quick Reference](./QUICK_REFERENCE.md)
Quick reference guide with:
- Common request examples
- Response formats
- Status codes
- Error messages
- Best practices
- Common patterns

## 🚀 Quick Start

### 1. Get an API Key

Sign up at the [developer portal](https://developers.illnessprediction.example.com) to obtain your API key.

### 2. Make Your First Request

```bash
curl -X POST https://api.illnessprediction.example.com/v1/sessions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "user_id": "user_123",
    "language": "en"
  }'
```

### 3. Explore the API

Visit the interactive documentation:
- **Swagger UI**: https://api.illnessprediction.example.com/docs
- **ReDoc**: https://api.illnessprediction.example.com/redoc

## 📖 Key Concepts

### Sessions

A session represents a conversation between a user and the system. Each session:
- Has a unique identifier (UUID)
- Maintains conversation context
- Stores symptom information
- Expires after 24 hours of inactivity

### Channels

The API supports multiple communication channels:
- **Web**: Browser-based interactions
- **SMS**: Text message integration via Twilio
- **WhatsApp**: WhatsApp Business API integration

### Languages

Multi-language support for:
- English (`en`)
- Spanish (`es`)
- French (`fr`)
- Hindi (`hi`)
- Mandarin (`zh`)

### Predictions

The system provides:
- Top 3 most likely illnesses
- Confidence scores (30-100%)
- Severity levels (low, moderate, high, critical)
- Explainable predictions with SHAP values
- Treatment suggestions

## 🔐 Authentication

All API requests (except health checks) require authentication via API key:

```http
X-API-Key: your-api-key-here
```

See [Authentication and Rate Limiting](./AUTHENTICATION_AND_RATE_LIMITING.md) for details.

## ⚡ Rate Limiting

- **60 requests per minute** per client
- Rate limit headers included in all responses
- HTTP 429 when limit exceeded

See [Authentication and Rate Limiting](./AUTHENTICATION_AND_RATE_LIMITING.md) for handling strategies.

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/sessions` | Create session |
| GET | `/sessions/{id}` | Get session state |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/messages` | Send message |
| POST | `/webhooks/sms` | SMS webhook |
| POST | `/webhooks/whatsapp` | WhatsApp webhook |

## 💻 Code Examples

### Python

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "https://api.illnessprediction.example.com/v1"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Create session
response = requests.post(
    f"{BASE_URL}/sessions",
    headers=headers,
    json={
        "channel": "web",
        "user_id": "user_123",
        "language": "en"
    }
)

session_id = response.json()["session_id"]

# Send message
response = requests.post(
    f"{BASE_URL}/sessions/{session_id}/messages",
    headers=headers,
    json={"message": "I have a fever and headache"}
)

print(response.json())
```

### JavaScript

```javascript
const axios = require('axios');

const API_KEY = 'your-api-key';
const BASE_URL = 'https://api.illnessprediction.example.com/v1';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

// Create session
const sessionResponse = await axios.post(
  `${BASE_URL}/sessions`,
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
  `${BASE_URL}/sessions/${sessionId}/messages`,
  { message: 'I have a fever and headache' },
  { headers }
);

console.log(messageResponse.data);
```

## 🛠️ Tools and SDKs

### Import OpenAPI Spec

Import `openapi.yaml` into:
- **Postman**: File → Import → Upload openapi.yaml
- **Insomnia**: Create → Import → From File
- **Swagger Editor**: https://editor.swagger.io

### Official SDKs

Coming soon:
- Python SDK
- JavaScript/TypeScript SDK
- Java SDK
- Ruby SDK

### HTTP Clients

Works with any HTTP client:
- Python: `requests`, `httpx`, `aiohttp`
- JavaScript: `axios`, `fetch`, `node-fetch`
- Java: `OkHttp`, `Apache HttpClient`
- Ruby: `httparty`, `faraday`

## 🔍 Interactive Documentation

### Swagger UI

Visit https://api.illnessprediction.example.com/docs for interactive API documentation where you can:
- Browse all endpoints
- View request/response schemas
- Try API calls directly from the browser
- See example requests and responses

### ReDoc

Visit https://api.illnessprediction.example.com/redoc for a clean, three-panel documentation interface.

## 📊 Response Examples

### Successful Session Creation

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

### Prediction Response

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
    }
  ],
  "requires_input": false,
  "session_status": "completed"
}
```

## ❗ Error Handling

All errors return JSON with details:

```json
{
  "error": "Session not found",
  "status_code": 404,
  "path": "/sessions/invalid-id"
}
```

Common status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `429`: Too Many Requests
- `500`: Internal Server Error

## 🔒 Security

### Best Practices

1. **Never expose API keys** in client-side code
2. **Use HTTPS** for all requests
3. **Store keys securely** in environment variables
4. **Rotate keys regularly** (every 90 days)
5. **Use different keys** per environment
6. **Implement rate limiting** on your side
7. **Validate all inputs** before sending to API

### Compliance

The API is designed to comply with:
- **HIPAA**: Health Insurance Portability and Accountability Act
- **GDPR**: General Data Protection Regulation
- **CCPA**: California Consumer Privacy Act

Features:
- Data encryption at rest and in transit
- PII anonymization
- Session data deletion (right to be forgotten)
- Audit logging

## 📈 Monitoring

### Health Check

Monitor API availability:

```bash
curl https://api.illnessprediction.example.com/v1/health
```

Response:
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

### Status Page

Check system status: https://status.illnessprediction.example.com

## 🆘 Support

### Documentation

- **API Guide**: [API_GUIDE.md](./API_GUIDE.md)
- **Quick Reference**: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- **Auth & Rate Limiting**: [AUTHENTICATION_AND_RATE_LIMITING.md](./AUTHENTICATION_AND_RATE_LIMITING.md)

### Resources

- **Developer Portal**: https://developers.illnessprediction.example.com
- **Status Page**: https://status.illnessprediction.example.com
- **GitHub**: https://github.com/illness-prediction/api

### Contact

- **Email**: support@illnessprediction.example.com
- **Sales**: sales@illnessprediction.example.com
- **Security**: security@illnessprediction.example.com

### Report Issues

For bugs or feature requests:
1. Check existing issues on GitHub
2. Create a new issue with:
   - Description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Request ID (from `X-Request-ID` header)
   - Timestamp

## 📝 Changelog

### v1.0.0 (2024-01-15)

**Initial Release**
- Session management endpoints
- Message processing with conversational AI
- Multi-channel support (Web, SMS, WhatsApp)
- Multi-language support (5 languages)
- Illness predictions with confidence scores
- Explainable AI with SHAP values
- Treatment suggestions
- Rate limiting (60 req/min)
- API key authentication
- HIPAA/GDPR compliance features

## 📄 License

This API documentation is licensed under MIT License.

The API itself is proprietary. See Terms of Service for usage terms.

## 🙏 Acknowledgments

Built with:
- FastAPI
- XGBoost
- SHAP
- OpenAI/Anthropic LLMs
- Twilio
- WhatsApp Business API

---

**Ready to get started?** Check out the [API Guide](./API_GUIDE.md) or visit our [interactive documentation](https://api.illnessprediction.example.com/docs).
