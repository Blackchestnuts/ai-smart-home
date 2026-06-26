from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base, DBDevice

# 自动在数据库中创建表结构（如果不存在）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 智能家居控制台", description="用于管理智能家居设备的API接口", version="1.0.0")

# 依赖项：用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic 模型：定义请求体的数据格式
class DeviceRequest(BaseModel):
    name: str
    room: str

@app.post("/api/devices", status_code=201)
def create_device(device_request: DeviceRequest, db: Session = Depends(get_db)):
    """创建一个新的智能家居设备，并存入数据库"""
    # 1. 创建 ORM 对象 (不需要传 device_id，数据库会自动生成)
    new_device = DBDevice(name=device_request.name, room=device_request.room, is_on=False)
    
    # 2. 添加到会话并提交到数据库
    db.add(new_device)
    db.commit()
    
    # 3. 刷新对象，获取数据库自动生成的 device_id
    db.refresh(new_device) 
    
    return new_device

@app.get("/api/devices")
def list_devices(db: Session = Depends(get_db)):
    """查询所有智能家居设备"""
    # 直接查询数据库中的所有设备
    devices = db.query(DBDevice).all()
    return devices

@app.post("/api/devices/{device_id}/on")
def turn_device_on(device_id: int, db: Session = Depends(get_db)):
    """开启设备"""
    # 1. 去数据库里查找这个设备
    device = db.query(DBDevice).filter(DBDevice.device_id == device_id).first()
    
    # 2. 如果没找到，返回 404
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 3. 判断状态 (直接看数据库里的 is_on 字段)
    if device.is_on:
        raise HTTPException(status_code=400, detail=f"设备 [{device.name}] 已经开启，无需重复操作！")
    
    # 4. 修改状态并提交
    device.is_on = True
    db.commit()
    db.refresh(device)
    
    return {"message": f"{device.name} 已开启", "is_on": device.is_on}

@app.post("/api/devices/{device_id}/off")
def turn_device_off(device_id: int, db: Session = Depends(get_db)):
    """关闭设备"""
    # 1. 去数据库里查找这个设备
    device = db.query(DBDevice).filter(DBDevice.device_id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
        
    if not device.is_on:
        raise HTTPException(status_code=400, detail=f"设备 [{device.name}] 已经关闭，无需重复操作！")
    
    # 修改状态并提交
    device.is_on = False
    db.commit()
    db.refresh(device)
    
    return {"message": f"{device.name} 已关闭", "is_on": device.is_on}