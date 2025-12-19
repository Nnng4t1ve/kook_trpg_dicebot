"""配置管理模块"""
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from pathlib import Path


# 敏感字段名列表，这些字段在日志中会被掩码
SENSITIVE_FIELDS = {"kook_token", "db_password", "llm_api_token"}


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
    
    # Web 服务配置
    web_host: str = Field("0.0.0.0", env="WEB_HOST")
    web_port: int = Field(8080, env="WEB_PORT")
    web_base_url: str = Field("http://localhost:8080", env="WEB_BASE_URL")
    
    # LLM 服务配置
    llm_service: bool = Field(False, env="LLM_SERVICE")
    llm_api_url: str = Field("", env="LLM_API_URL")
    llm_api_token: str = Field("", env="LLM_API_TOKEN")
    llm_model: str = Field("", env="LLM_MODEL")
    llm_prompt: str = Field("", env="PROMPT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def safe_dict(self) -> dict:
        """返回安全的配置字典，敏感字段会被掩码"""
        data = {}
        for key, value in self.model_dump().items():
            if key in SENSITIVE_FIELDS:
                if value:
                    # 只显示前4个字符，其余用 * 掩码
                    masked = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "****"
                    data[key] = masked
                else:
                    data[key] = "(empty)"
            else:
                data[key] = value
        return data
    
    def __repr__(self) -> str:
        """安全的字符串表示，不暴露敏感信息"""
        safe = self.safe_dict()
        items = ", ".join(f"{k}={v!r}" for k, v in safe.items())
        return f"Settings({items})"
    
    def __str__(self) -> str:
        """安全的字符串表示"""
        return self.__repr__()


settings = Settings()
