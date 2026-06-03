# Dynamic Pricing Engine

**Production-Ready ML-Powered Dynamic Pricing System** ✅

An advanced, enterprise-grade dynamic pricing solution with demand forecasting, price optimization, comprehensive monitoring, and full deployment automation. Designed for real-time pricing decisions at scale with business constraints and operational safety.

**Status**: ✅ **PRODUCTION READY** | Full monitoring, testing, deployment automation, and operational guides included.

---

## Executive Summary

The Dynamic Pricing Engine is a complete, production-ready system for intelligent product pricing. It combines machine learning for demand prediction with optimization algorithms to maximize revenue while respecting business constraints (margins, inventory, price ranges).

### What You Get

- 🤖 **ML Demand Forecasting**: XGBoost model predicting product demand with ~49% R² accuracy
- 💰 **Intelligent Price Optimization**: Bayesian optimization to find optimal prices for maximum profit
- 🚀 **Production API**: FastAPI service for real-time pricing decisions
- 📊 **Complete Monitoring**: Health checks, metrics, prediction logging, data drift detection
- 🐳 **Docker Deployment**: Multi-stage builds, Nginx reverse proxy, automated deployment
- 🔒 **Enterprise Security**: Rate limiting, input validation, error handling, non-root containers
- 📈 **Operations Ready**: Comprehensive monitoring, backup/restore, health checks, logging
- ✅ **Well Tested**: Unit tests, integration tests, smoke tests, and pre-deployment checks

---

## Core Features

### ML & Optimization
- **Demand Forecasting**: XGBoost-based model with time-series validation
- **Price Optimization**: Multiple methods (Bayesian, grid search) with business constraints
- **Feature Engineering**: Automated calendar, price, and temporal features
- **Hyperparameter Tuning**: Optuna-based automated optimization (up to 50 trials)
- **Model Monitoring**: Data drift detection, performance tracking, prediction logging
- **Comprehensive Metrics**: MAE, RMSE, R², MAPE, directional accuracy

### Production Infrastructure
- **REST API**: FastAPI with automatic Swagger/ReDoc documentation
- **Monitoring**: Health checks, system metrics (CPU, memory, disk), request tracking
- **Logging**: Structured JSON logs, prediction audit trail (JSONL), log rotation
- **Containerization**: Docker with Nginx reverse proxy, resource limits
- **Database**: SQLite with automated backup/restore (7-day retention)
- **Error Handling**: Global error handlers, input validation, graceful shutdown

### Deployment & Operations
- **Automated Deployment**: Bash scripts for AWS EC2, rollback support
- **CI/CD Ready**: Testing automation, Docker image building, smoke tests
- **Operations Tools**: Health check scripts, metrics dashboard, log viewer
- **Documentation**: API docs, deployment guide, operations manual, troubleshooting guides

---

## Architecture

```
├── src/
│   ├── api/              # FastAPI endpoints & middleware
│   ├── data/             # Data generation, ingestion, validation
│   ├── features/         # Feature engineering & transformation
│   ├── training/         # Model training pipeline & evaluation
│   ├── pricing/          # Price optimization engines
│   ├── monitoring/       # Health checks, metrics, prediction logging
│   └── utils/            # Shared utilities
├── tests/                # Unit, integration, smoke tests
├── configs/              # Environment-based configuration (dev/prod)
├── scripts/              # Training, deployment, operations scripts
├── models/               # Trained models & feature metadata
├── logs/                 # Prediction logs, metrics
├── docker-compose.yml    # Development stack (with reload)
├── docker-compose.prod.yml # Production stack (optimized)
└── nginx/                # Nginx configuration for production
```

---

## Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (for containerized deployment)
- Git

### Local Development Setup

```bash
# Clone repository
git clone <your-repo>
cd Dynamic-Pricing-Engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure (optional)
cp configs/config.dev.yaml configs/config.yaml
```

### Train the Model

