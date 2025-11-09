# potensia_ai/ai_clients/anthropic_client.py
"""
Anthropic Claude client implementation with retry logic and cost tracking.
"""

import asyncio
from typing import Optional
from anthropic import AsyncAnthropic, APIError, RateLimitError, APIConnectionError

from core.config import settings
from core.logger import get_logger, token_logger
from ai_clients.base import AIClient, CompletionRequest, CompletionResponse, MessageRole


class AnthropicClient(AIClient):
    """
    Anthropic Claude API client with automatic retry and token tracking.

    Supports:
    - Claude 3.5 Sonnet
    - Claude 3 Opus
    - Claude 3 Haiku
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        logger_name: str = "ai_client.anthropic"
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (uses settings.ANTHROPIC_API_KEY if None)
            logger_name: Logger name
        """
        super().__init__(api_key or settings.ANTHROPIC_API_KEY, logger_name)
        self.logger = get_logger(logger_name)
        self.client = AsyncAnthropic(api_key=self.api_key)

        # Cost per 1M tokens (as of 2025)
        self.costs = {
            'claude-3-5-sonnet': {'input': 3.00, 'output': 15.00},
            'claude-3-opus': {'input': 15.00, 'output': 75.00},
            'claude-3-sonnet': {'input': 3.00, 'output': 15.00},
            'claude-3-haiku': {'input': 0.25, 'output': 1.25},
        }

    def is_reasoning_model(self, model: str) -> bool:
        """Claude models don't have separate reasoning mode"""
        return False

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for Anthropic API call"""
        # Find matching model
        model_key = None
        for key in self.costs.keys():
            if key in model.lower():
                model_key = key
                break

        if not model_key:
            # Default to claude-3-5-sonnet pricing
            self.logger.warning(f"Unknown model for cost calculation: {model}, using Claude 3.5 Sonnet pricing")
            model_key = 'claude-3-5-sonnet'

        rates = self.costs[model_key]
        input_cost = (input_tokens / 1_000_000) * rates['input']
        output_cost = (output_tokens / 1_000_000) * rates['output']

        return input_cost + output_cost

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate text completion using Anthropic Claude API.

        Implements automatic retry with exponential backoff.

        Args:
            request: Completion request

        Returns:
            Completion response with generated text and usage info

        Raises:
            Exception: If all retries fail
        """
        model = request.model or settings.MODEL_FALLBACK

        self.logger.info(
            f"Starting Anthropic completion",
            extra={
                'model_name': model,
                'message_count': len(request.messages)
            }
        )

        # Anthropic requires system prompt separate from messages
        system_prompt = request.system_prompt
        messages = []

        # Extract system message if present
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        # Build API parameters
        api_params = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens or settings.DEFAULT_MAX_TOKENS,
        }

        # Add system prompt if provided
        if system_prompt:
            api_params["system"] = system_prompt

        # Add temperature if not reasoning model
        if request.temperature is not None:
            api_params["temperature"] = request.temperature
        else:
            api_params["temperature"] = settings.DEFAULT_TEMPERATURE

        # Retry loop
        for attempt in range(settings.MAX_RETRIES):
            try:
                self.logger.info(f"Anthropic API call attempt {attempt + 1}/{settings.MAX_RETRIES}")

                response = await self.client.messages.create(**api_params)

                # Extract response data
                content = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text

                if not content:
                    raise ValueError("Empty response from Anthropic")

                # Extract usage information
                usage = response.usage
                input_tokens = usage.input_tokens if usage else 0
                output_tokens = usage.output_tokens if usage else 0
                total_tokens = input_tokens + output_tokens

                # Calculate cost
                cost = self._calculate_cost(model, input_tokens, output_tokens)

                # Log token usage
                token_logger.log_completion(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    component=self.logger_name
                )

                self.logger.info(
                    f"Anthropic completion successful",
                    extra={
                        'model_name': model,
                        'tokens': total_tokens,
                        'cost': f"${cost:.6f}"
                    }
                )

                return CompletionResponse(
                    content=content.strip(),
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    provider="anthropic",
                    raw_response=response
                )

            except (RateLimitError, APIConnectionError) as e:
                self.logger.warning(f"Anthropic API error (attempt {attempt + 1}): {str(e)}")

                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = min(
                        settings.BACKOFF_MIN * (2 ** attempt),
                        settings.BACKOFF_MAX
                    )
                    self.logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"Anthropic API failed after {settings.MAX_RETRIES} attempts: {str(e)}")

            except Exception as e:
                self.logger.error(f"Unexpected error in Anthropic completion: {str(e)}")
                raise

        raise Exception("Anthropic completion failed: Maximum retries exceeded")


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from ai_clients.base import Message, MessageRole

    async def test():
        client = AnthropicClient()

        request = CompletionRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
                Message(role=MessageRole.USER, content="Write a haiku about Python programming.")
            ],
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            temperature=0.7
        )

        print("\n" + "="*80)
        print("Anthropic Client Test")
        print("="*80 + "\n")

        try:
            response = await client.complete(request)

            print(f"Model: {response.model}")
            print(f"Provider: {response.provider}")
            print(f"Tokens: {response.total_tokens} ({response.input_tokens} input + {response.output_tokens} output)")
            print(f"Cost: ${response.cost:.6f}")
            print(f"\nGenerated content:")
            print("-" * 80)
            print(response.content)
            print("-" * 80)

        except Exception as e:
            print(f"ERROR: {str(e)}")

    asyncio.run(test())
