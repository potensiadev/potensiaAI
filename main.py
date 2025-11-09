# main.py
import sys
from pathlib import Path

# Railway 배포를 위한 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.router import router as writer_router  # ✅ 변경 포인트

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1",
    description="AI-powered content automation platform",
)

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: 전체 허용 (추후 제한)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health Check
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}

# ✅ Writer Router 연결
app.include_router(writer_router)  # /api/write/* 포함됨

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
