# Authentication and Rate Limiting

## Table of Contents

1. [Authentication](#authentication)
2. [Rate Limiting](#rate-limiting)
3. [Security Best Practices](#security-best-practices)
4. [Troubleshooting](#troubleshooting)

## Authentication

### Overview

The Illness Prediction System API uses **API Key authentication** to secure access to endpoints. Authentication is optional but strongly recommended for production deployments.

### API Key Format

API keys follow this format:
```
sk_[environment]_[random_string]
```

Examples:
- Development: `sk_dev_abc123xyz789`
- Staging: `sk_stg_def456uvw012`
- Production: `sk_live_ghi789rst345`

### How to Authenticate

Include your API key in the `X-API-Key` header with every request:

```http
GET /sessions HTTP/1.1
Host: api.illnessprediction.example.com
X-API-Key: sk_live_abc123xyz789
Content-Type: application/json
```

### Obtaining an API Key

#### Step 1: Sign Up

1. Visit the developer portal: https://developers.illnessprediction.example.com
2. Create an account or sign in
3. Complete email verification

#### Step 2: Create an Application

1. Navigate to "Applications" in the dashboard
2. Click "Create New Application"
3. Provide application details:
   - Name
   - Description
   - Environment (development, staging, production)
   - Callback URLs (for webhooks)

#### Step 3: Generate API Key

1. Select your application
2. Navigate to "API Keys" tab
3. Click "Generate New Key"
4. **Important**: Copy and store the key immediately - it won't be shown again
5. Store the key securely (use environment variables or secret management)

### Authentication Examples

#### Python

```python
import requests
import os

API_KEY = os.getenv('ILLNESS_PREDICTION_API_KEY')
BASE_URL = 'https://api.illnessprediction.example.com/v1'

headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
}

response = requests.post(
    f'{BASE_URL}/sessions',
    headers=headers,
    json={
        'channel': 'web',
        'user_id': 'user_123',
        'language': 'en'
    }
)

print(response.json())
```

#### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_KEY = process.env.ILLNESS_PREDICTION_API_KEY;
const BASE_URL = 'https://api.illnessprediction.example.com/v1';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

async function createSession() {
  try {
    const response = await axios.post(
      `${BASE_URL}/sessions`,
      {
        channel: 'web',
        user_id: 'user_123',
        language: 'en'
      },
      { headers }
    );
    
    console.log(response.data);
  } catch (error) {
    console.error('Error:', error.response?.data);
  }
}

createSession();
```

#### cURL

```bash
curl -X POST https://api.illnessprediction.example.com/v1/sessions \
  -H "X-API-Key: sk_live_abc123xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "user_id": "user_123",
    "language": "en"
  }'
```

#### Java

```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public class IllnessPredictionClient {
    private static final String API_KEY = System.getenv("ILLNESS_PREDICTION_API_KEY");
    private static final String BASE_URL = "https://api.illnessprediction.example.com/v1";
    
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newHttpClient();
        
        String requestBody = """
            {
                "channel": "web",
                "user_id": "user_123",
                "language": "en"
            }
            """;
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(BASE_URL + "/sessions"))
            .header("X-API-Key", API_KEY)
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();
        
        HttpResponse<String> response = client.send(
            request,
            HttpResponse.BodyHandlers.ofString()
        );
        
        System.out.println(response.body());
    }
}
```

### Authentication Errors

#### Missing API Key

**Request:**
```http
GET /sessions HTTP/1.1
Host: api.illnessprediction.example.com
```

**Response (401 Unauthorized):**
```json
{
  "error": "API key is required",
  "status_code": 401,
  "path": "/sessions"
}
```

**Headers:**
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: ApiKey
```

#### Invalid API Key

**Request:**
```http
GET /sessions HTTP/1.1
Host: api.illnessprediction.example.com
X-API-Key: invalid_key
```

**Response (401 Unauthorized):**
```json
{
  "error": "Invalid API key",
  "status_code": 401,
  "path": "/sessions"
}
```

### Unauthenticated Endpoints

The following endpoints do **not** require authentication:

- `GET /health` - Health check
- `GET /` - API information
- `GET /docs` - Swagger documentation
- `GET /redoc` - ReDoc documentation
- `GET /openapi.json` - OpenAPI specification

### API Key Management

#### Rotating Keys

It's recommended to rotate API keys every 90 days:

1. Generate a new API key
2. Update your application configuration
3. Test with the new key
4. Revoke the old key

#### Revoking Keys

If a key is compromised:

1. Navigate to the developer portal
2. Select your application
3. Find the compromised key
4. Click "Revoke"
5. Generate a new key immediately

#### Multiple Keys

You can have multiple active keys per application:

- **Primary Key**: Main production key
- **Secondary Key**: Backup or rotation key
- **Development Keys**: For testing

### Environment-Specific Keys

Use different keys for each environment:

```bash
# Development
export ILLNESS_PREDICTION_API_KEY=sk_dev_abc123

# Staging
export ILLNESS_PREDICTION_API_KEY=sk_stg_def456

# Production
export ILLNESS_PREDICTION_API_KEY=sk_live_ghi789
```

## Rate Limiting

### Overview

Rate limiting protects the API from abuse and ensures fair usage across all clients. Limits are applied per API key (authenticated) or per IP address (unauthenticated).

### Rate Limits

| Tier | Requests per Minute | Requests per Hour | Requests per Day |
|------|---------------------|-------------------|------------------|
| Free | 60 | 3,600 | 86,400 |
| Basic | 300 | 18,000 | 432,000 |
| Pro | 1,000 | 60,000 | 1,440,000 |
| Enterprise | Custom | Custom | Custom |

**Note**: Current implementation enforces 60 requests per minute. Contact sales for higher limits.

### Rate Limit Headers

Every API response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-Process-Time: 0.123
```

**Headers:**
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-Process-Time`: Request processing time in seconds

### Rate Limit Algorithm

The API uses a **sliding window** algorithm:

1. Track requests in a 60-second window
2. Remove requests older than 60 seconds
3. Count remaining requests in window
4. Allow request if count < limit
5. Reject request if count >= limit

### Rate Limit Exceeded

When the rate limit is exceeded:

**Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

**Headers:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
```

### Handling Rate Limits

#### Strategy 1: Exponential Backoff

```python
import time
import requests

def make_request_with_backoff(url, headers, max_retries=5):
    """Make request with exponential backoff on rate limit."""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            # Get retry-after header or default to 60 seconds
            retry_after = int(response.headers.get('Retry-After', 60))
            
            # Exponential backoff: 60s, 120s, 240s, etc.
            wait_time = retry_after * (2 ** attempt)
            
            print(f"Rate limited. Waiting {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
            continue
        
        # Success or other error
        return response
    
    raise Exception(f"Max retries ({max_retries}) exceeded")

# Usage
response = make_request_with_backoff(
    'https://api.illnessprediction.example.com/v1/sessions',
    headers={'X-API-Key': API_KEY}
)
```

#### Strategy 2: Rate Limit Monitoring

```python
import requests
import time

class RateLimitedClient:
    """HTTP client with rate limit monitoring."""
    
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {'X-API-Key': api_key}
    
    def get_remaining_requests(self, response):
        """Extract remaining requests from response headers."""
        return int(response.headers.get('X-RateLimit-Remaining', 0))
    
    def make_request(self, endpoint, method='GET', **kwargs):
        """Make request with rate limit monitoring."""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        
        # Check remaining requests
        remaining = self.get_remaining_requests(response)
        
        if remaining < 10:
            print(f"Warning: Only {remaining} requests remaining")
        
        if remaining < 5:
            print("Critical: Rate limit nearly exceeded. Slowing down...")
            time.sleep(2)  # Slow down requests
        
        return response

# Usage
client = RateLimitedClient(API_KEY, BASE_URL)
response = client.make_request('/sessions', method='POST', json={...})
```

#### Strategy 3: Request Queuing

```python
import queue
import threading
import time
import requests

class RateLimitedQueue:
    """Queue-based rate limiter."""
    
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute  # Seconds between requests
        self.queue = queue.Queue()
        self.running = True
        
        # Start worker thread
        self.worker = threading.Thread(target=self._process_queue)
        self.worker.start()
    
    def _process_queue(self):
        """Process queued requests at controlled rate."""
        while self.running:
            try:
                # Get request from queue (with timeout)
                request_func, callback = self.queue.get(timeout=1)
                
                # Execute request
                try:
                    result = request_func()
                    callback(result, None)
                except Exception as e:
                    callback(None, e)
                
                # Wait before next request
                time.sleep(self.interval)
                
            except queue.Empty:
                continue
    
    def add_request(self, request_func, callback):
        """Add request to queue."""
        self.queue.put((request_func, callback))
    
    def stop(self):
        """Stop processing queue."""
        self.running = False
        self.worker.join()

# Usage
def make_request():
    return requests.post(
        f"{BASE_URL}/sessions",
        headers={'X-API-Key': API_KEY},
        json={'channel': 'web', 'user_id': 'user_123'}
    )

def handle_response(response, error):
    if error:
        print(f"Error: {error}")
    else:
        print(f"Response: {response.json()}")

limiter = RateLimitedQueue(requests_per_minute=60)

# Queue multiple requests
for i in range(100):
    limiter.add_request(make_request, handle_response)

# Wait for completion
time.sleep(120)
limiter.stop()
```

#### Strategy 4: Adaptive Rate Limiting

```javascript
class AdaptiveRateLimiter {
  constructor(initialRate = 60) {
    this.requestsPerMinute = initialRate;
    this.requestTimes = [];
  }
  
  async makeRequest(requestFunc) {
    // Wait if necessary
    await this.waitIfNeeded();
    
    try {
      const response = await requestFunc();
      
      // Track successful request
      this.requestTimes.push(Date.now());
      
      // Adjust rate based on response headers
      const remaining = parseInt(response.headers.get('X-RateLimit-Remaining') || '0');
      const limit = parseInt(response.headers.get('X-RateLimit-Limit') || '60');
      
      // If we're using more than 80% of limit, slow down
      if (remaining < limit * 0.2) {
        this.requestsPerMinute = Math.max(30, this.requestsPerMinute * 0.8);
        console.log(`Slowing down to ${this.requestsPerMinute} req/min`);
      }
      
      return response;
      
    } catch (error) {
      if (error.response?.status === 429) {
        // Rate limited - reduce rate significantly
        this.requestsPerMinute = Math.max(10, this.requestsPerMinute * 0.5);
        console.log(`Rate limited! Reducing to ${this.requestsPerMinute} req/min`);
        
        // Wait and retry
        const retryAfter = parseInt(error.response.headers.get('Retry-After') || '60');
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        return this.makeRequest(requestFunc);
      }
      throw error;
    }
  }
  
  async waitIfNeeded() {
    // Remove old requests (older than 1 minute)
    const oneMinuteAgo = Date.now() - 60000;
    this.requestTimes = this.requestTimes.filter(time => time > oneMinuteAgo);
    
    // Check if we need to wait
    if (this.requestTimes.length >= this.requestsPerMinute) {
      const oldestRequest = this.requestTimes[0];
      const waitTime = 60000 - (Date.now() - oldestRequest);
      
      if (waitTime > 0) {
        console.log(`Waiting ${waitTime}ms to respect rate limit`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
  }
}

// Usage
const limiter = new AdaptiveRateLimiter(60);

async function createSession() {
  return limiter.makeRequest(async () => {
    return axios.post(
      `${BASE_URL}/sessions`,
      { channel: 'web', user_id: 'user_123' },
      { headers: { 'X-API-Key': API_KEY } }
    );
  });
}
```

### Rate Limit Best Practices

1. **Monitor Headers**: Always check `X-RateLimit-Remaining`
2. **Implement Backoff**: Use exponential backoff on 429 errors
3. **Cache Responses**: Cache data to reduce API calls
4. **Batch Operations**: Combine multiple operations when possible
5. **Use Webhooks**: For real-time updates instead of polling
6. **Request Increase**: Contact sales for higher limits if needed

### Exempt Endpoints

These endpoints are **not** rate limited:

- `GET /health`
- `GET /`
- `GET /docs`
- `GET /redoc`
- `GET /openapi.json`

## Security Best Practices

### 1. API Key Storage

**✅ DO:**
- Store keys in environment variables
- Use secret management services (AWS Secrets Manager, HashiCorp Vault)
- Encrypt keys at rest
- Use different keys per environment

**❌ DON'T:**
- Hardcode keys in source code
- Commit keys to version control
- Share keys via email or chat
- Use production keys in development

### 2. Key Rotation

**Recommended Schedule:**
- Development: Every 30 days
- Staging: Every 60 days
- Production: Every 90 days

**Rotation Process:**
```bash
# 1. Generate new key
NEW_KEY=$(curl -X POST https://developers.illnessprediction.example.com/api/keys \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"name": "Production Key 2024-Q1"}' | jq -r '.key')

# 2. Update configuration (zero-downtime)
kubectl set env deployment/api ILLNESS_PREDICTION_API_KEY=$NEW_KEY

# 3. Wait for rollout
kubectl rollout status deployment/api

# 4. Revoke old key
curl -X DELETE https://developers.illnessprediction.example.com/api/keys/$OLD_KEY_ID \
  -H "Authorization: Bearer $AUTH_TOKEN"
```

### 3. Network Security

**Use HTTPS:**
```python
# ✅ Secure
response = requests.post('https://api.illnessprediction.example.com/v1/sessions', ...)

# ❌ Insecure
response = requests.post('http://api.illnessprediction.example.com/v1/sessions', ...)
```

**Verify SSL Certificates:**
```python
# ✅ Verify certificates (default)
response = requests.post(url, headers=headers, verify=True)

# ❌ Don't disable verification in production
response = requests.post(url, headers=headers, verify=False)  # NEVER DO THIS
```

### 4. Request Signing (Advanced)

For additional security, implement request signing:

```python
import hmac
import hashlib
import time

def sign_request(api_key, api_secret, method, path, body=''):
    """Sign API request with HMAC-SHA256."""
    timestamp = str(int(time.time()))
    
    # Create signature payload
    payload = f"{method}\n{path}\n{timestamp}\n{body}"
    
    # Generate signature
    signature = hmac.new(
        api_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return {
        'X-API-Key': api_key,
        'X-Timestamp': timestamp,
        'X-Signature': signature
    }

# Usage
headers = sign_request(
    api_key='sk_live_abc123',
    api_secret='secret_xyz789',
    method='POST',
    path='/v1/sessions',
    body='{"channel":"web","user_id":"user_123"}'
)
```

### 5. IP Whitelisting

For enterprise deployments, configure IP whitelisting:

```bash
# Configure allowed IPs in developer portal
curl -X POST https://developers.illnessprediction.example.com/api/whitelist \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "api_key_id": "key_123",
    "allowed_ips": [
      "203.0.113.0/24",
      "198.51.100.42"
    ]
  }'
```

### 6. Audit Logging

Enable audit logging for compliance:

```python
import logging

# Configure audit logger
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

handler = logging.FileHandler('audit.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(message)s'
))
audit_logger.addHandler(handler)

# Log API calls
def make_api_call(endpoint, data):
    audit_logger.info(f"API call: {endpoint} - User: {data.get('user_id')}")
    response = requests.post(f"{BASE_URL}{endpoint}", json=data, headers=headers)
    audit_logger.info(f"API response: {response.status_code}")
    return response
```

## Troubleshooting

### Common Issues

#### Issue 1: "API key is required"

**Cause**: Missing `X-API-Key` header

**Solution**:
```python
# ❌ Missing header
response = requests.post(url, json=data)

# ✅ Include header
headers = {'X-API-Key': API_KEY}
response = requests.post(url, json=data, headers=headers)
```

#### Issue 2: "Invalid API key"

**Causes**:
- Typo in API key
- Key has been revoked
- Using wrong environment key

**Solution**:
1. Verify key in developer portal
2. Check environment variables
3. Generate new key if necessary

#### Issue 3: Rate Limit Exceeded

**Cause**: Too many requests in short time

**Solution**:
```python
# Implement exponential backoff
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    time.sleep(retry_after)
    # Retry request
```

#### Issue 4: Intermittent 401 Errors

**Causes**:
- Key rotation in progress
- Network issues
- Load balancer routing

**Solution**:
```python
# Implement retry logic
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[401, 429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)

response = session.post(url, json=data, headers=headers)
```

### Debug Mode

Enable debug logging:

```python
import logging
import http.client

# Enable debug logging
http.client.HTTPConnection.debuglevel = 1
logging.basicConfig(level=logging.DEBUG)

# Make request
response = requests.post(url, json=data, headers=headers)
```

### Testing Authentication

Test your API key:

```bash
# Test authentication
curl -X GET https://api.illnessprediction.example.com/v1/health \
  -H "X-API-Key: $API_KEY" \
  -v

# Check response headers
# Look for: X-RateLimit-Limit, X-RateLimit-Remaining
```

### Support

If you continue to experience issues:

1. Check the [status page](https://status.illnessprediction.example.com)
2. Review [API documentation](https://api.illnessprediction.example.com/docs)
3. Contact support: support@illnessprediction.example.com
4. Include:
   - Request ID (from `X-Request-ID` header)
   - Timestamp
   - Error message
   - Code snippet (without API key)
