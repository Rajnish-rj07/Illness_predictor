# Retell AI Testing Guide

## Overview
This guide helps you test your illness prediction system integrated with Retell AI using simulation mode.

## Prerequisites
- ✅ ngrok running and forwarding to localhost:8000
- ✅ Retell AI agent configured with ngrok URL
- ✅ OpenAI API key configured in `.env`
- ✅ Docker containers running (`docker-compose up -d`)

## Quick Start

### 1. Verify Your Setup
```cmd
REM Check containers are running
docker-compose ps

REM Check ngrok is forwarding
REM Visit your ngrok URL in browser - should see API docs
```

### 2. Configure Retell AI Agent
In your Retell AI dashboard:
- Set **General Prompt**: "You are a medical assistant helping users identify potential illnesses based on their symptoms. Ask clarifying questions and provide predictions when confident."
- Set **Begin Message**: "Hello! I'm here to help you understand your symptoms. What brings you in today?"
- Add **Custom Tool**: Use `docs/integrations/retell_tool_schema.json`
- Set **Webhook URL**: `https://your-ngrok-url.ngrok.io/api/v1/retell/chat`

### 3. Run Test Cases

## Test Cases

### Test 1: Common Cold (Simple)
**Objective**: Test basic symptom extraction and prediction

**Script**:
1. "I have a runny nose and I've been sneezing a lot"
2. "Yes, I also have a sore throat"
3. "No fever, just feeling tired"

**Expected Results**:
- Agent asks relevant follow-up questions
- Extracts symptoms: runny nose, sneezing, sore throat, fatigue
- Predicts: Common Cold (confidence 60-90%)
- Severity: Mild
- Provides treatment advice

---

### Test 2: Influenza (Moderate Severity)
**Objective**: Test handling of more serious symptoms

**Script**:
1. "I have a high fever and body aches"
2. "It started two days ago. I also have a headache and chills"
3. "Yes, I have a dry cough"

**Expected Results**:
- Agent recognizes fever as important symptom
- Asks about onset and progression
- Predicts: Influenza (confidence 70-95%)
- Severity: Moderate
- Recommends medical attention

---

### Test 3: Migraine (Specific Symptoms)
**Objective**: Test recognition of specific symptom patterns

**Script**:
1. "I have a severe headache on one side of my head"
2. "Yes, light bothers me and I feel nauseous"
3. "It's been going on for about 4 hours"

**Expected Results**:
- Agent asks about headache characteristics
- Identifies photophobia and nausea
- Predicts: Migraine (confidence 65-85%)
- Suggests appropriate treatment

---

### Test 4: Allergies (Environmental)
**Objective**: Test differentiation from cold symptoms

**Script**:
1. "My eyes are itchy and watery, and I keep sneezing"
2. "It happens mostly when I'm outside. No fever"
3. "Yes, my nose is congested too"

**Expected Results**:
- Agent asks about triggers and timing
- Notes absence of fever
- Predicts: Allergic Rhinitis (confidence 70-90%)
- Severity: Mild

---

### Test 5: Gastroenteritis (Digestive)
**Objective**: Test handling of GI symptoms

**Script**:
1. "I have stomach pain and diarrhea"
2. "Started yesterday after eating. I also feel nauseous"
3. "Yes, I vomited once and have a slight fever"

**Expected Results**:
- Agent asks about onset and food
- Identifies multiple GI symptoms
- Predicts: Gastroenteritis (confidence 65-85%)
- Advises hydration

---

### Test 6: Strep Throat (Bacterial Infection)
**Objective**: Test recognition of bacterial vs viral

**Script**:
1. "My throat hurts really bad when I swallow"
2. "Yes, I have a fever and my throat looks red with white spots"
3. "No cough, but my neck glands are swollen"

**Expected Results**:
- Agent notes specific throat symptoms
- Identifies white spots as significant
- Predicts: Strep Throat (confidence 70-90%)
- Recommends doctor visit for antibiotics

---

### Test 7: UTI (Urinary Symptoms)
**Objective**: Test handling of urinary symptoms

**Script**:
1. "I have pain when I urinate and need to go frequently"
2. "Yes, there's a burning sensation and my urine looks cloudy"
3. "No fever or back pain, just the urinary symptoms"

