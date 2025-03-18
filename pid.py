class PID:
    def __init__(self, Kp, Ki, Kd,lim):
        """
        PID 控制器初始化
        :param Kp: 比例增益
        :param Ki: 积分增益 
        :param Kd: 微分增益
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.lim= lim
        self.reset()
        
    def reset(self):
        """重置控制器状态"""
        self.prev_error = 0.0
        self.integral = 0.0
        
    def update(self, setpoint, measured_value, dt):
        """
        更新 PID 控制器
        :param setpoint: 目标值
        :param measured_value: 测量值
        :param dt: 时间步长
        :return: 控制输出
        """
        error = setpoint - measured_value
        
        # 比例项
        P = self.Kp * error
        
        # 积分项
        if(abs(error)>self.lim):
            self.integral += 0
            
        else :
            self.integral += error * dt
        I = self.Ki * self.integral  
        # 微分项
        derivative = (error - self.prev_error) / dt
        D = self.Kd * derivative
        
        # 保存当前误差
        self.prev_error = error
        
        # 计算输出
        output = P + I + D
        
        return output
