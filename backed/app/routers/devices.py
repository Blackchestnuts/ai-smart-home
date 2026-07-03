"""设备管理路由：RESTful CRUD + SSE 实时推送。

路由只负责"接客"和"端菜"，具体业务逻辑全部交给 crud.py。
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import SessionLocal
from app import crud, schemas
from app.sse import broadcast, device_dict, get_recent_events, subscribe, unsubscribe, sse_format

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[schemas.DeviceResponse])
def list_devices(db: Session = Depends(get_db)):
    return crud.get_all_devices(db)


@router.post("", status_code=201, response_model=schemas.DeviceResponse)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    new_dev = crud.create_new_device(db, device)
    broadcast({"type": "created", "device": device_dict(new_dev)})
    return new_dev


@router.post("/{device_id}/on", response_model=schemas.DeviceResponse)
def turn_device_on(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if device.is_on:
        raise HTTPException(status_code=400, detail=f"设备 [{device.name}] 已经开启，无需重复操作！")
    updated = crud.update_device_status(db, device, is_on=True)
    broadcast({"type": "updated", "device": device_dict(updated)})
    return updated


@router.post("/{device_id}/off", response_model=schemas.DeviceResponse)
def turn_device_off(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if not device.is_on:
        raise HTTPException(status_code=400, detail=f"设备 [{device.name}] 已经关闭，无需重复操作！")
    updated = crud.update_device_status(db, device, is_on=False)
    broadcast({"type": "updated", "device": device_dict(updated)})
    return updated


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    deleted_device = crud.delete_device(db, device_id)
    if not deleted_device:
        raise HTTPException(status_code=404, detail="设备不存在，无法删除")
    broadcast({"type": "deleted", "device_id": device_id})
    return {"message": f"设备 [{deleted_device.name}] 已成功删除"}


@router.get("/stream")
async def device_stream():
    """SSE 端点：客户端订阅后，设备状态变化会实时推送。"""
    queue = subscribe()

    async def event_generator():
        try:
            # 先回放历史事件
            for ev in get_recent_events():
                yield sse_format(ev)
            # 持续推送新事件
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield sse_format(event)
                except asyncio.TimeoutError:
                    # 心跳，防止代理超时断开
                    yield ": heartbeat\n\n"
        finally:
            unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭 nginx 缓冲
        },
    )
