#把所有跟数据库打交道的代码（增删改查）抽离出来。以后不管哪个路由要用数据，都调这里的函数。
from sqlalchemy.orm import Session
from database import DBDevice
from app.schemas import DeviceCreate

# 查询所有设备
def get_all_devices(db: Session):
    return db.query(DBDevice).all()

# 创建新设备
def create_new_device(db: Session, device_data: DeviceCreate):
    new_device = DBDevice(name=device_data.name, room=device_data.room, is_on=False)
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

# 根据 ID 获取单个设备 (供开关接口调用)
def get_device_by_id(db: Session, device_id: int):
    return db.query(DBDevice).filter(DBDevice.device_id == device_id).first()

# 修改设备状态 (开启/关闭)
def update_device_status(db: Session, device: DBDevice, is_on: bool):
    device.is_on = is_on
    db.commit()
    db.refresh(device)
    return device

# 删除设备
def delete_device(db: Session, device_id: int):
    # 1. 先去数据库找这个设备存不存在
    device = db.query(DBDevice).filter(DBDevice.device_id == device_id).first()
    if device:
        # 2. 如果存在，执行删除操作
        db.delete(device)
        db.commit()
    # 3. 返回被删除的设备对象（如果没找到，返回的是 None）
    return device