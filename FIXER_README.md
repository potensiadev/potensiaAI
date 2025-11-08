# Fixer Module Documentation

## 개요

Fixer는 Validator의 리포트를 기반으로 GPT-4o를 사용하여 콘텐츠를 자동으로 교정하는 AI 기반 콘텐츠 개선 모듈입니다.

## 주요 기능

### 1. 자동 FAQ 생성
- Validator가 FAQ 누락을 감지하면 자동으로 2-3개의 FAQ 추가
- Focus Keyphrase를 자연스럽게 포함
- 사용자가 궁금해할 질문을 지능적으로 생성

### 2. 키워드 밀도 최적화
- SEO 최적 범위(1.5-2.5%) 자동 조정
- 자연스러운 키워드 배치
- 키워드 스터핑 방지

### 3. AI 탐지율 감소
- 인간적인 문체로 리라이팅
- 반복적인 표현 제거
- 다양한 어휘와 문장 구조 사용

### 4. SEO 최적화
- 제목, 서론, 결론에 키워드 배치
- 헤더 구조 개선 (H1, H2, H3)
- 메타 정보 최적화

### 5. 문법 및 가독성 개선
- 문장 간 자연스러운 연결
- 불필요한 반복 제거
- 전문성과 신뢰성 유지

## 입출력 구조

### Input
```python
{
  "content": str,              # 원본 콘텐츠 (Markdown)
  "validation_report": dict,   # Validator 결과
  "metadata": {                # 선택적 메타데이터
      "focus_keyphrase": str,  # 주요 키워드
      "language": str,         # 언어 (ko/en)
      "style": str             # 스타일 (guide/informational/review)
  }
}
```

### Output
```python
{
  "fixed_content": str,        # 교정된 콘텐츠
  "fix_summary": list[str],    # 수정 항목 요약
  "added_FAQ": bool,           # FAQ 추가 여부
  "keyword_density": float     # 최종 키워드 밀도 (%)
}
```

## 사용 예시

### Python 모듈로 사용
```python
import asyncio
from ai_tools.writer.fixer import fix_content

async def main():
    # Validator 결과
    validation_report = {
        "grammar_score": 6,
        "human_score": 4,
        "seo_score": 5,
        "has_faq": False,
        "suggestions": ["FAQ 누락", "키워드 부족"]
    }

    # 메타데이터
    metadata = {
        "focus_keyphrase": "파이썬 웹 크롤링",
        "language": "ko",
        "style": "guide"
    }

    # 콘텐츠 교정
    result = await fix_content(
        content=original_content,
        validation_report=validation_report,
        metadata=metadata
    )

    print(f"Fixed: {result['fixed_content']}")
    print(f"Summary: {result['fix_summary']}")
    print(f"Keyword Density: {result['keyword_density']}%")

asyncio.run(main())
```

### API 엔드포인트로 사용
```bash
curl -X POST http://localhost:8000/api/fix \
  -H "Content-Type: application/json" \
  -d @test_fix.json
```

**test_fix.json:**
```json
{
  "content": "# 원본 콘텐츠...",
  "validation_report": {
    "grammar_score": 6,
    "human_score": 4,
    "seo_score": 5,
    "has_faq": false,
    "suggestions": ["FAQ 누락", "반복 표현", "키워드 부족"]
  },
  "metadata": {
    "focus_keyphrase": "파이썬 웹 크롤링",
    "language": "ko",
    "style": "guide"
  }
}
```

## 교정 로직

### 1. 수정 필요 항목 분석
```python
fix_needs = [
    'faq_missing',           # FAQ 섹션 누락
    'grammar_improvement',   # 문법 점수 < 7
    'humanize_content',      # 인간 점수 < 7
    'seo_optimization'       # SEO 점수 < 7
]
```

### 2. GPT-4o 호출
- **모델**: gpt-4o
- **Temperature**: 0.4 (일관성 유지)
- **Max Tokens**: 3000
- **System Prompt**: 자연스러운 인간 문체 + SEO 최적화 지침

### 3. 후처리
- 불필요한 공백 제거
- 연속 개행 정리 (3개 이상 → 2개)
- FAQ 섹션 감지
- 키워드 밀도 계산

## 키워드 밀도 계산

```python
density = (keyword_count / total_words) * 100
```

- **최적 범위**: 1.5% ~ 2.5%
- **코드 블록 제외**: 순수 텍스트만 카운트
- **대소문자 무시**: case-insensitive 매칭

## 성능 특성

| 항목 | 값 |
|------|-----|
| 평균 처리 시간 | 8-15초 |
| API 모델 | GPT-4o |
| 토큰 사용량 | 1500-3000 tokens |
| 최대 출력 | 3000 tokens |

## 에러 처리

### 교정 실패 시
```python
{
  "fixed_content": original_content,  # 원본 반환
  "fix_summary": ["교정 실패: {error}"],
  "added_FAQ": False,
  "keyword_density": 0.0
}
```

### 빈 응답 시
```python
{
  "fixed_content": original_content,
  "fix_summary": ["OpenAI 응답 오류 - 원본 반환"],
  "added_FAQ": False,
  "keyword_density": 0.0
}
```

## 주의사항

### 키워드 밀도 범위 초과
키워드 밀도가 1.5-2.5% 범위를 벗어나면 경고 메시지 포함:
```
"[주의] 키워드 밀도 범위 초과 (3.5%) - 수동 조정 권장"
```

### 원본 내용 보존
- 중요한 정보는 절대 삭제하지 않음
- 기존 톤앤매너 유지
- 코드 블록 및 예제 보존

## 테스트

### 단독 테스트
```bash
python ai_tools/writer/fixer.py
```

### 전체 파이프라인 테스트
```bash
python test_full_pipeline.py
```

## API 통합

Fixer는 FastAPI router에 `/api/fix` 엔드포인트로 통합되어 있습니다.

**Endpoint**: `POST /api/fix`

**Request**:
```json
{
  "content": "string",
  "validation_report": {...},
  "metadata": {...}
}
```

**Response**:
```json
{
  "status": "success",
  "fixed_content": "string",
  "fix_summary": [...],
  "added_FAQ": true,
  "keyword_density": 1.85
}
```

## 개선 로드맵

### v1.1
- [ ] Claude 3.5 Sonnet 지원 (크레딧 확보 시)
- [ ] 다중 언어 지원 확장
- [ ] 사용자 커스텀 프롬프트 지원

### v1.2
- [ ] 키워드 밀도 자동 재조정 (범위 초과 시)
- [ ] A/B 테스트를 위한 다양한 버전 생성
- [ ] 이미지 alt 텍스트 최적화

### v2.0
- [ ] 실시간 스트리밍 교정
- [ ] 배치 교정 지원
- [ ] 교정 히스토리 저장

## 문의 및 지원

- GitHub Issues: https://github.com/potensiadev/potensiaAI/issues
- 문서: API_README.md, IMPLEMENTATION_SUMMARY.md

---

**Version**: 1.0.0
**Last Updated**: 2025-11-08
**Model**: GPT-4o (OpenAI)
