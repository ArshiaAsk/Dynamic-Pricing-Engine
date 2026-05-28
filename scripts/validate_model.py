#!/usr/bin/env python3
"""Validate model performance for CI/CD pipeline"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)


def validate_model():
    """Validate model meets performance thresholds"""
    
    # Check model file exists
    model_path = Path("models/demand_model.pkl")
    if not model_path.exists():
        logger.error("Model file not found")
        return False
    
    # Check metrics file exists
    metrics_path = Path("reports/training_metrics.json")
    if not metrics_path.exists():
        logger.error("Training metrics not found")
        return False
    
    # Load metrics
    with open(metrics_path) as f:
        metrics = json.load(f)
    
    # Define thresholds
    thresholds = {
        'R2': 0.40,
        'MAPE': 0.30,  # 30%
        'MAE': 30.0
    }
    
    # Validate metrics
    passed = True
    for metric, threshold in thresholds.items():
        if metric not in metrics:
            logger.warning(f"Metric {metric} not found in training metrics")
            continue
        
        value = metrics[metric]
        
        # For R2, higher is better
        if metric == 'R2':
            if value < threshold:
                logger.error(f"{metric} = {value:.3f} below threshold {threshold}")
                passed = False
            else:
                logger.info(f"✅ {metric} = {value:.3f} (threshold: {threshold})")
        
        # For MAPE and MAE, lower is better
        else:
            if value > threshold:
                logger.error(f"{metric} = {value:.3f} above threshold {threshold}")
                passed = False
            else:
                logger.info(f"✅ {metric} = {value:.3f} (threshold: {threshold})")
    
    # Check feature importance exists
    feature_importance_path = Path("reports/feature_importance.csv")
    if feature_importance_path.exists():
        logger.info("✅ Feature importance file exists")
    else:
        logger.warning("Feature importance file not found")
    
    return passed


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Model Validation for CI/CD")
    logger.info("=" * 60)
    
    if validate_model():
        logger.info("=" * 60)
        logger.info("✅ Model validation PASSED")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ Model validation FAILED")
        logger.error("=" * 60)
        sys.exit(1)
