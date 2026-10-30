from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./bloom_kitchen.db"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    JWT_SECRET: str = "development-secret-change-this-before-use-123"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    FRONTEND_ORIGINS: str = "http://127.0.0.1:5500,http://localhost:5500"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self):
        return [x.strip() for x in self.FRONTEND_ORIGINS.split(",") if x.strip()]

settings = Settings()
