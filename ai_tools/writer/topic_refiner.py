# potensia_ai/ai_tools/writer/topic_refiner.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openai import OpenAI
from core.config import settings

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# ============================================================
# 🔹 SEO + AEO 통합 프롬프트
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
# 🔹 메인 함수
# ============================================================
async def refine_topic(user_topic: str) -> str:
    """입력된 topic을 자연스러운 질문형 제목으로 변환"""
    try:
        # ✅ full_prompt: system + user 통합
        full_prompt = f"{TOPIC_PROMPT}\n\nInput: {user_topic}\nOutput:"

        response = openai_client.chat.completions.create(
            model=settings.MODEL_PRIMARY,          # 예: gpt-4o-mini
            messages=[
                {"role": "system", "content": TOPIC_PROMPT},
                {"role": "user", "content": user_topic}
            ],
            # temperature=0.7,                      # gpt-4o-mini doesn't support custom temperature
            max_completion_tokens=1500,              # High limit for reasoning models to produce output
        )

        # ✅ 응답 안전 파싱
        choice = response.choices[0]
        content = None

        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            content = choice.message.content
        elif hasattr(choice, "output_text"):
            content = choice.output_text

        title = (content or "").strip().replace('"', "").replace("'", "")

        # ✅ 예외: 빈 결과나 동일 반환일 경우 원문 유지
        if not title or title.strip() == user_topic.strip():
            print(f"[WARNING] 모델이 변환하지 않아 원문 유지: {user_topic}")
            title = user_topic.strip()

        print(f"[OK] Refined topic: {title}")
        return title

    except Exception as e:
        print(f"[TopicRefiner Error] {e}")
        return user_topic


# ============================================================
# 🔹 단독 실행 테스트
# ============================================================
if __name__ == "__main__":
    import asyncio

    async def test():
        for t in ["생애최초주택담보대출"]:
            print("입력:", t)
            result = await refine_topic(t)
            print("결과:", result, "\n")

    asyncio.run(test())
