# potensia_ai/ai_clients/base.py
"""
Base classes and interfaces for AI client abstraction.

Defines common data structures and abstract base class that all
AI clients must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """Message role in conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Conversation message"""
    role: MessageRole
    content: str


@dataclass
class CompletionRequest:
    """
    Unified request format for text completion across all AI providers.

    This abstraction allows switching between providers without changing
    application logic.
    """
    messages: List[Message]
    model: Optional[str] = None  # If None, uses default from settings
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None  # Alternative to system message


@dataclass
class CompletionResponse:
    """
    Unified response format for text completion.

    Attributes:
        content: Generated text
        model: Actual model used
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        total_tokens: Total tokens (input + output)
        cost: Estimated cost in USD
        provider: AI provider name (openai, anthropic, google)
        raw_response: Original response object for debugging
    """
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    provider: str
    raw_response: Optional[Any] = None


class AIClient(ABC):
    """
    Abstract base class for AI clients.

    All AI provider clients must implement this interface to ensure
    consistent behavior across the application.
    """

    def __init__(self, api_key: str, logger_name: str = "ai_client"):
        """
        Initialize AI client.

        Args:
            api_key: API key for the provider
            logger_name: Logger name for tracking
        """
        self.api_key = api_key
        self.logger_name = logger_name

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate text completion.

        Args:
            request: Completion request with messages and parameters

        Returns:
            Completion response with generated text and metadata

        Raises:
            Exception: If API call fails after all retries
        """
        pass

    @abstractmethod
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for the API call.

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        pass

    @abstractmethod
    def is_reasoning_model(self, model: str) -> bool:
        """
        Check if model is a reasoning model requiring special parameters.

        Args:
            model: Model name

        Returns:
            True if reasoning model (o1, o3, etc.)
        """
        pass

    def _format_messages(self, request: CompletionRequest) -> List[Dict[str, str]]:
        """
        Convert Message objects to provider-specific format.

        Args:
            request: Completion request

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system prompt if provided
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })

        # Add conversation messages
        for msg in request.messages:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return messages
