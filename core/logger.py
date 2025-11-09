# potensia_ai/core/logger.py
"""
Centralized Logging System for PotensiaAI

Provides structured logging with:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic timestamp and module tracking
- File and console output
- JSON formatting for production environments
- Token usage tracking
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json

from core.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured logs with consistent format.

    Format: [TIMESTAMP] [LEVEL] [MODULE] Message
    Example: [2025-01-09 10:30:45] [INFO] [writer.generator] Content generation started
    """

    def format(self, record: logging.LogRecord) -> str:
        # Create timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Extract module name (e.g., "writer.generator" from "ai_tools.writer.generator")
        module_parts = record.name.split('.')
        if len(module_parts) > 2:
            module_name = '.'.join(module_parts[-2:])
        else:
            module_name = record.name

        # Build structured message
        level = record.levelname
        message = record.getMessage()

        # Add extra fields if present
        extra_fields = {}
        for key in ['topic', 'tokens', 'model_name', 'cost', 'duration', 'component']:
            if hasattr(record, key):
                extra_fields[key] = getattr(record, key)

        if extra_fields:
            extra_str = ' | ' + ' | '.join(f"{k}={v}" for k, v in extra_fields.items())
        else:
            extra_str = ''

        return f"[{timestamp}] [{level:8}] [{module_name}] {message}{extra_str}"


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for production environments and log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'file': record.pathname,
            'line': record.lineno,
        }

        # Add extra fields
        for key in ['topic', 'tokens', 'model_name', 'cost', 'duration', 'component', 'user_id', 'request_id']:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    use_json: bool = False
) -> logging.Logger:
    """
    Set up a logger with consistent configuration.

    Args:
        name: Logger name (usually module name like "writer.generator")
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses settings.LOG_LEVEL
        log_file: Optional file path for file logging
        use_json: If True, use JSON formatter instead of structured text

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger("writer.generator", level="INFO")
        >>> logger.info("Content generation started", extra={'topic': 'Python tutorial'})
    """
    logger = logging.getLogger(name)

    # Set level
    log_level = level or getattr(settings, 'LOG_LEVEL', 'INFO')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logger.level)

    if use_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(StructuredFormatter())

    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logger.level)

        if use_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(StructuredFormatter())

        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with standard configuration.

    Args:
        name: Logger name (e.g., "writer.generator", "keyword.analyzer")

    Returns:
        Configured logger instance

    Example:
        >>> from core.logger import get_logger
        >>> logger = get_logger("writer.generator")
        >>> logger.info("Starting content generation")
    """
    # Check if logger already exists and is configured
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Configure with default settings
        log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
        log_dir = getattr(settings, 'LOG_DIR', 'logs')
        use_json = getattr(settings, 'LOG_JSON', False)

        # Create log file path
        log_file = None
        if log_dir:
            log_file = f"{log_dir}/potensia_ai.log"

        logger = setup_logger(
            name=name,
            level=log_level,
            log_file=log_file,
            use_json=use_json
        )

    return logger


class TokenUsageLogger:
    """
    Specialized logger for tracking API token usage and costs.
    """

    def __init__(self, logger_name: str = "usage.tokens"):
        self.logger = get_logger(logger_name)

        # Token costs (approximate, as of 2025)
        self.costs = {
            # OpenAI GPT models (per 1M tokens)
            'gpt-4o': {'input': 2.50, 'output': 10.00},
            'gpt-4o-mini': {'input': 0.150, 'output': 0.600},
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
            'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},

            # OpenAI O1 models
            'o1-preview': {'input': 15.00, 'output': 60.00},
            'o1-mini': {'input': 3.00, 'output': 12.00},

            # Anthropic Claude models
            'claude-3-5-sonnet': {'input': 3.00, 'output': 15.00},
            'claude-3-opus': {'input': 15.00, 'output': 75.00},
            'claude-3-haiku': {'input': 0.25, 'output': 1.25},

            # DALL-E models (per image)
            'dall-e-3': {'standard_1024': 0.040, 'standard_1792': 0.080, 'hd_1024': 0.080, 'hd_1792': 0.120},
            'dall-e-2': {'256': 0.016, '512': 0.018, '1024': 0.020},
        }

    def log_completion(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        topic: Optional[str] = None,
        component: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log token usage for a completion request.

        Args:
            model: Model name (e.g., "gpt-4o-mini")
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            topic: Optional topic/task description
            component: Optional component/module name (e.g., "writer.generator")

        Returns:
            Dictionary with usage statistics and cost
        """
        # Calculate cost
        cost_info = self._calculate_cost(model, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens

        # Build log message
        msg = f"Token usage: {total_tokens:,} total ({input_tokens:,} input + {output_tokens:,} output)"

        extra = {
            'model_name': model,
            'tokens': total_tokens,
            'cost': f"${cost_info['total_cost']:.6f}"
        }

        if topic:
            extra['topic'] = topic[:50]
        if component:
            extra['component'] = component

        self.logger.info(msg, extra=extra)

        return {
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            **cost_info
        }

    def log_image_generation(
        self,
        model: str,
        size: str,
        quality: str = 'standard',
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log image generation request.

        Args:
            model: Model name ("dall-e-2" or "dall-e-3")
            size: Image size ("1024x1024", etc.)
            quality: Image quality ("standard" or "hd")
            topic: Optional topic/prompt description

        Returns:
            Dictionary with cost information
        """
        cost = self._calculate_image_cost(model, size, quality)

        msg = f"Image generated: {model} {size} ({quality})"
        extra = {
            'model_name': model,
            'size': size,
            'cost': f"${cost:.6f}"
        }

        if topic:
            extra['topic'] = topic[:50]

        self.logger.info(msg, extra=extra)

        return {
            'model': model,
            'size': size,
            'quality': quality,
            'cost': cost
        }

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Calculate cost for text completion"""
        # Normalize model name
        model_lower = model.lower()

        # Find matching model in cost table
        model_key = None
        for key in self.costs.keys():
            if key in model_lower:
                model_key = key
                break

        if not model_key or 'dall-e' in model_key:
            # Unknown model or image model
            return {'input_cost': 0.0, 'output_cost': 0.0, 'total_cost': 0.0}

        rates = self.costs[model_key]
        input_cost = (input_tokens / 1_000_000) * rates['input']
        output_cost = (output_tokens / 1_000_000) * rates['output']

        return {
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': input_cost + output_cost
        }

    def _calculate_image_cost(self, model: str, size: str, quality: str) -> float:
        """Calculate cost for image generation"""
        model_lower = model.lower()

        if 'dall-e-3' in model_lower:
            # DALL-E 3 pricing
            size_key = size.replace('x', '_')
            quality_prefix = f"{quality}_{size.split('x')[0]}"

            if quality_prefix in self.costs['dall-e-3']:
                return self.costs['dall-e-3'][quality_prefix]
            elif size.split('x')[0] in self.costs['dall-e-3']:
                return self.costs['dall-e-3'][size.split('x')[0]]
            else:
                return 0.040  # Default standard 1024

        elif 'dall-e-2' in model_lower:
            # DALL-E 2 pricing
            size_num = size.split('x')[0]
            return self.costs.get('dall-e-2', {}).get(size_num, 0.020)

        return 0.0


# Global token usage logger instance
token_logger = TokenUsageLogger()


# ============================================================
# Test & Examples
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Example 1: Basic logging
    logger = get_logger("test.module")

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Example 2: Logging with extra fields
    logger.info(
        "Content generation completed",
        extra={
            'topic': 'Python tutorial',
            'tokens': 1500,
            'model_name': 'gpt-4o-mini',
            'duration': 2.5
        }
    )

    # Example 3: Token usage logging
    usage = token_logger.log_completion(
        model='gpt-4o-mini',
        input_tokens=500,
        output_tokens=1000,
        topic='Python web scraping tutorial',
        component='writer.generator'
    )
    print(f"\nUsage stats: {usage}")

    # Example 4: Image generation logging
    img_usage = token_logger.log_image_generation(
        model='dall-e-3',
        size='1024x1024',
        quality='standard',
        topic='Modern tech illustration'
    )
    print(f"\nImage generation cost: ${img_usage['cost']:.6f}")
