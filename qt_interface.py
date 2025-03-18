import sys
import cv2
import time
import math
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSpinBox, QGroupBox)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject, Qt
from PyQt5.QtGui import QFont
from driver import ServoDriver
from pid import PID
from data_logger import DataLogger

# 创建一个信号类用于线程间通信
class CommunicationSignals(QObject):
    update_position = pyqtSignal(float)
    update_speed = pyqtSignal(float)
    update_mode = pyqtSignal(str, str)
    update_error = pyqtSignal(float)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化信号对象
        self.signals = CommunicationSignals()
        
        # 初始化UI
        self.initUI()
        
        # 初始化全局变量
        self.prev_x = None
        self.prev_y = None
        self.prev_time = None
        self.count = 0
        self.tar_pos = 100  # 默认目标位置
        self.status = False
        self.fine_tune_status = False
        self.precision_mode_count = 0
        self.precision_mode_locked = False
        
        # 初始化驱动和PID控制器
        self.driver = ServoDriver()
        self.degree_pid = PID(Kp=0.22, Ki=0, Kd=0.01, lim=10000)  # 速度-角度PID参数
        self.pos_pid = PID(Kp=4, Ki=0, Kd=0.6, lim=30)  # 位置-速度PID参数
        self.fine_tune_pid = PID(Kp=0.05, Ki=0, Kd=0.005, lim=5)  # 微调PID参数
        
        # 初始化数据记录器
        self.data_logger = DataLogger()
        
        # 连接信号到槽函数
        self.signals.update_position.connect(self.update_position_display)
        self.signals.update_speed.connect(self.update_speed_display)
        self.signals.update_mode.connect(self.update_mode_display)
        self.signals.update_error.connect(self.update_error_display)
        
        # 创建并启动摄像头线程
        self.camera_thread = threading.Thread(target=self.camera_processing_loop)
        self.camera_thread.daemon = True  # 设置为守护线程，随主线程退出
        self.camera_thread.start()

    def initUI(self):
        # 设置窗口基本属性
        self.setWindowTitle('小球位置控制系统')
        self.setGeometry(100, 100, 500, 400)
        
        # 创建主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建目标位置控制组
        target_group = QGroupBox('目标位置控制')
        target_layout = QVBoxLayout()
        
        # 创建水平布局用于目标位置控制
        target_input_layout = QHBoxLayout()
        
        # 减小目标位置按钮
        self.decrease_btn = QPushButton('-')
        self.decrease_btn.setFont(QFont('Arial', 14))
        self.decrease_btn.setFixedSize(50, 50)
        self.decrease_btn.clicked.connect(self.decrease_target)
        
        # 目标位置输入框
        self.target_spinbox = QSpinBox()
        self.target_spinbox.setRange(-320, 320)
        self.target_spinbox.setValue(100)  # 默认值
        self.target_spinbox.setFont(QFont('Arial', 14))
        self.target_spinbox.valueChanged.connect(self.set_target)
        
        # 增加目标位置按钮
        self.increase_btn = QPushButton('+')
        self.increase_btn.setFont(QFont('Arial', 14))
        self.increase_btn.setFixedSize(50, 50)
        self.increase_btn.clicked.connect(self.increase_target)
        
        # 添加控件到水平布局
        target_input_layout.addWidget(self.decrease_btn)
        target_input_layout.addWidget(self.target_spinbox)
        target_input_layout.addWidget(self.increase_btn)
        
        # 添加水平布局到目标位置组布局
        target_layout.addLayout(target_input_layout)
        target_group.setLayout(target_layout)
        
        # 创建位置显示组
        position_group = QGroupBox('位置信息')
        position_layout = QVBoxLayout()
        
        # 当前位置显示
        self.current_pos_label = QLabel('当前位置: 0')
        self.current_pos_label.setFont(QFont('Arial', 12))
        self.current_pos_label.setAlignment(Qt.AlignCenter)
        
        # 当前速度显示
        self.current_speed_label = QLabel('当前速度: 0 px/s')
        self.current_speed_label.setFont(QFont('Arial', 12))
        self.current_speed_label.setAlignment(Qt.AlignCenter)
        
        # 当前模式显示
        self.current_mode_label = QLabel('模式: 跟踪模式 (未锁定)')
        self.current_mode_label.setFont(QFont('Arial', 12))
        self.current_mode_label.setAlignment(Qt.AlignCenter)
        
        # 当前误差显示
        self.current_error_label = QLabel('误差: 0')
        self.current_error_label.setFont(QFont('Arial', 12))
        self.current_error_label.setAlignment(Qt.AlignCenter)
        
        # 添加标签到位置显示组布局
        position_layout.addWidget(self.current_pos_label)
        position_layout.addWidget(self.current_speed_label)
        position_layout.addWidget(self.current_mode_label)
        position_layout.addWidget(self.current_error_label)
        position_group.setLayout(position_layout)
        
        # 创建按钮组
        button_group = QGroupBox('操作')
        button_layout = QHBoxLayout()
        
        # 重置按钮
        self.reset_btn = QPushButton('重置')
        self.reset_btn.setFont(QFont('Arial', 12))
        self.reset_btn.clicked.connect(self.reset_system)
        
        # 退出按钮
        self.exit_btn = QPushButton('退出')
        self.exit_btn.setFont(QFont('Arial', 12))
        self.exit_btn.clicked.connect(self.close)
        
        # 添加按钮到按钮组布局
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.exit_btn)
        button_group.setLayout(button_layout)
        
        # 将组添加到主布局
        main_layout.addWidget(target_group)
        main_layout.addWidget(position_group)
        main_layout.addWidget(button_group)

    def set_target(self, value):
        self.tar_pos = value
        print(f'目标位置已设置为: {self.tar_pos}')

    def increase_target(self):
        self.target_spinbox.setValue(self.target_spinbox.value() + 5)
        
    def decrease_target(self):
        self.target_spinbox.setValue(self.target_spinbox.value() - 5)
        
    def update_position_display(self, position):
        self.current_pos_label.setText(f'当前位置: {position:.2f}')
        
    def update_speed_display(self, speed):
        self.current_speed_label.setText(f'当前速度: {speed:.2f} px/s')
        
    def update_mode_display(self, mode, lock_status):
        self.current_mode_label.setText(f'模式: {mode} ({lock_status})')
        
    def update_error_display(self, error):
        self.current_error_label.setText(f'误差: {error:.2f}')
        
    def reset_system(self):
        # 重置系统状态
        self.driver.move_degree(1, 2100, 0, 100)
        self.status = False
        self.fine_tune_status = False
        self.precision_mode_count = 0
        self.precision_mode_locked = False
        self.count = 0
        
        # 更新UI
        self.update_mode_display('跟踪模式', '未锁定')
        print('系统已重置')
    
    def camera_processing_loop(self):
        # 尝试打开摄像头
        for i in range(4):  # 尝试0-3号摄像头
            cap = cv2.VideoCapture(2)
            if cap.isOpened():
                print(f'成功打开摄像头 #{i}')
                break
        
        if not cap.isOpened():
            print('无法打开摄像头')
            return
        
        self.driver.move_degree(1, 2100, 0, 100)  # 控制ID为1的舵机
        time.sleep(0.5)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print('无法获取画面')
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
                    current_time = time.time()
                    
                    if self.prev_x is not None and self.prev_y is not None:
                        # 计算位移
                        dx = x - self.prev_x
                        distance = dx
                        
                        # 计算时间差
                        dt = current_time - self.prev_time
                        
                        # 计算速度 (像素/秒)
                        cur_speed = distance / dt if dt > 0 else 0
                        
                        # 显示速度和坐标
                        cv2.putText(frame, f'Ball: ({int(x)}, {int(y)})', 
                                  (10*20, 60*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                        cv2.putText(frame, f'Speed: {cur_speed:.1f} px/s', 
                                  (10*20, 90*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                        
                        cur_pos = x - 320
                        print(f'cur_pos:{cur_pos}')
                        
                        # 更新UI上的位置和速度显示
                        self.signals.update_position.emit(cur_pos)
                        self.signals.update_speed.emit(cur_speed)
                        
                        # 位置闭环控制
                        tar_speed = self.pos_pid.update(self.tar_pos, cur_pos, dt)
                        print(tar_speed)
                        
                        # 角度闭环控制
                        tar_degree = self.degree_pid.update(tar_speed, cur_speed, dt)
                        
                        # 记录数据，包括tar_degree
                        self.data_logger.log_data(tar_speed, cur_pos, cur_speed, tar_degree)
                        
                        # 将控制输出映射到舵机角度
                        servo_angle = 2100 + int(tar_degree)  # 2048为中心位置
                        servo_angle = max(2000, min(2200, servo_angle))  # 限制在安全范围内
                        servo_angle_tiny = 2100 + int(tar_degree/10)
                        servo_angle_tiny = max(2050, min(2150, servo_angle_tiny))
                        self.driver.move_degree(1, servo_angle, 0, 500)  # 限制在安全范围内
                        print(f'servo_angle:{servo_angle}')
                        
                        # 计算当前误差
                        current_error = abs(self.tar_pos - cur_pos)
                        
                        # 更新UI上的误差显示
                        self.signals.update_error.emit(current_error)
                        
                        # 检测是否应该退出精准模式
                        if self.precision_mode_locked and current_error > 15:
                            print('######### 误差过大，退出锁定精准模式 #########')
                            self.precision_mode_locked = False
                            self.precision_mode_count = 0
                            self.status = False
                            
                            # 更新UI上的模式显示
                            self.signals.update_mode.emit('跟踪模式', '未锁定')
                        
                        # 检测是否接近目标位置（速度小，位置接近）
                        if not self.precision_mode_locked:  # 只有在未锁定精准模式时才检测是否进入精准模式
                            if((abs(cur_speed) < 50) and current_error < 10):
                                self.status = True
                                self.precision_mode_count += 1  # 增加精准模式计数
                                print(f'进入精准模式第 {self.precision_mode_count} 次')
                                
                                # 如果进入精准模式次数达到10次，锁定精准模式
                                if self.precision_mode_count >= 10:
                                    self.precision_mode_locked = True
                                    print('######### 已锁定精准模式 #########')
                                    
                                    # 更新UI上的模式显示
                                    self.signals.update_mode.emit('精准模式', '已锁定')
                            
                            if((abs(cur_speed) > 50) or current_error > 10):
                                self.status = False
                                # 如果未锁定，则重置计数
                                if not self.precision_mode_locked:
                                    self.precision_mode_count = 0
                                    
                                    # 更新UI上的模式显示
                                    self.signals.update_mode.emit('跟踪模式', '未锁定')
                        
                        # 显示当前模式和锁定状态
                        mode_text = '精准模式' if self.status else '跟踪模式'
                        lock_text = '已锁定' if self.precision_mode_locked else '未锁定'
                        cv2.putText(frame, f'模式: {mode_text} ({lock_text})', 
                                  (10*20, 120*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                        cv2.putText(frame, f'误差: {current_error:.2f}', 
                                  (10*20, 150*20), cv2.FONT_HERSHEY_SIMPLEX, 0.8*2, (0, 255, 0), 2*2)
                        
                        if(self.status):
                            print('######### 进入精确定位模式 #########')
                            # 使用微调PID进行更精确的控制
                            fine_tune_degree = self.fine_tune_pid.update(self.tar_pos, cur_pos, dt)
                            fine_tune_angle = 2100 + int(fine_tune_degree)
                            fine_tune_angle = max(2050, min(2150, fine_tune_angle))  # 限制在更小的范围内
                            
                            print(f'微调角度: {fine_tune_angle}, 误差: {self.tar_pos-cur_pos:.2f}')
                            self.driver.move_degree(1, fine_tune_angle, 0, 200)  # 使用更低的速度控制舵机
                            self.count += 1
                            self.fine_tune_status = True
                            if(self.count > 10 and self.fine_tune_status == True and abs(cur_speed) < 10):
                                print('######### 精确定位完成 #########')
                                self.driver.move_degree(1, 2100, 0, 100)  # 使用更低的速度控制舵机
                                print(f'误差: {self.tar_pos-cur_pos:.2f}')
                        else:
                            # 使用常规PID控制
                            self.driver.move_degree(1, servo_angle, 0, 500)
                    
                    # 更新上一帧信息
                    self.prev_x = x
                    self.prev_y = y
                    self.prev_time = current_time
            
            # 创建可调整大小的窗口并显示当前帧
            cv2.namedWindow('Camera Test', cv2.WINDOW_NORMAL)
            cv2.imshow('Camera Test', frame)
            
            # 按ESC键退出
            if cv2.waitKey(1) == 27:
                break
        
        cap.release()
        cv2.destroyAllWindows()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
