# potensia_ai/ai_tools/writer/validator.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import json
import datetime
import re
from openai import AsyncOpenAI
from core.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

VALIDATOR_PROMPT = """You are an expert content quality analyst specializing in SEO, AEO (Answer Engine Optimization), and AI-written content detection.

Your task is to evaluate blog articles and provide a detailed quality assessment.

Analyze the content for:
1. **Grammar & Readability** (grammar_score: 0-10)
   - Spelling, punctuation, sentence structure
   - Flow and readability

2. **Human-like Quality** (human_score: 0-10)
   - Does it sound natural or robotic?
   - Does it have AI telltale signs (repetitive phrases, generic conclusions, excessive formal tone)?
   - Higher score = more human-like

3. **SEO/AEO Quality** (seo_score: 0-10)
   - Keyword optimization
   - Header structure (H1, H2, H3)
   - Meta information
   - Answer Engine Optimization for featured snippets

4. **FAQ Section** (has_faq: true/false)
   - Does the article include an FAQ section?

5. **Suggestions** (list of strings)
   - Specific, actionable improvements in Korean
   - Examples: "서론이 너무 짧습니다", "AI가 쓴 티가 많이 납니다", "FAQ에 키워드를 더 추가하세요"

**IMPORTANT**: You must respond ONLY with valid JSON in this exact format:
```json
{
  "grammar_score": 8,
  "human_score": 7,
  "seo_score": 9,
  "has_faq": true,
  "suggestions": [
    "서론을 더 자연스럽게 작성하세요.",
    "AI 특유의 반복적인 표현을 줄이세요.",
    "메타 설명을 추가하세요."
  ]
}
```

Do NOT include any explanation outside the JSON structure."""


def log_validation(status: str, error: str | None = None):
    """로그 출력 헬퍼"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [VALIDATOR] [{status}]")
    if error:
        print(f" └─ Error: {error}\n")


async def validate_content(content: str, model: str | None = None) -> dict:
    """
    OpenAI API를 사용하여 콘텐츠 품질을 평가합니다.

    Args:
        content: 평가할 블로그 콘텐츠 (Markdown 형식)
        model: 사용할 OpenAI 모델 (기본값: settings.MODEL_PRIMARY)

    Returns:
        dict: 평가 결과 (grammar_score, human_score, seo_score, has_faq, suggestions)
              JSON 파싱 실패 시 {"raw_output": result} 반환
    """
    log_validation("START")

    try:
        # Use provided model or fall back to settings
        model_to_use = model or settings.MODEL_PRIMARY

        # Determine if this is a reasoning model (o1, o3, gpt-5, etc.)
        model_name = model_to_use.lower()
        is_reasoning_model = any(keyword in model_name
                                for keyword in ["o1-", "o3-", "gpt-5"])

        # Prepare API call parameters based on model type
        api_params = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": VALIDATOR_PROMPT},
                {"role": "user", "content": f"다음 블로그 글을 평가해주세요:\n\n{content}"}
            ],
        }

        # Reasoning models use max_completion_tokens and don't support temperature
        if is_reasoning_model:
            api_params["max_completion_tokens"] = 800
        else:
            api_params["max_tokens"] = 800
            api_params["temperature"] = 0.3

        response = await openai_client.chat.completions.create(**api_params)

        result = response.choices[0].message.content

        if not result or not result.strip():
            log_validation("ERROR", "Empty response from OpenAI")
            return {"raw_output": ""}

        # JSON 파싱 시도
        try:
            # Remove markdown code blocks using regex (more robust)
            result_clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.strip(), flags=re.DOTALL).strip()

            validated_data = json.loads(result_clean)

            # 필수 키 검증
            required_keys = ["grammar_score", "human_score", "seo_score", "has_faq", "suggestions"]
            if all(key in validated_data for key in required_keys):
                log_validation("OK", f"Scores: G={validated_data['grammar_score']}, H={validated_data['human_score']}, SEO={validated_data['seo_score']}")
                return validated_data
            else:
                log_validation("ERROR", f"Missing required keys. Got: {list(validated_data.keys())}")
                return {"raw_output": result}

        except json.JSONDecodeError as e:
            log_validation("ERROR", f"JSON parse failed: {e}")
            return {"raw_output": result}

    except Exception as e:
        log_validation("ERROR", f"OpenAI API call failed: {str(e)}")
        return {
            "error": str(e),
            "grammar_score": 0,
            "human_score": 0,
            "seo_score": 0,
            "has_faq": False,
            "suggestions": ["검증 중 오류가 발생했습니다."]
        }


# ─────────────────────────────────────────────────────────────────────────────
# 테스트 러너
# ─────────────────────────────────────────────────────────────────────────────
async def test_validator():
    """validator.py 단독 실행 시 테스트"""
    print("\n" + "="*80)
    print("[TEST] VALIDATOR TEST")
    print("="*80 + "\n")

    # 테스트용 샘플 콘텐츠 (한국어 블로그 글)
    sample_content = """
# 파이썬으로 웹 크롤링 시작하기

## 서론
웹 크롤링은 인터넷에서 데이터를 수집하는 강력한 방법입니다. 파이썬은 이를 위한 최고의 도구를 제공합니다.

## 본론

### BeautifulSoup 사용법
BeautifulSoup은 HTML을 파싱하는 라이브러리입니다. 설치는 다음과 같이 합니다:

```python
pip install beautifulsoup4
```

### 실전 예제
아래는 간단한 크롤링 예제입니다:

```python
from bs4 import BeautifulSoup
import requests

response = requests.get('https://example.com')
soup = BeautifulSoup(response.text, 'html.parser')
print(soup.title)
```

## FAQ

**Q: 웹 크롤링은 합법인가요?**
A: 사이트의 robots.txt를 준수하고 서비스 약관을 확인해야 합니다.

**Q: 어떤 라이브러리를 사용해야 하나요?**
A: BeautifulSoup, Selenium, Scrapy 등이 있습니다.

## 결론
파이썬을 활용하면 누구나 쉽게 웹 크롤링을 시작할 수 있습니다.
"""

    print("[CONTENT] Testing with sample blog content:")
    print(sample_content[:200] + "...\n")

    print("[PROCESS] Running validation with gpt-4o-mini...\n")
    result = await validate_content(sample_content, model="gpt-4o-mini")

    print("\n" + "-"*80)
    print("[RESULT] Validation Results:")
    print("-"*80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_validator())
