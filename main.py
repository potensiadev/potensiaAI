# potensia_ai/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from potensia_ai.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1",
    description="AI-powered content automation platform",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP에서는 전체 허용, 추후 제한 예정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}

# 추후 모듈 연결 예시
# from potensia_ai.ai_tools.writer.router import router as writer_router
# app.include_router(writer_router, prefix="/api/write", tags=["Writer"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("potensia_ai.main:app", host="0.0.0.0", port=8000, reload=True)
