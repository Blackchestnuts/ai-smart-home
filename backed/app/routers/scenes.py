"""场景预设路由：CRUD + 激活场景。

场景是一组设备动作的预设组合，比如"观影模式"=关客厅灯+开电视+开空调。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.sse import broadcast, device_dict
from database import SessionLocal

router = APIRouter(prefix="/api/scenes", tags=["场景预设"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[schemas.SceneResponse])
def list_scenes(db: Session = Depends(get_db)):
    scenes = crud.get_all_scenes(db)
    result = []
    for s in scenes:
        result.append({
            "scene_id": s.scene_id,
            "name": s.name,
            "description": s.description,
            "actions": crud.get_scene_actions(s),
        })
    return result


@router.post("", status_code=201, response_model=schemas.SceneResponse)
def create_scene(scene: schemas.SceneCreate, db: Session = Depends(get_db)):
    if crud.get_scene_by_name(db, scene.name):
        raise HTTPException(status_code=400, detail=f"场景 [{scene.name}] 已存在")
    new_scene = crud.create_scene(db, scene)
    return {
        "scene_id": new_scene.scene_id,
        "name": new_scene.name,
        "description": new_scene.description,
        "actions": crud.get_scene_actions(new_scene),
    }


@router.delete("/{scene_id}")
def delete_scene(scene_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_scene(db, scene_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="场景不存在")
    return {"message": f"场景 [{deleted.name}] 已删除"}


@router.post("/{scene_id}/activate")
def activate_scene(scene_id: int, db: Session = Depends(get_db)):
    """激活场景：依次应用所有预设的设备动作。"""
    scene = db.query(crud.Scene if hasattr(crud, 'Scene') else None).filter_by(scene_id=scene_id).first()
    # 直接用 SessionLocal 查询
    from database import Scene
    scene = db.query(Scene).filter(Scene.scene_id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    actions = crud.get_scene_actions(scene)
    applied = 0
    for action in actions:
        device = crud.get_device_by_id(db, action["device_id"])
        if not device:
            continue
        target = action["is_on"]
        if device.is_on != target:
            crud.update_device_status(db, device, is_on=target)
            broadcast({"type": "updated", "device": device_dict(device)})
            applied += 1

    return {"message": f"场景 [{scene.name}] 已激活，应用了 {applied} 个设备动作"}
