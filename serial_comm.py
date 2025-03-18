import serial
import serial.tools.list_ports
import time

def list_serial_ports():
    """列出所有可用串口"""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("没有找到可用串口")
        return None
    
    print("可用串口列表：")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
    
    while True:
        try:
            choice = int(input("请选择要使用的串口编号："))
            if 1 <= choice <= len(ports):
                return ports[choice-1].device
            print("输入错误，请输入有效编号")
        except ValueError:
            print("请输入数字")

def configure_serial():
    """配置串口参数"""
    # 修改以下参数：
    # port: 串口设备路径，如'/dev/ttyUSB0'
    # baudrate: 波特率，如100000
    port = '/dev/ttyACM1'  # 修改此处设置串口设备
    baudrate = 1000000      # 修改此处设置波特率
    
    return serial.Serial(
        port=port,
        baudrate=baudrate,
        timeout=1
    )
tip=0xff
def send_data(ser):
    """发送数据"""
    # 16位int数组，每个元素是0-255的整数
    data_list = [
        0xFF,  # 帧头
        0xFF,  # 帧头
        0x01,  # 设备ID
        0x09,  # 指令长度
        0x03,  # 指令类型
        0x2A,  # 参数1
        0x00,  # 参数2
        0x08,  # 参数3
        0x00,  # 参数4
        0x00,  # 参数5
        0xE8,  # 参数6
        0x03,  # 参数7
        0xD5,  # 校验和
        0x00,  # 保留
        0x00,  # 保留
        0x00   # 保留
    ]
    
    loop = True      # 修改此处设置是否循环发送
    interval = 1.0   # 修改此处设置发送间隔时间
    
    try:
        while True:
            # 将int数组转换为bytes
            data_bytes = bytes(data_list)
            print(f"发送数据：{data_bytes.hex()}")
            ser.write(data_bytes)
            time.sleep(interval)
            
            if not loop:
                break
    except KeyboardInterrupt:
        print("\n程序终止")
    finally:
        ser.close()


if __name__ == "__main__":
    ser = configure_serial()
    if ser:
        send_data(ser)
