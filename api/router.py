# potensia_ai/api/router.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ai_tools.writer.topic_refiner import refine_topic
from ai_tools.writer.generator import generate_content
from ai_tools.writer.validator import validate_content
from ai_tools.writer.fixer import fix_content

# Configure logging
logger = logging.getLogger("api.router")

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


class FixRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Blog content to fix")
    validation_report: dict = Field(..., description="Validator result")
    metadata: dict | None = Field(None, description="Optional metadata (focus_keyphrase, language, style)")


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


class FixResponse(BaseModel):
    status: str
    fixed_content: str
    fix_summary: list[str]
    added_FAQ: bool
    keyword_density: float


class ErrorResponse(BaseModel):
    status: str = "error"
    detail: str


# ─────────────────────────────────────────────────────────────────────────────
# Helper: 로깅
# ─────────────────────────────────────────────────────────────────────────────
def log_api(endpoint: str, status: str, detail: str = ""):
    """Structured logging helper for API endpoints"""
    log_message = f"[API:{endpoint}] [{status}] {detail}"

    if status in ["ERROR", "WARN", "VALIDATE_WARN"]:
        logger.warning(log_message)
    elif status == "SUCCESS" or status.endswith("_OK"):
        logger.info(log_message)
    else:
        logger.info(log_message)


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 1: /api/write - 전체 파이프라인
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/write",
    response_model=WriteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": WriteResponse, "description": "Successfully generated content"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
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
        # Input validation
        if not request.topic or not request.topic.strip():
            log_api("write", "ERROR", "Empty topic provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topic cannot be empty"
            )

        # Step 1: Topic refinement
        log_api("write", "REFINE", "Refining topic...")
        refined_topic = await refine_topic(request.topic)
        if not refined_topic or not refined_topic.strip():
            log_api("write", "ERROR", "Topic refinement returned empty result")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Content generation service unavailable"
            )
        log_api("write", "REFINE_OK", f"refined='{refined_topic[:50]}...'")

        # Step 2: Content generation
        log_api("write", "GENERATE", "Generating content...")
        content = await generate_content(refined_topic)
        if not content or not content.strip():
            log_api("write", "ERROR", "Content generation returned empty result")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Content generation service unavailable"
            )
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
        log_api("write", "ERROR", f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during content generation"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 2: /api/refine - 주제 정제만
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/refine",
    response_model=RefineResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": RefineResponse, "description": "Successfully refined topic"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
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
        # Input validation
        if not request.topic or not request.topic.strip():
            log_api("refine", "ERROR", "Empty topic provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topic cannot be empty"
            )

        refined_topic = await refine_topic(request.topic)

        if not refined_topic or not refined_topic.strip():
            log_api("refine", "ERROR", "Topic refinement returned empty result")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Topic refinement service unavailable"
            )

        log_api("refine", "SUCCESS", f"refined='{refined_topic[:50]}...'")

        return RefineResponse(
            status="success",
            input_topic=request.topic,
            refined_topic=refined_topic
        )

    except HTTPException:
        raise
    except Exception as e:
        log_api("refine", "ERROR", f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during topic refinement"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 3: /api/validate - 콘텐츠 검증만
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/validate",
    response_model=ValidateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": ValidateResponse, "description": "Successfully validated content"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
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
        # Input validation
        if not request.content or not request.content.strip():
            log_api("validate", "ERROR", "Empty content provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content cannot be empty"
            )

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

    except HTTPException:
        raise
    except Exception as e:
        log_api("validate", "ERROR", f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during content validation"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 엔드포인트 4: /api/fix - 콘텐츠 자동 교정
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/fix",
    response_model=FixResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": FixResponse, "description": "Successfully fixed content"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Fix content issues",
    description="Automatically fix content based on validation report using GPT-4o"
)
async def fix_content_issues(request: FixRequest):
    """
    Validator 리포트를 기반으로 콘텐츠를 자동 교정합니다:
    - FAQ 자동 생성
    - 키워드 밀도 조정 (1.5-2.5%)
    - 반복 표현 제거
    - AI 탐지율 감소
    - SEO 최적화
    """
    log_api("fix", "START", f"content_length={len(request.content)}")

    try:
        # Input validation
        if not request.content or not request.content.strip():
            log_api("fix", "ERROR", "Empty content provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content cannot be empty"
            )

        if not request.validation_report:
            log_api("fix", "ERROR", "Empty validation report provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Validation report is required"
            )

        result = await fix_content(
            content=request.content,
            validation_report=request.validation_report,
            metadata=request.metadata
        )

        log_api("fix", "SUCCESS",
               f"density={result['keyword_density']}%, FAQ={result['added_FAQ']}")

        return FixResponse(
            status="success",
            fixed_content=result['fixed_content'],
            fix_summary=result['fix_summary'],
            added_FAQ=result['added_FAQ'],
            keyword_density=result['keyword_density']
        )

    except HTTPException:
        raise
    except Exception as e:
        log_api("fix", "ERROR", f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during content fixing"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Health Check 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the Writer API is running"
)
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
