"""SSE 事件广播器。

被 devices.py 和 chat.py 共享。当设备状态变化时，所有 SSE 订阅者
都能收到推送，无需前端轮询。
"""
import asyncio
import json
from collections import deque
from typing import Any

# 所有活跃的 SSE 订阅者队列
_SUBSCRIBERS: list[asyncio.Queue] = []

# 最近 50 条事件，供新连接回放
_RECENT_EVENTS: deque = deque(maxlen=50)


def subscribe() -> asyncio.Queue:
    """注册一个新的 SSE 订阅者，返回它的事件队列。"""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _SUBSCRIBERS.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """取消订阅。"""
    if q in _SUBSCRIBERS:
        _SUBSCRIBERS.remove(q)


def get_recent_events() -> list[dict]:
    """获取历史事件用于回放。"""
    return list(_RECENT_EVENTS)


def broadcast(event: dict[str, Any]) -> None:
    """向所有订阅者推送一条事件。慢消费者直接丢消息。"""
    _RECENT_EVENTS.append(event)
    for q in list(_SUBSCRIBERS):  # 复制一份避免迭代中修改
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


def device_dict(d) -> dict:
    """把 ORM 设备对象转成 dict（用于 SSE 事件）。"""
    return {
        "device_id": d.device_id,
        "name": d.name,
        "room": d.room,
        "is_on": d.is_on,
    }


def sse_format(event: dict) -> str:
    """格式化为 SSE 数据帧。"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
