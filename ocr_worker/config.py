from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    minio_endpoint: str = "http://localhost:9000"
    rabbitmq_host: str = "localhost"
    minio_access_key: str = "admin"          
    minio_secret_key: str = "password123"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()