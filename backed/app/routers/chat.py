"""AI 聊天路由：GLM-4 Function Calling 智能家居管家。

设计要点：
- 工具注册表（Tool Registry）：每个工具一个 handler 函数，新增工具只需注册一次
- 支持单轮多工具并发调用（用户说"开客厅灯和卧室空调"会同时执行两个 tool_call）
- 历史记录里过滤 system 消息，避免重复 system role 报错
- 返回 device_changed 标志位，前端只在状态变更时刷新设备列表
- 错误信息脱敏：日志记录完整堆栈，前端只看到通用提示
"""
import json
import logging
import os
from datetime import datetime
from typing import Callable

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud, schemas
from app.sse import broadcast, device_dict
from database import Scene, SessionLocal

load_dotenv()
logger = logging.getLogger("ai-smart-home.chat")

router = APIRouter(prefix="/api/chat", tags=["AI 助手"])

# ============ OpenAI 客户端（懒加载，便于测试 mock） ============
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """单例 OpenAI 客户端，避免每次请求重建。"""
    global _client
    if _client is None:
        api_key = os.getenv("GLM_API_KEY")
        if not api_key:
            raise RuntimeError("GLM_API_KEY 环境变量未配置")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4",
            timeout=30.0,
        )
    return _client


# ============ 请求/响应模型 ============
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    device_changed: bool = False


# ============ 工具定义（喂给 GLM） ============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": "控制智能家居设备的开关状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "设备的完整名称，必须包含房间信息！例如'卧室空调'、'客厅台灯'，绝对不能只写'空调'或'台灯'！",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["on", "off"],
                        "description": "动作，开=on，关=off",
                    },
                },
                "required": ["device_name", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_device",
            "description": "当用户要求添加、录入、购买新设备时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {"type": "string", "description": "新设备的名称，如'微波炉'"},
                    "room": {
                        "type": "string",
                        "enum": ["客厅", "卧室", "厨房", "书房"],
                        "description": "设备所在的房间",
                    },
                },
                "required": ["device_name", "room"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_device",
            "description": "当用户要求删除、移除、扔掉设备时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {"type": "string", "description": "要删除的设备名称"}
                },
                "required": ["device_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "turn_off_all_devices",
            "description": "当用户要求关闭所有设备、离家模式、晚安模式、一键全关时调用",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "welcome_home_mode",
            "description": "当用户说即将到家、我回来了、准备回家时调用。会根据天气自动开启空调到舒适温度，并打开必要的灯。",
            "parameters": {
                "type": "object",
                "properties": {
                    "eta_minutes": {
                        "type": "integer",
                        "description": "用户预计还有几分钟到家，如果是刚说'我回来了'则为0",
                    }
                },
                "required": ["eta_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_memory",
            "description": "当用户告诉你他的名字、偏好、习惯，或者要求你记住某件事时调用此工具保存。",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "记忆的类别，如'user_name'(用户名)、'preferred_temp'(偏好温度)、'habit'(习惯)",
                    },
                    "value": {
                        "type": "string",
                        "description": "记忆的具体内容，如'张三'、'26度'、'喜欢睡前关灯'",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "activate_scene",
            "description": "当用户要求激活预设场景（如观影模式、用餐模式、阅读模式）时调用。需要先查询场景列表确认存在。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_name": {
                        "type": "string",
                        "description": "场景名称，如'观影模式'、'用餐模式'"
                    }
                },
                "required": ["scene_name"],
            },
        },
    },
]


# ============ 工具执行结果 ============
class ToolResult:
    """工具执行结果。device_changed 用于驱动前端刷新。"""
    def __init__(self, message: str, device_changed: bool = False):
        self.message = message
        self.device_changed = device_changed


# ============ 设备匹配工具函数 ============
def find_device(all_devices, query: str):
    """三级匹配：精确名称 → 房间+名称 → 名称包含。
    多结果时返回 list，由调用方决定如何提示。"""
    query = query.strip()
    norm_query = query.replace(" ", "")

    # 1. 精确匹配 name
    exact = [d for d in all_devices if d.name == query]
    if exact:
        return exact[0]

    # 2. 房间+名称匹配（如"卧室空调" → room=卧室, name=空调）
    for d in all_devices:
        if norm_query == f"{d.room}{d.name}".replace(" ", ""):
            return d

    # 3. 名称包含匹配
    partial = [d for d in all_devices if norm_query in d.name.replace(" ", "") or d.name.replace(" ", "") in norm_query]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        return partial  # 多结果，交给调用方提示
    return None


