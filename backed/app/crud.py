#把所有跟数据库打交道的代码（增删改查）抽离出来。以后不管哪个路由要用数据，都调这里的函数。
from sqlalchemy.orm import Session
from database import DBDevice
from app.schemas import DeviceCreate
from database import Memory


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

# 在 app/crud.py 底部新增

# 保存或更新记忆 (如果 key 已存在就覆盖)
def save_memory(db: Session, key: str, value: str):
    existing_memory = db.query(Memory).filter(Memory.key == key).first()
    if existing_memory:
        existing_memory.value = value
    else:
        new_memory = Memory(key=key, value=value)
        db.add(new_memory)
    db.commit()
    return {"key": key, "value": value}

# 获取所有记忆 (用于每次对话前喂给 AI)
def get_all_memories(db: Session):
    return db.query(Memory).all()