# potensia_ai/api/main.py
"""
PotensiaAI Writer API - Main Application Entry Point
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import router

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App 초기화
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PotensiaAI Writer API",
    description="AI-powered blog content generation and validation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS 설정 (필요시)
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영환경에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Router 등록
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(router)


# ─────────────────────────────────────────────────────────────────────────────
# Root Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "service": "PotensiaAI Writer API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "write": "/api/write",
            "refine": "/api/refine",
            "validate": "/api/validate",
            "fix": "/api/fix",
            "health": "/api/health"
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 로컬 개발 서버 실행
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("PotensiaAI Writer API Server")
    print("="*80)
    print("Endpoints:")
    print("  POST   http://localhost:8000/api/write     - Full pipeline")
    print("  POST   http://localhost:8000/api/refine    - Topic refinement only")
    print("  POST   http://localhost:8000/api/validate  - Content validation only")
    print("  POST   http://localhost:8000/api/fix       - Auto-fix content issues")
    print("  GET    http://localhost:8000/api/health    - Health check")
    print("  GET    http://localhost:8000/docs          - Interactive API docs")
    print("="*80 + "\n")

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
