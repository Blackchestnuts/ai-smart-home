#路由只负责“接客”和“端菜”，具体的炒菜逻辑全部交给 crud.py。
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from app import crud, schemas

# 实例化一个路由器，相当于招募了一个专门管设备的接待员
router = APIRouter(prefix="/api/devices", tags=["设备管理"])

# 依赖注入：获取数据库连接
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
    return crud.create_new_device(db, device)

@router.post("/{device_id}/on", response_model=schemas.DeviceResponse)
def turn_device_on(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if device.is_on:
        raise HTTPException(status_code=400, detail=f"设备 [{device.name}] 已经开启，无需重复操作！")
    return crud.update_device_status(db, device, is_on=True)

@router.post("/{device_id}/off", response_model=schemas.DeviceResponse)
def turn_device_off(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if not device.is_on:
        raise HTTPException(status_code=400, detail=f"设备 [{device.name}] 已经关闭，无需重复操作！")
    return crud.update_device_status(db, device, is_on=False)

@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    """删除指定ID的设备"""
    # 调用后厨的删除函数
    deleted_device = crud.delete_device(db, device_id)
    # 如果后厨返回 None，说明设备不存在
    if not deleted_device:
        raise HTTPException(status_code=404, detail="设备不存在，无法删除")
    # 删除成功，返回提示信息
    return {"message": f"设备 [{deleted_device.name}] 已成功删除"}