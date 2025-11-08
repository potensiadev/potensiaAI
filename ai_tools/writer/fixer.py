# potensia_ai/ai_tools/writer/fixer.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import json
import re
import datetime
from openai import AsyncOpenAI
from core.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# System Prompt for Claude
# ─────────────────────────────────────────────────────────────────────────────
FIXER_SYSTEM_PROMPT = """너는 고급 SEO·콘텐츠 에디터이자 자연스러운 글쓰기 교정 전문가다.

입력된 블로그 글을 다음 기준으로 자동 수정하라:

1. **문체는 사람다운 흐름과 자연스러운 리듬을 유지**
   - AI가 쓴 티가 나지 않도록 자연스럽게
   - 불필요한 반복 제거
   - 문장 간 연결을 매끄럽게
   - 인간적인 변주와 다양한 표현 사용

2. **SEO 기준 충족**
   - Focus Keyphrase는 본문 1.5~2.5% 내에서 자연스럽게 반복
   - 제목, 서론, 결론, FAQ에도 Keyphrase를 포함
   - 키워드 스터핑 방지 (억지로 넣지 말 것)

3. **구조적 결함 교정**
   - 서론(H2), 본문(H2/H3), FAQ(H2) 순서 유지
   - FAQ는 최소 2문항 이상
   - 누락된 부분은 새로 작성하되, 기존 톤앤매너를 유지

4. **내용 누락 없이 자연스럽게 리라이트**
   - 중요한 정보는 절대 삭제하지 말 것
   - 기존 내용을 보완하고 개선
   - 전문성과 신뢰성 유지

5. **출력 형식**
   - 순수 마크다운 텍스트로만 반환
   - 메타 설명이나 슬러그 등은 포함하지 말 것
   - 자연스러운 블로그 글 형태

**중요**: AI 탐지율을 10% 이하로 유지하기 위해 인간적인 문체와 다양한 표현을 사용하라."""

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def log_fixer(status: str, detail: str = ""):
    """로깅 헬퍼"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [FIXER] [{status}] {detail}")


def calculate_keyword_density(content: str, keyphrase: str) -> float:
    """
    키워드 밀도 계산

    Args:
        content: 본문 텍스트
        keyphrase: 검색할 키워드

    Returns:
        float: 키워드 밀도 (%)
    """
    if not keyphrase or not content:
        return 0.0

    # 코드 블록 제거 (키워드 카운트에서 제외)
    content_no_code = re.sub(r'```[\s\S]*?```', '', content)

    # 마크다운 제거하고 순수 텍스트만
    clean_text = re.sub(r'[#*`\[\]\(\)]', '', content_no_code)

    # 단어 수 계산
    words = clean_text.split()
    total_words = len(words)

    if total_words == 0:
        return 0.0

    # 키워드 출현 횟수 (대소문자 무시)
    keyphrase_lower = keyphrase.lower()
    keyword_count = clean_text.lower().count(keyphrase_lower)

    # 밀도 계산: (키워드 출현 횟수 / 총 단어 수) * 100
    density = (keyword_count / total_words) * 100

    return round(density, 2)


def extract_fix_needs(validation_report: dict) -> list[str]:
    """
    Validation 리포트에서 수정이 필요한 항목 추출 (issues type 기반)

    Args:
        validation_report: Validator 결과

    Returns:
        list: 수정 필요 항목 목록 (type 기반)
    """
    fix_needs = []

    # 새로운 구조: issues 리스트에서 type 추출
    issues = validation_report.get('issues', [])
    for issue in issues:
        if isinstance(issue, dict) and 'type' in issue:
            fix_needs.append(issue['type'])

    # FAQ 누락 확인 (레거시 호환)
    has_faq = validation_report.get('has_faq', False)
    if not has_faq and 'faq_missing' not in fix_needs:
        fix_needs.append('faq_missing')

    # 점수 기반 개선 필요 항목 (레거시 호환)
    scores = validation_report.get('scores', {})
    grammar_score = scores.get('grammar', validation_report.get('grammar_score', 10))
    human_score = scores.get('human', validation_report.get('human_score', 10))
    seo_score = scores.get('seo', validation_report.get('seo_score', 10))

    if grammar_score < 7 and 'grammar_improvement' not in fix_needs:
        fix_needs.append('grammar_improvement')
    if human_score < 7 and 'humanize_content' not in fix_needs:
        fix_needs.append('humanize_content')
    if seo_score < 7 and 'seo_optimization' not in fix_needs:
        fix_needs.append('seo_optimization')

    return fix_needs


def post_process_content(content: str) -> str:
    """
    콘텐츠 후처리

    Args:
        content: 원본 콘텐츠

    Returns:
        str: 정리된 콘텐츠
    """
    # 불필요한 공백 제거
    content = re.sub(r' +', ' ', content)

    # 3개 이상의 연속 개행을 2개로
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 마크다운 코드 블록 외의 백틱 정리
    content = re.sub(r'(?<!`)`(?!`)', '', content)

    # 문장 끝 공백 제거
    lines = [line.rstrip() for line in content.split('\n')]
    content = '\n'.join(lines)

    return content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main Fixer Function
# ─────────────────────────────────────────────────────────────────────────────

async def fix_content(
    content: str,
    validation_report: dict,
    metadata: dict | None = None
) -> dict:
    """
    Validator 리포트를 기반으로 콘텐츠 자동 교정

    Args:
        content: 원본 콘텐츠
        validation_report: Validator 결과
        metadata: 메타데이터 (focus_keyphrase, language, style 등)

    Returns:
        dict: {
            "fixed_content": str,
            "fix_summary": list[str],
            "added_FAQ": bool,
            "keyword_density": float
        }
    """
    log_fixer("START", f"content_length={len(content)}")

    # 메타데이터 기본값 설정
    if metadata is None:
        metadata = {}

    focus_keyphrase = metadata.get('focus_keyphrase', '')
    language = metadata.get('language', 'ko')
    style = metadata.get('style', 'informational')

    # 수정 필요 항목 추출
    fix_needs = extract_fix_needs(validation_report)
    log_fixer("ANALYSIS", f"fix_needs={fix_needs}")

    # 수정이 필요 없는 경우
    if not fix_needs and validation_report.get('grammar_score', 0) >= 8:
        log_fixer("SKIP", "Content quality is already good")
        return {
            "fixed_content": content,
            "fix_summary": ["콘텐츠 품질이 우수하여 수정 불필요"],
            "added_FAQ": validation_report.get('has_faq', False),
            "keyword_density": calculate_keyword_density(content, focus_keyphrase)
        }

    # Claude에 전달할 User Prompt 구성
    user_prompt = f"""다음은 Validator 리포트와 원문이다.

