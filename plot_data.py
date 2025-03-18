import matplotlib.pyplot as plt
import pandas as pd
import sys
import os

def plot_data_from_csv(csv_file):
    """Read data from CSV file and plot charts
    
    Args:
        csv_file: Path to CSV file
    """
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} does not exist")
        return False
    
    try:
        # Read CSV data
        df = pd.read_csv(csv_file)
        
        # Check required columns
        required_columns = ['Time (s)', 'Target Speed', 'Current Position', 'Current Speed']
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: CSV file is missing column '{col}'")
                return False
        
        # Check if Target Degree data exists
        has_tar_degree = 'Target Degree' in df.columns
        
        # Create plots, add a third subplot if Target Degree data exists
        if has_tar_degree:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
        else:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # Plot speed chart
        ax1.plot(df['Time (s)'], df['Target Speed'], 'r-', label='Target Speed (tar_speed)', linewidth=2)
        ax1.plot(df['Time (s)'], df['Current Speed'], 'b-', label='Current Speed (cur_speed)', linewidth=2)
        ax1.set_ylabel('Speed (px/s)', fontsize=12)
        ax1.set_title('Speed Change Over Time', fontsize=14)
        ax1.grid(True)
        ax1.legend(loc='best', fontsize=11)
        
        # Plot position chart
        ax2.plot(df['Time (s)'], df['Current Position'], 'g-', label='Current Position (cur_pos)', linewidth=2)
        
        # Get target position from first row of CSV if available, otherwise use default
        target_position = 150  # Default value, consistent with main.py
        
        # Check if Target Position info exists in CSV
        if 'Target Position' in df.columns and len(df) > 0:
            target_position = df['Target Position'].iloc[0]
            
        ax2.axhline(y=target_position, color='r', linestyle='--', label=f'Target Position (tar_pos={target_position})')
        # Add x-axis label to position chart if no degree data
        if not has_tar_degree:
            ax2.set_xlabel('Time (s)', fontsize=12)
        
        ax2.set_ylabel('Position (px)', fontsize=12)
        ax2.set_title('Position Change Over Time', fontsize=14)
        ax2.grid(True)
        ax2.legend(loc='best', fontsize=11)
        
        # Plot degree chart if Target Degree data exists
        if has_tar_degree:
            ax3.plot(df['Time (s)'], df['Target Degree'], 'm-', label='Target Degree (tar_degree)', linewidth=2)
            ax3.set_xlabel('Time (s)', fontsize=12)
            ax3.set_ylabel('Degree Value', fontsize=12)
            ax3.set_title('Degree Change Over Time', fontsize=14)
            ax3.grid(True)
            ax3.legend(loc='best', fontsize=11)
        
        plt.tight_layout()
        
        # Save the plot
        plot_filename = csv_file.replace('.csv', '_plot.png')
        plt.savefig(plot_filename, dpi=300)
        print(f"Plot saved as: {plot_filename}")
        
        # Show the plot
        plt.show()
        return True
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def list_data_files():
    """List all CSV data files in the data directory"""
    # Get data directory path
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # Ensure data directory exists
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory: {data_dir}")
    
    # Get CSV files from data directory
    data_files = [f for f in os.listdir(data_dir) if f.startswith('data_log_') and f.endswith('.csv')]
    
    if not data_files:
        print("No data files found")
        return []
    
    # Convert filenames to full paths
    data_files_with_path = [os.path.join(data_dir, f) for f in data_files]
    
    print("Available data files:")
    for i, file in enumerate(data_files_with_path, 1):
        file_size = os.path.getsize(file)
        file_time = os.path.getmtime(file)
        # Show only filename, not full path
        display_name = os.path.basename(file)
        print(f"{i}. {display_name} - Size: {file_size/1024:.1f} KB - Time: {pd.to_datetime(file_time, unit='s')}")
    
    return data_files_with_path

if __name__ == "__main__":
    # Get data directory path
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # If filename is specified, plot that file directly
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # If only filename is provided (not full path), look in data directory
        if not os.path.isabs(file_path) and not os.path.exists(file_path):
            possible_path = os.path.join(data_dir, file_path)
            if os.path.exists(possible_path):
                file_path = possible_path
        plot_data_from_csv(file_path)
    else:
        # List all data files
        data_files = list_data_files()
        
        if data_files:
            # Ask user to select a file
            try:
                choice = input("Please select a file number to plot (press Enter to select the most recent file): ")
                
                if choice.strip() == "":
                    # Default to the most recent file
                    newest_file = max(data_files, key=os.path.getmtime)
                    plot_data_from_csv(newest_file)
                else:
                    idx = int(choice) - 1
                    if 0 <= idx < len(data_files):
                        plot_data_from_csv(data_files[idx])
                    else:
                        print("Invalid choice")
            except (ValueError, IndexError):
                print("Invalid input")