# ============ 工具实现 ============
def tool_control_device(db: Session, args: dict) -> ToolResult:
    device_name = args.get("device_name", "")
    action = args.get("action")
    all_devices = crud.get_all_devices(db)

    matched = find_device(all_devices, device_name)

    if isinstance(matched, list):
        names = "、".join(f"{d.room}的{d.name}" for d in matched)
        return ToolResult(f"找到多个匹配设备：{names}，请明确指定哪一个", device_changed=False)

    if not matched:
        return ToolResult(f"抱歉，家里没有找到叫 {device_name} 的设备", device_changed=False)

    if action == "on":
        if matched.is_on:
            return ToolResult(f"{matched.room}的{matched.name} 已经是开启状态了", device_changed=False)
        crud.update_device_status(db, matched, is_on=True)
        broadcast({"type": "updated", "device": device_dict(matched)})
        return ToolResult(f"已为您开启 {matched.room}的{matched.name}", device_changed=True)
    elif action == "off":
        if not matched.is_on:
            return ToolResult(f"{matched.room}的{matched.name} 已经是关闭状态了", device_changed=False)
        crud.update_device_status(db, matched, is_on=False)
        broadcast({"type": "updated", "device": device_dict(matched)})
        return ToolResult(f"已为您关闭 {matched.room}的{matched.name}", device_changed=True)
    return ToolResult(f"未知的 action: {action}", device_changed=False)


def tool_add_device(db: Session, args: dict) -> ToolResult:
    device_name = args.get("device_name")
    room = args.get("room", "客厅")
    if not device_name:
        return ToolResult("设备名称不能为空", device_changed=False)
    new_dev = crud.create_new_device(db, schemas.DeviceCreate(name=device_name, room=room))
    broadcast({"type": "created", "device": device_dict(new_dev)})
    return ToolResult(f"好的，已为您在{room}录入新设备：{new_dev.name}", device_changed=True)


def tool_delete_device(db: Session, args: dict) -> ToolResult:
    device_name = args.get("device_name", "")
    all_devices = crud.get_all_devices(db)
    matched = find_device(all_devices, device_name)

    if isinstance(matched, list):
        names = "、".join(f"{d.room}的{d.name}" for d in matched)
        return ToolResult(f"找到多个匹配设备：{names}，请明确指定哪一个", device_changed=False)
    if not matched:
        return ToolResult(f"没找到叫 {device_name} 的设备，无法移除", device_changed=False)

    crud.delete_device(db, matched.device_id)
    broadcast({"type": "deleted", "device_id": matched.device_id})
    return ToolResult(f"好的，已为您移除设备：{matched.room}的{matched.name}", device_changed=True)


def tool_turn_off_all_devices(db: Session, args: dict) -> ToolResult:
    all_devices = crud.get_all_devices(db)
    turned_off = 0
    for d in all_devices:
        if d.is_on:
            crud.update_device_status(db, d, is_on=False)
            broadcast({"type": "updated", "device": device_dict(d)})
            turned_off += 1
    if turned_off > 0:
        return ToolResult(f"已为您关闭全屋 {turned_off} 个设备，安心休息吧！", device_changed=True)
    return ToolResult("目前家里没有开启的设备哦", device_changed=False)


def _get_outdoor_temp() -> int:
    """获取真实室外温度，失败则回退到模拟值。"""
    # 优先用环境变量配置的城市
    weather_api_key = os.getenv("WEATHER_API_KEY")
    city = os.getenv("WEATHER_CITY", "北京")
    if weather_api_key:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric&lang=zh_cn"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if resp.status_code == 200 and "main" in data:
                return int(data["main"]["temp"])
            logger.warning(f"天气 API 返回异常: {data}")
        except Exception as e:
            logger.warning(f"天气 API 调用失败，使用模拟值: {e}")
    # 回退：模拟夏天 28-38℃
    import random
    return random.randint(28, 38)


