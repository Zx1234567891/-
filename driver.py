import serial
import time
import struct
from pid import PID
def configure_serial():
    """配置串口参数"""
    # 修改以下参数：
    # port: 串口设备路径，如'/dev/ttyUSB0'
    # baudrate: 波特率，如100000
    port = '/dev/ttyCH343USB0'  # 修改此处设置串口设备
    baudrate = 1000000      # 修改此处设置波特率
    
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        timeout=1
    )
class ServoDriver:
    def __init__(self, timeout=0.1):
        self.ser = configure_serial()
        self.ser.timeout = timeout

    def send_packet(self, servo_id, instruction, params=[]):
        length = len(params) + 2
        packet = [0xFF, 0xFF, servo_id, length, instruction] + params
        checksum = (~sum(packet[2:]) & 0xFF)
        packet.append(checksum)
        data_bytes = bytes(packet)
        try:
            
            self.ser.write(data_bytes)
           
        except KeyboardInterrupt:
            print("\n程序终止")
    



    def ping(self, servo_id):
        self.send_packet(servo_id, 0x01)
    def read_data(self, servo_id, address, length):
        """
        读取舵机内存数据
        :param servo_id: 舵机ID
        :param address: 读取起始地址
        :param length: 读取数据长度
        """
        self.send_packet(servo_id, 0x02, [address, length])
        return self.read_response()
    
    def write_data(self, servo_id, address, data):
        """
        写入舵机内存数据
        :param servo_id: 舵机ID
        :param address: 写入起始地址
        :param data: 数据（列表）
        """
        self.send_packet(servo_id, 0x03, [address] + data)
    
    def reg_write(self, servo_id, address, data):
        """
        异步写入指令
        """
        self.send_packet(servo_id, 0x04, [address] + data)
    
    def action(self):
        """
        执行异步写入
        """         
        self.send_packet(0xFE, 0x05)
    
    def sync_write(self, address, length, servo_data):
        """
        同步写入多个舵机
        :param address: 写入起始地址
        :param length: 写入数据长度
        :param servo_data: 形如 [(id, [data...]), (id, [data...])]
        """
        params = [address, length]
        for sid, data in servo_data:
            params.append(sid)
            params.extend(data)
        self.send_packet(0xFE, 0x83, params)
    
    def sync_read(self, address, length, servo_ids):
        """
        同步读取多个舵机
        """
        self.send_packet(0xFE, 0x82, [address, length] + servo_ids)
        return self.read_response()
    
    def recovery(self, servo_id):
        """
        恢复出厂设置
        """
        self.send_packet(servo_id, 0x06)
        return self.read_response()
    
    def reset(self, servo_id):
        """
        复位舵机
        """
        self.send_packet(servo_id, 0x0A)
        return self.read_response()

    def read_response(self):
        header = self.ser.read(2)
        if header != b'\xFF\xFF':
            return None
        data = self.ser.read(4)
        if len(data) < 4:
            return None
        _, _, error = struct.unpack('BBB', data[:3])
        return error

    def move_degree(self, servo_id, degree, time, speed):
        max_degree=2248
        min_degree=1848
        
        params = [0x2A, degree & 0xFF, degree >> 8, time & 0xFF, time >> 8, speed & 0xFF, speed >> 8]
        self.send_packet(servo_id, 0x03, params)
        
        return self.read_response()
    

if __name__ == '__main__':
    driver = ServoDriver()
    max_degree=2248
    min_degree=1848
    error = driver.move_degree(1, 2100, 0, 100)
    print(error)