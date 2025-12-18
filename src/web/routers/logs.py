"""游戏日志API路由"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..dependencies import get_db

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/{log_name}/export")
async def export_log(log_name: str, db=Depends(get_db)):
    """导出游戏日志为JSON"""
    # 获取日志信息
    log_info = await db.get_game_log(log_name)
    if not log_info:
        raise HTTPException(status_code=404, detail="日志不存在")

    # 获取所有条目
    entries = await db.get_game_log_entries(log_name)

    # 构建导出数据
    export_data = {
        "log_name": log_info["log_name"],
        "channel_id": log_info["channel_id"],
        "initiator_id": log_info["initiator_id"],
        "participants": log_info["participants"],
        "started_at": log_info["started_at"].isoformat() if log_info.get("started_at") else None,
        "ended_at": log_info["ended_at"].isoformat() if log_info.get("ended_at") else None,
        "entries": entries,
    }

    # 返回JSON文件
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{log_name}.json"',
            "Content-Type": "application/json; charset=utf-8",
        },
    )
