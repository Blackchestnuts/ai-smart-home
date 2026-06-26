class DeviceAlreadyOnError(Exception):
    """自定义异常类：设备已开启，不能再开启"""
    pass

class DeviceAlreadyOffError(Exception):
    """自定义异常类：设备已关闭，不能再关闭"""
    pass

class Device:
    def __init__(self,device_id: int,name: str, room: str):
        """
        初始化一个智能家居设备对象
        ：param device_id: 设备ID
        ：param name: 设备名称(如：客厅空调)
        ：param room: 设备所在房间(如：客厅)
        """
        self.device_id = device_id
        self.name = name
        self.room = room
        self.is_on = False  # 设备初始状态为关闭

    def turn_on(self) -> bool:
        """开启设备
        :return: 如果设备成功开启，返回当前状态；如果设备已经开启，抛出DeviceAlreadyOnError异常
        :raises DeviceAlreadyOnError: 如果设备已经开启，抛出该异常
        """
        if self.is_on:
            raise DeviceAlreadyOnError(f"设备 [{self.name}] 已经开启，无需重复操作！")
        
        self.is_on = True
        print(f"√[系统日志]设备 [{self.name}] 已开启。")
        return self.is_on
    
    def turn_off(self) -> bool:
        """关闭设备
        ：return:如果设备成功关闭，返回当前状态；如果设备已经关闭，抛出DeviceAlreadyOffError异常
        ：raises DeviceAlreadyOffError: 如果设备已经关闭，抛出该异常
        """
        if not self.is_on:
            raise DeviceAlreadyOffError(f"设备 [{self.name}] 已经关闭，无需重复操作！")
        
        self.is_on = False
        print(f"×[系统日志]设备 [{self.name}] 已关闭。")
        return self.is_on

    def get_status(self) -> str:
        """获取设备状态
        ：return:返回设备当前状态描述"""
        status_text = "开启" if self.is_on else "关闭"
        return f"{self.room}的{self.name}当前状态:{status_text}"
    
    