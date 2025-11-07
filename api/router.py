# potensia_ai/api/router.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_tools.writer.topic_refiner import refine_topic
from ai_tools.writer.generator import generate_content
from ai_tools.writer.validator import validate_content

# ─────────────────────────────────────────────────────────────────────────────
# APIRouter 설정
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api", tags=["Writer"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic 모델 정의
# ─────────────────────────────────────────────────────────────────────────────
class WriteRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Raw keyword or topic to generate content for")
    model: str | None = Field(None, description="Optional: OpenAI model name (e.g., gpt-4o-mini)")


class RefineRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Raw keyword to refine")


class ValidateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Blog content to validate (Markdown format)")
    model: str | None = Field(None, description="Optional: OpenAI model name")


class WriteResponse(BaseModel):
    status: str
    input_topic: str
    refined_topic: str
    content: str
    validation: dict


class RefineResponse(BaseModel):
    status: str
    input_topic: str
    refined_topic: str


class ValidateResponse(BaseModel):
    status: str
    validation: dict


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str


# ─────────────────────────────────────────────────────────────────────────────
# Helper: 로깅
# ─────────────────────────────────────────────────────────────────────────────
def log_api(endpoint: str, status: str, detail: str = ""):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [API:{endpoint}] [{status}] {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 1: /api/write - 전체 파이프라인
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/write",
    response_model=WriteResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Generate complete blog article",
    description="Full pipeline: refine topic → generate content → validate quality"
)
async def write_article(request: WriteRequest):
    """
    전체 블로그 생성 파이프라인:
    1. topic_refiner: 키워드를 SEO/AEO 친화적 제목으로 변환
    2. generator: 블로그 본문 생성 (GPT-4o-mini → Claude 폴백)
    3. validator: 콘텐츠 품질 평가 (문법, AI 탐지, SEO, FAQ)
    """
    log_api("write", "START", f"topic='{request.topic[:50]}...'")

    try:
        # Step 1: Topic refinement
        log_api("write", "REFINE", "Refining topic...")
        refined_topic = await refine_topic(request.topic)
        if not refined_topic or not refined_topic.strip():
            raise HTTPException(status_code=500, detail="Topic refinement failed: empty result")
        log_api("write", "REFINE_OK", f"refined='{refined_topic[:50]}...'")

        # Step 2: Content generation
        log_api("write", "GENERATE", "Generating content...")
        content = await generate_content(refined_topic)
        if not content or not content.strip():
            raise HTTPException(status_code=500, detail="Content generation failed: empty result")
        log_api("write", "GENERATE_OK", f"content_length={len(content)}")

        # Step 3: Content validation
        log_api("write", "VALIDATE", "Validating content quality...")
        validation = await validate_content(content, model=request.model)

        # Check if validation returned an error
        if "error" in validation:
            log_api("write", "VALIDATE_WARN", f"Validation error: {validation['error']}")
        else:
            log_api("write", "VALIDATE_OK",
                   f"scores: G={validation.get('grammar_score', 0)}, "
                   f"H={validation.get('human_score', 0)}, "
                   f"SEO={validation.get('seo_score', 0)}")

        log_api("write", "SUCCESS", "Full pipeline completed")

        return WriteResponse(
            status="success",
            input_topic=request.topic,
            refined_topic=refined_topic,
            content=content,
            validation=validation
        )

    except HTTPException:
        raise
    except Exception as e:
        log_api("write", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 2: /api/refine - 주제 정제만
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/refine",
    response_model=RefineResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Refine topic only",
    description="Converts a raw keyword into a natural, SEO/AEO-friendly question-style title"
)
async def refine_topic_only(request: RefineRequest):
    """
    키워드를 자연스러운 질문형 제목으로 변환합니다.
    예: "파이썬 크롤링" → "파이썬으로 웹 크롤링을 시작하는 방법은?"
    """
    log_api("refine", "START", f"topic='{request.topic[:50]}...'")

    try:
        refined_topic = await refine_topic(request.topic)

        if not refined_topic or not refined_topic.strip():
            raise HTTPException(status_code=500, detail="Topic refinement failed: empty result")

        log_api("refine", "SUCCESS", f"refined='{refined_topic[:50]}...'")

        return RefineResponse(
            status="success",
            input_topic=request.topic,
            refined_topic=refined_topic
        )

    except HTTPException:
        raise
    except Exception as e:
        log_api("refine", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 3: /api/validate - 콘텐츠 검증만
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/validate",
    response_model=ValidateResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Validate content quality",
    description="Analyzes blog content for grammar, human-like quality, SEO/AEO, and AI detection"
)
async def validate_content_only(request: ValidateRequest):
    """
    블로그 콘텐츠의 품질을 평가합니다:
    - 문법 및 가독성 (0-10)
    - 사람다운 품질 / AI 탐지 (0-10)
    - SEO/AEO 최적화 (0-10)
    - FAQ 포함 여부
    - 개선 제안사항 (한국어)
    """
    log_api("validate", "START", f"content_length={len(request.content)}")

    try:
        validation = await validate_content(request.content, model=request.model)

        # Check if validation returned an error
        if "error" in validation:
            log_api("validate", "WARN", f"Validation error: {validation['error']}")
        else:
            log_api("validate", "SUCCESS",
                   f"scores: G={validation.get('grammar_score', 0)}, "
                   f"H={validation.get('human_score', 0)}, "
                   f"SEO={validation.get('seo_score', 0)}")

        return ValidateResponse(
            status="success",
            validation=validation
        )

    except Exception as e:
        log_api("validate", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Health Check 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/health", summary="Health check", description="Check if the Writer API is running")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "PotensiaAI Writer API",
        "timestamp": datetime.datetime.now().isoformat()
    }


# ─────────────────────────────────────────────────────────────────────────────
# 로컬 테스트 러너
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("Starting PotensiaAI Writer API Server...")
    print("="*80)
    print("Endpoints:")
    print("  POST   http://localhost:8000/api/write     - Full pipeline")
    print("  POST   http://localhost:8000/api/refine    - Topic refinement only")
    print("  POST   http://localhost:8000/api/validate  - Content validation only")
    print("  GET    http://localhost:8000/api/health    - Health check")
    print("  GET    http://localhost:8000/docs          - Interactive API docs")
    print("="*80 + "\n")

    # Use string import path for reload to work
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
