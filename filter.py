import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

class LowPassFilter:
    """
    低通滤波器类
    用于平滑数据，减少噪声
    """
    def __init__(self, cutoff_freq, sampling_rate, order=2):
        """
        初始化低通滤波器
        
        Args:
            cutoff_freq: 截止频率 (Hz)
            sampling_rate: 采样率 (Hz)
            order: 滤波器阶数，默认为2
        """
        self.cutoff_freq = cutoff_freq
        self.sampling_rate = sampling_rate
        self.order = order
        
        # 计算归一化截止频率 (0.0 到 1.0)
        self.normalized_cutoff = 2 * cutoff_freq / sampling_rate
        
        # 计算滤波器系数
        self.b, self.a = signal.butter(self.order, self.normalized_cutoff, 'low')
        
        # 初始化状态变量
        self.zi = signal.lfilter_zi(self.b, self.a)
        self.z = self.zi.copy()
        
        # 存储上一次的输出值
        self.last_output = 0.0
        
    def update(self, input_value):
        """
        使用滤波器处理单个输入值
        
        Args:
            input_value: 输入值
            
        Returns:
            滤波后的输出值
        """
        output, self.z = signal.lfilter(self.b, self.a, [input_value], zi=self.z)
        self.last_output = output[0]
        return self.last_output
    
    def filter_data(self, data):
        """
        对整个数据序列进行滤波
        
        Args:
            data: 输入数据序列 (numpy array 或 list)
            
        Returns:
            滤波后的数据序列
        """
        # 重置状态变量
        self.z = self.zi.copy()
        
        # 应用滤波器
        filtered_data = signal.lfilter(self.b, self.a, data)
        return filtered_data
    
    def reset(self):
        """
        重置滤波器状态
        """
        self.z = self.zi.copy()
        self.last_output = 0.0


class MovingAverageFilter:
    """
    移动平均滤波器类
    简单的滑动窗口平均
    """
    def __init__(self, window_size):
        """
        初始化移动平均滤波器
        
        Args:
            window_size: 窗口大小
        """
        self.window_size = window_size
        self.buffer = [0.0] * window_size
        self.index = 0
        self.sum = 0.0
    
    def update(self, input_value):
        """
        使用滤波器处理单个输入值
        
        Args:
            input_value: 输入值
            
        Returns:
            滤波后的输出值
        """
        # 更新总和，减去旧值，加上新值
        self.sum -= self.buffer[self.index]
        self.sum += input_value
        
        # 更新缓冲区
        self.buffer[self.index] = input_value
        self.index = (self.index + 1) % self.window_size
        
        # 返回平均值
        return self.sum / self.window_size
    
    def filter_data(self, data):
        """
        对整个数据序列进行滤波
        
        Args:
            data: 输入数据序列 (numpy array 或 list)
            
        Returns:
            滤波后的数据序列
        """
        # 重置滤波器
        self.reset()
        
        # 应用滤波器
        filtered_data = np.zeros_like(data)
        for i, value in enumerate(data):
            filtered_data[i] = self.update(value)
        
        return filtered_data
    
    def reset(self):
        """
        重置滤波器状态
        """
        self.buffer = [0.0] * self.window_size
        self.index = 0
        self.sum = 0.0


def demo_filters():
    """
    演示滤波器的效果
    """
    # 创建测试数据
    t = np.linspace(0, 1, 1000)  # 1秒，1000个采样点
    sampling_rate = 1000  # Hz
    
    # 创建一个包含噪声的信号
    clean_signal = np.sin(2 * np.pi * 5 * t)  # 5Hz的正弦波
    noise = 0.5 * np.random.randn(len(t))  # 随机噪声
    noisy_signal = clean_signal + noise
    
    # 创建滤波器
    butterworth_filter = LowPassFilter(cutoff_freq=10, sampling_rate=sampling_rate)
    moving_avg_filter = MovingAverageFilter(window_size=20)
    
    # 应用滤波器
    butterworth_filtered = butterworth_filter.filter_data(noisy_signal)
    moving_avg_filtered = moving_avg_filter.filter_data(noisy_signal)
    
    # 绘制结果
    plt.figure(figsize=(12, 8))
    
    plt.subplot(4, 1, 1)
    plt.plot(t, clean_signal)
    plt.title('原始信号 (5Hz正弦波)')
    plt.grid(True)
    
    plt.subplot(4, 1, 2)
    plt.plot(t, noisy_signal)
    plt.title('带噪声的信号')
    plt.grid(True)
    
    plt.subplot(4, 1, 3)
    plt.plot(t, butterworth_filtered)
    plt.title('巴特沃斯低通滤波器结果 (截止频率 10Hz)')
    plt.grid(True)
    
    plt.subplot(4, 1, 4)
    plt.plot(t, moving_avg_filtered)
    plt.title(f'移动平均滤波器结果 (窗口大小 {moving_avg_filter.window_size})')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('filter_demo.png', dpi=300)
    plt.show()


if __name__ == "__main__":
    demo_filters()
