"""Health check and monitoring endpoints"""
import time
import psutil
from typing import Dict
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)

class HealthChecker:
    """
    System health monitoring
    Checks model availability, system resources, and performance
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_prediction_time = None
    
    def check_health(self, model=None) -> Dict:
        """
        Comprehensive health check
        
        Returns:
            Health status dictionary
        """
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.start_time,
            'checks': {}
        }
        
        # Model check
        if model is not None:
            try:
                # Quick prediction test
                import numpy as np
                n_features = int(getattr(model, "n_features_in_", 10))
                test_input = np.zeros((1, n_features))  # Dummy input matching model expectation
                _ = model.predict(test_input)
                health['checks']['model'] = {'status': 'ok', 'loaded': True}
            
            except Exception as e:
                health['checks']['model'] = {'status': 'error', 'error': str(e)}
                health['status'] = 'degraded'
        else:
            health['checks']['model'] = {'status': 'warning', 'loaded': False}
            health['status'] = 'degraded'
        
        # System resources
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health['checks']['system'] = {
                'status': 'ok',
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            }
            
            # Warn if resources are low
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                health['status'] = 'degraded'
                health['checks']['system']['status'] = 'warning'
                
        except Exception as e:
            health['checks']['system'] = {'status': 'error', 'error': str(e)}
        
        # Request metrics
        health['metrics'] = {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'last_prediction': self.last_prediction_time
        }
        
        return health
    
    def check_readiness(self, model=None) -> Dict:
        """
        Readiness check for load balancer
        Returns quickly, only checks critical components
        """
        ready = {
            'ready': True,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check model is loaded
        if model is None:
            ready['ready'] = False
            ready['reason'] = 'Model not loaded'
        
        return ready
    
    def check_liveness(self) -> Dict:
        """
        Liveness check for container orchestration
        Returns quickly, just confirms process is alive
        """
        return {
            'alive': True,
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.start_time
        }
    
    def record_request(self):
        """Record a successful request"""
        self.request_count += 1
        self.last_prediction_time = datetime.now().isoformat()
    
    def record_error(self):
        """Record an error"""
        self.error_count += 1
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'requests_per_second': self.request_count / max(uptime, 1),
            'last_prediction': self.last_prediction_time
        }


# Global health checker instance
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
