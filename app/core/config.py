from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:pass@localhost/inventory"

    class Config:
        env_file = .env

settings = Settings()