def tool_welcome_home_mode(db: Session, args: dict) -> ToolResult:
    eta_minutes = args.get("eta_minutes", 0)
    outdoor_temp = _get_outdoor_temp()

    if outdoor_temp > 30:
        target_temp, action_desc = 24, "制冷"
    elif outdoor_temp < 15:
        target_temp, action_desc = 26, "制热"
    else:
        target_temp, action_desc = 25, "舒适送风"

    all_devices = crud.get_all_devices(db)

    # 优先找客厅空调
    ac_device = next((d for d in all_devices if "空调" in d.name and "客厅" in d.room), None)
    if not ac_device:
        ac_device = next((d for d in all_devices if "空调" in d.name), None)

    # 优先找客厅灯
    light_device = next((d for d in all_devices if "灯" in d.name and "客厅" in d.room), None)
    if not light_device:
        light_device = next((d for d in all_devices if "灯" in d.name), None)

    actions_taken = []
    changed = False
    if ac_device and not ac_device.is_on:
        crud.update_device_status(db, ac_device, is_on=True)
        broadcast({"type": "updated", "device": device_dict(ac_device)})
        actions_taken.append(f"{ac_device.room}的{ac_device.name}已开启{action_desc}模式({target_temp}℃)")
        changed = True
    elif ac_device and ac_device.is_on:
        actions_taken.append(f"{ac_device.room}的{ac_device.name}已经在运行中")

    if light_device and not light_device.is_on:
        crud.update_device_status(db, light_device, is_on=True)
        broadcast({"type": "updated", "device": device_dict(light_device)})
        actions_taken.append(f"{light_device.room}的{light_device.name}已为您点亮")
        changed = True

    prefix = (f"收到！室外当前 {outdoor_temp}℃，已提前 {eta_minutes} 分钟为您准备回家环境。"
              if eta_minutes > 0
              else f"欢迎回家！室外当前 {outdoor_temp}℃，")
    suffix = "，家里已经舒服啦！" if eta_minutes == 0 else "。"
    return ToolResult(prefix + ", ".join(actions_taken) + suffix, device_changed=changed)


def tool_save_user_memory(db: Session, args: dict) -> ToolResult:
    key = args.get("key")
    value = args.get("value")
    if not key or not value:
        return ToolResult("记忆的 key 和 value 都不能为空", device_changed=False)
    try:
        crud.save_memory(db, key, value)
        return ToolResult(f"好的，我已经牢牢记住了（{key}: {value}）。", device_changed=False)
    except Exception as e:
        logger.exception("保存记忆失败")
        return ToolResult("抱歉，我的记忆系统出故障了，没能记住。", device_changed=False)


def tool_activate_scene(db: Session, args: dict) -> ToolResult:
    scene_name = args.get("scene_name", "").strip()
    if not scene_name:
        return ToolResult("场景名称不能为空", device_changed=False)

    scene = db.query(Scene).filter(Scene.name == scene_name).first()
    if not scene:
        all_scenes = crud.get_all_scenes(db)
        names = "、".join(s.name for s in all_scenes) if all_scenes else "（暂无场景）"
        return ToolResult(f"未找到场景 [{scene_name}]。当前可用场景：{names}", device_changed=False)

    actions = crud.get_scene_actions(scene)
    applied = 0
    changed = False
    for action in actions:
        device = crud.get_device_by_id(db, action["device_id"])
        if not device:
            continue
        target = action["is_on"]
        if device.is_on != target:
            crud.update_device_status(db, device, is_on=target)
            broadcast({"type": "updated", "device": device_dict(device)})
            changed = True
        applied += 1

    return ToolResult(
        f"已为您激活场景 [{scene.name}]，共应用 {applied} 个设备动作。",
        device_changed=changed,
    )


# ============ 工具注册表 ============
TOOL_REGISTRY: dict[str, Callable[[Session, dict], ToolResult]] = {
    "control_device": tool_control_device,
    "add_device": tool_add_device,
    "delete_device": tool_delete_device,
    "turn_off_all_devices": tool_turn_off_all_devices,
    "welcome_home_mode": tool_welcome_home_mode,
    "save_user_memory": tool_save_user_memory,
    "activate_scene": tool_activate_scene,
}


# ============ 依赖 ============
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ 限流（P1-5） ============
# 简单的内存级 IP 限流：每 IP 每分钟最多 20 次
# 生产环境多实例部署时建议换成 redis
from collections import defaultdict, deque

_rate_limit_store: dict[str, deque] = defaultdict(deque)
RATE_LIMIT_WINDOW = 60  # 秒
RATE_LIMIT_MAX = 20     # 次数


def check_rate_limit(client_ip: str) -> bool:
    """返回 True 表示放行，False 表示超限。"""
    now = datetime.now().timestamp()
    q = _rate_limit_store[client_ip]
    # 清掉窗口外的旧记录
    while q and q[0] < now - RATE_LIMIT_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT_MAX:
        return False
    q.append(now)
    return True


