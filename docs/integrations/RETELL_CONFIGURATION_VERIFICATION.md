# Retell AI Configuration Verification Guide

## Quick Verification

Run this command to automatically verify your integration:

```cmd
scripts\verify_retell_integration.bat
```

Or directly with Python:

```cmd
python scripts/verify_retell_integration.py
```

## Manual Verification Checklist

### 1. Docker & API Status

**Check Docker containers:**
```cmd
docker-compose ps
```

Expected output:
- `app` container should be "Up"
- `postgres` container should be "Up"  
- `redis` container should be "Up"

**Test API health:**
```cmd
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "..."
}
```

### 2. Retell Endpoint Verification

**Test Retell health endpoint:**
```cmd
curl http://localhost:8000/api/v1/retell/health
```

Expected response:
```json
{
  "status": "healthy",
  "active_calls": 0,
  "timestamp": "..."
}
```

**Test Retell chat endpoint:**
```cmd
curl -X POST http://localhost:8000/api/v1/retell/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"call_id\":\"test_123\",\"user_message\":\"I have a headache\",\"language\":\"en\"}"
```

Expected response:
```json
{
  "response": "I understand you have a headache. When did it start?...",
  "end_call": false,
  "metadata": {
    "session_id": "...",
    "has_predictions": false,
    "is_complete": false
  }
}
```

### 3. Retell AI Dashboard Configuration

#### A. Agent Settings

Go to your Retell AI agent → Settings:

**General Prompt:**
- [ ] Contains instructions for symptom gathering
- [ ] Mentions asking 3-5 follow-up questions
- [ ] Instructs NOT to end conversation early
- [ ] See `RETELL_AGENT_CONFIGURATION.md` for full prompt

**Response Engine:**
- [ ] Model: GPT-4 or GPT-4 Turbo
- [ ] Temperature: 0.7
- [ ] Max Tokens: 150-200

**Begin Message:**
- [ ] Set to: "Hello! I'm here to help you understand your symptoms. What brings you in today?"

**End Call Settings:**
- [ ] "Auto-end after silence" is DISABLED
- [ ] "End after X turns" is DISABLED

#### B. Webhook Configuration

Go to your Retell AI agent → Integrations → Webhook:

**Webhook URL:**
- [ ] Format: `https://your-ngrok-url.ngrok.io/api/v1/retell/chat`
- [ ] Replace `your-ngrok-url` with your actual ngrok URL
- [ ] Webhook is ENABLED

**Test webhook:**
- [ ] Click "Test Webhook" in Retell dashboard
- [ ] Should return 200 OK status
- [ ] Response should contain valid JSON

#### C. Custom Tool (Optional but Recommended)

Go to your Retell AI agent → Tools → Add Custom Tool:

**Tool Configuration:**
- [ ] Tool name: `predict-illness`
- [ ] Tool description: "Generate illness predictions based on symptoms"
- [ ] Tool schema: Copy from `docs/integrations/retell_tool_schema.json`
- [ ] Tool endpoint: `https://your-ngrok-url.ngrok.io/api/v1/retell/tool/predict-illness`

### 4. ngrok Configuration

**Check ngrok is running:**
```cmd
curl http://localhost:4040/api/tunnels
```

Expected: Should show active tunnel to port 8000

**Get your ngrok URL:**
1. Visit http://localhost:4040
2. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
3. Use this URL in Retell AI webhook configuration

### 5. Environment Variables

**Check .env file:**
```cmd
type .env | findstr LLM_API_KEY
```

Verify:
- [ ] `LLM_API_KEY` is NOT set to "changeme"
- [ ] `LLM_API_KEY` starts with "sk-" (OpenAI format)
- [ ] `LLM_PROVIDER` is set to "openai"

### 6. ML Prediction Verification

**Test that ML predictions are working:**

1. Start a conversation in Retell AI simulation
2. Provide symptoms: "I have a headache, fever, and sore throat"
3. Answer follow-up questions
4. After 3-5 exchanges, you should see predictions

