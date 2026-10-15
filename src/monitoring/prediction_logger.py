"""Production prediction logging system"""
import atexit
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from collections import deque
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PredictionLogger:
    """
    Log predictions for monitoring, auditing, and retraining
    Thread-safe with batch writing for performance
    """
    
    def __init__(self, log_dir: str = "logs/predictions", batch_size: int = 100):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self.buffer = deque(maxlen=batch_size * 2)
        self.stats = {
            'total_predictions': 0,
            'total_optimizations': 0,
            'avg_response_time_ms': 0.0,
        }
        # R17: flush remaining entries at interpreter exit via atexit, not in
        # __del__. Running I/O from __del__ during teardown raises
        # `ImportError: sys.meta_path is None, Python is likely shutting down`.
        # atexit callbacks run before module teardown, so the flush is safe.
        atexit.register(self.flush)
    
    def log_optimization(
        self,
        request_id: str,
        input_data: Dict,
        result: Dict,
        response_time_ms: float,
        metadata: Optional[Dict] = None
    ):
        """Log a price optimization request"""
        self.stats['total_optimizations'] += 1
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'type': 'optimization',
            'input': self._sanitize_input(input_data),
            'result': result,
            'response_time_ms': response_time_ms,
            'metadata': metadata or {}
        }
        
        self.buffer.append(log_entry)
        
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def log_error(
        self,
        request_id: str,
        error_type: str,
        error_message: str,
        input_data: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ):
        """Log an error"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'input': self._sanitize_input(input_data) if input_data else None,
            'metadata': metadata or {}
        }
        
        self.buffer.append(log_entry)
        
        # Flush errors immediately
        self.flush()
    
    def flush(self):
        """Write buffered logs to disk"""
        if not self.buffer:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H")
        log_file = self.log_dir / f"predictions_{timestamp}.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                while self.buffer:
                    entry = self.buffer.popleft()
                    f.write(json.dumps(entry) + '\n')
            
            logger.debug(f"Flushed prediction logs to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to flush logs: {e}")
    
    def get_stats(self) -> Dict:
        """Get logging statistics"""
        return {
            **self.stats,
            'buffer_size': len(self.buffer),
            'log_dir': str(self.log_dir)
        }
    
    def _sanitize_input(self, input_data: Dict) -> Dict:
        """Remove sensitive data from logs"""
        if not input_data:
            return {}
        
        # Remove potentially sensitive fields
        sensitive_fields = ['user_id', 'customer_id', 'email', 'phone']
        sanitized = input_data.copy()
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***REDACTED***'
        
        return sanitized


# Global prediction logger instance
_prediction_logger = None


def get_prediction_logger(log_dir: str = "logs/predictions") -> PredictionLogger:
    """Get or create global prediction logger"""
    global _prediction_logger
    if _prediction_logger is None:
        _prediction_logger = PredictionLogger(log_dir)
    return _prediction_logger