```bash
# Basic training
python src/training/train.py

# With hyperparameter tuning (recommended for production)
python scripts/train_with_tuning.py

# Configuration options in configs/config.yaml:
# - run_cv: true          → Enable time-series cross-validation
# - run_hyperparameter_tuning: true → Use Optuna to optimize parameters
# - tuning_trials: 50     → Number of tuning iterations
```

### Run API Locally

```bash
# Development mode (with auto-reload)
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
# - Swagger UI: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
# - Health check: http://localhost:8000/v1/health
```

### Test the API

```bash
# Example: Get optimal price
curl -X POST "http://localhost:8000/optimize-price" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 42,
    "competitor_price": 89.99,
    "dow": 2,
    "is_weekend": 0,
    "week": 15,
    "month": 4,
    "sin_annual": 0.5,
    "cos_annual": 0.866,
    "lag_units_sold_1": 45.0,
    "lag_units_sold_7": 42.0,
    "lag_units_sold_14": 40.0,
    "roll_mean_units_7": 43.5,
    "roll_mean_units_14": 41.2,
    "roll_mean_units_28": 39.8,
    "roll_std_units_7": 5.2,
    "roll_std_units_14": 6.1,
    "roll_std_units_28": 7.3,
    "price_min": 70.0,
    "price_max": 110.0,
    "cost": 60.0,
    "min_margin_pct": 0.15,
    "inventory_limit": 100,
    "optimization_method": "bayesian"
  }'
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run smoke tests
pytest tests/smoke_tests.py -v
```

---

## Production Setup

### Option 1: Docker Compose (Recommended)

```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up -d

# View services
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f pricing-api

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Option 2: AWS EC2 Deployment

For complete AWS deployment guide see [DEPLOYMENT.md](DEPLOYMENT.md):

```bash
# Quick setup (requires AWS instance)
# 1. Provision EC2 instance (Ubuntu 22.04 LTS, t2.micro, 20GB storage)
# 2. Create security group (allow SSH, HTTP, HTTPS)
# 3. Connect to instance and run:

ssh -i your-key.pem ubuntu@YOUR_EC2_IP
cd /home/ubuntu
git clone <your-repo> pricing-engine
cd pricing-engine

# Run deployment script
DEPLOY_HOST=YOUR_EC2_IP ./scripts/deploy.sh

# Verify deployment
./scripts/health_check.sh
```

### Pre-Deployment Checklist

```bash
# Verify everything is ready
./scripts/pre_deploy_check.sh

# This checks:
# ✓ Model file exists
# ✓ Features file exists
# ✓ Configuration is valid
# ✓ Docker setup
# ✓ Tests pass
# ✓ No lint errors
```

---

## Daily Operations

### Morning Checklist

```bash
# 1. Check service health
./scripts/health_check.sh

# 2. Review metrics and performance
./scripts/metrics.sh

# 3. Check for errors in logs (last 50 errors)
./scripts/logs.sh -l ERROR -n 50

# 4. Verify backup completed
ls -lh logs/predictions/ | tail -5
```

### Monitoring & Health Checks

```bash
# Check API health
curl http://localhost:8000/v1/health

# Check readiness (for load balancer)
curl http://localhost:8000/v1/health/ready

# Check liveness
curl http://localhost:8000/v1/health/live

# View system metrics
curl http://localhost:8000/v1/metrics
```

### Common Maintenance Tasks

```bash
# Backup database (manual)
./scripts/backup_database.sh

# Restore database (if needed)
./scripts/restore_database.sh backup_file.db

# View prediction logs
tail -f logs/predictions/predictions_$(date +%Y%m%d)_*.jsonl

# Rotate logs manually
find logs/ -name "*.jsonl" -mtime +7 -delete

# Run load tests
./scripts/load_test.sh
```

### Service Management

```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Restart (for updates)
docker-compose -f docker-compose.prod.yml restart pricing-api

