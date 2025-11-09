# potensia_ai/ai_tools/writer/topic_refiner.py
import asyncio
import logging
from openai import AsyncOpenAI
from core.config import settings

# Configure logging
logger = logging.getLogger("topic_refiner")

# Lazy initialization: 클라이언트를 필요할 때 생성
_openai_client = None

def get_openai_client():
    """OpenAI 클라이언트를 lazy하게 초기화"""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

# ============================================================
# SEO + AEO 통합 프롬프트
# ============================================================
TOPIC_PROMPT = """당신은 SEO 전문가입니다. 주어진 키워드를 자연스러운 질문형 제목으로 변환해주세요.

규칙:
1. 한국어로 질문 형태의 제목을 만드세요 (? 로 끝나야 함)
2. 25-35자 정도의 자연스러운 문장
3. 원본 키워드를 그대로 반환하지 말고, 반드시 질문으로 변환하세요
4. 따옴표나 설명 없이 제목만 출력하세요

예시:
입력: 목동 영어유치원 학비
출력: 목동 영어유치원 학비는 얼마나 될까?

입력: 겨울철 싱크대 냄새
출력: 겨울철 싱크대 냄새는 왜 생길까?

입력받은 키워드를 위 형식으로 변환해주세요."""


# ============================================================
# Helper: 모델 타입 감지
# ============================================================
def is_reasoning_model(model_name: str) -> bool:
    """Reasoning 모델 여부 판단"""
    model_lower = model_name.lower()
    return any(keyword in model_lower for keyword in ["o1-", "o3-", "gpt-5"])


# ============================================================
# 메인 함수
# ============================================================
async def refine_topic(user_topic: str) -> str:
    """
    입력된 topic을 자연스러운 질문형 제목으로 변환

    Args:
        user_topic: 원본 키워드 또는 주제

    Returns:
        str: 변환된 질문형 제목
    """
    logger.info(f"Starting topic refinement: {user_topic[:50]}...")

    # 재시도 로직 with exponential backoff
    for attempt in range(settings.MAX_RETRIES):
        try:
            # 모델별 파라미터 설정
            api_params = {
                "model": settings.MODEL_PRIMARY,
                "messages": [
                    {"role": "system", "content": TOPIC_PROMPT},
                    {"role": "user", "content": user_topic}
                ],
            }

            # Reasoning 모델 vs 일반 모델
            if is_reasoning_model(settings.MODEL_PRIMARY):
                api_params["max_completion_tokens"] = 500
            else:
                api_params["max_tokens"] = 500
                api_params["temperature"] = settings.DEFAULT_TEMPERATURE

            response = await get_openai_client().chat.completions.create(**api_params)

            # 응답 파싱
            content = response.choices[0].message.content
            title = (content or "").strip().replace('"', "").replace("'", "")

            # 검증: 빈 결과나 동일 반환일 경우 원문 유지
            if not title or title.strip() == user_topic.strip():
                logger.warning(f"Model returned unchanged topic, keeping original: {user_topic}")
                return user_topic.strip()

            logger.info(f"Topic refined successfully: {title[:50]}...")
            return title

        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{settings.MAX_RETRIES} failed: {str(e)}")

            if attempt < settings.MAX_RETRIES - 1:
                # Exponential backoff
                wait_time = min(settings.BACKOFF_MIN * (2 ** attempt), settings.BACKOFF_MAX)
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue

            # 최종 실패 시 원본 반환
            logger.error(f"All retry attempts failed, returning original topic: {user_topic}")
            return user_topic


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
        test_topics = [
            "생애최초주택담보대출",
            "파이썬 웹 크롤링",
            "목동 영어유치원"
        ]

        for topic in test_topics:
            print(f"\n입력: {topic}")
            result = await refine_topic(topic)
            print(f"결과: {result}")

    asyncio.run(test())
