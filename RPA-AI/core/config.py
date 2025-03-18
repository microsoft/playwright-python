from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List

class Settings(BaseSettings):
    # 基础配置
    BASE_DIR: Path = Path(__file__).parent.parent
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    CORS_ORIGINS: List[str] = ["*"]
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 缓存时间（秒）
    
    # 并发配置
    MAX_WORKERS: int = 3  # Playwright工作进程数
    
    # 各服务超时设置
    CHAT_TIMEOUT: int = 30  # AI对话超时时间
    SEARCH_TIMEOUT: int = 20  # 搜索超时时间
    
    # 重试配置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1
    
    class Config:
        env_file = ".env"

settings = Settings()
