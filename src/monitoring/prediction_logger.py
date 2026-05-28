"""Production prediction logging system"""
import json
import pandas as pd
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
    
    def log_prediction(
        self,
        request_id: str,
        input_data: Dict,
        prediction: Dict,
        response_time_ms: float,
        metadata: Optional[Dict] = None
    ):
        """
        Log a single prediction
        
        Args:
            request_id: Unique request identifier
            input_data: Input features
            prediction: Model prediction/optimization result
            response_time_ms: Response time in milliseconds
            metadata: Additional metadata (user_id, session_id, etc.)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'input': self._sanitize_input(input_data),
            'prediction': prediction,
            'response_time_ms': response_time_ms,
            'metadata': metadata or {}
        }
        
        self.buffer.append(log_entry)
        self.stats['total_predictions'] += 1
        
        # Update rolling average response time
        alpha = 0.1  # Exponential moving average factor
        self.stats['avg_response_time_ms'] = (
            alpha * response_time_ms + 
            (1 - alpha) * self.stats['avg_response_time_ms']
        )
        
        # Flush if buffer is full
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
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
    
    def load_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        log_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load logs for analysis
        
        Args:
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            log_type: Filter by type ('optimization', 'error', etc.)
            
        Returns:
            DataFrame with logs
        """
        logs = []
        
        for log_file in sorted(self.log_dir.glob("predictions_*.jsonl")):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if start_date and datetime.fromisoformat(entry['timestamp']) < start_date:
                            continue
                        if end_date and datetime.fromisoformat(entry['timestamp']) > end_date:
                            continue
                        if log_type and entry.get('type') != log_type:
                            continue
                        
                        logs.append(entry)
                        
            except Exception as e:
                logger.warning(f"Failed to read {log_file}: {e}")
        
        return pd.DataFrame(logs) if logs else pd.DataFrame()
    
    def __del__(self):
        """Flush remaining logs on cleanup"""
        self.flush()


# Global prediction logger instance
_prediction_logger = None


def get_prediction_logger(log_dir: str = "logs/predictions") -> PredictionLogger:
    """Get or create global prediction logger"""
    global _prediction_logger
    if _prediction_logger is None:
        _prediction_logger = PredictionLogger(log_dir)
    return _prediction_logger
