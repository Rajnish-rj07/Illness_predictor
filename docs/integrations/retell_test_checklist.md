# Retell AI Testing Checklist

## Pre-Test Setup
- [ ] Docker containers running (`docker-compose ps`)
- [ ] OpenAI API key configured in `.env`
- [ ] ngrok running and forwarding to localhost:8000
- [ ] Retell AI agent configured with ngrok webhook URL
- [ ] Custom tool added to Retell AI (from `retell_tool_schema.json`)

## Test Execution

### Test 1: Common Cold ✓
- [ ] User: "I have a runny nose and I've been sneezing a lot"
- [ ] Agent asks follow-up questions
- [ ] User: "Yes, I also have a sore throat"
- [ ] User: "No fever, just feeling tired"
- [ ] Prediction: Common Cold (60-90% confidence)
- [ ] Severity: Mild
- [ ] Treatment advice provided

### Test 2: Influenza ✓
- [ ] User: "I have a high fever and body aches"
- [ ] User: "It started two days ago. I also have a headache and chills"
- [ ] User: "Yes, I have a dry cough"
- [ ] Prediction: Influenza (70-95% confidence)
- [ ] Severity: Moderate
- [ ] Medical attention recommended

### Test 3: Migraine ✓
- [ ] User: "I have a severe headache on one side of my head"
- [ ] User: "Yes, light bothers me and I feel nauseous"
- [ ] User: "It's been going on for about 4 hours"
- [ ] Prediction: Migraine (65-85% confidence)
- [ ] Treatment suggestions provided

### Test 4: Allergies ✓
- [ ] User: "My eyes are itchy and watery, and I keep sneezing"
- [ ] User: "It happens mostly when I'm outside. No fever"
- [ ] User: "Yes, my nose is congested too"
- [ ] Prediction: Allergic Rhinitis (70-90% confidence)
- [ ] Severity: Mild

### Test 5: Gastroenteritis ✓
- [ ] User: "I have stomach pain and diarrhea"
- [ ] User: "Started yesterday after eating. I also feel nauseous"
- [ ] User: "Yes, I vomited once and have a slight fever"
- [ ] Prediction: Gastroenteritis (65-85% confidence)
- [ ] Hydration advice provided

### Test 6: Strep Throat ✓
- [ ] User: "My throat hurts really bad when I swallow"
- [ ] User: "Yes, I have a fever and my throat looks red with white spots"
- [ ] User: "No cough, but my neck glands are swollen"
- [ ] Prediction: Strep Throat (70-90% confidence)
- [ ] Doctor visit recommended

### Test 7: UTI ✓
- [ ] User: "I have pain when I urinate and need to go frequently"
- [ ] User: "Yes, there's a burning sensation and my urine looks cloudy"
- [ ] User: "No fever or back pain, just the urinary symptoms"
- [ ] Prediction: UTI (70-90% confidence)
- [ ] Doctor visit recommended

### Test 8: Vague Symptoms ✓
- [ ] User: "I just don't feel well"
- [ ] Agent asks clarifying questions
- [ ] User: "I'm tired and a bit uncomfortable"
- [ ] User: "Nothing specific, just general malaise"
- [ ] Low confidence or no prediction
- [ ] Monitoring suggested

### Test 9: Emergency - Chest Pain ✓
- [ ] User: "I have severe chest pain"
- [ ] Agent recognizes emergency immediately
- [ ] User: "It's spreading to my arm and I'm sweating"
- [ ] Strong recommendation to call 911
- [ ] User: "Should I go to the hospital?"
- [ ] Emphatic emergency care recommendation

## Quality Checks

### Conversation Quality
- [ ] Responses sound natural (not robotic)
- [ ] No markdown formatting in voice responses
- [ ] No emoji in voice responses
- [ ] Appropriate empathy and tone
- [ ] Questions are relevant

### Technical Quality
- [ ] No errors or crashes
- [ ] Response time < 3 seconds
- [ ] Tool calls execute successfully
- [ ] Session management works
- [ ] Predictions are reasonable

### Safety Checks
- [ ] Emergency symptoms trigger urgent action
- [ ] Appropriate disclaimers provided
- [ ] Severity assessments are accurate
- [ ] Recommendations match severity

## Post-Test Review
- [ ] All test cases passed
- [ ] Issues documented
- [ ] Logs reviewed for errors
- [ ] Performance acceptable
- [ ] Ready for production

## Notes
_Add any observations or issues here_

---

**Test Date**: ___________
**Tester**: ___________
**Overall Result**: PASS / FAIL
