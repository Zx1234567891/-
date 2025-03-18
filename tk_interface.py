import sys
import cv2
import time
import math
import threading
import tkinter as tk
from tkinter import ttk, font
from driver import ServoDriver
from pid import PID
from data_logger import DataLogger
import Jetson.GPIO as GPIO
output_pin = 37  #J41_BOARD_PIN37---gpio12/GPIO.B26/SPI2_MOSI
 
# Pin Setup:
# Board pin-numbering scheme
GPIO.setmode(GPIO.BOARD)
# set pin as an output pin with optional initial state of HIGH
GPIO.setup(output_pin, GPIO.OUT, initial=GPIO.LOW)
class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 初始化UI
        self.title('小球位置控制系统')
        self.geometry('600x500')  # 增加窗口大小
        self.configure(bg='#f0f0f0')
        
        # 初始化单位转换
        self.px_to_mm_ratio_neg = 150 / 130  # -160px = -150mm
        self.px_to_mm_ratio_pos = 150 / 160  # 130px = 150mm
        
        # 初始化全局变量
        self.prev_x = None
        self.prev_y = None
        self.prev_time = None
        self.count = 0
        self.tar_pos_px = 0  # 默认目标位置(像素)
        self.tar_pos = self.px_to_mm(self.tar_pos_px)  # 默认目标位置(毫米)
        self.status = False
        self.fine_tune_status = False
        self.precision_mode_count = 0
        self.precision_mode_locked = False
        self.show_camera = False  # 不显示摄像头画面
        
        # 初始化驱动和PID控制器
        self.driver = ServoDriver()
        self.degree_pid = PID(Kp=0.22, Ki=0, Kd=0.01, lim=10000)  # 速度-角度PID参数
        self.pos_pid = PID(Kp=4, Ki=0, Kd=0.6, lim=30)  # 位置-速度PID参数
        self.fine_tune_pid = PID(Kp=0.05, Ki=0, Kd=0.005, lim=5)  # 微调PID参数
        
        # 初始化数据记录器
        self.data_logger = DataLogger()
        
        # 创建界面
        self.create_widgets()
        
        # 创建并启动摄像头线程
        self.camera_thread = threading.Thread(target=self.camera_processing_loop)
        self.camera_thread.daemon = True  # 设置为守护线程，随主线程退出
        self.camera_thread.start()
        
        # 创建定时器来更新UI
        self.update_ui()
    
    def px_to_mm(self, px_value):
        """将像素值转换为毫米值"""
        if px_value < 0:
            return px_value * self.px_to_mm_ratio_neg
        else:
            return px_value * self.px_to_mm_ratio_pos
    
    def mm_to_px(self, mm_value):
        """将毫米值转换为像素值"""
        if mm_value < 0:
            return mm_value / self.px_to_mm_ratio_neg
        else:
            return mm_value / self.px_to_mm_ratio_pos
    
    def create_widgets(self):
        # 设置全局字体
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=14)  # 增大默认字体
        text_font = font.nametofont("TkTextFont")
        text_font.configure(size=14)  # 增大文本字体
        fixed_font = font.nametofont("TkFixedFont")
        fixed_font.configure(size=14)  # 增大固定宽度字体
        
        self.option_add("*Font", default_font)
        
        # 主容器框架
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建目标位置控制框架
        target_frame = ttk.LabelFrame(main_frame, text='目标位置控制 (mm)', padding="15")
        target_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 目标位置控制行
        target_control_frame = ttk.Frame(target_frame)
        target_control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 减少按钮
        decrease_btn = ttk.Button(target_control_frame, text='-', width=4, command=self.decrease_target)
        decrease_btn.pack(side=tk.LEFT, padx=10)
        
        # 目标位置输入
        self.target_var = tk.DoubleVar(value=self.tar_pos)
        # 设置输入框的验证函数
        vcmd = (self.register(self.validate_target), '%P')
        self.target_entry = ttk.Spinbox(
            target_control_frame, 
            from_=-150, 
            to=150, 
            textvariable=self.target_var,
            width=10,
            validate='key', 
            validatecommand=vcmd,
            command=self.update_target
        )
        self.target_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        self.target_entry.bind('<Return>', lambda e: self.update_target())
        
        # 增加按钮
        increase_btn = ttk.Button(target_control_frame, text='+', width=4, command=self.increase_target)
        increase_btn.pack(side=tk.LEFT, padx=10)
        
        # 创建位置信息框架
        info_frame = ttk.LabelFrame(main_frame, text='位置信息', padding="15")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 创建位置信息标签
        self.pos_label = ttk.Label(info_frame, text='当前位置: 0 mm', font=('Arial', 16))
        self.pos_label.pack(fill=tk.X, pady=5)
        
        self.speed_label = ttk.Label(info_frame, text='当前速度: 0 mm/s', font=('Arial', 16))
        self.speed_label.pack(fill=tk.X, pady=5)
        
        self.mode_label = ttk.Label(info_frame, text='   ', font=('Arial', 16))
        self.mode_label.pack(fill=tk.X, pady=5)
        
        self.error_label = ttk.Label(info_frame, text='error: 0 mm', font=('Arial', 16))
        self.error_label.pack(fill=tk.X, pady=5)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=15)
        
        # 重置按钮
        reset_btn = ttk.Button(button_frame, text='重置', command=self.reset_system, width=10)
        reset_btn.pack(side=tk.LEFT, padx=10)
        
        # 退出按钮
        exit_btn = ttk.Button(button_frame, text='退出', command=self.quit, width=10)
        exit_btn.pack(side=tk.RIGHT, padx=10)
    
    def validate_target(self, new_value):
        if new_value == '':
            return True
        try:
            value = float(new_value)
            return -150 <= value <= 150
        except ValueError:
            return False
    
    def update_target(self):
        try:
            self.tar_pos = self.target_var.get()  # 获取毫米值
            self.tar_pos_px = self.mm_to_px(self.tar_pos)  # 转换为像素值
            print(f'目标位置已设置为: {self.tar_pos} mm ({self.tar_pos_px:.2f} px)')
        except tk.TclError:
            # 如果转换出错，重置为当前值
            self.target_var.set(self.tar_pos)
    
    def increase_target(self):
        current = self.target_var.get()
        self.target_var.set(min(150, current + 5))  # 增加5mm
        self.update_target()
    
    def decrease_target(self):
        current = self.target_var.get()
        self.target_var.set(max(-150, current - 5))  # 减少5mm
        self.update_target()
    
    def reset_system(self):
        # 重置系统状态
        self.driver.move_degree(1, 2100, 0, 100)
        self.status = False
        self.fine_tune_status = False
        self.precision_mode_count = 0
        self.precision_mode_locked = False
        self.count = 0
        print('系统已重置')
        
        # 更新UI
        self.mode_label.config(text='   ')
    
    def update_ui(self):
        # 使用这个方法定期更新UI，避免UI和线程的冲突
        self.after(100, self.update_ui)  # 每100毫秒调用一次
    
    def camera_processing_loop(self):
        # 尝试打开摄像头
        for i in range(4):  # 尝试0-3号摄像头
            cap = cv2.VideoCapture(0)  # 从原始代码中可以看出使用的是2号摄像头
            if cap.isOpened():
                print(f'成功打开摄像头 #{i}')
                break
        
        if not cap.isOpened():
            print('无法打开摄像头')
            return
        
        self.driver.move_degree(1, 2100, 0, 100)  # 控制ID为1的舵机
        time.sleep(0.5)
        
        while True:
            try:
                ret, frame = cap.read()
                if not ret:
                    print('无法获取画面')
                    break
                
                # ##转换到HSV颜色空间
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
#
#
                #
                #
                ## 查找轮廓
                contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                ## 转换到HSV颜色空间
                #hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
