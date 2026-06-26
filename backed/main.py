from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
#导入home_device模块中的Device类和异常类
from home_device import Device, DeviceAlreadyOnError, DeviceAlreadyOffError

app = FastAPI(title="智能家居设备管理API", description="用于管理智能家居设备的API接口", version="1.0.0")

#模拟一个设备列表，实际应用中可以从数据库获取
db = {}

#定义请求体的数据格式
class DeviceRequest(BaseModel):
    name: str
    room: str

@app.post("/api/devices/", status_code=201)
def create_device(device_request: DeviceRequest):
    """创建一个新的智能家居设备"""
    new_id = len(db) + 1
    #实例化昨天的Device类
    new_device = Device(device_id=new_id, name=device_request.name, room=device_request.room)
    db[new_id] = new_device
    return{"device_id": new_id, "name": new_device.name, "room": new_device.room, "is_on": new_device.is_on}

@app.get("/api/devices")
def list_devices():
    """查询所有智能家居设备"""
    return [{"device_id": device.device_id, "name": device.name, "room": device.room, "is_on": device.is_on} for device in db.values()]
@app.post("/api/devices/{device_id}/on")
def turn_device_on(device_id: int):
    """开启设备"""
    if device_id not in db:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    device = db[device_id]
    try:
        device.turn_on()
        return {"message": f"{device.name} 已开启", "is_on": device.is_on}
    except DeviceAlreadyOnError as e:
        # 如果昨天写的异常被触发了，转成 HTTP 400 错误返回
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/devices/{device_id}/off")
def turn_device_off(device_id: int):
    """关闭设备"""
    if device_id not in db:
        raise HTTPException(status_code=404, detail="设备不存在")
        
    device = db[device_id]
    try:
        device.turn_off()
        return {"message": f"{device.name} 已关闭", "is_on": device.is_on}
    except DeviceAlreadyOffError as e:
        raise HTTPException(status_code=400, detail=str(e))