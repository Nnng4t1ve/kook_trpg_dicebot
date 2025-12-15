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
    
    # MySQL 数据库配置
    db_host: str = Field("localhost", env="DB_HOST")
    db_port: int = Field(3306, env="DB_PORT")
    db_user: str = Field("root", env="DB_USER")
    db_password: str = Field("", env="DB_PASSWORD")
    db_name: str = Field("trpg_dicebot", env="DB_NAME")
    
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
