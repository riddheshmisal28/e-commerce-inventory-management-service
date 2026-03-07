from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:qwer%40321@localhost/inventory"

    model_config = ConfigDict(
        env_file = ".env"
    )

settings = Settings()