[Validator Report]
{json.dumps(validation_report, ensure_ascii=False, indent=2)}

[Fix Needs]
{', '.join(fix_needs)}

[Original Content]
{content}

[Metadata]
- Focus Keyphrase: {focus_keyphrase}
- Language: {language}
- Style: {style}

위 정보를 바탕으로 콘텐츠를 교정하라. 특히 다음 사항에 주의:
1. FAQ가 없다면 Focus Keyphrase를 포함한 2~3개의 FAQ 추가
2. 키워드 밀도는 1.5~2.5% 사이로 자연스럽게 조정
3. 반복적인 표현 제거 및 문장 흐름 개선
4. AI가 쓴 티를 최소화하고 자연스러운 인간 문체 유지

교정된 콘텐츠만 반환하라 (메타 정보나 설명 없이)."""

    try:
        # OpenAI API 호출 (gpt-4o 사용)
        log_fixer("OPENAI_CALL", "model=gpt-4o")

        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=3000,
            temperature=0.4,
            messages=[
                {"role": "system", "content": FIXER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        # 응답 추출
        fixed_content = response.choices[0].message.content.strip()

        if not fixed_content:
            log_fixer("ERROR", "Empty response from OpenAI")
            return {
                "fixed_content": content,
                "fix_summary": ["OpenAI 응답 오류 - 원본 반환"],
                "added_FAQ": False,
                "keyword_density": calculate_keyword_density(content, focus_keyphrase)
            }

        # 후처리
        fixed_content = post_process_content(fixed_content)

        # FAQ 추가 여부 확인 (개선된 정규식)
        had_faq = validation_report.get('has_faq', False)
        now_has_faq = bool(re.search(r'(?:##\s*FAQ|##\s*자주\s*묻는\s*질문)', fixed_content, re.IGNORECASE))
        added_faq = not had_faq and now_has_faq

        # 키워드 밀도 계산
        final_density = calculate_keyword_density(fixed_content, focus_keyphrase)

        # 수정 요약 생성
        fix_summary = []
        if added_faq:
            fix_summary.append("FAQ 섹션 자동 추가")
        if 'grammar_improvement' in fix_needs:
            fix_summary.append("문법 및 가독성 개선")
        if 'humanize_content' in fix_needs:
            fix_summary.append("AI 탐지율 감소 (인간 문체 적용)")
        if 'seo_optimization' in fix_needs:
            fix_summary.append("SEO 최적화 적용")
        if focus_keyphrase:
            fix_summary.append(f"키워드 밀도 조정: {final_density}%")

        # 키워드 밀도가 범위를 벗어나면 추가 조정 필요 표시
        if focus_keyphrase and (final_density < 1.5 or final_density > 2.5):
            fix_summary.append(f"[주의] 키워드 밀도 범위 초과 ({final_density}%) - 수동 조정 권장")

        log_fixer("SUCCESS", f"fixed_length={len(fixed_content)}, density={final_density}%")

        return {
            "fixed_content": fixed_content,
            "fix_summary": fix_summary if fix_summary else ["콘텐츠 전반적 품질 개선"],
            "added_FAQ": added_faq,
            "keyword_density": final_density
        }

    except Exception as e:
        log_fixer("ERROR", str(e))
        return {
            "fixed_content": content,
            "fix_summary": [f"교정 실패: {str(e)}"],
            "added_FAQ": False,
            "keyword_density": calculate_keyword_density(content, focus_keyphrase)
        }


# ─────────────────────────────────────────────────────────────────────────────
# 테스트 러너
# ─────────────────────────────────────────────────────────────────────────────
async def test_fixer():
    """Fixer 모듈 테스트"""
    print("\n" + "="*80)
    print("[TEST] Content Fixer Module")
    print("="*80 + "\n")

    # 테스트용 샘플 콘텐츠
    sample_content = """# 파이썬 크롤링 시작하기

