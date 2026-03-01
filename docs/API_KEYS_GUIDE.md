# API Keys & Services Guide

Complete guide to all API keys and external services needed for the Illness Prediction System.

## Quick Start (Minimum Cost)

**Total Cost for Testing: ~$5 (OpenAI free credits)**

You only need:
1. OpenAI API key ($5 free credits)
2. A random secret key (free to generate)

Everything else is optional or runs locally for free.

---

## 1. LLM API (REQUIRED)

The system needs an AI model to understand natural language symptoms.

### Option A: OpenAI (Recommended for Beginners)

**Cost:** $5 free credits for new accounts

**Steps:**
1. Go to: https://platform.openai.com/signup
2. Create an account
3. Add payment method (required, but you get $5 free)
4. Go to: https://platform.openai.com/api-keys
5. Click "Create new secret key"
6. Copy the key (starts with `sk-`)
7. Add to `.env`: `OPENAI_API_KEY=sk-...`

**Pricing after free credits:**
- GPT-3.5-turbo: $0.0015 per 1K tokens (~$0.002 per conversation)
- GPT-4: $0.03 per 1K tokens (~$0.05 per conversation)

**Free credits last:** 3 months or until used up

### Option B: Anthropic Claude

**Cost:** No free tier, but cheaper than GPT-4

**Steps:**
1. Go to: https://console.anthropic.com/
2. Create an account
3. Add payment method
4. Go to API keys section
5. Create new key
6. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

**Pricing:**
- Claude 3 Haiku: $0.00025 per 1K tokens (~$0.001 per conversation)
- Claude 3 Sonnet: $0.003 per 1K tokens (~$0.005 per conversation)

### Option C: Local LLM (FREE but Advanced)

**Cost:** $0 (completely free)

**Requirements:**
- 16GB+ RAM
- Good CPU or GPU
- Technical knowledge

**Steps:**
1. Install Ollama: https://ollama.ai/
2. Download a model: `ollama pull llama2`
3. Run locally: `ollama serve`
4. Configure app to use local endpoint
5. Modify code to use Ollama API format

**Pros:** Free, private, no API limits
**Cons:** Slower, requires powerful hardware, more setup

---

## 2. Database & Cache (FREE - Included)

These run in Docker containers - no API keys needed!

### PostgreSQL Database
- **Cost:** $0 (runs locally in Docker)
- **Setup:** Automatic via docker-compose
- **Storage:** Your local disk

### Redis Cache
- **Cost:** $0 (runs locally in Docker)
- **Setup:** Automatic via docker-compose
- **Storage:** Your local RAM

**No action needed** - these start automatically with `docker-compose up`

---

## 3. Translation Service (OPTIONAL)

Only needed for multi-language support (English, Spanish, French, Hindi, Mandarin).

### Option A: Google Cloud Translation API

**Cost:** $300 free credits for new accounts

**Steps:**
1. Go to: https://cloud.google.com/translate
2. Create Google Cloud account
3. Enable Translation API
4. Create API key
5. Add to `.env`: `GOOGLE_TRANSLATE_API_KEY=...`

**Pricing after free credits:**
- $20 per 1 million characters
- ~$0.02 per conversation

**Free credits last:** 90 days

### Option B: Skip Translation (FREE)

**Cost:** $0

**Steps:**
1. Don't add translation API key
2. System will only support English
3. Remove translation service calls from code

**Trade-off:** English only, but completely free

---

## 4. Location Services (OPTIONAL)

Only needed for "find nearby hospitals/clinics" feature.

### Option A: Google Places API

**Cost:** $200 monthly free credit

**Steps:**
1. Go to: https://console.cloud.google.com/
2. Enable Places API
3. Create API key
4. Add to `.env`: `GOOGLE_PLACES_API_KEY=...`

**Pricing:**
- $200 free monthly credit
- Covers ~40,000 place searches per month
- $0.017 per search after free tier

**Free tier:** Renews monthly

### Option B: Skip Location Feature (FREE)

**Cost:** $0

**Steps:**
1. Don't add Places API key
2. Disable location service in code
3. Users won't see nearby facilities

**Trade-off:** No location features, but free

---

## 5. SMS/WhatsApp (OPTIONAL)

Only needed for SMS and WhatsApp channels.

### Twilio

**Cost:** $15 free trial credit

**Steps:**
1. Go to: https://www.twilio.com/try-twilio
2. Sign up for free trial
3. Get phone number
4. Copy credentials
5. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=+1...
   ```

**Pricing after trial:**
- SMS: $0.0075 per message
- WhatsApp: $0.005 per message

**Trial limitations:**
- Can only send to verified numbers
- Upgrade to send to anyone

### Skip SMS/WhatsApp (FREE)

**Cost:** $0

**Steps:**
1. Don't add Twilio credentials
2. Use web API only
3. Users access via HTTP/REST

**Trade-off:** Web only, but free

---

## 6. Monitoring (FREE)

All monitoring tools are open-source and free!

### Prometheus (Metrics)
- **Cost:** $0
- **Setup:** Included in docker-compose
- **Storage:** Local disk

### Grafana (Dashboards)
- **Cost:** $0
- **Setup:** Included in docker-compose
- **Access:** http://localhost:3000

### Alertmanager (Alerts)
- **Cost:** $0
- **Setup:** Included in docker-compose
- **Notifications:** Email, Slack (free)

**No API keys needed** - all run locally!

---

## Cost Comparison

### Minimum (Testing)
- **OpenAI free credits:** $5 (free for 3 months)
- **Database/Redis:** $0 (local Docker)
- **Total:** $0 for 3 months

### Basic (English-only, Web-only)
- **OpenAI:** ~$10/month (1000 conversations)
- **Database/Redis:** $0 (local Docker)
- **Total:** ~$10/month

### Full Features
- **OpenAI:** ~$10/month
- **Translation:** $0 (within free tier)
- **Location:** $0 (within free tier)
- **SMS:** ~$7.50/month (1000 messages)
- **Total:** ~$17.50/month

### Production (High Volume)
- **OpenAI:** ~$100/month (10,000 conversations)
- **Translation:** ~$20/month
- **Location:** ~$50/month
- **SMS:** ~$75/month (10,000 messages)
- **Hosting:** ~$100/month (AWS/GCP)
- **Total:** ~$345/month

---

## Setup Instructions

### Step 1: Get OpenAI API Key (Required)

```bash
# 1. Sign up at https://platform.openai.com/signup
# 2. Add payment method (get $5 free)
# 3. Create API key
# 4. Copy the key
```

### Step 2: Create .env File

```bash
# Copy the minimal template
copy .env.minimal .env