#
                ## 定义绿色的HSV范围（替换原来的红色范围）
                #lower_green = (35, 50, 50)    # 色相(H)范围35-85
                #upper_green = (85, 255, 255)
#
                ## 创建绿色掩码（删除原来的红色掩码）
                #mask = cv2.inRange(hsv, lower_green, upper_green)
#
                ## 查找轮廓
                #contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                
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
                        current_time = time.time()
                        
                        if self.prev_x is not None and self.prev_y is not None and self.prev_time is not None:
                            # 计算位移
                            dx = x - self.prev_x
                            distance = dx
                            
                            # 计算时间差
                            dt = current_time - self.prev_time
                            
                            # 计算速度 (像素/秒)
                            cur_speed_px = distance / dt if dt > 0 else 0
                            
                            # 显示速度和坐标
                            cv2.putText(frame, f'Ball: ({int(x)}, {int(y)})', 
                                      (10*20, 60*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                            cv2.putText(frame, f'Speed: {cur_speed_px:.1f} px/s', 
                                      (10*20, 90*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                            
                            cur_pos_px = x - 320
                            cur_pos = self.px_to_mm(cur_pos_px)  # 转换为毫米
                            cur_speed = self.px_to_mm(cur_speed_px)  # 转换为毫米/秒
                            
                            print(f'cur_pos:{cur_pos_px} px ({cur_pos:.2f} mm)')
                            
                            # 更新UI
                            self.after(10, lambda: self.update_position_display(cur_pos))
                            self.after(10, lambda: self.update_speed_display(cur_speed))
                            
                            # 位置闭环控制 (使用像素值进行PID计算)
                            tar_speed = self.pos_pid.update(self.tar_pos_px, cur_pos_px, dt)
                            print(f'tar_speed:{tar_speed}')
                            
                            # 角度闭环控制
                            tar_degree = self.degree_pid.update(tar_speed, cur_speed_px, dt)
                            
                            # 记录数据
                            self.data_logger.log_data(tar_speed, cur_pos_px, cur_speed_px, tar_degree)
                            
                            # 将控制输出映射到舵机角度
                            servo_angle = 2100 + int(tar_degree)  # 2048为中心位置
                            servo_angle = max(2000, min(2200, servo_angle))  # 限制在安全范围内
                            servo_angle_tiny = 2100 + int(tar_degree/10)
                            servo_angle_tiny = max(2050, min(2150, servo_angle_tiny))
                            
                            print(f'servo_angle:{servo_angle}')
                            
                            # 计算当前误差
                            current_error_px = abs(self.tar_pos_px - cur_pos_px)
                            current_error = abs(self.tar_pos - cur_pos)  # 毫米误差
                            
                            # 更新UI
                            self.after(10, lambda: self.update_error_display(current_error))
                            
                            # 检测是否应该退出精准模式
                            if self.precision_mode_locked and current_error_px > 10:
                                print('######### 误差过大，退出锁定精准模式 #########')
                                self.precision_mode_locked = False
                                self.precision_mode_count = 0
                                self.status = False
                                
                                # 更新UI
                                self.after(10, lambda: self.update_mode_display('跟踪模式', '未锁定'))
                            
                            # 检测是否接近目标位置
                            if not self.precision_mode_locked:
                                if((abs(cur_speed_px) < 50) and current_error_px < 8):
                                    self.status = True
                                    self.precision_mode_count += 1
                                    print(f'进入精准模式第 {self.precision_mode_count} 次')
                                    
                                    # 如果进入精准模式次数达到10次，锁定精准模式
                                    if self.precision_mode_count >= 10:
                                        self.precision_mode_locked = True
                                        print('######### 已锁定精准模式 #########')
                                        self.after(5, lambda: self.update_mode_display('精准模式', '已锁定'))
                                
                                if((abs(cur_speed_px) > 50) or current_error_px > 10):
                                    self.status = False
                                    # 如果未锁定，则重置计数
                                    if not self.precision_mode_locked:
                                        self.precision_mode_count = 0
                                        self.after(10, lambda: self.update_mode_display('跟踪模式', '未锁定'))
                            
                            # 显示当前模式和锁定状态
                            mode_text = '精准模式' if self.status else '跟踪模式'
                            lock_text = '已锁定' if self.precision_mode_locked else '未锁定'
                            cv2.putText(frame, f'模式: {mode_text} ({lock_text})', 
                                      (10*20, 120*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                            cv2.putText(frame, f'误差: {current_error_px:.2f} px ({current_error:.2f} mm)', 
                                      (10*20, 150*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                            
                            if(self.status):
                                print('######### 进入精确定位模式 #########')
                                # 使用微调PID进行更精确的控制
                                fine_tune_degree = self.fine_tune_pid.update(self.tar_pos_px, cur_pos_px, dt)
                                fine_tune_angle = 2100 + int(fine_tune_degree)
                                fine_tune_angle = max(2080, min(2120, fine_tune_angle))
                                
                                print(f'微调角度: {fine_tune_angle}, 误差: {self.tar_pos-cur_pos:.2f} mm')
                                self.driver.move_degree(1, fine_tune_angle, 0, 200)
                                self.count += 1
                                self.fine_tune_status = True

                                if(self.count > 10 and self.fine_tune_status == True and abs(cur_speed_px) <5 and current_error < 3):
                                    print('######### 精确定位完成 #########')
                                    self.driver.move_degree(1, 2100, 0, 100)
                                    
                                    GPIO.output(output_pin, GPIO.HIGH)
                                    print(f'误差: {self.tar_pos-cur_pos:.2f} mm')
                            else:
                                # 使用常规PID控制
                                self.driver.move_degree(1, servo_angle, 0, 500)
                        
                        # 更新上一帧信息
                        self.prev_x = x
                        self.prev_y = y
                        self.prev_time = current_time
                
                # 仅当需要显示摄像头画面时才显示
                if self.show_camera:
                    cv2.namedWindow('Camera Test', cv2.WINDOW_NORMAL)
                    cv2.imshow('Camera Test', frame)
                    
                    # 按ESC键退出
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
            except Exception as e:
                print(f'处理帧时出错: {e}')
                continue
        
        cap.release()
        cv2.destroyAllWindows()
    
    def update_position_display(self, position):
        self.pos_label.config(text=f'当前位置: {position:.2f} mm')
    
    def update_speed_display(self, speed):
        self.speed_label.config(text=f'当前速度: {speed:.2f} mm/s')
    
    def update_mode_display(self, mode, lock_status):
        self.mode_label.config(text=f'   ')
    
    def update_error_display(self, error):
        self.error_label.config(text=f'error: {error:.2f} mm')

def main():
    app = MainApplication()
    app.mainloop()

if __name__ == '__main__':
    main()
