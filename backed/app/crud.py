"""数据库 CRUD 操作：设备 + 记忆 + 场景。"""
import json

from sqlalchemy.orm import Session

from database import DBDevice, Memory, Scene
from app.schemas import DeviceCreate, SceneCreate


# ============ 设备 ============
def get_all_devices(db: Session):
    return db.query(DBDevice).all()


def create_new_device(db: Session, device_data: DeviceCreate):
    new_device = DBDevice(name=device_data.name, room=device_data.room, is_on=False)
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device


def get_device_by_id(db: Session, device_id: int):
    return db.query(DBDevice).filter(DBDevice.device_id == device_id).first()


def update_device_status(db: Session, device: DBDevice, is_on: bool):
    device.is_on = is_on
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device_id: int):
    device = db.query(DBDevice).filter(DBDevice.device_id == device_id).first()
    if device:
        db.delete(device)
        db.commit()
    return device


# ============ 记忆 ============
def save_memory(db: Session, key: str, value: str):
    existing_memory = db.query(Memory).filter(Memory.key == key).first()
    if existing_memory:
        existing_memory.value = value
    else:
        new_memory = Memory(key=key, value=value)
        db.add(new_memory)
    db.commit()
    return {"key": key, "value": value}


def get_all_memories(db: Session):
    return db.query(Memory).all()


# ============ 场景预设 ============
def get_all_scenes(db: Session):
    return db.query(Scene).all()


def get_scene_by_name(db: Session, name: str):
    return db.query(Scene).filter(Scene.name == name).first()


def create_scene(db: Session, scene_data: SceneCreate):
    new_scene = Scene(
        name=scene_data.name,
        description=scene_data.description,
        config=json.dumps({"actions": [a.model_dump() for a in scene_data.actions]}),
    )
    db.add(new_scene)
    db.commit()
    db.refresh(new_scene)
    return new_scene


def delete_scene(db: Session, scene_id: int):
    scene = db.query(Scene).filter(Scene.scene_id == scene_id).first()
    if scene:
        db.delete(scene)
        db.commit()
    return scene


def get_scene_actions(scene: Scene) -> list[dict]:
    """从 Scene.config 解析出 actions 列表。"""
    try:
        return json.loads(scene.config).get("actions", [])
    except (json.JSONDecodeError, TypeError):
        return []
