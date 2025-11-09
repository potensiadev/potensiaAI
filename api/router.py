# api/router.py
import datetime
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# ✅ 루트 기준으로 import (potensia_ai. ❌)
from ai_tools.writer.topic_refiner import refine_topic
from ai_tools.writer.generator import generate_content
from ai_tools.writer.validator import validate_content
from ai_tools.writer.fixer import fix_content

router = APIRouter(prefix="/api/write", tags=["Writer"])

# ─────────────── 모델 정의 ───────────────
class WriteRequest(BaseModel):
    topic: str
    model: str | None = None

class WriteResponse(BaseModel):
    status: str
    input_topic: str
    refined_topic: str
    content: str
    validation: dict

class RefineRequest(BaseModel):
    topic: str

class RefineResponse(BaseModel):
    status: str
    input_topic: str
    refined_topic: str

class ValidateRequest(BaseModel):
    content: str
    model: str | None = None

class ValidateResponse(BaseModel):
    status: str
    validation: dict

class FixRequest(BaseModel):
    content: str
    validation_report: dict
    metadata: dict | None = None

class FixResponse(BaseModel):
    status: str
    fixed_content: str
    fix_summary: list
    added_FAQ: bool
    keyword_density: float

# ─────────────── Helper ───────────────
def log_api(endpoint: str, status: str, detail: str = ""):
    print(f"[{endpoint}] [{status}] {detail}")

# ─────────────── /api/write ───────────────
@router.post("", response_model=WriteResponse)
async def write_article(request: WriteRequest):
    try:
        log_api("write", "START", f"topic={request.topic}")
        refined = await refine_topic(request.topic)
        content = await generate_content(refined)
        validation = await validate_content(content, model=request.model)

        return WriteResponse(
            status="success",
            input_topic=request.topic,
            refined_topic=refined,
            content=content,
            validation=validation
        )
    except Exception as e:
        log_api("write", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────── /api/write/refine ───────────────
@router.post("/refine", response_model=RefineResponse)
async def refine_topic_endpoint(request: RefineRequest):
    try:
        log_api("refine", "START", f"topic={request.topic}")
        refined = await refine_topic(request.topic)

        return RefineResponse(
            status="success",
            input_topic=request.topic,
            refined_topic=refined
        )
    except Exception as e:
        log_api("refine", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────── /api/write/validate ───────────────
@router.post("/validate", response_model=ValidateResponse)
async def validate_content_endpoint(request: ValidateRequest):
    try:
        log_api("validate", "START", f"content_length={len(request.content)}")
        validation = await validate_content(request.content, model=request.model)

        return ValidateResponse(
            status="success",
            validation=validation
        )
    except Exception as e:
        log_api("validate", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────── /api/write/fix ───────────────
@router.post("/fix", response_model=FixResponse)
async def fix_content_endpoint(request: FixRequest):
    try:
        log_api("fix", "START", f"content_length={len(request.content)}")
        result = await fix_content(
            request.content,
            request.validation_report,
            metadata=request.metadata
        )

        return FixResponse(
            status="success",
            fixed_content=result["fixed_content"],
            fix_summary=result["fix_summary"],
            added_FAQ=result["added_FAQ"],
            keyword_density=result["keyword_density"]
        )
    except Exception as e:
        log_api("fix", "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────── /api/write/health ───────────────
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Writer API",
        "timestamp": datetime.datetime.now().isoformat()
    }
