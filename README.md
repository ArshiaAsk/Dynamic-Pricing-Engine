# Dynamic Pricing Engine

An advanced ML-powered dynamic pricing system with demand forecasting and price optimization.

## Features

### Core Capabilities
- **Demand Forecasting**: XGBoost-based model predicting product demand
- **Price Optimization**: Bayesian optimization for revenue maximization
- **Business Constraints**: Support for minimum margins, inventory limits
- **REST API**: FastAPI-based service for real-time pricing decisions

### Advanced Features
- **Hyperparameter Tuning**: Optuna-based automated optimization
- **Cross-Validation**: Time-series aware validation
- **Model Monitoring**: Data drift detection and performance tracking
- **Comprehensive Metrics**: MAE, RMSE, R², MAPE, directional accuracy
- **Feature Importance**: SHAP-ready model explainability
- **Multiple Optimizers**: Grid search and Bayesian optimization

## Architecture

```
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── data/             # Data generation and ingestion
│   ├── features/         # Feature engineering
│   ├── training/         # Model training pipeline
│   ├── pricing/          # Price optimization engines
│   ├── monitoring/       # Model monitoring and metrics
│   └── utils/            # Utilities
├── tests/                # Comprehensive test suite
├── configs/              # Configuration files
├── scripts/              # Training and utility scripts
└── models/               # Trained models
```

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Training

**Basic Training:**
```bash
python src/training/train.py
```

**With Hyperparameter Tuning:**
```bash
python scripts/train_with_tuning.py
```

**Configuration Options** (`configs/config.yaml`):
- `run_cv: true` - Enable cross-validation
- `run_hyperparameter_tuning: true` - Enable Optuna tuning
- `tuning_trials: 50` - Number of tuning trials

### Running the API

```bash
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

### API Usage

**Optimize Price (Bayesian):**
```bash
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

**Response:**
```json
{
  "optimal_price": 87.50,
  "expected_demand": 48.3,
  "expected_revenue": 4226.25,
  "optimization_method": "bayesian",
  "profit_margin": 0.314,
  "profit_per_unit": 27.50,
  "total_profit": 1328.25,
  "optimization_success": true,
  "optimization_iterations": 12
}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_optimizer.py -v
```

## Model Performance

Current metrics are tracked in `reports/training_metrics.json`:
- **MAE**: Mean Absolute Error
- **RMSE**: Root Mean Squared Error
- **R²**: Coefficient of determination
- **MAPE**: Mean Absolute Percentage Error
- **Directional Accuracy**: Trend prediction accuracy

Feature importance is saved to `reports/feature_importance.csv`.

## Monitoring

The system includes production monitoring capabilities:

- **Data Drift Detection**: Statistical tests for feature distribution changes
- **Performance Tracking**: Real-time metric calculation
- **Degradation Alerts**: Automatic detection of model performance drops
- **Prediction Logging**: JSONL logs for audit and retraining

## Configuration

Key configuration options in `configs/config.yaml`:

```yaml
model:
  n_estimators: 600
  max_depth: 6
  learning_rate: 0.05

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

## Docker Deployment

```bash
# Build image
docker build -t pricing-engine .

# Run container
docker run -p 8000:8000 pricing-engine

# Or use docker-compose
docker-compose up
```

## Development Roadmap

### Completed ✅
- Enhanced evaluation metrics (MAPE, directional accuracy)
- Cross-validation with time-series splits
- Hyperparameter tuning with Optuna
- Bayesian optimization for pricing
- Business constraints (margins, inventory)
- Comprehensive test suite
- Model monitoring infrastructure
- Configurable API with validation

### Future Enhancements
- [ ] A/B testing framework
- [ ] Multi-product bundle optimization
- [ ] Competitor reaction modeling
- [ ] SHAP explainability integration
- [ ] MLflow model versioning
- [ ] Automated retraining pipeline
- [ ] Real-time data streaming
- [ ] Advanced ensemble models (LightGBM, CatBoost)

## Contributing

1. Run tests before committing: `pytest`
2. Follow existing code style
3. Add tests for new features
4. Update documentation

## License

MIT License
