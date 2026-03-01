# Retell AI Integration - Quick Start

## 5-Minute Setup

### 1. Start Your Application

```cmd
docker-compose up -d
```

### 2. Test Locally

```cmd
python scripts\test_retell_integration.py
```

All tests should pass.

### 3. Install & Start ngrok

```cmd
# Download from https://ngrok.com/download
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 4. Configure Retell Dashboard

#### Custom LLM Settings:
- **Webhook URL**: `https://YOUR_NGROK_URL/retell/chat`
- **Method**: POST

#### Custom Tool (Copy-Paste):

```json
{
  "type": "function",
  "function": {
    "name": "predict_illness",
    "description": "Predicts illnesses based on symptoms",
    "parameters": {
      "type": "object",
      "properties": {
        "symptoms": {
          "type": "string",
          "description": "Comma-separated symptoms"
        },
        "language": {
          "type": "string",
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

#### Agent System Prompt:

```
You are a compassionate health assistant. 

1. Greet warmly and ask about symptoms
2. Ask clarifying questions (one at a time)
3. When you have 2-3 symptoms, use predict_illness tool
4. Present results clearly and empathetically
5. Always remind: "This is informational only. Consult a doctor."

Keep responses concise for voice. Be empathetic.
```

### 5. Test Voice Agent

In Retell Dashboard:
1. Go to your agent
2. Click "Test Agent"
3. Say: "I have a headache and fever"
4. Verify the system responds correctly

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/retell/chat` | Main conversation |
| `/retell/tool/predict-illness` | Prediction tool |
| `/retell/end-call` | Cleanup |
| `/retell/health` | Health check |

## Troubleshooting

**Can't reach endpoint?**
- Check ngrok is running
- Verify URL in Retell Dashboard
- Test locally first

**No predictions?**
- Check OpenAI API key in `.env`
- View logs: `docker-compose logs app`

**Responses cut off?**
- Normal - optimized for voice (~200 words max)

## Full Documentation

See: `docs/integrations/RETELL_AI_INTEGRATION.md`

## Support

- Retell Docs: https://docs.retellai.com
- Your logs: `docker-compose logs app --tail=50`