# Stop services
docker-compose -f docker-compose.prod.yml down

# View detailed logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

---

## Model Performance

Current model metrics (in `reports/training_metrics.json`):

- **R² Score**: 0.49 (model explains 49% of demand variance)
- **MAE**: Mean Absolute Error on demand
- **RMSE**: Root Mean Squared Error  
- **MAPE**: Mean Absolute Percentage Error
- **Directional Accuracy**: Ability to predict trend direction

Feature importance: `reports/feature_importance.csv`

---

## Configuration

Edit `configs/config.yaml` for environment-specific settings:

```yaml
model:
  n_estimators: 600      # XGBoost trees
  max_depth: 6          # Tree depth
  learning_rate: 0.05   # Learning rate

pricing:
  default_method: bayesian  # or "grid"
  price_min: 30.0
  price_max: 120.0

training:
  run_cv: false
  run_hyperparameter_tuning: false
  tuning_trials: 50

monitoring:
  enabled: true
  drift_threshold: 0.1
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [API.md](docs/API.md) | Complete API endpoint reference |
| [DEPLOYMENT.md](DEPLOYMENT.md) | AWS deployment guide with step-by-step instructions |
| [OPERATIONS.md](docs/OPERATIONS.md) | Day-to-day operations, troubleshooting, incident response |
| [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md) | Detailed feature implementation guide |
| [PRODUCTION_READY.md](PRODUCTION_READY.md) | Production readiness checklist |

---

## Troubleshooting

### API not responding
```bash
./scripts/health_check.sh
docker-compose -f docker-compose.prod.yml logs pricing-api | tail -50
```

### High error rates
```bash
./scripts/metrics.sh
# Check logs for patterns
./scripts/logs.sh -l ERROR
```

### Database issues
```bash
# Check backup exists
ls -lh backups/database/

# Restore from backup
./scripts/restore_database.sh backups/database/latest.db
```

### Model performance degraded
```bash
# Check data drift
curl http://localhost:8000/v1/health

# Retrain model
python scripts/train_with_tuning.py

# Deploy new model
docker-compose -f docker-compose.prod.yml restart pricing-api
```

See [OPERATIONS.md](docs/OPERATIONS.md) for complete troubleshooting guide.

---

## Development Roadmap

### ✅ Completed
- ML demand forecasting with XGBoost
- Bayesian + grid search optimization
- Business constraints (margins, inventory)
- Comprehensive test suite & monitoring
- Docker containerization
- Production deployment automation
- Health checks & metrics
- Database backup/restore
- Prediction logging & audit trail

### 🚀 Future Enhancements
- A/B testing framework
- Multi-product bundle optimization
- Competitor reaction modeling
- SHAP explainability integration
- MLflow model versioning
- Automated retraining pipelines
- Real-time data streaming
- Advanced ensemble models

---

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `pytest tests/ -v`
3. Commit with clear messages
4. Push and create pull request

Code quality requirements:
- All tests pass: `pytest`
- No lint errors: `flake8 src/`
- Code formatted: `black src/`

---

## Support & Issues

For issues or questions:
1. Check [OPERATIONS.md](docs/OPERATIONS.md) troubleshooting section
2. Review logs: `./scripts/logs.sh`
3. Run health check: `./scripts/health_check.sh`

---

## License

MIT License

---

## Quick Reference

| Task | Command |
|------|---------|
| Start API (dev) | `uvicorn src.api.server:app --reload` |
| Start API (prod) | `docker-compose -f docker-compose.prod.yml up -d` |
| Train model | `python scripts/train_with_tuning.py` |
| Run tests | `pytest tests/ -v` |
| Check health | `./scripts/health_check.sh` |
| View metrics | `./scripts/metrics.sh` |
| Backup database | `./scripts/backup_database.sh` |
| Deploy to AWS | `DEPLOY_HOST=IP ./scripts/deploy.sh` |
