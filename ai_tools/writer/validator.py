# potensia_ai/ai_tools/writer/validator.py
import asyncio
import json
import datetime
import re
import logging
from openai import AsyncOpenAI
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("validator")

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

5. **Suggestions** (list of objects with type and message)
   - Specific, actionable improvements in Korean
   - Each suggestion must have a "type" (category) and "message" (description)
   - Types: intro_missing, faq_missing, ai_tone, keyword_density_low, repetitive_phrases, etc.

**IMPORTANT**: You must respond ONLY with valid JSON in this exact format:
```json
{
  "grammar_score": 8,
  "human_score": 7,
  "seo_score": 9,
  "has_faq": true,
  "suggestions": [
    {"type": "intro_improvement", "message": "서론을 더 자연스럽게 작성하세요."},
    {"type": "ai_tone", "message": "AI 특유의 반복적인 표현을 줄이세요."},
    {"type": "seo_meta", "message": "메타 설명을 추가하세요."}
  ]
}
```

Do NOT include any explanation outside the JSON structure."""


def log_validation(status: str, message: str | None = None, **kwargs):
    """
    구조화된 로깅 헬퍼

    Args:
        status: 상태 (START, OK, ERROR 등)
        message: 로그 메시지
        **kwargs: 추가 컨텍스트 정보
    """
    log_data = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "module": "validator",
        "status": status,
        "message": message or "",
        **kwargs
    }

    if status == "ERROR":
        logger.error(json.dumps(log_data, ensure_ascii=False))
    else:
        logger.info(json.dumps(log_data, ensure_ascii=False))


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
    log_validation("START", "Starting content validation", content_length=len(content), model=model)

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

    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await openai_client.chat.completions.create(**api_params)
            result = response.choices[0].message.content

            if not result or not result.strip():
                log_validation("ERROR", "Empty response from OpenAI", attempt=attempt+1)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {
                    "scores": {"grammar": 0, "human": 0, "seo": 0},
                    "has_faq": False,
                    "issues": [],
                    "raw_output": ""
                }
            break

        except Exception as e:
            log_validation("ERROR", f"OpenAI API call failed: {str(e)}",
                          attempt=attempt+1, max_retries=max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return {
                "error": str(e),
                "scores": {"grammar": 0, "human": 0, "seo": 0},
                "has_faq": False,
                "issues": [{"type": "validation_error", "message": "검증 중 오류가 발생했습니다."}],
                "raw_output": ""
            }

    try:

        # Enhanced JSON extraction with fallback
        json_match = re.search(r'\{[\s\S]*\}', result)
        if not json_match:
            log_validation("ERROR", "No valid JSON found in response")
            return {
                "scores": {"grammar": 0, "human": 0, "seo": 0},
                "has_faq": False,
                "issues": [{"type": "parse_error", "message": "응답 파싱 실패"}],
                "raw_output": result
            }

        result_clean = json_match.group().strip()
        validated_data = json.loads(result_clean)

        # 필수 키 검증
        required_keys = ["grammar_score", "human_score", "seo_score", "has_faq", "suggestions"]
        if not all(key in validated_data for key in required_keys):
            log_validation("ERROR", "Missing required keys",
                          expected=required_keys,
                          got=list(validated_data.keys()))
            return {
                "scores": {"grammar": 0, "human": 0, "seo": 0},
                "has_faq": False,
                "issues": [{"type": "parse_error", "message": "응답 구조 오류"}],
                "raw_output": result
            }

        # 구조화된 응답 반환 (Fixer 친화적)
        structured_response = {
            "scores": {
                "grammar": validated_data["grammar_score"],
                "human": validated_data["human_score"],
                "seo": validated_data["seo_score"]
            },
            "has_faq": validated_data["has_faq"],
            "issues": validated_data["suggestions"],  # Fixer가 바로 사용 가능

            # 레거시 호환성을 위해 유지
            "grammar_score": validated_data["grammar_score"],
            "human_score": validated_data["human_score"],
            "seo_score": validated_data["seo_score"],
            "suggestions": [
                item["message"] if isinstance(item, dict) else item
                for item in validated_data["suggestions"]
            ]
        }

        log_validation("OK", "Validation completed successfully",
                      grammar=structured_response["scores"]["grammar"],
                      human=structured_response["scores"]["human"],
                      seo=structured_response["scores"]["seo"])

        return structured_response

    except json.JSONDecodeError as e:
        log_validation("ERROR", f"JSON parse failed: {str(e)}", raw_output=result[:200])
        return {
            "scores": {"grammar": 0, "human": 0, "seo": 0},
            "has_faq": False,
            "issues": [{"type": "parse_error", "message": f"JSON 파싱 실패: {str(e)}"}],
            "raw_output": result
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

    # 결과를 파일로 저장 (regression test용)
    with open("validator_test_output.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\nTest results saved to: validator_test_output.json")


if __name__ == "__main__":
    # sys.path 설정 (테스트 모드에서만)
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    asyncio.run(test_validator())