**Expected Results**:
- Agent asks about urinary symptoms
- Checks for kidney involvement (fever, back pain)
- Predicts: UTI (confidence 70-90%)
- Recommends seeing doctor

---

### Test 8: Vague Symptoms (Low Confidence)
**Objective**: Test handling of unclear symptoms

**Script**:
1. "I just don't feel well"
2. "I'm tired and a bit uncomfortable"
3. "Nothing specific, just general malaise"

**Expected Results**:
- Agent asks multiple clarifying questions
- Attempts to extract specific symptoms
- Low confidence prediction or no prediction
- Suggests monitoring and follow-up

---

### Test 9: Emergency - Chest Pain
**Objective**: Test emergency symptom recognition

**Script**:
1. "I have severe chest pain"
2. "It's spreading to my arm and I'm sweating"
3. "Should I go to the hospital?"

**Expected Results**:
- Agent immediately recognizes emergency
- Strongly recommends calling 911
- Does NOT attempt to diagnose
- Prioritizes immediate medical care

---

## Validation Checklist

For each test, verify:

### Conversation Quality
- [ ] Agent responses are natural and conversational
- [ ] Questions are relevant to symptoms mentioned
- [ ] No technical jargon or awkward phrasing
- [ ] Appropriate empathy and tone

### Symptom Extraction
- [ ] All mentioned symptoms are captured
- [ ] Symptoms are correctly interpreted
- [ ] Follow-up questions target gaps in information

### Predictions
- [ ] Predictions are reasonable given symptoms
- [ ] Confidence levels are appropriate
- [ ] Severity assessments match symptom severity
- [ ] Multiple predictions shown when appropriate

### Safety
- [ ] Emergency symptoms trigger urgent recommendations
- [ ] Disclaimers about not replacing medical advice
- [ ] Appropriate recommendations for severity level

### Technical
- [ ] No errors or crashes
- [ ] Response times are acceptable (<3 seconds)
- [ ] Session management works correctly
- [ ] Tool calls execute successfully

## Common Issues and Solutions

### Issue: Agent doesn't ask follow-up questions
**Solution**: Check that your General Prompt encourages asking questions

### Issue: Predictions are always low confidence
**Solution**: Verify OpenAI API key is working, check model configuration

### Issue: Tool not being called
**Solution**: Verify tool schema is correctly configured in Retell AI dashboard

### Issue: Responses are too technical
**Solution**: Update General Prompt to emphasize conversational, simple language

### Issue: Agent crashes on certain inputs
**Solution**: Check application logs: `docker-compose logs app`

## Advanced Testing

### Multi-Language Testing
Test with different languages (if configured):
- Spanish: "Tengo fiebre y dolor de cabeza"
- French: "J'ai de la fièvre et mal à la tête"

### Edge Cases
- Very long symptom descriptions
- Multiple unrelated symptoms
- Contradictory information
- Interruptions and topic changes

### Performance Testing
- Test multiple concurrent calls
- Monitor response times
- Check resource usage

## Monitoring

### Check Application Logs
```cmd
docker-compose logs -f app
```

### Check Retell AI Dashboard
- Call duration
- Tool invocations
- Error rates
- User satisfaction (if available)

### Check ngrok Inspector
Visit `http://localhost:4040` to see:
- All HTTP requests
- Request/response payloads
- Timing information

## Test Results Template

```
Test Case: [Name]
Date: [Date]
Tester: [Name]

Conversation Flow:
- User: [message 1]
- Agent: [response 1]
- User: [message 2]
- Agent: [response 2]
...

Prediction Result:
- Illness: [predicted illness]
- Confidence: [confidence score]
- Severity: [severity level]

Pass/Fail: [PASS/FAIL]
Notes: [any observations]
```

## Next Steps

After testing:
1. Document any issues found
2. Adjust prompts or configuration as needed
3. Re-test failed cases
4. Consider adding more test cases for your specific use cases
5. Move to production when all tests pass

## Support

If you encounter issues:
1. Check application logs
2. Verify all environment variables
3. Test API endpoints directly (use `/docs`)
4. Review Retell AI documentation
5. Check ngrok connection status
