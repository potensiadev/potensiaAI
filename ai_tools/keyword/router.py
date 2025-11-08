# potensia_ai/ai_tools/keyword/router.py
import logging
import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ai_tools.keyword.analyzer import analyze_keywords

# Configure logging
logger = logging.getLogger("api.keyword")

# Create router
router = APIRouter(prefix="/api/keyword", tags=["Keyword"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class KeywordAnalyzeRequest(BaseModel):
    """Request model for keyword analysis"""
    topic: str = Field(..., min_length=1, max_length=500, description="Blog topic to analyze")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of keywords to return")


class KeywordItem(BaseModel):
    """Individual keyword with metrics"""
    keyword: str = Field(..., description="The keyword phrase")
    search_volume: int = Field(..., ge=0, description="Estimated monthly search volume")
    competition: float = Field(..., ge=0.0, le=1.0, description="Competition level (0.0-1.0)")
    difficulty: float = Field(..., ge=0.0, le=1.0, description="SEO ranking difficulty (0.0-1.0)")
    type: str = Field(..., description="Keyword type: primary, long-tail, semantic, or question")


class KeywordAnalyzeResponse(BaseModel):
    """Response model for keyword analysis"""
    status: str = Field(..., description="Response status")
    topic: str = Field(..., description="Original topic analyzed")
    keywords: List[KeywordItem] = Field(..., description="List of extracted keywords")
    total_keywords: int = Field(..., description="Total number of keywords returned")


class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = "error"
    detail: str


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Logging
# ─────────────────────────────────────────────────────────────────────────────

def log_api(endpoint: str, status: str, detail: str = ""):
    """Structured logging helper for API endpoints"""
    log_message = f"[API:keyword/{endpoint}] [{status}] {detail}"

    if status in ["ERROR", "WARN"]:
        logger.warning(log_message)
    elif status == "SUCCESS":
        logger.info(log_message)
    else:
        logger.info(log_message)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 1: POST /api/keyword/analyze
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=KeywordAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": KeywordAnalyzeResponse, "description": "Successfully analyzed keywords"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Analyze keywords for a blog topic",
    description="Extracts SEO/AEO optimized keywords from a given blog topic with search volume, competition, and difficulty metrics"
)
async def analyze_topic_keywords(request: KeywordAnalyzeRequest):
    """
    Analyze a blog topic and extract relevant SEO keywords.

    This endpoint uses AI to identify:
    - Primary keywords (high volume, moderate competition)
    - Long-tail keywords (specific phrases, lower competition)
    - Semantic keywords (related concepts)
    - Question-based keywords (common searches)

    Each keyword includes estimated search volume, competition level, and SEO difficulty.
    """
    log_api("analyze", "START", f"topic='{request.topic[:50]}...', max_results={request.max_results}")

    try:
        # Input validation
        if not request.topic or not request.topic.strip():
            log_api("analyze", "ERROR", "Empty topic provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topic cannot be empty"
            )

        # Call analyzer
        log_api("analyze", "PROCESSING", "Calling keyword analyzer...")
        keywords = await analyze_keywords(request.topic, max_results=request.max_results)

        if not keywords or len(keywords) == 0:
            log_api("analyze", "WARN", "No keywords extracted")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Keyword analysis service failed to extract keywords"
            )

        log_api("analyze", "SUCCESS", f"Extracted {len(keywords)} keywords")

        return KeywordAnalyzeResponse(
            status="success",
            topic=request.topic,
            keywords=[KeywordItem(**kw) for kw in keywords],
            total_keywords=len(keywords)
        )

    except HTTPException:
        raise
    except Exception as e:
        log_api("analyze", "ERROR", f"Unexpected error: {str(e)}")
        logger.exception("Keyword analysis failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during keyword analysis"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 2: GET /api/keyword/ping
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the Keyword API is running"
)
async def ping():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PotensiaAI Keyword API",
        "timestamp": datetime.datetime.now().isoformat()
    }


# ─────────────────────────────────────────────────────────────────────────────
# Local Test Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    import uvicorn
    from fastapi import FastAPI

    # Create test app
    app = FastAPI(title="Keyword API Test")
    app.include_router(router)

    # Configure logging for test
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("Starting Keyword API Test Server...")
    print("="*80)
    print("Endpoints:")
    print("  POST   http://localhost:8001/api/keyword/analyze")
    print("  GET    http://localhost:8001/api/keyword/ping")
    print("  GET    http://localhost:8001/docs - Interactive API docs")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8001)
