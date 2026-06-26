import pytest
from home_device import Device,DeviceAlreadyOffError,DeviceAlreadyOnError

@pytest.fixture
def living_room_light():
    """创建一个客厅灯设备实例"""
    return Device(device_id=1, name="客厅灯", room="客厅")

def test_device_turn_on(living_room_light):
    """测试设备开启功能"""
    # 测试用例:验证设备初始状态应为关闭
    assert living_room_light.is_on == False

def test_turn_on_device(living_room_light):
    """测试用例2：正常流 - 开启设备"""
    result = living_room_light.turn_on()
    assert result == True
    assert living_room_light.is_on == True

def test_turn_on_device_already_on(living_room_light):
    """测试用例3：正常流 - 关闭设备"""
    living_room_light.turn_on() #先开启设备
    result = living_room_light.turn_off() #再关闭
    assert result == False
    assert living_room_light.is_on == False

def test_turn_on_already_on_device(living_room_light):
    """测试用例4：异常流 - 重复开启设备应抛出异常"""
    living_room_light.turn_on()  # 先开启设备
    with pytest.raises(DeviceAlreadyOnError) as exc_info:
        living_room_light.turn_on()  # 再尝试开启设备，应该抛出异常
    assert "已经开启，无需重复操作！" in str(exc_info.value)

def test_turn_off_already_off_device(living_room_light):
    """测试用例5：异常流 - 重复关闭设备应抛出异常"""
    with pytest.raises(DeviceAlreadyOffError) as exc_info:
        living_room_light.turn_off()  # 尝试关闭设备，应该抛出异常
    assert "已经关闭，无需重复操作！" in str(exc_info.value)