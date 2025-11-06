# potensia_ai/ai_tools/writer/router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from potensia_ai.ai_tools.writer.generator import generate_content

router = APIRouter()

class WriteRequest(BaseModel):
    topic: str

@router.post("/")
async def write_post(request: WriteRequest):
    try:
        content = await generate_content(request.topic)
        return {"topic": request.topic, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
