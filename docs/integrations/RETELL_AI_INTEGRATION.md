# Retell AI Integration Guide

Complete guide for integrating your Illness Prediction System with Retell AI's voice agent platform.

## Overview

This integration allows users to interact with your illness prediction system through voice conversations powered by Retell AI. The system:

- Accepts voice input transcribed by Retell AI
- Processes symptoms using your existing ML models
- Returns voice-optimized responses for natural TTS
- Supports multi-language conversations
- Handles errors gracefully to prevent call drops

## Architecture

```
User Voice → Retell AI → Your FastAPI Backend → Prediction System → Voice Response
```

## Setup Steps

### 1. Register Routes

The Retell routes are already created in `src/api/routes/retell.py`. Add them to your main application:

```python
# In src/main.py, add:
from src.api.routes import retell
app.include_router(retell.router)
```

### 2. Expose Your Local Server with ngrok

Since Retell AI needs to reach your server, use ngrok to create a public URL:

#### Install ngrok

**Windows:**
```cmd
# Download from https://ngrok.com/download
# Or use chocolatey:
choco install ngrok
```

**Mac/Linux:**
```bash
brew install ngrok
# Or download from https://ngrok.com/download
```

#### Authenticate ngrok

```cmd
ngrok authtoken YOUR_NGROK_AUTH_TOKEN
```

Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

#### Start ngrok Tunnel

```cmd
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

Copy the `https://abc123.ngrok.io` URL - this is your public endpoint.

### 3. Configure Retell AI Dashboard

#### A. Create Custom LLM

1. Go to Retell AI Dashboard → Custom LLM
2. Click "Create Custom LLM"
3. Configure:
   - **Name**: Illness Prediction System
   - **Webhook URL**: `https://YOUR_NGROK_URL/retell/chat`
   - **Method**: POST
   - **Authentication**: None (or add API key if needed)

#### B. Add Custom Tool (Function Calling)

1. Go to Tools → Create Tool
2. Use this JSON schema:

```json
{
  "type": "function",
  "function": {
    "name": "predict_illness",
    "description": "Predicts possible illnesses based on user's symptoms. Use this when the user has described their symptoms and you need to provide a diagnosis.",
    "parameters": {
      "type": "object",
      "properties": {
        "symptoms": {
          "type": "string",
          "description": "Comma-separated list of symptoms the user has described (e.g., 'headache, fever, nausea')"
        },
        "language": {
          "type": "string",
          "description": "Language code for the response (en, es, fr, hi)",
          "enum": ["en", "es", "fr", "hi"],
          "default": "en"
        }
      },
      "required": ["symptoms"]
    }
  },
  "server": {
    "url": "https://YOUR_NGROK_URL/retell/tool/predict-illness",
    "method": "POST"
  }
}
```

Replace `YOUR_NGROK_URL` with your actual ngrok URL.

#### C. Create Voice Agent

1. Go to Agents → Create Agent
2. Configure:
   - **Name**: Health Assistant
   - **Voice**: Choose a natural, empathetic voice
   - **LLM**: Select your Custom LLM (Illness Prediction System)
   - **Tools**: Add the `predict_illness` tool
   - **System Prompt**:

```
You are a compassionate health assistant helping users understand their symptoms.

Your role:
1. Greet the user warmly and ask about their symptoms
2. Listen carefully and ask clarifying questions
3. When you have enough information, use the predict_illness tool
4. Present results clearly and empathetically
5. Always remind users this is informational only and to consult a doctor

Guidelines:
- Be empathetic and reassuring
- Ask one question at a time
- Use simple, clear language
- Never diagnose definitively
- For serious symptoms, urge immediate medical attention
- Keep responses concise for voice

Example flow:
User: "I have a headache"
You: "I'm sorry to hear that. How long have you had this headache?"
User: "About 2 days"
You: "I see. On a scale of 1 to 10, how severe is the pain?"
User: "About 7"
You: "Do you have any other symptoms like fever, nausea, or sensitivity to light?"
User: "Yes, I feel nauseous"
You: [Use predict_illness tool with symptoms: "headache, nausea"]
```

### 4. Test the Integration

#### Local Testing

Test the endpoints directly:

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/retell/chat \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "test-123",
    "user_message": "I have a headache and fever",
    "language": "en"
  }'

# Test tool endpoint
curl -X POST http://localhost:8000/retell/tool/predict-illness \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "test-123",
    "tool_name": "predict_illness",
    "parameters": {
      "symptoms": "headache, fever, body aches",
      "language": "en"
    }
  }'
