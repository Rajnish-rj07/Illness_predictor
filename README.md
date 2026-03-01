# 🏥 AI-Powered Illness Prediction System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-553%20passing-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)

An intelligent healthcare application that combines machine learning with conversational AI to predict potential illnesses based on user-reported symptoms. The system provides accurate predictions with confidence scores, severity assessments, and personalized treatment recommendations through natural voice and text conversations.

## 🌟 Key Features

### 🤖 Intelligent Symptom Analysis
- **Natural Language Processing**: Extract symptoms from conversational input using OpenAI GPT-4
- **Smart Follow-up Questions**: Information gain-based questioning to gather relevant symptoms
- **Context-Aware Conversations**: Maintains conversation history for coherent multi-turn interactions

### 🎯 ML-Powered Predictions
- **XGBoost Classification**: Trained machine learning models for accurate illness prediction
- **Confidence Scoring**: Transparent confidence percentages for each prediction
- **Top-K Results**: Returns multiple possible conditions ranked by likelihood
- **Model Explainability**: SHAP-based explanations showing which symptoms influenced predictions

### 🚨 Safety & Severity Assessment
- **Automated Severity Scoring**: Classifies conditions as Low, Moderate, High, or Critical
- **Emergency Detection**: Identifies life-threatening symptoms requiring immediate attention
- **Safety Disclaimers**: Clear medical advice disclaimers on all predictions

### 💊 Treatment Recommendations
- **OTC Medication Suggestions**: Context-appropriate over-the-counter medication recommendations
- **Home Care Advice**: Practical self-care instructions based on predicted conditions
- **Professional Referrals**: Guidance on when to seek medical attention

### 🌐 Multi-Channel Support
- **Voice Interface**: Retell AI integration for natural voice conversations
- **Web API**: RESTful API for chat-based interactions
- **SMS/WhatsApp**: Twilio integration for messaging platforms (configurable)

### 🌍 Multi-Language Support
- **5 Languages**: English, Spanish, French, Hindi, and Mandarin Chinese
- **Automatic Translation**: Seamless translation while preserving medical terminology
- **Language Detection**: Automatic detection of user's preferred language

### 🔒 Privacy & Security
- **HIPAA/GDPR Compliant**: Privacy-first architecture with data encryption
- **PII Protection**: Automatic detection and anonymization of personal information
- **Secure Sessions**: Encrypted session management with Redis
- **Data Retention Controls**: Configurable data deletion policies

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
│  Voice (Retell AI) │ Web Chat │ SMS │ WhatsApp              │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   API Gateway (FastAPI)                      │
│  • Authentication  • Rate Limiting  • Request Routing        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Conversation Manager                            │
│  • Session Management  • Context Tracking  • Flow Control    │
└─────┬──────────────┬──────────────┬────────────────┬────────┘
      │              │              │                │
┌─────▼─────┐  ┌────▼─────┐  ┌────▼──────┐  ┌─────▼────────┐
│   LLM     │  │ Question │  │Prediction │  │  Treatment   │
│  Service  │  │  Engine  │  │  Service  │  │   Service    │
│           │  │          │  │           │  │              │
│ Symptom   │  │Info Gain │  │ML Model   │  │Medication    │
│Extraction │  │Questions │  │Inference  │  │Suggestions   │
└───────────┘  └──────────┘  └─────┬─────┘  └──────────────┘
                                    │
                             ┌──────▼──────┐
                             │  ML Model   │
                             │  (XGBoost)  │
                             └─────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  PostgreSQL (Persistent) │ Redis (Sessions) │ MLflow (Models)│
└─────────────────────────────────────────────────────────────┘
```

## 📊 System Capabilities

| Feature | Status | Description |
|---------|--------|-------------|
| Symptom Extraction | ✅ | NLP-powered extraction from natural language |
| Intelligent Questioning | ✅ | Information gain algorithm for optimal questions |
| ML Predictions | ✅ | XGBoost models with 75%+ accuracy |
| Severity Scoring | ✅ | 4-level severity classification |
| Treatment Suggestions | ✅ | Context-aware medication and care advice |
| Voice Interface | ✅ | Retell AI integration |
| Chat Interface | ✅ | RESTful API with session management |
| Multi-Language | ✅ | 5 languages supported |
| Model Explainability | ✅ | SHAP-based feature importance |
| Drift Detection | ✅ | PSI-based feature and concept drift monitoring |
| Privacy Controls | ✅ | Encryption, PII removal, anonymization |
| Production Ready | ✅ | Docker, K8s, monitoring, CI/CD |

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (recommended)
- PostgreSQL 14+ (if not using Docker)
- Redis 7+ (if not using Docker)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/illness-prediction-system.git
cd illness-prediction-system

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys (OpenAI, Twilio, etc.)

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec app python -m src.database.init_db

# View logs
docker-compose logs -f app
```

