# potensia_ai/test_full_pipeline.py
"""
Full pipeline test: refine → generate → validate → fix
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_tools.writer.topic_refiner import refine_topic
from ai_tools.writer.validator import validate_content
from ai_tools.writer.fixer import fix_content


async def test_full_pipeline():
    """전체 파이프라인 테스트"""
    print("\n" + "="*80)
    print("FULL PIPELINE TEST: Refine → Validate → Fix")
    print("="*80 + "\n")

    # Step 1: Topic Refinement
    print("[STEP 1] Topic Refinement")
    print("-" * 80)
    raw_topic = "python web scraping"
    print(f"Raw Topic: {raw_topic}")

    refined_topic = await refine_topic(raw_topic)
    print(f"Refined Topic: {refined_topic}\n")

    # Step 2: Sample Content (simulate generator output)
    print("[STEP 2] Content Generation (Simulated)")
    print("-" * 80)
    sample_content = f"""# {refined_topic}

## 서론
웹 크롤링은 데이터 수집의 좋은 방법입니다. 웹 크롤링은 유용합니다.

## 본론
파이썬을 사용하면 쉽습니다. BeautifulSoup을 사용하세요. BeautifulSoup을 사용하세요.

### 설치
pip install beautifulsoup4

### 사용
코드를 작성하세요.

## 결론
파이썬은 좋습니다."""

    print(f"Content length: {len(sample_content)} characters\n")

    # Step 3: Validation
    print("[STEP 3] Content Validation")
    print("-" * 80)
    validation = await validate_content(sample_content, model="gpt-4o-mini")

    print(f"Grammar Score: {validation.get('grammar_score', 'N/A')}")
    print(f"Human Score: {validation.get('human_score', 'N/A')}")
    print(f"SEO Score: {validation.get('seo_score', 'N/A')}")
    print(f"Has FAQ: {validation.get('has_faq', False)}")
    print(f"Suggestions: {len(validation.get('suggestions', []))} items\n")

    # Step 4: Auto-Fix
    print("[STEP 4] Content Auto-Fix")
    print("-" * 80)
    fix_result = await fix_content(
        content=sample_content,
        validation_report=validation,
        metadata={
            "focus_keyphrase": "파이썬 웹 크롤링",
            "language": "ko",
            "style": "guide"
        }
    )

    print("Fix Summary:")
    for item in fix_result['fix_summary']:
        print(f"  - {item}")
    print(f"\nFAQ Added: {fix_result['added_FAQ']}")
    print(f"Keyword Density: {fix_result['keyword_density']}%")
    print(f"\nFixed Content Preview (first 300 chars):")
    print("-" * 80)
    print(fix_result['fixed_content'][:300] + "...")

    # Step 5: Final Summary
    print("\n" + "="*80)
    print("PIPELINE SUMMARY")
    print("="*80)
    print(f"1. Topic Refined: {refined_topic[:50]}...")
    print(f"2. Content Generated: {len(sample_content)} chars")
    print(f"3. Validation Scores: G={validation.get('grammar_score', 0)}, "
          f"H={validation.get('human_score', 0)}, "
          f"SEO={validation.get('seo_score', 0)}")
    print(f"4. Content Fixed: {len(fix_result['fixed_content'])} chars")
    print(f"5. Final Keyword Density: {fix_result['keyword_density']}%")
    print(f"6. FAQ Added: {'Yes' if fix_result['added_FAQ'] else 'No'}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
