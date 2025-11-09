# potensia_ai/ai_tools/media/router.py
import logging
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ai_tools.media.thumbnail import generate_thumbnail

# Configure logging
logger = logging.getLogger("api.media")

# Create router
router = APIRouter(prefix="/api/media", tags=["Media"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class ThumbnailRequest(BaseModel):
    """Request model for thumbnail generation"""
    topic: str = Field(..., min_length=1, max_length=1000, description="Topic or description for thumbnail image")
    size: Optional[str] = Field(None, description="Image size (e.g., '1024x1024', '1792x1024', '1024x1792')")


class ThumbnailResponse(BaseModel):
    """Response model for successful thumbnail generation"""
    status: str = Field(..., description="Response status")
    url: str = Field(..., description="Direct URL to the generated image")
    prompt_used: str = Field(..., description="The prompt sent to the image generation API")
    size: str = Field(..., description="Image dimensions used")
    revised_prompt: Optional[str] = Field(None, description="AI-revised version of the prompt (DALL-E 3)")


class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = "error"
    detail: str


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Logging
# ─────────────────────────────────────────────────────────────────────────────

def log_api(endpoint: str, status: str, detail: str = ""):
    """Structured logging helper for API endpoints"""
    log_message = f"[API:media/{endpoint}] [{status}] {detail}"

    if status in ["ERROR", "WARN"]:
        logger.warning(log_message)
    elif status == "SUCCESS":
        logger.info(log_message)
    else:
        logger.info(log_message)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 1: POST /api/media/thumbnail
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/thumbnail",
    response_model=ThumbnailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": ThumbnailResponse, "description": "Successfully generated thumbnail image"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Generate thumbnail image for blog topic",
    description="Creates an AI-generated thumbnail image using OpenAI DALL-E based on a text description"
)
async def create_thumbnail(request: ThumbnailRequest):
    """
    Generate a thumbnail image from a text description.

    This endpoint uses OpenAI's DALL-E model to create visually appealing
    thumbnail images suitable for blog posts, articles, or social media.

    The AI interprets the topic description and generates a relevant,
    professional-looking image.
    """
    log_api("thumbnail", "START", f"topic='{request.topic[:50]}...', size={request.size}")

    try:
        # Input validation
        if not request.topic or not request.topic.strip():
            log_api("thumbnail", "ERROR", "Empty topic provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topic cannot be empty"
            )

        # Set default size if not provided
        size = request.size or "1024x1024"

        # Validate size format
        valid_sizes = ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]
        if size not in valid_sizes:
            log_api("thumbnail", "ERROR", f"Invalid size: {size}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid size '{size}'. Must be one of: {', '.join(valid_sizes)}"
            )

        # Call thumbnail generator
        log_api("thumbnail", "PROCESSING", "Calling image generation API...")
        result = await generate_thumbnail(request.topic, size)

        # Check for errors in result
        if "error" in result:
            log_api("thumbnail", "ERROR", result["error"])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image generation failed: {result['error']}"
            )

        log_api("thumbnail", "SUCCESS", f"Generated image: {result['url'][:80]}...")

        response_data = {
            "status": "success",
            "url": result["url"],
            "prompt_used": result["prompt_used"],
            "size": result["size"],
        }

        # Include revised prompt if available (DALL-E 3)
        if "revised_prompt" in result:
            response_data["revised_prompt"] = result["revised_prompt"]

        return ThumbnailResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        log_api("thumbnail", "ERROR", f"Unexpected error: {str(e)}")
        logger.exception("Thumbnail generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during thumbnail generation"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint 2: GET /api/media/ping
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the Media API is running"
)
async def ping():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PotensiaAI Media API",
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
    app = FastAPI(title="Media API Test")
    app.include_router(router)

    # Configure logging for test
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("Starting Media API Test Server...")
    print("="*80)
    print("Endpoints:")
    print("  POST   http://localhost:8002/api/media/thumbnail")
    print("  GET    http://localhost:8002/api/media/ping")
    print("  GET    http://localhost:8002/docs - Interactive API docs")
    print("="*80)
    print("\nExample curl command:")
    print('  curl -X POST http://localhost:8002/api/media/thumbnail \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"topic": "겨울철 싱크대 냄새 일러스트"}\'')
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8002)
