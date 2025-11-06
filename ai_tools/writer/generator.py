# potensia_ai/ai_tools/writer/generator.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import datetime
import random
import traceback
from openai import OpenAI
from anthropic import Anthropic
from core.config import settings
from ai_tools.writer.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from ai_tools.writer.topic_refiner import refine_topic

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
claude_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

MAX_RETRY = 2               # 모델별 최대 재시도 횟수
BACKOFF_MIN = 1             # 최소 대기 (초)
BACKOFF_MAX = 2             # 최대 대기 (초)


def log_event(model: str, topic: str, status: str, error: str | None = None):
    """기본 콘솔 로그 (운영 시 Loguru/Sentry로 교체 가능)"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{model}] [{status}] Topic: {topic}")
    if error:
        print(f" └─ Error: {error}\n")


async def try_model(model_name: str, topic: str, user_prompt: str) -> str | None:
    """GPT or Claude 실행 (실패 시 None 반환)"""
    try:
        if model_name == "GPT":
            resp = openai_client.chat.completions.create(
                model=settings.MODEL_PRIMARY,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                # Note: reasoning models don't support temperature
                max_completion_tokens=10000,  # Very high limit for reasoning models
            )
            text = resp.choices[0].message.content

            # Debug: Check if we got empty content due to reasoning token usage
            if not text or not text.strip():
                usage = resp.usage
                log_event(model_name, topic, "EMPTY_CONTENT",
                         f"Reasoning tokens: {usage.completion_tokens_details.reasoning_tokens if hasattr(usage.completion_tokens_details, 'reasoning_tokens') else 'N/A'}, "
                         f"Total completion: {usage.completion_tokens}")
                return None

            return text.strip()

        elif model_name == "Claude":
            resp = claude_client.messages.create(
                model=settings.MODEL_FALLBACK,
                max_tokens=5000,
                temperature=0.7,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = resp.content[0].text.strip()
            return text if text else None

    except Exception as e:
        log_event(model_name, topic, "FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return None


async def generate_content(topic: str) -> str:
    """
    Step 1️⃣: Topic Refiner로 질문형 제목 생성
    Step 2️⃣: 생성된 제목(generated_topic)을 user_prompt에 삽입
    Step 3️⃣: GPT-4o → Claude → GPT-4o 재시도 → Claude 재시도 (최대 2회 루프)
    Step 4️⃣: 모든 실패 시 RuntimeError (FastAPI 500)
    """

    # 1️⃣ topic refinement (질문형 제목으로 보정)
    try:
        generated_topic = await refine_topic(topic)
        print(f"[Refined Topic] {topic} → {generated_topic}")
    except Exception as e:
        generated_topic = topic
        print(f"[TopicRefiner Error] {e} (fallback to original topic)")

    # 2️⃣ 보정된 topic을 user_prompt에 삽입
    user_prompt = USER_PROMPT_TEMPLATE.format(topic=generated_topic)

    # 3️⃣ 모델 실행 순서 정의 (GPT 우선, Claude는 최종 fallback만)
    model_sequence = ["GPT", "GPT", "GPT", "Claude"]

    # 4️⃣ 실행 루프
    for attempt, model in enumerate(model_sequence, start=1):
        retry_round = (attempt - 1) // 2 + 1
        retry_label = "RETRY_START" if attempt > 2 else "START"
        log_event(model, generated_topic, retry_label)

        content = await try_model(model, generated_topic, user_prompt)

        if content:
            # 성공 로그
            success_label = "RETRY_SUCCESS" if attempt > 2 else "SUCCESS"
            log_event(model, generated_topic, success_label)
            return content

        # 실패 시 로그
        fail_label = "RETRY_FAIL" if attempt > 2 else "FAIL"
        log_event(model, generated_topic, fail_label)

        # 자동 백오프 (마지막 시도가 아닐 경우만)
        if attempt < len(model_sequence):
            backoff = random.uniform(BACKOFF_MIN, BACKOFF_MAX)
            print(f"⏳ Waiting {backoff:.1f}s before next retry...\n")
            await asyncio.sleep(backoff)

        # 재시도 제한
        if retry_round > MAX_RETRY:
            log_event(model, generated_topic, "RETRY_LIMIT_REACHED")
            break

    # 5️⃣ 모든 모델/재시도 실패
    log_event("SYSTEM", generated_topic, "TOTAL_FAIL", "All GPT & Claude attempts failed")
    raise RuntimeError(f"All model attempts failed for topic: {generated_topic}")


# ============================================================
# 🔹 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
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
            print(result)
        except Exception as e:
            print(f"\n[ERROR] Content generation failed: {e}")

    asyncio.run(test())
