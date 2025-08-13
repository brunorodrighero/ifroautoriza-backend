from pydantic_settings import BaseSettings
from pydantic import EmailStr
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str
    API_V1_STR: str
    BACKEND_CORS_ORIGINS: List[str]
    
    DB_USER: str
    DB_PASSWORD: str
    DB_SERVER: str
    DB_PORT: str
    DB_NAME: str
    DATABASE_URL: str = ""

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}"

    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    FROM_EMAIL: EmailStr
    
    UPLOAD_DIRECTORY: str
    MAX_FILE_SIZE: int
    ALLOWED_FILE_TYPES: List[str]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()