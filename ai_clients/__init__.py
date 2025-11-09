# potensia_ai/ai_clients/__init__.py
"""
AI Client Abstraction Layer for PotensiaAI

Provides unified interfaces for multiple AI providers:
- OpenAI (GPT-4, GPT-3.5, DALL-E)
- Anthropic (Claude)
- Google (Gemini)

Features:
- Automatic retry with exponential backoff
- Token usage tracking
- Cost calculation
- Error handling
- Async support
"""

from .base import AIClient, CompletionRequest, CompletionResponse
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient

__all__ = [
    "AIClient",
    "CompletionRequest",
    "CompletionResponse",
    "OpenAIClient",
    "AnthropicClient",
]
