# app/core/logging_config.py
"""
Comprehensive logging configuration for PyWhatsApp.
Provides file-based logging with rotation for debugging template API issues.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path


# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log files
ERROR_LOG_FILE = LOGS_DIR / "error.log"
DEBUG_LOG_FILE = LOGS_DIR / "debug.log"
TEMPLATE_API_LOG_FILE = LOGS_DIR / "template_api.log"


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(app_name: str = "pywhatsapp", level: str = "DEBUG"):
    """
    Setup comprehensive logging with file handlers.

    Creates three log files:
    - error.log: Only ERROR and CRITICAL messages
    - debug.log: All DEBUG and above messages
    - template_api.log: Specific to template API operations
    """

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # ═══════════════════════════════════════════════════════════
    # Console Handler - with colors
    # ═══════════════════════════════════════════════════════════
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(levelname)s | %(name)s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ═══════════════════════════════════════════════════════════
    # ERROR Log File - Rotating, only errors
    # ═══════════════════════════════════════════════════════════
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s\n'
        '%(exc_info)s' if '%(exc_info)s' else '',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)

    # ═══════════════════════════════════════════════════════════
    # DEBUG Log File - Rotating, all messages
    # ═══════════════════════════════════════════════════════════
    debug_handler = logging.handlers.RotatingFileHandler(
        DEBUG_LOG_FILE,
        maxBytes=20 * 1024 * 1024,  # 20 MB
        backupCount=5,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    debug_handler.setFormatter(debug_formatter)
    root_logger.addHandler(debug_handler)

    # ═══════════════════════════════════════════════════════════
    # Template API Log File - Specific to template operations
    # ═══════════════════════════════════════════════════════════
    template_handler = logging.handlers.RotatingFileHandler(
        TEMPLATE_API_LOG_FILE,
        maxBytes=20 * 1024 * 1024,  # 20 MB
        backupCount=5,
        encoding='utf-8'
    )
    template_handler.setLevel(logging.DEBUG)
    template_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    template_handler.setFormatter(template_formatter)

    # Only attach to template-related loggers
    template_logger = logging.getLogger("template_api")
    template_logger.addHandler(template_handler)
    template_logger.setLevel(logging.DEBUG)
    template_logger.propagate = True  # Also send to root handlers

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"{'='*60}")
    logger.info(f"Logging initialized for {app_name}")
    logger.info(f"Log directory: {LOGS_DIR}")
    logger.info(f"Error log: {ERROR_LOG_FILE}")
    logger.info(f"Debug log: {DEBUG_LOG_FILE}")
    logger.info(f"Template API log: {TEMPLATE_API_LOG_FILE}")
    logger.info(f"{'='*60}")

    return root_logger


def get_template_logger():
    """Get logger specifically for template API operations"""
    return logging.getLogger("template_api")


# ═══════════════════════════════════════════════════════════
# Helper functions for detailed logging
# ═══════════════════════════════════════════════════════════

def log_api_request(logger, method: str, endpoint: str, data: dict = None, headers: dict = None):
    """Log outgoing API request details"""
    logger.debug(f"{'─'*60}")
    logger.debug(f"🌐 API REQUEST: {method} {endpoint}")
    logger.debug(f"{'─'*60}")
    if headers:
        logger.debug(f"Headers: {headers}")
    if data:
        logger.debug(f"Request Data: {data}")
    logger.debug(f"{'─'*60}")


def log_api_response(logger, status_code: int, response_data: any, error: Exception = None):
    """Log API response details"""
    logger.debug(f"{'─'*60}")
    logger.debug(f"📥 API RESPONSE: Status {status_code}")
    logger.debug(f"{'─'*60}")
    if error:
        logger.error(f"❌ Error: {error}")
        logger.error(f"Error Type: {type(error).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
    else:
        logger.debug(f"Response Data: {response_data}")
    logger.debug(f"{'─'*60}")


def log_function_entry(logger, func_name: str, **kwargs):
    """Log function entry with parameters"""
    logger.debug(f"{'═'*60}")
    logger.debug(f"➡️  ENTERING: {func_name}")
    if kwargs:
        for key, value in kwargs.items():
            # Hide sensitive data
            if key in ['token', 'password', 'secret', 'api_key']:
                value = '***HIDDEN***'
            logger.debug(f"  ├─ {key}: {value}")
    logger.debug(f"{'═'*60}")


def log_function_exit(logger, func_name: str, result: any = None, error: Exception = None):
    """Log function exit with result or error"""
    logger.debug(f"{'═'*60}")
    if error:
        logger.error(f"❌ EXITING: {func_name} with ERROR")
        logger.error(f"  └─ Error: {error}")
    else:
        logger.debug(f"✅ EXITING: {func_name}")
        if result is not None:
            logger.debug(f"  └─ Result: {result}")
    logger.debug(f"{'═'*60}")
