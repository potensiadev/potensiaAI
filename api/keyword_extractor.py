# potensia_ai/api/keyword_extractor.py
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
너는 고급 SEO·콘텐츠 전략가이자 키워드 분석 전문가다.
사용자가 /키워드추출 [키워드]를 입력하면 이를 “메인 키워드”로 인식하고,
다음 단계로 작동한다:

1️⃣ '메인 키워드'를 중심으로 4개 카테고리(정보탐색 / 구매의도 / 비교 / 문제해결)별로 8~10개 키워드 생성
2️⃣ 상위 10개 주요 키워드 선정 후 표 형태로 요약
   (검색량 / 경쟁도 / 트렌드 / 난이도 / 수익성 / 총점 / 등급 포함)
3️⃣ 각 키워드의 활용 방안 및 예시 제목을 제시
출력은 Markdown 표 없이 JSON 형태로 반환하라.
형식:
{
  "top_keywords": [
    {"keyword": "...", "search_volume": "...", "competition": "...", "trend": "...", "score": "...", "grade": "..."},
    ...
  ]
}
"""

class KeywordRequest(BaseModel):
    keyword: str

@router.post("/api/getTopKeywords")
async def get_top_keywords(req: KeywordRequest):
    """
    입력된 키워드를 기반으로 상위 10개 연관 키워드 리스트 반환
    """
    try:
        prompt = f"/키워드추출 [{req.keyword}]"
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        response_text = completion.choices[0].message.content.strip()

        # 응답이 JSON 형태면 그대로 파싱
        import json
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="응답 파싱 실패")

        return {"status": "success", "keyword": req.keyword, "data": data["top_keywords"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
