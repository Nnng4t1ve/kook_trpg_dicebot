"""错误处理中间件"""
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class ErrorResponse:
    """统一错误响应"""
    
    def __init__(self, code: int, message: str, detail: str = None):
        self.code = code
        self.message = message
        self.detail = detail
    
    def to_dict(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.detail:
            result["detail"] = self.detail
        return result


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception(f"Unhandled error: {request.method} {request.url.path}")
            error = ErrorResponse(
                code=500,
                message="服务器内部错误",
                detail=str(e) if logger.level("DEBUG").no <= logger._core.min_level else None
            )
            return JSONResponse(
                status_code=500,
                content=error.to_dict()
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger.debug(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"Response: {request.method} {request.url.path} -> {response.status_code}")
        return response
