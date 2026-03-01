# Quick Start Guide

This guide will help you get the Illness Prediction System up and running quickly.

## Prerequisites

- Python 3.10 or higher
- PostgreSQL 14 or higher
- Redis 7 or higher
- Git

## Option 1: Local Setup (Recommended for Development)

### Step 1: Clone and Setup Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd illness-prediction-system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# At minimum, update:
# - Database credentials
# - Redis connection
# - LLM API key (OpenAI or Anthropic)
# - Encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Step 3: Start Required Services

**PostgreSQL:**
```bash
# On Ubuntu/Debian:
sudo systemctl start postgresql

# On macOS with Homebrew:
brew services start postgresql

# On Windows:
# Start PostgreSQL service from Services panel
```

**Redis:**
```bash
# On Ubuntu/Debian:
sudo systemctl start redis

# On macOS with Homebrew:
brew services start redis

# On Windows:
# Download and run Redis from https://github.com/microsoftarchive/redis/releases
redis-server
```

### Step 4: Initialize Database

```bash
# Create database tables
python -m src.database.init_db
```

### Step 5: Run the Application

```bash
# Development mode (with auto-reload)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or use the Makefile:
make run
```

### Step 6: Verify Installation

Open your browser and navigate to:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Root: http://localhost:8000/

## Option 2: Docker Setup (Recommended for Production)

### Step 1: Install Docker

Install Docker and Docker Compose from https://docs.docker.com/get-docker/

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Update LLM API key and other external service credentials
```

### Step 3: Start All Services

```bash
# Build and start all containers
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Step 4: Initialize Database

```bash
# Run database initialization inside the container
docker-compose exec app python -m src.database.init_db
```

### Step 5: Verify Installation

Open your browser and navigate to:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m property      # Property-based tests only
pytest -m integration   # Integration tests only

# Or use Makefile:
make test
make test-cov
```

## Common Issues

### Database Connection Error

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
1. Ensure PostgreSQL is running: `sudo systemctl status postgresql`
2. Check database credentials in `.env`
3. Verify database exists: `psql -U postgres -c "\l"`
4. Create database if needed: `createdb -U postgres illness_prediction`

### Redis Connection Error

**Problem:** `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solution:**
1. Ensure Redis is running: `redis-cli ping` (should return "PONG")
2. Check Redis connection settings in `.env`
3. Start Redis: `redis-server`

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
1. Ensure virtual environment is activated
2. Install dependencies: `pip install -r requirements.txt`
3. Run from project root directory

### LLM API Errors

**Problem:** `openai.error.AuthenticationError: Invalid API key`

**Solution:**
1. Verify your API key in `.env`
2. Ensure you have credits/access to the LLM service
3. Check the `LLM_PROVIDER` setting matches your API key type

## Next Steps

1. **Configure External Services:**
   - Set up Twilio for SMS/WhatsApp (optional)
   - Configure Google Places API for location services (optional)
   - Set up translation API for multi-language support (optional)

2. **Train Initial Model:**
   ```bash
   # Prepare training data in data/training/
   # Run training pipeline
   python -m src.mlops.train --data-path data/training
   ```

3. **Explore API:**
   - Visit http://localhost:8000/docs for interactive API documentation
   - Try the example endpoints
   - Review the API schemas

4. **Read Documentation:**
   - See README.md for detailed architecture
   - Review design.md in .kiro/specs/illness-prediction-system/
   - Check requirements.md for feature specifications

## Development Workflow

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test

# Clean generated files
make clean
```

## Getting Help

- Check the README.md for detailed documentation
- Review the API documentation at /docs
- Open an issue on GitHub
- Contact the development team

## Production Deployment

For production deployment:
1. Use Docker Compose or Kubernetes
2. Set up proper secrets management
3. Configure SSL/TLS certificates
4. Set up monitoring and alerting
5. Configure backup strategies
6. Review security settings in .env

See the deployment documentation for detailed instructions.
