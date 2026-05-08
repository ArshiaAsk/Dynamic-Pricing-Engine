"""Prometheus-style metrics tracking"""
from typing import Dict
from collections import defaultdict
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsTracker:
    """Track API and model metrics for monitoring"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.gauges = {}
        
    def increment_counter(self, name: str, value: int = 1, labels: Dict = None):
        """Increment a counter metric"""
        key = self._make_key(name, labels)
        self.counters[key] += value
    
    def record_histogram(self, name: str, value: float, labels: Dict = None):
        """Record a value in a histogram"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict = None):
        """Set a gauge value"""
        key = self._make_key(name, labels)
        self.gauges[key] = value
    
    def _make_key(self, name: str, labels: Dict = None) -> str:
        """Create metric key with labels"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def get_metrics(self) -> Dict:
        """Get all metrics"""
        metrics = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {}
        }
        
        # Calculate histogram statistics
        for key, values in self.histograms.items():
            if values:
                import numpy as np
                metrics["histograms"][key] = {
                    "count": len(values),
                    "sum": float(np.sum(values)),
                    "mean": float(np.mean(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "p50": float(np.percentile(values, 50)),
                    "p95": float(np.percentile(values, 95)),
                    "p99": float(np.percentile(values, 99))
                }
        
        return metrics
    
    def reset(self):
        """Reset all metrics"""
        self.counters.clear()
        self.histograms.clear()
        self.gauges.clear()


# Global metrics tracker
_metrics_tracker = MetricsTracker()


def get_metrics_tracker() -> MetricsTracker:
    """Get global metrics tracker"""
    return _metrics_tracker


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, tracker: MetricsTracker, metric_name: str, labels: Dict = None):
        self.tracker = tracker
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.tracker.record_histogram(self.metric_name, duration, self.labels)
