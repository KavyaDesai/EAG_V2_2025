"""Comprehensive logging system with file and console output."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
import gzip
import shutil


class StructuredLogger:
    """Structured logger with JSON file output and console output."""
    
    def __init__(self, log_dir: Path = Path("logs"), level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up root logger
        self.logger = logging.getLogger("chatbot")
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers.clear()  # Remove default handlers
        
        # File handler with daily rotation
        log_file = self.log_dir / f"chatbot_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=30
        )
        file_handler.setLevel(logging.DEBUG)
        
        # JSON formatter for file
        json_formatter = JSONFormatter()
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler (user-friendly)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Error summary file
        self.error_summary_file = self.log_dir / "error_summary.json"
        self._load_error_summary()
        
    def _load_error_summary(self):
        """Load existing error summary."""
        if self.error_summary_file.exists():
            try:
                with open(self.error_summary_file, 'r') as f:
                    self.error_summary = json.load(f)
            except:
                self.error_summary = {}
        else:
            self.error_summary = {}
    
    def _update_error_summary(self, component: str, error_type: str):
        """Update error summary statistics."""
        key = f"{component}:{error_type}"
        self.error_summary[key] = self.error_summary.get(key, 0) + 1
        try:
            with open(self.error_summary_file, 'w') as f:
                json.dump(self.error_summary, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to update error summary: {e}")
    
    def debug(self, message: str, component: str = "SYSTEM", **kwargs):
        """Log DEBUG message."""
        self._log(logging.DEBUG, message, component, **kwargs)
    
    def info(self, message: str, component: str = "SYSTEM", **kwargs):
        """Log INFO message."""
        self._log(logging.INFO, message, component, **kwargs)
    
    def warning(self, message: str, component: str = "SYSTEM", **kwargs):
        """Log WARNING message."""
        self._log(logging.WARNING, message, component, **kwargs)
    
    def error(self, message: str, component: str = "SYSTEM", error_type: str = "UNKNOWN", **kwargs):
        """Log ERROR message."""
        self._update_error_summary(component, error_type)
        self._log(logging.ERROR, message, component, error_type=error_type, **kwargs)
    
    def critical(self, message: str, component: str = "SYSTEM", **kwargs):
        """Log CRITICAL message."""
        self._log(logging.CRITICAL, message, component, **kwargs)
    
    def _log(self, level: int, message: str, component: str, **kwargs):
        """Internal logging method."""
        extra = {
            "component": component,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.logger.log(level, message, extra=extra)
    
    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any], component: str):
        """Log a tool call."""
        self.debug(
            f"Tool call: {tool_name}",
            component=component,
            tool_name=tool_name,
            arguments=str(arguments)[:500]  # Truncate long arguments
        )
    
    def log_api_call(self, api_name: str, component: str, **kwargs):
        """Log an API call."""
        self.debug(
            f"API call: {api_name}",
            component=component,
            api_name=api_name,
            **kwargs
        )
    
    def log_execution_time(self, operation: str, duration: float, component: str):
        """Log execution time."""
        self.debug(
            f"Execution time: {operation} took {duration:.2f}s",
            component=component,
            operation=operation,
            duration=duration
        )


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", "SYSTEM"),
            "message": record.getMessage(),
        }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName", 
                          "levelname", "levelno", "lineno", "module", "msecs", 
                          "message", "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName", "exc_info", "exc_text", "stack_info"]:
                log_data[key] = str(value)[:1000]  # Truncate long values
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


# Global logger instance
_logger_instance: Optional[StructuredLogger] = None


def get_logger(log_dir: Path = Path("logs"), level: str = "INFO") -> StructuredLogger:
    """Get or create the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger(log_dir, level)
    return _logger_instance