## 서론
웹 크롤링은 데이터 수집의 좋은 방법입니다.

## 본론
파이썬을 사용하면 쉽습니다. BeautifulSoup을 사용하세요. BeautifulSoup을 사용하세요.

### 설치
pip install beautifulsoup4

### 사용
코드를 작성하세요.

## 결론
파이썬은 좋습니다."""

    # 테스트용 Validation Report
    sample_validation = {
        "grammar_score": 7,
        "human_score": 6,
        "seo_score": 5,
        "has_faq": False,
        "suggestions": [
            "FAQ 섹션이 없습니다.",
            "반복적인 표현이 있습니다.",
            "키워드가 부족합니다."
        ]
    }

    # 테스트용 메타데이터
    sample_metadata = {
        "focus_keyphrase": "파이썬 웹 크롤링",
        "language": "ko",
        "style": "guide"
    }

    print("원본 콘텐츠:")
    print("-" * 80)
    print(sample_content[:300] + "...")
    print()

    print("Validation Report:")
    print("-" * 80)
    print(json.dumps(sample_validation, indent=2, ensure_ascii=False))
    print()

    # Fixer 실행
    result = await fix_content(sample_content, sample_validation, sample_metadata)

    print("\n" + "="*80)
    print("교정 결과:")
    print("="*80)
    print(f"\n수정 요약:")
    for item in result['fix_summary']:
        print(f"  - {item}")
    print(f"\nFAQ 추가: {result['added_FAQ']}")
    print(f"키워드 밀도: {result['keyword_density']}%")
    print(f"\n교정된 콘텐츠 (처음 500자):")
    print("-" * 80)
    print(result['fixed_content'][:500] + "...")
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_fixer())
