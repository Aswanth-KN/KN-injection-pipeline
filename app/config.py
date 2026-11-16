from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.1:latest"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ingestion_db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
