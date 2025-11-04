# potensia_ai/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "PotensiaAI"
    ENV: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/potensia_ai"
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    MODEL_PRIMARY: str = "gpt-5"
    MODEL_FALLBACK: str = "claude-3.5-sonnet"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# ✅ 테스트 실행용 (python -m potensia_ai.core.config)
if __name__ == "__main__":
    print(
        f"APP_NAME={settings.APP_NAME} / ENV={settings.ENV} / DB={settings.DATABASE_URL}"
    )