**Expected prediction format:**
```
Based on your symptoms, here are the most likely conditions:

1. Influenza 🟡 (MODERATE)
   Confidence: 75.3%
   
   Suggested OTC Medications:
   - Acetaminophen (Tylenol)
   - Ibuprofen (Advil)
   
   Self-Care Recommendations:
   - Rest
   - Stay hydrated
```

**Indicators that ML is working:**
- Specific illness names (e.g., "Influenza", "Common Cold")
- Confidence percentages (e.g., "75.3%")
- Severity levels (LOW, MODERATE, HIGH, CRITICAL)
- Treatment suggestions

**Indicators that only AI is responding:**
- Generic advice without specific illness names
- No confidence scores
- No severity indicators
- Vague recommendations

### 7. Test Conversation Flow

**Complete test conversation:**

1. **User**: "I have a runny nose and I've been sneezing"
   - **Expected**: Agent asks follow-up questions

2. **User**: "Yes, I also have a sore throat"
   - **Expected**: Agent continues gathering symptoms

3. **User**: "No fever, just feeling tired"
   - **Expected**: Agent may ask 1-2 more questions

4. **User**: "It started about 2 days ago"
   - **Expected**: Agent provides prediction (Common Cold, 60-80% confidence)

**Verify:**
- [ ] Conversation has 4-6 exchanges minimum
- [ ] Agent asks relevant follow-up questions
- [ ] Prediction includes illness name, confidence, severity
- [ ] Treatment suggestions are provided
- [ ] Conversation ends naturally

### 8. Check Application Logs

**View Docker logs:**
```cmd
docker-compose logs -f app
```

**Look for:**
- [ ] "Retell chat request for call..." messages
- [ ] "Generating predictions for session..." messages
- [ ] "Generated X predictions for session..." messages
- [ ] No error messages or exceptions

**Successful log example:**
```
INFO: Retell chat request for call test_123
INFO: Processing message for session abc-def-123
INFO: Generating predictions for session abc-def-123
INFO: Generated 3 predictions for session abc-def-123
INFO: Retell response for call test_123: 245 chars
```

## Troubleshooting

### Issue: Webhook returns 404

**Solution:**
- Verify ngrok is running: `curl http://localhost:4040`
- Check webhook URL format: `https://your-ngrok-url.ngrok.io/api/v1/retell/chat`
- Ensure Docker containers are running: `docker-compose ps`

### Issue: Predictions not appearing

**Solution:**
- Check OpenAI API key is configured: `type .env | findstr LLM_API_KEY`
- Verify ML model is loaded: Check Docker logs for "MLModelService initialized"
- Ensure enough symptoms provided: Need at least 2-3 symptoms

### Issue: Conversation ends too early

**Solution:**
- Update agent prompt (see `RETELL_AGENT_CONFIGURATION.md`)
- Disable "End after X turns" in Retell settings
- Ensure prompt instructs to ask 3-5 questions

### Issue: Generic AI responses instead of predictions

**Solution:**
- Verify webhook is configured correctly
- Check that `/retell/chat` endpoint is being called (check logs)
- Ensure ConversationManager is using PredictionService (check code)

## Verification Complete

If all checks pass:
- ✅ Your Retell AI integration is working correctly
- ✅ Your system is using ML predictions (not just AI)
- ✅ Both voice and chat interfaces are functional
- ✅ You're ready for production deployment!

## Next Steps

1. **Test with real users**: Have team members test the voice interface
2. **Monitor performance**: Check logs and metrics regularly
3. **Tune prompts**: Adjust agent prompt based on user feedback
4. **Add more test cases**: Create additional simulation tests
5. **Deploy to production**: Follow `docs/operations/DEPLOYMENT_GUIDE.md`

## Support

If you encounter issues:
1. Run the verification script: `scripts\verify_retell_integration.bat`
2. Check application logs: `docker-compose logs -f app`
3. Review Retell AI dashboard for webhook errors
4. Verify ngrok is running: http://localhost:4040
