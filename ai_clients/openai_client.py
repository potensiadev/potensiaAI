# potensia_ai/ai_clients/openai_client.py
"""
OpenAI client implementation with retry logic and cost tracking.
"""

import asyncio
from typing import Optional
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from core.config import settings
from core.logger import get_logger, token_logger
from ai_clients.base import AIClient, CompletionRequest, CompletionResponse


class OpenAIClient(AIClient):
    """
    OpenAI API client with automatic retry and token tracking.

    Supports:
    - GPT-4, GPT-4 Turbo, GPT-4o
    - GPT-3.5 Turbo
    - O1 and O3 reasoning models
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        logger_name: str = "ai_client.openai"
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (uses settings.OPENAI_API_KEY if None)
            logger_name: Logger name
        """
        super().__init__(api_key or settings.OPENAI_API_KEY, logger_name)
        self.logger = get_logger(logger_name)
        self.client = AsyncOpenAI(api_key=self.api_key)

        # Cost per 1M tokens (as of 2025)
        self.costs = {
            'gpt-4o': {'input': 2.50, 'output': 10.00},
            'gpt-4o-mini': {'input': 0.150, 'output': 0.600},
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
            'gpt-4': {'input': 30.00, 'output': 60.00},
            'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
            'o1-preview': {'input': 15.00, 'output': 60.00},
            'o1-mini': {'input': 3.00, 'output': 12.00},
            'o3-mini': {'input': 3.00, 'output': 12.00},
        }

    def is_reasoning_model(self, model: str) -> bool:
        """Check if model requires reasoning parameters"""
        model_lower = model.lower()
        return any(keyword in model_lower for keyword in ["o1-", "o3-", "gpt-5"])

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for OpenAI API call"""
        # Find matching model
        model_key = None
        for key in self.costs.keys():
            if key in model.lower():
                model_key = key
                break

        if not model_key:
            self.logger.warning(f"Unknown model for cost calculation: {model}")
            return 0.0

        rates = self.costs[model_key]
        input_cost = (input_tokens / 1_000_000) * rates['input']
        output_cost = (output_tokens / 1_000_000) * rates['output']

        return input_cost + output_cost

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Generate text completion using OpenAI API.

        Implements automatic retry with exponential backoff.

        Args:
            request: Completion request

        Returns:
            Completion response with generated text and usage info

        Raises:
            Exception: If all retries fail
        """
        model = request.model or settings.MODEL_PRIMARY
        is_reasoning = self.is_reasoning_model(model)

        self.logger.info(
            f"Starting OpenAI completion",
            extra={
                'model_name': model,
                'is_reasoning': is_reasoning,
                'message_count': len(request.messages)
            }
        )

        # Format messages
        messages = self._format_messages(request)

        # Build API parameters
        api_params = {
            "model": model,
            "messages": messages,
        }

        # Reasoning models use different parameters
        if is_reasoning:
            api_params["max_completion_tokens"] = request.max_tokens or 2000
            # Reasoning models don't support temperature
        else:
            api_params["max_tokens"] = request.max_tokens or settings.DEFAULT_MAX_TOKENS
            api_params["temperature"] = request.temperature or settings.DEFAULT_TEMPERATURE

        # Retry loop
        for attempt in range(settings.MAX_RETRIES):
            try:
                self.logger.info(f"OpenAI API call attempt {attempt + 1}/{settings.MAX_RETRIES}")

                response = await self.client.chat.completions.create(**api_params)

                # Extract response data
                content = response.choices[0].message.content

                if not content:
                    raise ValueError("Empty response from OpenAI")

                # Extract usage information
                usage = response.usage
                input_tokens = usage.prompt_tokens if usage else 0
                output_tokens = usage.completion_tokens if usage else 0
                total_tokens = usage.total_tokens if usage else (input_tokens + output_tokens)

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
                    f"OpenAI completion successful",
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
                    provider="openai",
                    raw_response=response
                )

            except (RateLimitError, APIConnectionError) as e:
                self.logger.warning(f"OpenAI API error (attempt {attempt + 1}): {str(e)}")

                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = min(
                        settings.BACKOFF_MIN * (2 ** attempt),
                        settings.BACKOFF_MAX
                    )
                    self.logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"OpenAI API failed after {settings.MAX_RETRIES} attempts: {str(e)}")

            except Exception as e:
                self.logger.error(f"Unexpected error in OpenAI completion: {str(e)}")
                raise

        raise Exception("OpenAI completion failed: Maximum retries exceeded")


# ============================================================
# Test
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from ai_clients.base import Message, MessageRole

    async def test():
        client = OpenAIClient()

        request = CompletionRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
                Message(role=MessageRole.USER, content="Write a haiku about Python programming.")
            ],
            model="gpt-4o-mini",
            max_tokens=100,
            temperature=0.7
        )

        print("\n" + "="*80)
        print("OpenAI Client Test")
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
