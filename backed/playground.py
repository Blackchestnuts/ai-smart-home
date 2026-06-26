from home_device import Device, DeviceAlreadyOnError
#定义两个设备
light1 = Device(device_id=1, name="客厅灯", room="客厅")
light2 = Device(device_id=2, name="卧室灯", room="卧室")
print("===智能家居设备操作演示===")
#操作：1.获取设备状态 
print(light1.get_status())
print(light2.get_status())
#2.开启设备 
light1.turn_on()
light2.turn_on()
print(light1.get_status())
print(light2.get_status())
#3.再次尝试开启已经开启的设备，捕获异常
try:
    light1.turn_on()  # 尝试再次开启已经开启的设备
except DeviceAlreadyOnError as e:
    print(f"错误: {e}")

try:
    light2.turn_on()  # 尝试再次开启已经开启的设备
except DeviceAlreadyOnError as e:
    print(f"错误: {e}")