from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_NAME: str = "Jarvis Skill Registry"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Organizations
    ORGANIZATIONS: str = "ABC Construction,XYZ Builders"
    
    @property
    def organization_list(self) -> List[str]:
        return [org.strip() for org in self.ORGANIZATIONS.split(",") if org.strip()]


settings = Settings()