"""配置管理模块"""
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""
    # KOOK 配置
    kook_token: str = Field(..., env="KOOK_TOKEN")
    kook_api_base: str = "https://www.kookapp.cn/api/v3"
    
    # 日志配置
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_path: Path = Path("logs")
    
    # 数据库配置
    database_path: Path = Field(Path("data/bot.db"), env="DATABASE_PATH")
    
    # 规则配置
    default_rule: str = Field("coc7", env="DEFAULT_RULE")
    critical_threshold: int = Field(5, env="CRITICAL_THRESHOLD")
    fumble_threshold: int = Field(96, env="FUMBLE_THRESHOLD")
    
    # WebSocket 配置
    heartbeat_interval: int = 30
    reconnect_max_retries: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
