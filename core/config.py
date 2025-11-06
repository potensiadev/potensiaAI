# potensia_ai/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv  # ✅ 추가

# ✅ .env 강제 로드 (경로를 명시적으로 지정)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
env_path = os.path.abspath(env_path)
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print(f"⚠️  .env 파일을 찾을 수 없습니다: {env_path}")

class Settings(BaseSettings):
    APP_NAME: str = "PotensiaAI"
    ENV: str = "development"
    DEBUG: bool = True

    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    MODEL_PRIMARY: str = "gpt-4o-mini"
    MODEL_FALLBACK: str = "claude-3-5-sonnet-20241022"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra fields in .env

settings = Settings()

if __name__ == "__main__":
    print(f"OPENAI_API_KEY={settings.OPENAI_API_KEY}")
