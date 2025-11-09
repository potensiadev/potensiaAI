# potensia_ai/core/exceptions.py
"""
Custom exception classes for PotensiaAI.

Provides structured exception hierarchy for better error handling
and consistent error responses across the application.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class PotensiaAIError(Exception):
    """
    Base exception class for all PotensiaAI errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize custom exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (e.g., "INVALID_INPUT")
            details: Additional error details for debugging
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


# ============================================================
# API / HTTP Exceptions
# ============================================================

class APIError(PotensiaAIError):
    """Base class for API-related errors"""
    pass


class ValidationError(APIError):
    """Input validation error (HTTP 400)"""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = {"field": field} if field else {}
        details.update(kwargs)
        super().__init__(message, "VALIDATION_ERROR", details)


class ResourceNotFoundError(APIError):
    """Resource not found error (HTTP 404)"""

    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} not found: {resource_id}"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        details.update(kwargs)
        super().__init__(message, "RESOURCE_NOT_FOUND", details)


class AuthenticationError(APIError):
    """Authentication error (HTTP 401)"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, "AUTHENTICATION_ERROR", kwargs)


class AuthorizationError(APIError):
    """Authorization error (HTTP 403)"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, "AUTHORIZATION_ERROR", kwargs)


class RateLimitExceeded(APIError):
    """Rate limit exceeded error (HTTP 429)"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        details = {"retry_after": retry_after} if retry_after else {}
        details.update(kwargs)
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


# ============================================================
# AI Provider Exceptions
# ============================================================

class AIProviderError(PotensiaAIError):
    """Base class for AI provider errors"""
    pass


class OpenAIError(AIProviderError):
    """OpenAI API error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "OPENAI_ERROR", kwargs)


class AnthropicError(AIProviderError):
    """Anthropic API error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "ANTHROPIC_ERROR", kwargs)


class GeminiError(AIProviderError):
    """Google Gemini API error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, "GEMINI_ERROR", kwargs)


class AITimeoutError(AIProviderError):
    """AI API timeout error"""

    def __init__(self, provider: str, timeout: int, **kwargs):
        message = f"{provider} API timeout after {timeout}s"
        details = {"provider": provider, "timeout": timeout}
        details.update(kwargs)
        super().__init__(message, "AI_TIMEOUT", details)


class AIQuotaExceeded(AIProviderError):
    """AI API quota exceeded"""

    def __init__(self, provider: str, **kwargs):
        message = f"{provider} API quota exceeded"
        details = {"provider": provider}
        details.update(kwargs)
        super().__init__(message, "AI_QUOTA_EXCEEDED", details)


# ============================================================
# Content Generation Exceptions
# ============================================================

class ContentGenerationError(PotensiaAIError):
    """Base class for content generation errors"""
    pass


class TopicRefinementError(ContentGenerationError):
    """Topic refinement failed"""

    def __init__(self, topic: str, reason: Optional[str] = None, **kwargs):
        message = f"Failed to refine topic: {topic}"
        if reason:
            message += f" - {reason}"
        details = {"topic": topic, "reason": reason}
        details.update(kwargs)
        super().__init__(message, "TOPIC_REFINEMENT_ERROR", details)


class ContentValidationError(ContentGenerationError):
    """Content validation failed"""

    def __init__(self, issues: list, **kwargs):
        message = f"Content validation failed: {len(issues)} issues found"
        details = {"issues": issues}
        details.update(kwargs)
        super().__init__(message, "CONTENT_VALIDATION_ERROR", details)


class KeywordExtractionError(ContentGenerationError):
    """Keyword extraction failed"""

    def __init__(self, topic: str, reason: Optional[str] = None, **kwargs):
        message = f"Failed to extract keywords for: {topic}"
        if reason:
            message += f" - {reason}"
        details = {"topic": topic, "reason": reason}
        details.update(kwargs)
        super().__init__(message, "KEYWORD_EXTRACTION_ERROR", details)


class ImageGenerationError(ContentGenerationError):
    """Image generation failed"""

    def __init__(self, prompt: str, reason: Optional[str] = None, **kwargs):
        message = f"Failed to generate image"
        if reason:
            message += f": {reason}"
        details = {"prompt": prompt[:100], "reason": reason}
        details.update(kwargs)
        super().__init__(message, "IMAGE_GENERATION_ERROR", details)


# ============================================================
# Security Exceptions
# ============================================================

class SecurityError(PotensiaAIError):
    """Base class for security-related errors"""
    pass


class PromptInjectionDetected(SecurityError):
    """Prompt injection attack detected"""

    def __init__(self, input_text: str, **kwargs):
        message = "Potential prompt injection detected"
        details = {"input_preview": input_text[:100]}
        details.update(kwargs)
        super().__init__(message, "PROMPT_INJECTION_DETECTED", details)


class MaliciousContentDetected(SecurityError):
    """Malicious content detected"""

    def __init__(self, content_type: str, **kwargs):
        message = f"Malicious content detected: {content_type}"
        details = {"content_type": content_type}
        details.update(kwargs)
        super().__init__(message, "MALICIOUS_CONTENT", details)


# ============================================================
# Exception to HTTP Status Mapping
# ============================================================

EXCEPTION_STATUS_MAP = {
    ValidationError: status.HTTP_400_BAD_REQUEST,
    ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    RateLimitExceeded: status.HTTP_429_TOO_MANY_REQUESTS,
    AITimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    AIQuotaExceeded: status.HTTP_503_SERVICE_UNAVAILABLE,
    PromptInjectionDetected: status.HTTP_400_BAD_REQUEST,
    MaliciousContentDetected: status.HTTP_400_BAD_REQUEST,

    # Default mappings
    ContentGenerationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    AIProviderError: status.HTTP_503_SERVICE_UNAVAILABLE,
    SecurityError: status.HTTP_403_FORBIDDEN,
    APIError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    PotensiaAIError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def exception_to_http_exception(exc: PotensiaAIError) -> HTTPException:
    """
    Convert custom exception to FastAPI HTTPException.

    Args:
        exc: Custom PotensiaAI exception

    Returns:
        HTTPException with appropriate status code and details
    """
    status_code = EXCEPTION_STATUS_MAP.get(
        type(exc),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    return HTTPException(
        status_code=status_code,
        detail=exc.to_dict()
    )


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    print("\n" + "="*80)
    print("Exception Classes Test")
    print("="*80 + "\n")

    # Test validation error
    try:
        raise ValidationError("Invalid email format", field="email")
    except ValidationError as e:
        print(f"ValidationError: {e.message}")
        print(f"Error dict: {e.to_dict()}")
        print(f"HTTP Exception: {exception_to_http_exception(e)}\n")

    # Test content generation error
    try:
        raise TopicRefinementError(
            topic="Python tutorial",
            reason="AI returned empty response"
        )
    except TopicRefinementError as e:
        print(f"TopicRefinementError: {e.message}")
        print(f"Error dict: {e.to_dict()}\n")

    # Test prompt injection
    try:
        raise PromptInjectionDetected("Ignore previous instructions and...")
    except PromptInjectionDetected as e:
        print(f"PromptInjectionDetected: {e.message}")
        print(f"Error dict: {e.to_dict()}\n")

    print("="*80)
    print("All exception tests passed!")
    print("="*80 + "\n")