```

#### Test with Retell AI

1. In Retell Dashboard, go to your agent
2. Click "Test Agent"
3. Start a voice conversation
4. Describe symptoms and verify the system responds correctly

## API Endpoints

### POST /retell/chat

Main conversation endpoint.

**Request:**
```json
{
  "call_id": "unique-call-id",
  "user_message": "I have a headache",
  "conversation_history": [],
  "language": "en",
  "metadata": {}
}
```

**Response:**
```json
{
  "response": "I'm sorry to hear that. How long have you had this headache?",
  "end_call": false,
  "metadata": {
    "session_id": "session-123"
  }
}
```

### POST /retell/tool/predict-illness

Illness prediction tool.

**Request:**
```json
{
  "call_id": "unique-call-id",
  "tool_name": "predict_illness",
  "parameters": {
    "symptoms": "headache, fever, nausea",
    "language": "en"
  }
}
```

**Response:**
```json
{
  "result": "Based on your symptoms, the most likely condition is Migraine, with 78 percent confidence...",
  "success": true,
  "metadata": {
    "prediction_count": 3
  }
}
```

### POST /retell/end-call

Clean up when call ends.

**Request:**
```
POST /retell/end-call?call_id=unique-call-id
```

### GET /retell/health

Health check.

**Response:**
```json
{
  "status": "healthy",
  "active_calls": 5,
  "timestamp": "2026-02-22T10:30:00"
}
```

## Voice Optimization

The integration automatically optimizes responses for voice:

### Text Transformations

- **Removes markdown**: `**bold**` → `bold`
- **Removes emoji**: `🟢` → `low severity`
- **Simplifies bullets**: `- item` → `. item`
- **Adds pauses**: `\n\n` → `. `
- **Limits length**: Max ~200 words per response

### Example

**Original:**
```
Based on your symptoms, here are the most likely conditions:

1. **Migraine** 🟡 (MODERATE)
   Confidence: 78.5%
   
   Suggested OTC Medications:
   - Ibuprofen (Advil)
   - Acetaminophen (Tylenol)
```

**Voice-Optimized:**
```
Based on your symptoms, the most likely condition is Migraine, with 78 percent confidence. This is moderate severity. Remember, this is for informational purposes only. Please consult a healthcare professional for proper diagnosis.
```

## Multi-Language Support

The system supports multiple languages:

- **English** (en)
- **Spanish** (es)
- **French** (fr)
- **Hindi** (hi)

Language is automatically detected from the request or can be specified in the `language` parameter.

## Error Handling

The integration handles errors gracefully:

1. **LLM Failures**: Returns friendly message asking user to rephrase
2. **Session Not Found**: Creates new session automatically
3. **Prediction Errors**: Returns conversational error without technical details
4. **Network Issues**: Retries with exponential backoff

All errors are logged but never exposed to the user in a way that would disrupt the conversation.

## Security Considerations

### For Production

1. **Add Authentication**:
```python
# In src/api/routes/retell.py
from fastapi import Header

@router.post("/chat")
async def retell_chat(
    request: RetellChatRequest,
    x_retell_signature: str = Header(None)
):
    # Verify Retell signature
    verify_retell_signature(x_retell_signature, request)
```

2. **Rate Limiting**: Already implemented in main app

3. **Use Production URL**: Replace ngrok with proper domain

4. **Environment Variables**:
```env
RETELL_API_KEY=your_retell_api_key
RETELL_WEBHOOK_SECRET=your_webhook_secret
```

## Monitoring

Monitor your Retell integration:

```python
# Check active calls
GET /retell/health

# View logs
docker-compose logs app | grep "Retell"
```

## Troubleshooting

### Issue: Retell can't reach my endpoint

**Solution:**
- Verify ngrok is running: `ngrok http 8000`
- Check firewall settings
- Ensure Docker container is running
- Test endpoint locally first

### Issue: Responses are cut off

**Solution:**
- Responses are limited to ~200 words for voice
- System automatically summarizes longer content
- Adjust `format_for_voice()` function if needed

### Issue: Predictions not working

**Solution:**
- Verify OpenAI API key is set in `.env`
- Check logs: `docker-compose logs app --tail=50`
- Test prediction endpoint directly
- Ensure ML models are loaded

### Issue: Wrong language responses

**Solution:**
- Specify language in request: `"language": "es"`
- Check Retell agent language settings
- Verify language is supported

## Next Steps

1. **Test thoroughly** with various symptom combinations
2. **Customize voice prompts** in Retell Dashboard
3. **Add analytics** to track conversation quality
4. **Deploy to production** with proper domain
5. **Monitor performance** and user feedback

## Support

For issues:
- Retell AI: https://docs.retellai.com
- Your system logs: `docker-compose logs app`
- GitHub issues: [your-repo]/issues

## Example Conversation Flow

```
Agent: "Hello! I'm here to help you understand your symptoms. What brings you in today?"

User: "I have a really bad headache"

Agent: "I'm sorry to hear that. How long have you had this headache?"

User: "About two days now"

Agent: "I see. On a scale of 1 to 10, how severe is the pain?"

User: "It's about an 8"

Agent: "That sounds quite painful. Do you have any other symptoms, like fever, nausea, or sensitivity to light?"

User: "Yes, I've been feeling nauseous and light bothers me"

Agent: [Calls predict_illness tool]

Agent: "Based on your symptoms, the most likely condition is Migraine, with 78 percent confidence. This is moderate severity. I recommend rest in a dark, quiet room, and you might consider over-the-counter pain relievers like Ibuprofen. However, this is for informational purposes only. Please consult a healthcare professional for proper diagnosis and treatment."

User: "Thank you"

Agent: "You're welcome. I hope you feel better soon. Remember, if your symptoms worsen or you're concerned, please seek medical attention. Take care!"
```

Your Retell AI integration is ready to use!
