# potensia_ai/ai_tools/writer/generator.py
import asyncio
import datetime
import random
import logging
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from core.config import settings
from ai_tools.writer.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ai_tools.writer.topic_refiner import refine_topic

# Configure logging
logger = logging.getLogger("generator")

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
claude_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def is_reasoning_model(model_name: str) -> bool:
    """Check if model is a reasoning model (o1, o3, gpt-5 series)"""
    model_lower = model_name.lower()
    return any(keyword in model_lower for keyword in ["o1-", "o3-", "gpt-5"])


def log_event(model: str, topic: str, status: str, error: str | None = None):
    """Structured logging helper"""
    log_message = f"[{model}] [{status}] Topic: {topic[:50]}..."

    if error:
        logger.error(f"{log_message} | Error: {error}")
    elif status in ["SUCCESS", "RETRY_SUCCESS"]:
        logger.info(log_message)
    elif status in ["FAIL", "RETRY_FAIL", "RETRY_LIMIT_REACHED", "TOTAL_FAIL"]:
        logger.warning(log_message)
    else:
        logger.info(log_message)


async def try_model(model_name: str, topic: str, user_prompt: str) -> str | None:
    """
    GPT or Claude 실행 (실패 시 None 반환)

    Args:
        model_name: "GPT" or "Claude"
        topic: 주제 (로깅용)
        user_prompt: 사용자 프롬프트

    Returns:
        str | None: 생성된 콘텐츠 또는 실패 시 None
    """
    try:
        if model_name == "GPT":
            # Determine if this is a reasoning model
            is_reasoning = is_reasoning_model(settings.MODEL_PRIMARY)

            # Build API parameters based on model type
            api_params = {
                "model": settings.MODEL_PRIMARY,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            }

            # Reasoning models use max_completion_tokens and don't support temperature
            if is_reasoning:
                api_params["max_completion_tokens"] = 10000
            else:
                api_params["max_tokens"] = settings.DEFAULT_MAX_TOKENS
                api_params["temperature"] = settings.DEFAULT_TEMPERATURE

            resp = await openai_client.chat.completions.create(**api_params)
            text = resp.choices[0].message.content

            # Check for empty content
            if not text or not text.strip():
                usage = resp.usage
                log_event(model_name, topic, "EMPTY_CONTENT",
                         f"Completion tokens: {usage.completion_tokens}")
                return None

            return text.strip()

        elif model_name == "Claude":
            resp = await claude_client.messages.create(
                model=settings.MODEL_FALLBACK,
                max_tokens=settings.DEFAULT_MAX_TOKENS,
                temperature=settings.DEFAULT_TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = resp.content[0].text.strip()
            return text if text else None

    except Exception as e:
        log_event(model_name, topic, "FAIL", f"{type(e).__name__}: {e}")
        logger.exception(f"Exception in try_model({model_name})")
        return None


async def generate_content(topic: str) -> str:
    """
    콘텐츠 생성 파이프라인 (재시도 로직 포함)

    Step 1: Topic Refiner로 질문형 제목 생성
    Step 2: 생성된 제목을 user_prompt에 삽입
    Step 3: GPT (PRIMARY) → Claude (FALLBACK) 순서로 재시도
    Step 4: 모든 실패 시 RuntimeError

    Args:
        topic: 원본 주제

    Returns:
        str: 생성된 블로그 콘텐츠

    Raises:
        RuntimeError: 모든 재시도 실패 시
    """

    # 1️⃣ Topic refinement (질문형 제목으로 보정)
    try:
        generated_topic = await refine_topic(topic)
        logger.info(f"Topic refined: {topic} → {generated_topic}")
    except Exception as e:
        generated_topic = topic
        logger.warning(f"TopicRefiner failed, using original: {e}")

    # 2️⃣ User prompt 생성
    user_prompt = USER_PROMPT_TEMPLATE.format(topic=generated_topic)

    # 3️⃣ 모델 실행 순서: GPT → GPT (재시도) → Claude (최종 폴백)
    # MAX_RETRIES from settings
    model_sequence = ["GPT"] * settings.MAX_RETRIES + ["Claude"]

    # 4️⃣ 실행 루프 with exponential backoff
    for attempt, model in enumerate(model_sequence, start=1):
        retry_label = "RETRY_START" if attempt > 1 else "START"
        log_event(model, generated_topic, retry_label)

        content = await try_model(model, generated_topic, user_prompt)

        if content:
            # 성공
            success_label = "RETRY_SUCCESS" if attempt > 1 else "SUCCESS"
            log_event(model, generated_topic, success_label)
            return content

        # 실패 로그
        fail_label = "RETRY_FAIL" if attempt > 1 else "FAIL"
        log_event(model, generated_topic, fail_label)

        # Exponential backoff (마지막 시도가 아닐 경우만)
        if attempt < len(model_sequence):
            backoff = min(settings.BACKOFF_MIN * (2 ** (attempt - 1)), settings.BACKOFF_MAX)
            logger.info(f"Waiting {backoff:.1f}s before next retry...")
            await asyncio.sleep(backoff)

    # 5️⃣ 모든 모델/재시도 실패
    log_event("SYSTEM", generated_topic, "TOTAL_FAIL", "All attempts failed")
    raise RuntimeError(f"All model attempts failed for topic: {generated_topic}")


# ============================================================
# 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Configure logging for test
    logging.basicConfig(level=logging.INFO)

    async def test():
        test_topic = "생애최초 주택담보대출, 신청 자격과 한도·금리는?"
        print(f"\n{'='*60}")
        print(f"Testing Content Generator")
        print(f"{'='*60}\n")
        print(f"Input Topic: {test_topic}\n")

        try:
            result = await generate_content(test_topic)
            print(f"\n{'='*60}")
            print(f"Generated Content:")
            print(f"{'='*60}\n")
            print(result[:500] + "..." if len(result) > 500 else result)
        except Exception as e:
            print(f"\n[ERROR] Content generation failed: {e}")
            logger.exception("Test failed")

    asyncio.run(test())
