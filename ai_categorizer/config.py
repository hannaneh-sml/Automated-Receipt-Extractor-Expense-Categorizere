from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    rabbitmq_host: str = "localhost"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()