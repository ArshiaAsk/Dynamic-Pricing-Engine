"""Model monitoring for production deployment"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModelMonitor:
    """Monitor model performance and data drift in production"""
    
    def __init__(self, log_dir: str = "logs/monitoring"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.predictions_log = []
        self.feature_stats = {}
        
    def log_prediction(
        self,
        features: Dict,
        prediction: float,
        actual: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        """Log a prediction for monitoring"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "features": features,
            "prediction": float(prediction),
            "actual": float(actual) if actual is not None else None,
            "metadata": metadata or {}
        }
        
        self.predictions_log.append(log_entry)
        
        # Periodically save to disk
        if len(self.predictions_log) >= 100:
            self._save_logs()
    
    def _save_logs(self):
        """Save prediction logs to disk"""
        if not self.predictions_log:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"predictions_{timestamp}.jsonl"
        
        with open(log_file, 'w') as f:
            for entry in self.predictions_log:
                f.write(json.dumps(entry) + '\n')
        
        logger.info(f"Saved {len(self.predictions_log)} predictions to {log_file}")
        self.predictions_log = []
    
    def calculate_drift(
        self,
        current_features: pd.DataFrame,
        reference_features: pd.DataFrame,
        threshold: float = 0.1
    ) -> Dict:
        """
        Detect data drift using statistical tests
        
        Args:
            current_features: Recent production features
            reference_features: Training/reference features
            threshold: Drift threshold
            
        Returns:
            Dictionary with drift metrics per feature
        """
        drift_results = {}
        
        for col in current_features.columns:
            if col not in reference_features.columns:
                continue
            
            # Calculate distribution statistics
            ref_mean = reference_features[col].mean()
            ref_std = reference_features[col].std()
            
            curr_mean = current_features[col].mean()
            curr_std = current_features[col].std()
            
            # Normalized difference in means
            if ref_std > 0:
                mean_drift = abs(curr_mean - ref_mean) / ref_std
            else:
                mean_drift = 0.0
            
            # Std ratio
            std_ratio = curr_std / ref_std if ref_std > 0 else 1.0
            
            drift_detected = mean_drift > threshold or abs(1 - std_ratio) > threshold
            
            drift_results[col] = {
                "mean_drift": float(mean_drift),
                "std_ratio": float(std_ratio),
                "drift_detected": bool(drift_detected),
                "ref_mean": float(ref_mean),
                "curr_mean": float(curr_mean),
                "ref_std": float(ref_std),
                "curr_std": float(curr_std)
            }
        
        # Count drifted features
        n_drifted = sum(1 for v in drift_results.values() if v["drift_detected"])
        
        logger.info(f"Drift detection: {n_drifted}/{len(drift_results)} features drifted")
        
        return {
            "features": drift_results,
            "n_drifted": n_drifted,
            "total_features": len(drift_results),
            "drift_percentage": n_drifted / len(drift_results) if drift_results else 0
        }
    
    def calculate_performance_metrics(
        self,
        predictions: List[float],
        actuals: List[float]
    ) -> Dict:
        """Calculate performance metrics on recent predictions"""
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        mae = mean_absolute_error(actuals, predictions)
        rmse = np.sqrt(mean_squared_error(actuals, predictions))
        r2 = r2_score(actuals, predictions)
        
        # MAPE
        mask = actuals != 0
        mape = np.mean(np.abs((actuals[mask] - predictions[mask]) / actuals[mask])) if mask.any() else 0
        
        return {
            "MAE": float(mae),
            "RMSE": float(rmse),
            "R2": float(r2),
            "MAPE": float(mape),
            "n_samples": len(predictions)
        }
    
    def check_model_degradation(
        self,
        current_metrics: Dict,
        baseline_metrics: Dict,
        threshold: float = 0.1
    ) -> Dict:
        """
        Check if model performance has degraded
        
        Args:
            current_metrics: Recent performance metrics
            baseline_metrics: Training/baseline metrics
            threshold: Degradation threshold (e.g., 0.1 = 10% worse)
        """
        degradation = {}
        
        for metric in ['MAE', 'RMSE', 'R2', 'MAPE']:
            if metric not in current_metrics or metric not in baseline_metrics:
                continue
            
            baseline = baseline_metrics[metric]
            current = current_metrics[metric]
            
            # For MAE, RMSE, MAPE: lower is better
            if metric in ['MAE', 'RMSE', 'MAPE']:
                if baseline > 0:
                    pct_change = (current - baseline) / baseline
                    degraded = pct_change > threshold
                else:
                    pct_change = 0
                    degraded = False
            # For R2: higher is better
            else:
                if baseline > 0:
                    pct_change = (baseline - current) / abs(baseline)
                    degraded = pct_change > threshold
                else:
                    pct_change = 0
                    degraded = False
            
            degradation[metric] = {
                "baseline": float(baseline),
                "current": float(current),
                "pct_change": float(pct_change),
                "degraded": bool(degraded)
            }
        
        any_degraded = any(v["degraded"] for v in degradation.values())
        
        if any_degraded:
            logger.warning("Model performance degradation detected!")
        
        return {
            "metrics": degradation,
            "degraded": any_degraded
        }
