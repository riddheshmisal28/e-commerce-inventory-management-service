from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:qwer%40321@localhost/inventory"

    # class Config:
    #     env_file = .env

settings = Settings()