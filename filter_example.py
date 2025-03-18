import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
from filter import LowPassFilter, MovingAverageFilter

def apply_filters_to_csv(csv_file, cutoff_freq=5.0, sampling_rate=30.0, window_size=5, filter_order=4):
    """
    对CSV文件中的数据应用滤波器并绘制比较图

    参数:
        csv_file: CSV文件路径
        cutoff_freq: 截止频率 (Hz)
        sampling_rate: 采样率 (Hz)
        window_size: 移动平均窗口大小
        filter_order: 巴特沃斯滤波器阶数 (默认: 4)
    """
    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"错误: 文件 {csv_file} 不存在")
        return False
    
    try:
        # 读取CSV数据
        df = pd.read_csv(csv_file)
        
        # 检查必需的列
        required_columns = ['Time (s)', 'Target Speed', 'Current Position', 'Current Speed']
        for col in required_columns:
            if col not in df.columns:
                print(f"错误: CSV文件缺少列 '{col}'")
                return False
        
        # 创建滤波器
        butter_filter_speed = LowPassFilter(cutoff_freq=cutoff_freq, sampling_rate=sampling_rate, order=filter_order)
        butter_filter_pos = LowPassFilter(cutoff_freq=cutoff_freq/2, sampling_rate=sampling_rate, order=filter_order)  # 为位置使用较低的截止频率
        ma_filter_speed = MovingAverageFilter(window_size=window_size)
        ma_filter_pos = MovingAverageFilter(window_size=window_size)
        
        # 应用滤波器
        butter_filtered_speed = butter_filter_speed.filter_data(df['Current Speed'].values)
        butter_filtered_pos = butter_filter_pos.filter_data(df['Current Position'].values)
        ma_filtered_speed = ma_filter_speed.filter_data(df['Current Speed'].values)
        ma_filtered_pos = ma_filter_pos.filter_data(df['Current Position'].values)
        
        # 检查是否有目标角度数据
        has_tar_degree = 'Target Degree' in df.columns
        if has_tar_degree:
            butter_filter_degree = LowPassFilter(cutoff_freq=cutoff_freq, sampling_rate=sampling_rate, order=filter_order)
            ma_filter_degree = MovingAverageFilter(window_size=window_size)
            butter_filtered_degree = butter_filter_degree.filter_data(df['Target Degree'].values)
            ma_filtered_degree = ma_filter_degree.filter_data(df['Target Degree'].values)
        
        # 绘制结果
        time_data = df['Time (s)'].values
        
        if has_tar_degree:
            fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
        else:
            fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # 绘制速度比较
        ax1 = axes[0]
        ax1.plot(time_data, df['Target Speed'], 'r-', label='Target Speed', linewidth=1.5)
        ax1.plot(time_data, df['Current Speed'], 'b-', label='Current Speed', linewidth=1.5, alpha=0.7)
        ax1.plot(time_data, butter_filtered_speed, 'g-', label='Filtered Speed (Butterworth)', linewidth=1.5)
        ax1.plot(time_data, ma_filtered_speed, 'm-', label='Filtered Speed (Moving Average)', linewidth=1.5)
        ax1.set_ylabel('Speed (px/s)', fontsize=12)
        ax1.set_title('Speed Filtering Comparison', fontsize=14)
        ax1.grid(True)
        ax1.legend(loc='best', fontsize=10)
        
        # 绘制位置比较
        ax2 = axes[1]
        ax2.plot(time_data, df['Current Position'], 'b-', label='Current Position', linewidth=1.5, alpha=0.7)
        ax2.plot(time_data, butter_filtered_pos, 'g-', label='Filtered Position (Butterworth)', linewidth=1.5)
        ax2.plot(time_data, ma_filtered_pos, 'm-', label='Filtered Position (Moving Average)', linewidth=1.5)
        
        # Main target position line
        target_position = 150  # Default value, modify based on the actual use case
        ax2.axhline(y=target_position, color='r', linestyle='--', label=f'Target Position (tar_pos={target_position})')
        
        if not has_tar_degree:
            ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Position (px)', fontsize=12)
        ax2.set_title('Position Filtering Comparison', fontsize=14)
        ax2.grid(True)
        ax2.legend(loc='best', fontsize=10)
        
        # 如果存在，绘制角度比较
        if has_tar_degree:
            ax3 = axes[2]
            ax3.plot(time_data, df['Target Degree'], 'b-', label='Target Degree', linewidth=1.5, alpha=0.7)
            ax3.plot(time_data, butter_filtered_degree, 'g-', label='Filtered Degree (Butterworth)', linewidth=1.5)
            ax3.plot(time_data, ma_filtered_degree, 'm-', label='Filtered Degree (Moving Average)', linewidth=1.5)
            ax3.set_xlabel('Time (s)', fontsize=12)
            ax3.set_ylabel('Degree Value', fontsize=12)
            ax3.set_title('Degree Filtering Comparison', fontsize=14)
            ax3.grid(True)
            ax3.legend(loc='best', fontsize=10)
        
        plt.tight_layout()
        
        # 将图保存为图像
        plot_filename = csv_file.replace('.csv', '_filtered.png')
        plt.savefig(plot_filename, dpi=300)
        print(f"滤波比较图已保存为: {plot_filename}")
        
        # 显示图
        plt.show()
        return True
    
    except Exception as e:
        print(f"错误: {str(e)}")
        return False

def list_data_files():
    """列出数据目录中所有可用的CSV数据文件"""
    # 获取数据目录路径
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # 如果数据目录不存在，则创建
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建数据目录: {data_dir}")
    
    # 列出数据目录中的所有CSV文件
    data_files = [f for f in os.listdir(data_dir) if f.startswith('data_log_') and f.endswith('.csv')]
    
    if not data_files:
        print("未找到数据文件")
        return []
    
    # 将文件名转换为完整路径
    data_files_with_path = [os.path.join(data_dir, f) for f in data_files]
    
    print("可用的数据文件:")
    for i, file in enumerate(data_files_with_path, 1):
        file_size = os.path.getsize(file)
        file_time = os.path.getmtime(file)
        # 显示文件名和信息
        display_name = os.path.basename(file)
        print(f"{i}. {display_name} - Size: {file_size/1024:.1f} KB - Time: {pd.to_datetime(file_time, unit='s')}")
    
    return data_files_with_path

if __name__ == "__main__":
    import sys
    
    # 获取数据目录路径
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # 如果给定了特定的文件作为参数，则对该文件应用滤波器
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # 如果文件不是绝对路径，则在数据目录中检查
        if not os.path.isabs(file_path) and not os.path.exists(file_path):
            possible_path = os.path.join(data_dir, file_path)
            if os.path.exists(possible_path):
                file_path = possible_path
        apply_filters_to_csv(file_path)
    else:
        # 列出所有数据文件并允许用户选择一个
        data_files = list_data_files()
        
        if data_files:
            # Let the user select the file to apply the filter to
            try:
                choice = input("请选择要应用滤波器的文件编号（按回车键选择最新的文件）: ")
                
                if choice.strip() == "":
                    # 默认选择最新的文件
                    newest_file = max(data_files, key=os.path.getmtime)
                    apply_filters_to_csv(newest_file)
                else:
                    idx = int(choice) - 1
                    if 0 <= idx < len(data_files):
                        apply_filters_to_csv(data_files[idx])
                    else:
                        print("Invalid choice")
            except (ValueError, IndexError):
                print("Invalid input")
