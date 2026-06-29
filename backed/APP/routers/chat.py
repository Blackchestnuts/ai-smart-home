from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
from database import SessionLocal
from app import crud
from pydantic import BaseModel
import json
from app import schemas

router = APIRouter(prefix="/api/chat", tags=["AI 助手"])

# 🌟 1. 配置大模型客户端 (确保这里用的是你充好值的 DeepSeek 或其他模型)
client = OpenAI(
    api_key="34e9b194a77c45d0b58a8a7ccd862155.nO1dhiCGSijRAfBb",  # 替换成你自己的 API Key！如果是 Ollama 填 "ollama"
    base_url="https://open.bigmodel.cn/api/paas/v4" # 通义千问接口，也可换成 DeepSeek 的
)

class ChatRequest(BaseModel):
    message: str

# 🌟 2. 丰富工具库：不仅能让它开关，还要让它能录入和删除！
tools = [
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": "控制智能家居设备的开关状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {"type": "string", "description": "设备名称，如'空调'、'台灯'"},
                    "action": {"type": "string", "enum": ["on", "off"], "description": "动作，开=on，关=off"}
                },
                "required": ["device_name", "action"]
            }
        }
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
                    "room": {"type": "string", "enum": ["客厅", "卧室", "厨房", "书房"], "description": "设备所在的房间"}
                },
                "required": ["device_name", "room"]
            }
        }
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
                "required": ["device_name"]
            }
        }
    },
     # 🌟 新增：一键全关工具
    {
        "type": "function",
        "function": {
            "name": "turn_off_all_devices",
            "description": "当用户要求关闭所有设备、离家模式、晚安模式、一键全关时调用",
            "parameters": {
                "type": "object",
                "properties": {}, # 不需要参数，全关！
                "required": []
            }
        }
    },
     # 🌟 新增：回家模式工具
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
                        "description": "用户预计还有几分钟到家，如果是刚说'我回来了'则为0"
                    }
                },
                "required": ["eta_minutes"]
            }
        }
    },
      # 🌟 新增：记忆存储工具
    {
        "type": "function",
        "function": {
            "name": "save_user_memory",
            "description": "当用户告诉你他的名字、偏好、习惯，或者要求你记住某件事时调用此工具保存。",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆的类别，如'user_name'(用户名)、'preferred_temp'(偏好温度)、'habit'(习惯)"},
                    "value": {"type": "string", "description": "记忆的具体内容，如'张三'、'26度'、'喜欢睡前关灯'"}
                },
                "required": ["key", "value"]
            }
        }
    }
]
import random

# 🌟 模拟获取当前室外温度的函数 (真实场景应调用和风天气等API)
def get_simulated_outdoor_temp():
    # 模拟夏天高温 28-38度
    return random.randint(28, 38)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("")
