import cv2
import time
import math
from driver import ServoDriver
from pid import PID
from data_logger import DataLogger


# 全局变量存储上一帧信息
prev_x = None
prev_y = None
prev_time = None
count=0
# 初始化驱动和PID控制器
driver = ServoDriver()
degree_pid = PID(Kp=0.22, Ki=0, Kd=0.01,lim=10000)  # 速度-角度PID参数
pos_pid = PID(Kp=4, Ki=0, Kd=0.6,lim=30)  # 位置-速度PID参数

# 微调PID控制器 - 更温和的参数用于精确定位
fine_tune_pid = PID(Kp=0.05, Ki=0, Kd=0.005, lim=5)  # 微调PID参数

tar_pos = 0

# 初始化状态变量
status = False
fine_tune_status = False
precision_mode_count = 0  # 记录进入精准模式的次数
precision_mode_locked = False  # 是否锁定在精准模式

# 初始化数据记录器
data_logger = DataLogger()

def list_cameras():
    """列出可用摄像头"""
    for i in range(3):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"找到摄像头 #{i}")
            cap.release()

def capture_test_image():
    """捕获测试图像"""
    # 声明使用全局变量
    global prev_x, prev_y, prev_time, status, count, fine_tune_status
    global precision_mode_count, precision_mode_locked
    
    # 尝试打开所有可能的摄像头
    for i in range(4):  # 尝试0-3号摄像头
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print(f"成功打开摄像头 #{i}")
            # 设置摄像头分辨率
            break

    driver.move_degree(1, 2100, 0, 100)  # 控制ID为1的舵机
    time.sleep(0.5)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法获取画面")
            break
        
        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 定义红色的HSV范围
        lower_red = (0, 120, 70)
        upper_red = (10, 255, 255)
        lower_red2 = (170, 120, 70)
        upper_red2 = (180, 255, 255)
        
        # 创建红色掩码
        mask1 = cv2.inRange(hsv, lower_red, upper_red)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 0:
            # 找到最大轮廓
            c = max(contours, key=cv2.contourArea)
            
            # 获取最小外接圆
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            
            if radius > 10:  # 过滤小噪点

                scale = 1
                cv2.circle(frame, (int(x*scale), int(y*scale)), int(radius*scale), (0, 255, 255), 2)
                cv2.circle(frame, (int(x*scale), int(y*scale)), 5*scale, (0, 0, 255), -1)
                
                # 计算速度
                global prev_x, prev_y, prev_time
                current_time = time.time()
                
                if prev_x is not None and prev_y is not None:
                    # 计算位移
                    dx = x - prev_x
                    #dy = y - prev_y
                    #distance = math.sqrt(dx*dx + dy*dy)
                    distance=dx
                    # 计算时间差
                    dt = current_time - prev_time
                    
                    # 计算速度 (像素/秒)
                    cur_speed = distance / dt if dt > 0 else 0
                    
                    # 显示速度和坐标（坐标保持原始值）
                    cv2.putText(frame, f"Ball: ({int(x)}, {int(y)})", 
                              (10*20, 60*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                    cv2.putText(frame, f"Speed: {cur_speed:.1f} px/s", 
                              (10*20, 90*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                    
                    cur_pos=x-335
                    print(f'cur_pos:{cur_pos}')
                    #位置闭环控制
                    tar_speed=pos_pid.update(tar_pos,cur_pos,dt)
                    print(tar_speed)
                    
                    # 角度闭环控制
                    tar_degree = degree_pid.update(tar_speed, cur_speed, dt)
                    
                    # 记录数据，包括tar_degree
                    data_logger.log_data(tar_speed, cur_pos, cur_speed, tar_degree)
                    
                    # 将控制输出映射到舵机角度
                    servo_angle = 2100 +int(tar_degree )  # 2048为中心位置
                    
                    servo_angle = max(2000, min(2200, servo_angle))  # 限制在安全范围内
                    servo_angle_tiny = 2100 +int(tar_degree/10 )
                    servo_angle_tiny = max(2050, min(2150, servo_angle_tiny))
                    driver.move_degree(1, servo_angle, 0, 500)  # 限制在安全范围内
                    print(f'servo_angle:{servo_angle}')
                    
                    # 计算当前误差
                    current_error = abs(tar_pos-cur_pos)
                    
                    # 检测是否应该退出精准模式
                    if precision_mode_locked and current_error > 15:
                        print("######### 误差过大，退出锁定精准模式 #########")
                        precision_mode_locked = False
                        precision_mode_count = 0
                        status = False
                    
                    # 检测是否接近目标位置（速度小，位置接近）
                    if not precision_mode_locked:  # 只有在未锁定精准模式时才检测是否进入精准模式
                        if((abs(cur_speed)<50) and current_error<10):
                            status=True
                            precision_mode_count += 1  # 增加精准模式计数
                            print(f"进入精准模式第 {precision_mode_count} 次")
                            
                            # 如果进入精准模式次数达到10次，锁定精准模式
                            if precision_mode_count >= 10:
                                precision_mode_locked = True
                                print("######### 已锁定精准模式 #########")
                        
                        if((abs(cur_speed)>50) or current_error>10):
                            status=False
                            # 如果未锁定，则重置计数
                            if not precision_mode_locked:
                                precision_mode_count = 0
                    
                    # 显示当前模式和锁定状态
                    mode_text = "精准模式" if status else "跟踪模式"
                    lock_text = "已锁定" if precision_mode_locked else "未锁定"
                    cv2.putText(frame, f"模式: {mode_text} ({lock_text})", 
                              (10*20, 120*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                    cv2.putText(frame, f"误差: {current_error:.2f}", 
                              (10*20, 150*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                    
                    if(status):
                        print("######### 进入精确定位模式 #########")
                        # 使用微调PID进行更精确的控制
                        fine_tune_degree = fine_tune_pid.update(tar_pos, cur_pos, dt)
                        fine_tune_angle = 2100 + int(fine_tune_degree)
                        fine_tune_angle = max(2050, min(2150, fine_tune_angle))  # 限制在更小的范围内
                        
                        print(f'微调角度: {fine_tune_angle}, 误差: {tar_pos-cur_pos:.2f}')
                        driver.move_degree(1, fine_tune_angle, 0, 200)  # 使用更低的速度控制舵机
                        count += 1
                        fine_tune_status=True
                        if(count>10 and fine_tune_status==True and abs(cur_speed)<10):
                            
                            print("######### 精确定位完成 #########")
                            driver.move_degree(1, 2100, 0, 100)  # 使用更低的速度控制舵机
                            print(f'误差: {tar_pos-cur_pos:.2f}')
                    else:
                        # 使用常规PID控制
                        driver.move_degree(1, servo_angle, 0, 500)
                    
                    
                
                # 更新上一帧信息
                prev_x = x
                prev_y = y
                prev_time = current_time
        
        # 创建可调整大小的窗口并显示当前帧
        cv2.namedWindow('Camera Test', cv2.WINDOW_NORMAL)
        cv2.imshow('Camera Test', frame)
        
        # 设置窗口大小调整回调
        def on_resize(event, x, y, flags, param):
            if event == cv2.EVENT_WINDOW_RESIZED:
                # 重新绘制内容以适应新窗口大小
                cv2.imshow('Camera Test', frame)
        
        cv2.setMouseCallback('Camera Test', on_resize)
        
        ## 处理按键输入
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # 退出
            break
        #elif key == ord('s'):  # 保存图像
        #    cv2.imwrite('test_image.jpg', frame)
        #    print("已保存当前帧为 test_image.jpg")
        #    time.sleep(1)  # 防止连续保存

    cap.release()
    cv2.destroyAllWindows()
    
    # 绘制并保存数据图表
    print("正在生成数据图表...")
    data_logger.plot_data()

if __name__ == "__main__":
    list_cameras()
    capture_test_image()