# Edit the file
notepad .env

# Add your OpenAI key
OPENAI_API_KEY=sk-your-actual-key-here
```

### Step 3: Generate Secret Key

```bash
# Generate a random secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Copy the output and add to .env
SECRET_KEY=your-generated-secret-here
```

### Step 4: Start the System

```bash
docker-compose up -d
```

That's it! The system will run with:
- ✅ AI-powered symptom extraction (OpenAI)
- ✅ Database (PostgreSQL - local)
- ✅ Cache (Redis - local)
- ✅ Web API (FastAPI - local)
- ❌ Translation (disabled - English only)
- ❌ Location services (disabled)
- ❌ SMS/WhatsApp (disabled - web only)

---

## Adding Optional Services Later

### Enable Translation

```bash
# 1. Get Google Translate API key
# 2. Add to .env:
GOOGLE_TRANSLATE_API_KEY=your-key-here

# 3. Restart
docker-compose restart app
```

### Enable Location Services

```bash
# 1. Get Google Places API key
# 2. Add to .env:
GOOGLE_PLACES_API_KEY=your-key-here

# 3. Restart
docker-compose restart app
```

### Enable SMS/WhatsApp

```bash
# 1. Get Twilio credentials
# 2. Add to .env:
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# 3. Restart
docker-compose restart app
```

---

## Free Tier Limits

### OpenAI
- **Free:** $5 credit (3 months)
- **Limit:** ~2,500 conversations
- **After:** Pay as you go

### Google Cloud (Translation + Places)
- **Free:** $300 credit (90 days) + $200/month Places credit
- **Limit:** Varies by service
- **After:** Pay as you go

### Twilio
- **Free:** $15 trial credit
- **Limit:** ~2,000 SMS messages
- **Restrictions:** Can only send to verified numbers
- **After:** Pay as you go

---

## Recommended Setup for Different Use Cases

### 1. Personal Testing/Development
```
✅ OpenAI (free $5 credits)
✅ Local Database/Redis
❌ Translation
❌ Location
❌ SMS/WhatsApp
Cost: $0 for 3 months
```

### 2. MVP/Prototype (English-speaking users)
```
✅ OpenAI ($10/month)
✅ Local Database/Redis
❌ Translation
✅ Location (free tier)
❌ SMS/WhatsApp
Cost: ~$10/month
```

### 3. Full-Featured Demo
```
✅ OpenAI ($10/month)
✅ Local Database/Redis
✅ Translation (free tier)
✅ Location (free tier)
✅ SMS/WhatsApp ($10/month)
Cost: ~$20/month
```

### 4. Production
```
✅ OpenAI or Claude ($100+/month)
✅ Managed Database (AWS RDS, $50/month)
✅ Translation ($20/month)
✅ Location ($50/month)
✅ SMS/WhatsApp ($75/month)
✅ Hosting (AWS/GCP, $100/month)
Cost: ~$395/month
```

---

## Troubleshooting

### "Invalid API key" Error

**OpenAI:**
- Check key starts with `sk-`
- No spaces before/after key
- Key not expired
- Billing enabled on OpenAI account

**Google:**
- API enabled in Google Cloud Console
- Billing account linked
- Key restrictions not blocking requests

### "Quota exceeded" Error

**OpenAI:**
- Free credits used up
- Add payment method
- Check usage: https://platform.openai.com/usage

**Google:**
- Free tier exhausted
- Enable billing
- Check quotas in Cloud Console

### "Service unavailable" Error

**Check:**
- API key is set in .env
- Docker containers are running
- No typos in environment variables
- Restart containers: `docker-compose restart`

---

## Security Best Practices

1. **Never commit .env to git**
   ```bash
   # Add to .gitignore
   .env
   .env.local
   .env.*.local
   ```

2. **Use different keys for dev/prod**
   ```bash
   # Development
   OPENAI_API_KEY=sk-dev-key...
   
   # Production
   OPENAI_API_KEY=sk-prod-key...
   ```

3. **Rotate keys regularly**
   - Every 90 days minimum
   - Immediately if compromised

4. **Use environment-specific secrets**
   - Don't share production keys
   - Use secret management (AWS Secrets Manager, etc.)

5. **Monitor API usage**
   - Set up billing alerts
   - Track unusual spikes
   - Review logs regularly

---

## Summary

**To get started (FREE for 3 months):**

1. Get OpenAI API key ($5 free credits)
2. Generate a secret key
3. Create .env file
4. Run `docker-compose up -d`

**Total time:** 10 minutes
**Total cost:** $0 for testing

All other services are optional and can be added later as needed!

---

**Last Updated:** 2024
**Questions?** Check WINDOWS_SETUP_GUIDE.md or docs/PRE_DEPLOYMENT_CHECKLIST.md
