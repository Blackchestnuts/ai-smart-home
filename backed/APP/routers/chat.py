from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
from database import SessionLocal
from app import crud, schemas
from pydantic import BaseModel
import json
import random
import os
from dotenv import load_dotenv

load_dotenv() # 确保在文件顶部调用

router = APIRouter(prefix="/api/chat", tags=["AI 助手"])
#配置大模型API客户端，使用环境变量中的API Key
client = OpenAI(
    api_key=os.getenv("GLM_API_KEY"), # 🌟 从环境变量读取
    base_url="https://open.bigmodel.cn/api/paas/v4"
)

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = [] # 🌟 新增：接收前端传来的历史记录，默认为空

# 🌟 2. 丰富工具库
tools = [
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": "控制智能家居设备的开关状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_name": {"type": "string", "description": "设备的完整名称，必须包含房间信息！例如'卧室空调'、'客厅台灯'，绝对不能只写'空调'或'台灯'！"},
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
    {
        "type": "function",
        "function": {
            "name": "turn_off_all_devices",
            "description": "当用户要求关闭所有设备、离家模式、晚安模式、一键全关时调用",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
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
                        "description": "用户预计还有几分钟到家，如果是刚说'我回来了'则为0"
                    }
                },
                "required": ["eta_minutes"]
            }
        }
    },
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