The application will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/illness-prediction-system.git
cd illness-prediction-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start PostgreSQL and Redis (ensure they're running)

# Initialize database
python -m src.database.init_db

# Run the application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 Usage Examples

### Example 1: Chat-Based Symptom Check

```bash
# Create a new session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"channel": "web", "language": "en"}'

# Response: {"session_id": "abc123", ...}

# Send symptoms
curl -X POST http://localhost:8000/api/v1/sessions/abc123/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "I have a headache, fever, and sore throat"}'

# Response includes follow-up questions or predictions
```

### Example 2: Voice Conversation Flow

```
User: "I'm not feeling well"
System: "I'm sorry to hear that. Can you describe your symptoms?"

User: "I have a headache and fever"
System: "I understand. Do you have any body aches or muscle pain?"

User: "Yes, my whole body hurts"
System: "Are you experiencing a sore throat or cough?"

User: "Yes, sore throat"
System: "Based on your symptoms, here are the most likely conditions:

1. Influenza 🟡 (MODERATE)
   Confidence: 78.5%
   
   Key Contributing Symptoms:
   - Fever (high importance)
   - Body aches (high importance)
   - Headache (medium importance)
   
   Suggested OTC Medications:
   - Acetaminophen (Tylenol) for fever and pain
   - Ibuprofen (Advil) for inflammation
   
   Home Care:
   - Rest and stay hydrated
   - Monitor temperature
   - Isolate from others
   
   ⚠️ Seek medical attention if symptoms worsen or persist beyond 7 days."
```

## 🧪 Testing

The system includes comprehensive testing with 553 passing tests:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m property      # Property-based tests
pytest -m e2e          # End-to-end tests

# View coverage report
open htmlcov/index.html
```

### Test Coverage

- Unit Tests: 400+ tests covering individual components
- Integration Tests: 30+ tests for API endpoints and workflows
- Property-Based Tests: 60+ properties using Hypothesis
- End-to-End Tests: Complete conversation flows
- Performance Tests: Load testing with Locust

## 📁 Project Structure

```
illness-prediction-system/
├── src/                          # Source code
│   ├── api/                      # FastAPI routes and middleware
│   │   ├── routes/              # API endpoints
│   │   └── middleware/          # Authentication, rate limiting
│   ├── conversation/            # Conversation management
│   ├── prediction/              # Prediction service
│   ├── ml/                      # ML model service
│   ├── question_engine/         # Question generation
│   ├── llm/                     # LLM integration (OpenAI)
│   ├── treatment/               # Treatment suggestions
│   ├── explainability/          # SHAP explanations
│   ├── translation/             # Multi-language support
│   ├── location/                # Healthcare facility finder
│   ├── security/                # Encryption and privacy
│   ├── session/                 # Session management
│   ├── database/                # Database models and connections
│   ├── mlops/                   # MLOps pipeline
│   │   ├── training/           # Model training
│   │   ├── deployment/         # Model deployment
│   │   ├── monitoring/         # Performance monitoring
│   │   └── drift/              # Drift detection
│   └── main.py                  # Application entry point
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── property/               # Property-based tests
│   └── e2e/                    # End-to-end tests
├── data/                        # Training data and datasets
├── models/                      # Trained ML models
├── config/                      # Configuration files
├── docs/                        # Documentation
│   ├── api/                    # API documentation
│   ├── deployment/             # Deployment guides
│   └── operations/             # Operations runbooks
├── k8s/                         # Kubernetes manifests
├── scripts/                     # Utility scripts
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile                   # Docker image definition
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
└── README.md                    # This file
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=illness_pred_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=illness_prediction

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM Provider (OpenAI)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7

# ML Model
ML_MODEL_PATH=models/illness_predictor.pkl
CONFIDENCE_THRESHOLD=0.30

# Security
ENCRYPTION_KEY=your_fernet_key
JWT_SECRET=your_jwt_secret

# Twilio (Optional)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Retell AI (Optional)
RETELL_API_KEY=your_retell_api_key
```

## 📊 MLOps Pipeline

### Model Training

```bash
# Train a new model
python -m src.mlops.train \
  --data-path data/training \
  --model-name illness_predictor \
  --experiment-name production

# View training metrics in MLflow
mlflow ui --port 5000
```

### Model Deployment

```bash
# Deploy to staging
python -m src.mlops.deploy \
  --model-version v1.0.0 \
  --environment staging

# Canary deployment to production
python -m src.mlops.deploy \
  --model-version v1.0.0 \
  --environment production \
  --strategy canary \
  --canary-percentage 10
```

### Monitoring

- Prometheus metrics: http://localhost:9090/metrics
- Grafana dashboards: http://localhost:3000
- MLflow tracking: http://localhost:5000

## 🔐 Security Features

- **Encryption at Rest**: All sensitive data encrypted using Fernet
- **Encryption in Transit**: TLS/SSL for all API communications
- **PII Detection**: Automatic detection and removal of personal information
- **Session Anonymization**: User sessions anonymized before storage
- **Rate Limiting**: Protection against abuse and DDoS
- **Authentication**: JWT-based authentication for API access
- **Audit Logging**: Comprehensive logging of all system activities

## 🌐 API Documentation

Interactive API documentation is available at `/docs` when the application is running:

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sessions` | POST | Create new conversation session |
| `/api/v1/sessions/{id}` | GET | Get session details |
| `/api/v1/sessions/{id}/messages` | POST | Send message in session |
| `/api/v1/sessions/{id}/messages` | GET | Get conversation history |
| `/api/v1/retell/chat` | POST | Retell AI webhook endpoint |
| `/health` | GET | Health check endpoint |
| `/metrics` | GET | Prometheus metrics |

## 🚢 Deployment

### Docker Compose (Development/Staging)

```bash
docker-compose up -d
```

### Kubernetes (Production)

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n illness-prediction

# View logs
kubectl logs -f deployment/illness-pred-app -n illness-prediction
```

### Cloud Platforms

- **AWS**: Deploy to ECS/EKS with RDS and ElastiCache
- **Google Cloud**: Deploy to GKE with Cloud SQL and Memorystore
- **Azure**: Deploy to AKS with Azure Database and Azure Cache

See `docs/deployment/` for detailed deployment guides.

## 📈 Performance

- **Response Time**: < 500ms for predictions
- **Throughput**: 1000+ requests/minute
- **Accuracy**: 75%+ prediction accuracy
- **Availability**: 99.9% uptime target
- **Scalability**: Horizontal scaling with Kubernetes

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`pytest`)
- Code follows style guidelines (`black`, `flake8`, `mypy`)
- Documentation is updated
- Commit messages are descriptive

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Medical Disclaimer

This system is designed for educational and informational purposes only. It is NOT a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition. Never disregard professional medical advice or delay in seeking it because of something you have read or received from this system.

## 🙏 Acknowledgments

- **OpenAI**: GPT-4 for natural language processing
- **XGBoost**: Machine learning framework
- **FastAPI**: Modern web framework
- **Retell AI**: Voice conversation platform
- **Hypothesis**: Property-based testing framework
- **MLflow**: MLOps platform

## 📧 Contact

For questions, issues, or collaboration opportunities:

- GitHub Issues: [Create an issue](https://github.com/Rajnish-rj07/illness-prediction-system/issues)
- Email: rajnishmaurya7778@gmail.com
- Documentation: [Full Documentation](docs/)

## 🗺️ Roadmap

### Upcoming Features

- [ ] Mobile applications (iOS/Android)
- [ ] Integration with electronic health records (EHR)
- [ ] Telemedicine video consultation booking
- [ ] Wearable device integration
- [ ] Advanced deep learning models
- [ ] Personalized health recommendations
- [ ] Symptom tracking over time
- [ ] Family health profiles

---

**Built with ❤️ for better healthcare accessibility**

*Last Updated: March 2026*
