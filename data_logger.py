import matplotlib.pyplot as plt
import numpy as np
import time
import csv
import os
from datetime import datetime

class DataLogger:
    def __init__(self, filename=None):
        """初始化数据记录器
        
        Args:
            filename: 保存数据的文件名，如果为None则自动生成
        """
        # 确保data目录存在
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        if filename is None:
            # 使用当前时间创建文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filename = os.path.join(self.data_dir, f"data_log_{timestamp}.csv")
        else:
            # 如果提供了文件名但没有包含路径，则添加data目录路径
            if os.path.dirname(filename) == '':
                self.filename = os.path.join(self.data_dir, filename)
            else:
                self.filename = filename
            
        # 初始化数据列表
        self.time_data = []
        self.tar_speed_data = []
        self.cur_pos_data = []
        self.cur_speed_data = []
        self.tar_degree_data = []  # 添加tar_degree数据列表
        self.start_time = None
        
        # 创建CSV文件并写入表头
        with open(self.filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Time (s)', 'Target Speed', 'Current Position', 'Current Speed', 'Target Degree'])
    
    def start(self):
        """开始记录，重置开始时间"""
        self.start_time = time.time()
    
    def log_data(self, tar_speed, cur_pos, cur_speed, tar_degree=None):
        """记录一组数据
        
        Args:
            tar_speed: 目标速度
            cur_pos: 当前位置
            cur_speed: 当前速度
            tar_degree: 目标角度（可选）
        """
        if self.start_time is None:
            self.start()  # 如果还没开始，则开始记录
            
        current_time = time.time() - self.start_time
        
        # 添加到内存中的数据列表
        self.time_data.append(current_time)
        self.tar_speed_data.append(tar_speed)
        self.cur_pos_data.append(cur_pos)
        self.cur_speed_data.append(cur_speed)
        self.tar_degree_data.append(tar_degree if tar_degree is not None else 0)  # 添加tar_degree数据
        
        # 写入CSV文件
        with open(self.filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([current_time, tar_speed, cur_pos, cur_speed, tar_degree if tar_degree is not None else 0])
    
    def plot_data(self, show=True, save=True):
        """绘制记录的数据
        
        Args:
            show: 是否显示图表
            save: 是否保存图表
        """
        if len(self.time_data) == 0:
            print("没有数据可以绘制")
            return
            
        # 创建图表，添加第三个子图用于显示tar_degree
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
        
        # 绘制速度图表
        ax1.plot(self.time_data, self.tar_speed_data, 'r-', label='目标速度 (tar_speed)')
        ax1.plot(self.time_data, self.cur_speed_data, 'b-', label='当前速度 (cur_speed)')
        ax1.set_ylabel('速度 (px/s)')
        ax1.set_title('速度变化曲线')
        ax1.grid(True)
        ax1.legend(loc='best', fontsize=10)
        
        # 绘制位置图表
        ax2.plot(self.time_data, self.cur_pos_data, 'g-', label='当前位置 (cur_pos)')
        # 从main.py中获取目标位置值
        target_position = 150  # 默认值，与main.py中修改后的值一致
        ax2.axhline(y=target_position, color='r', linestyle='--', label=f'目标位置 (tar_pos={target_position})')
        ax2.set_ylabel('位置 (px)')
        ax2.set_title('位置变化曲线')
        ax2.grid(True)
        ax2.legend(loc='best', fontsize=10)
        
        # 绘制角度图表
        ax3.plot(self.time_data, self.tar_degree_data, 'm-', label='目标角度 (tar_degree)', linewidth=1.5)
        ax3.set_xlabel('时间 (s)')
        ax3.set_ylabel('角度值')
        ax3.set_title('角度变化曲线')
        ax3.grid(True)
        ax3.legend(loc='best', fontsize=10)
        
        plt.tight_layout()
        
        # 保存图表
        if save:
            plot_filename = self.filename.replace('.csv', '.png')
            plt.savefig(plot_filename, dpi=300)  # 提高分辨率
            print(f"图表已保存为: {plot_filename}")
        
        # 显示图表
        if show:
            plt.show()

if __name__ == "__main__":
    # 测试代码
    logger = DataLogger()
    
    # 模拟数据
    for i in range(100):
        logger.log_data(
            tar_speed=np.sin(i/10) * 20,
            cur_pos=40 + np.sin(i/15) * 10,
            cur_speed=np.sin((i+2)/10) * 18,
            tar_degree=np.sin(i/8) * 30  # 添加tar_degree测试数据
        )
        time.sleep(0.05)
    
    # 绘制数据
    logger.plot_data()