# ============ 主路由 ============
@router.post("", response_model=ChatResponse)
def chat_with_assistant(req: ChatRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        logger.warning(f"限流触发: ip={client_ip}")
        raise HTTPException(status_code=429, detail="请求太频繁，请稍后再试")

    try:
        client = get_client()

        # 1. 动态构造 System Prompt
        current_devices = crud.get_all_devices(db)
        device_list_str = ", ".join(
            [f"{d.room}的{d.name}(当前{'开启' if d.is_on else '关闭'})" for d in current_devices]
        )
        memories = crud.get_all_memories(db)
        memory_str = "; ".join([f"{m.key}: {m.value}" for m in memories])
        current_scenes = crud.get_all_scenes(db)
        scene_list_str = ", ".join([s.name for s in current_scenes]) if current_scenes else "暂无"

        system_prompt = f"""你是一个严格按指令行事的智能家居管家。
家中现有设备：[{device_list_str}]。
可用场景预设：[{scene_list_str}]。
你记得用户的偏好：[{memory_str if memory_str else '暂无'}]。

【绝对规则】：
1. 必须调用工具执行操作，不要只用嘴说！
2. 当用户提到某个房间的设备时，调用 control_device 的 device_name 参数必须严格包含房间名！例如用户说"关卧室空调"，你必须传"卧室空调"，绝不能只传"空调"！
3. 如果用户表达模糊，结合你的记忆推断他的意图。
4. 如果用户告诉你他的名字、偏好或要求你记住某事，请立刻调用 save_user_memory 工具！
5. 如果用户说要出门、睡觉，请调用 turn_off_all_devices。
6. 如果用户说快到家了，请调用 welcome_home_mode。
7. 如果用户提到某个场景（如"观影模式"、"用餐模式"），请调用 activate_scene。
8. 如果无关智能家居，礼貌闲聊。
"""

        # 2. 过滤历史中的 system 消息（P0-2）
        safe_history = [m for m in req.history if m.get("role") != "system"]

        chat_messages = [{"role": "system", "content": system_prompt}]
        chat_messages.extend(safe_history)
        chat_messages.append({"role": "user", "content": req.message})

        # 3. 第一次调用：决策是否需要工具
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=chat_messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        # 4. 不调用工具的直接回复
        if not message.tool_calls:
            return ChatResponse(reply=message.content or "", device_changed=False)

        # 5. 遍历所有 tool_calls（P0-1）
        any_device_changed = False
        tool_results_for_llm = []  # 喂给第二轮 LLM 的 tool 消息列表

        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            args_str = tool_call.function.arguments
            if isinstance(args_str, bytes):
                args_str = args_str.decode("utf-8")

            try:
                func_args = json.loads(args_str)
            except json.JSONDecodeError:
                logger.error(f"工具参数 JSON 解析失败: {func_name} -> {args_str}")
                result = ToolResult("工具参数格式错误", device_changed=False)
            else:
                logger.info(f"工具调用: {func_name} args={func_args}")
                handler = TOOL_REGISTRY.get(func_name)
                if handler is None:
                    logger.error(f"未知工具: {func_name}")
                    result = ToolResult(f"未知工具: {func_name}", device_changed=False)
                else:
                    try:
                        result = handler(db, func_args)
                    except Exception as e:
                        logger.exception(f"工具执行异常: {func_name}")
                        result = ToolResult("工具执行出错", device_changed=False)

            if result.device_changed:
                any_device_changed = True
            tool_results_for_llm.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.message,
                }
            )

        # 6. 第二次调用：让 LLM 把所有工具结果汇总成自然语言
        second_messages = [
            {"role": "system", "content": system_prompt},
            *safe_history,
            {"role": "user", "content": req.message},
            message,
            *tool_results_for_llm,
        ]
        second_response = client.chat.completions.create(
            model="glm-4-flash",
            messages=second_messages,
        )
        reply = second_response.choices[0].message.content or ""
        return ChatResponse(reply=reply, device_changed=any_device_changed)

    except HTTPException:
        raise
    except Exception as e:
        # P1-6：错误脱敏，日志记完整堆栈，前端只看到通用提示
        logger.exception("AI 调用失败")
        raise HTTPException(status_code=500, detail="AI 助手开小差了，请稍后再试")