# 🌟 模拟获取当前室外温度的函数
def get_simulated_outdoor_temp():
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
        # 🌟 3. 核心：动态生成 System Prompt
        current_devices = crud.get_all_devices(db)
        device_list_str = ", ".join([f"{d.room}的{d.name}(当前{'开启' if d.is_on else '关闭'})" for d in current_devices])
        
        # 🌟 读取 AI 的长期记忆
        memories = crud.get_all_memories(db)
        memory_str = "; ".join([f"{m.key}: {m.value}" for m in memories])
        
        system_prompt = f"""你是一个严格按指令行事的智能家居管家。
家中现有设备：[{device_list_str}]。
你记得用户的偏好：[{memory_str if memory_str else '暂无'}]。

【绝对规则】：
1. 必须调用工具执行操作，不要只用嘴说！
2. 🌟【极度重要-设备名规则】：当用户提到某个房间的设备时，调用 control_device 的 device_name 参数必须严格包含房间名！例如用户说"关卧室空调"，你必须传"卧室空调"，绝不能只传"空调"！
3. 如果用户表达模糊，结合你的记忆推断他的意图。
4. 如果用户告诉你他的名字、偏好或要求你记住某事，请立刻调用 save_user_memory 工具！
5. 如果用户说要出门、睡觉，请调用 turn_off_all_devices。
6. 如果用户说快到家了，请调用 welcome_home_mode。
7. 如果无关智能家居，礼貌闲聊。
"""
                # 4. 第一次请求
        # 🌟 构造完整的消息列表：系统提示词 + 历史记录 + 当前用户发言
        chat_messages = [
            {"role": "system", "content": system_prompt}
        ]
        # 把前端传来的历史记录塞进去
        chat_messages.extend(req.history)
        # 加上用户当前说的话
        chat_messages.append({"role": "user", "content": req.message})

        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=chat_messages, # 🌟 使用构造好的完整列表
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message
        
        # 🌟 透视大模型的原始回复
        # print("===🤖 AI原始回复开始===")
        # print(f"内容(content): {message.content}")
        # print(f"工具调用(tool_calls): {message.tool_calls}")
        # print("===🤖 AI原始回复结束===")

        # 5. 检查是否需要调用工具
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            func_name = tool_call.function.name
            args_str = tool_call.function.arguments
            if isinstance(args_str, bytes):
                args_str = args_str.decode('utf-8')
            func_args = json.loads(args_str)
            
            # result_msg = ""
            print(f"🤖 AI决定调用工具: {func_name}, 参数: {func_args}")

            # 🌟 6. 根据不同的工具名，执行不同的后端逻辑
            if func_name == "control_device":
                device_name = func_args.get("device_name")
                action = func_args.get("action")
                all_devices = crud.get_all_devices(db)
                
                # 🌟 优化匹配逻辑：优先精确匹配，再模糊匹配
                target_device = None
                
                # 1. 先尝试完全匹配 (比如传的是 "卧室空调"，库里有 "卧室空调")
                for d in all_devices:
                    if d.name == device_name:
                        target_device = d
                        break
                
                # 2. 如果没完全匹配上，再尝试包含匹配 (兼容 AI 传 "卧室 空格 空调" 等情况)
                if not target_device:
                    for d in all_devices:
                        # 去掉空格后比较，增加容错
                        if device_name.replace(" ", "") in d.name.replace(" ", "") or d.name.replace(" ", "") in device_name.replace(" ", ""):
                            target_device = d
                            break
                
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
                new_dev = crud.create_new_device(db, schemas.DeviceCreate(name=device_name, room=room))
                result_msg = f"好的，已为您在{room}录入新设备：{new_dev.name}"

            elif func_name == "delete_device":
                device_name = func_args.get("device_name")
                all_devices = crud.get_all_devices(db)
                target_device = next((d for d in all_devices if device_name in d.name or d.name in device_name), None)
                
                if target_device:
                    crud.delete_device(db, target_device.device_id)
                    result_msg = f"好的，已为您移除设备：{target_device.name}"
                else:
                    result_msg = f"没找到叫 {device_name} 的设备，无法移除"

            elif func_name == "turn_off_all_devices":
                all_devices = crud.get_all_devices(db)
                turned_off_count = 0
                for d in all_devices:
                    if d.is_on:
                        crud.update_device_status(db, d, is_on=False)
                        turned_off_count += 1
                
                if turned_off_count > 0:
                    result_msg = f"已为您关闭全屋 {turned_off_count} 个设备，安心休息吧！"
                else:
                    result_msg = "目前家里没有开启的设备哦"
            
            elif func_name == "welcome_home_mode":
                eta_minutes = func_args.get("eta_minutes", 0)
                outdoor_temp = get_simulated_outdoor_temp()
                
                if outdoor_temp > 30:
                    target_temp = 24
                    action_desc = "制冷"
                elif outdoor_temp < 15:
                    target_temp = 26
                    action_desc = "制热"
                else:
                    target_temp = 25
                    action_desc = "舒适送风"

                all_devices = crud.get_all_devices(db)
                
                # 🌟 修复：优先查找客厅的空调
                ac_device = next((d for d in all_devices if "空调" in d.name and "客厅" in d.room), None)
                # 如果客厅没空调，再退而求其次找其他房间的
                if not ac_device:
                    ac_device = next((d for d in all_devices if "空调" in d.name), None)

                # 🌟 修复：优先查找客厅的灯
                light_device = next((d for d in all_devices if "灯" in d.name and "客厅" in d.room), None)
                if not light_device:
                    light_device = next((d for d in all_devices if "灯" in d.name), None)
                
                actions_taken = []
                if ac_device and not ac_device.is_on:
                    crud.update_device_status(db, ac_device, is_on=True)
                    actions_taken.append(f"{ac_device.room}的{ac_device.name}已开启{action_desc}模式({target_temp}℃)")
                elif ac_device and ac_device.is_on:
                    actions_taken.append(f"{ac_device.room}的{ac_device.name}已经在运行中")
                    
                if light_device and not light_device.is_on:
                    crud.update_device_status(db, light_device, is_on=True)
                    actions_taken.append(f"{light_device.room}的{light_device.name}已为您点亮")

                if eta_minutes > 0:
                    result_msg = f"收到！室外当前 {outdoor_temp}℃，已提前 {eta_minutes} 分钟为您准备回家环境。{', '.join(actions_taken)}。"
                else:
                    result_msg = f"欢迎回家！室外当前 {outdoor_temp}℃，{', '.join(actions_taken)}，家里已经舒服啦！"

            # 🌟🌟🌟 修复核心：处理记忆保存逻辑 🌟🌟🌟
            elif func_name == "save_user_memory":
                key = func_args.get("key")
                value = func_args.get("value")
                
                # print(f"💾 [调试] 准备写入数据库: key={key}, value={value}")
                
                try:
                    crud.save_memory(db, key, value)
                    # print("✅ [调试] 数据库写入成功！")
                    result_msg = f"好的，我已经牢牢记住了（{key}: {value}）。"
                except Exception as e:
                    # print(f"❌ [错误] 数据库写入失败，报错内容: {e}")
                    result_msg = f"抱歉，我的记忆系统出故障了，没能记住。"

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
        print(f"❌ [全局错误] AI 调用出错: {e}")
        raise HTTPException(status_code=500, detail=f"AI 助手开小差了: {str(e)}")