def chat_with_assistant(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        # 🌟 3. 核心：动态生成 System Prompt (给 AI 看的员工手册)
        # 每次对话前，先去数据库查一下现在家里有什么设备，告诉 AI！
        current_devices = crud.get_all_devices(db)
        device_list_str = ", ".join([f"{d.room}的{d.name}(当前{'开启' if d.is_on else '关闭'})" for d in current_devices])
        
        # 🌟 读取 AI 的长期记忆
        memories = crud.get_all_memories(db)
        memory_str = "; ".join([f"{m.key}: {m.value}" for m in memories])
        
        system_prompt = f"""你是一个极其智能且贴心的智能家居管家。
目前家中已有以下设备：[{device_list_str}]。
你记得关于用户的以下信息：[{memory_str if memory_str else '暂无'}]。
你的原则：
1. 优先使用工具来执行操作，不要只是嘴上说。
2. 如果用户表达模糊，结合你的记忆推断他的意图。
3. 🌟 如果用户告诉你他的名字、偏好或要求你记住某事，请立刻调用 save_user_memory 工具！
4. 如果用户说要出门、睡觉，请调用 turn_off_all_devices。
5. 如果用户说快到家了，请调用 welcome_home_mode。
6. 如果无关智能家居，礼貌闲聊。"""
        # 4. 第一次请求：带上说明书和工具箱
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ],
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # 5. 检查是否需要调用工具
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            result_msg = ""

            # 🌟 6. 根据不同的工具名，执行不同的后端逻辑
            if func_name == "control_device":
                device_name = func_args.get("device_name")
                action = func_args.get("action")
                all_devices = crud.get_all_devices(db)
                target_device = next((d for d in all_devices if device_name in d.name), None)
                
                if target_device:
                    if action == "on" and not target_device.is_on:
                        crud.update_device_status(db, target_device, is_on=True)
                        result_msg = f"已为您开启 {target_device.room}的{target_device.name}"
                    elif action == "off" and target_device.is_on:
                        crud.update_device_status(db, target_device, is_on=False)
                        result_msg = f"已为您关闭 {target_device.room}的{target_device.name}"
                    else:
                        result_msg = f"{target_device.name} 已经是目标状态了"
                else:
                    result_msg = f"抱歉，家里没有找到叫 {device_name} 的设备"

            elif func_name == "add_device":
                device_name = func_args.get("device_name")
                room = func_args.get("room", "客厅")
                # 调用之前写好的 CRUD
                new_dev = crud.create_new_device(db, schemas.DeviceCreate(name=device_name, room=room))
                result_msg = f"好的，已为您在{room}录入新设备：{new_dev.name}"

            elif func_name == "delete_device":
                device_name = func_args.get("device_name")
                all_devices = crud.get_all_devices(db)
                target_device = next((d for d in all_devices if device_name in d.name), None)
                
                if target_device:
                    crud.delete_device(db, target_device.device_id)
                    result_msg = f"好的，已为您移除设备：{target_device.name}"
                else:
                    result_msg = f"没找到叫 {device_name} 的设备，无法移除"

              # 🌟 新增：处理一键全关逻辑
            elif func_name == "turn_off_all_devices":
                all_devices = crud.get_all_devices(db)
                turned_off_count = 0
                # 遍历所有设备，如果是开着的，就关掉
                for d in all_devices:
                    if d.is_on:
                        crud.update_device_status(db, d, is_on=False)
                        turned_off_count += 1
                
                if turned_off_count > 0:
                    result_msg = f"已为您关闭全屋 {turned_off_count} 个设备，安心休息吧！"
                else:
                    result_msg = "目前家里没有开启的设备哦"
            
             # 🌟 修正版：处理回家模式逻辑
            elif func_name == "welcome_home_mode":
                eta_minutes = func_args.get("eta_minutes", 0)
                outdoor_temp = get_simulated_outdoor_temp()
                
                # 模拟智能温控逻辑
                if outdoor_temp > 30:
                    target_temp = 24
                    action_desc = "制冷"
                elif outdoor_temp < 15:
                    target_temp = 26
                    action_desc = "制热"
                else:
                    target_temp = 25
                    action_desc = "舒适送风"

                # 寻找家里的空调和灯
                all_devices = crud.get_all_devices(db)
                ac_device = next((d for d in all_devices if "空调" in d.name), None)
                light_device = next((d for d in all_devices if "灯" in d.name), None)
                
                actions_taken = [] # 记录执行了哪些动作
                if ac_device and not ac_device.is_on:
                    crud.update_device_status(db, ac_device, is_on=True)
                    actions_taken.append(f"空调已开启{action_desc}模式({target_temp}℃)")
                elif ac_device and ac_device.is_on:
                    actions_taken.append(f"空调已经在运行中")
                    
                if light_device and not light_device.is_on:
                    crud.update_device_status(db, light_device, is_on=True)
                    actions_taken.append("灯已为您点亮")

                # 根据到家时间生成不同的反馈
                if eta_minutes > 0:
                    result_msg = f"收到！室外当前 {outdoor_temp}℃，已提前 {eta_minutes} 分钟为您准备回家环境。{', '.join(actions_taken)}。"
                else:
                    # 🌟 修复：把之前的 actions_done 改成 actions_taken
                    result_msg = f"欢迎回家！室外当前 {outdoor_temp}℃，{', '.join(actions_taken)}，家里已经舒服啦！"

            # 7. 把执行结果喂给大模型，让它说人话
            second_response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message},
                    message,
                    {"role": "tool", "tool_call_id": tool_call.id, "content": result_msg}
                ]
            )
            return {"reply": second_response.choices[0].message.content}
        
        # 不调用工具的直接回复
        return {"reply": message.content}

    except Exception as e:
        print(f"AI 调用出错: {e}")
        raise HTTPException(status_code=500, detail=f"AI 助手开小差了: {str(e)}")