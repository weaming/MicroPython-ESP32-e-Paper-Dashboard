import machine
import utime
import struct

# RTC Memory Layout
# We use RTC memory to persist state across deep sleep cycles.
# - Magic Header (4 bytes): To verify valid data
# - Task State (variable): Application specific state

RTC_MAGIC = 0xDEADBEEF


def deep_sleep(seconds):
    """Enter deep sleep for the specified number of seconds."""
    print(f"Entering deep sleep for {seconds} seconds...")
    # Configure wake up source
    machine.deepsleep(seconds * 1000)


def restart():
    """Soft reset the device."""
    machine.soft_reset()


def is_cold_boot():
    """Check if the device started from a complete power-off state."""
    return machine.wake_reason() != machine.DEEPSLEEP_RESET


class StateManager:
    """Manage persistent state in RTC memory."""
    def __init__(self):
        self.rtc = machine.RTC()
    
    def save(self, data):
        """Save bytes to RTC memory."""
        self.rtc.memory(data)
        
    def load(self):
        """Load bytes from RTC memory."""
        return self.rtc.memory()
    
    def clear(self):
        """Clear RTC memory."""
        self.rtc.memory(b'')


def read_battery_voltage(adc_pin=35, attenuation=machine.ADC.ATTN_11DB):
    """
    读取电池电压
    
    Args:
        adc_pin: ADC 引脚号（默认 GPIO 35）
        attenuation: ADC 衰减设置（默认 11dB，测量范围 0-3.6V）
    
    Returns:
        电压值（伏特）
    """
    try:
        from machine import ADC, Pin
        
        adc = ADC(Pin(adc_pin))
        adc.atten(attenuation)
        adc.width(machine.ADC.WIDTH_12BIT)
        
        raw_value = adc.read()
        voltage = (raw_value / 4095.0) * 3.6
        
        voltage_with_divider = voltage * 2
        
        return voltage_with_divider
    except Exception as e:
        print(f"Battery voltage read failed: {e}")
        return None


def get_battery_percentage(voltage):
    """
    根据电压计算电池电量百分比
    
    电池配置：2S 锂电池（两节串联）
    - 充满：8.4V (4.2V × 2)
    - 标称：7.4V (3.7V × 2)
    - 放空：6.0V (3.0V × 2)
    
    Args:
        voltage: 电池电压（伏特）
    
    Returns:
        电量百分比 (0-100)
    """
    if voltage is None:
        return None
    
    # 2S 锂电池电压范围
    MIN_VOLTAGE = 6.0   # 放空电压
    MAX_VOLTAGE = 8.4   # 充满电压
    
    if voltage >= MAX_VOLTAGE:
        return 100
    elif voltage <= MIN_VOLTAGE:
        return 0
    else:
        # 线性插值计算电量
        percentage = int((voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE) * 100)
        return max(0, min(100, percentage))


class WakeScheduler:
    """深度睡眠唤醒调度器"""
    
    def __init__(self):
        self.state_mgr = StateManager()
    
    def get_wake_count(self):
        """获取唤醒次数"""
        try:
            data = self.state_mgr.load()
            if len(data) >= 8:
                magic, count = struct.unpack('II', data[:8])
                if magic == RTC_MAGIC:
                    return count
        except:
            pass
        return 0
    
    def increment_wake_count(self):
        """增加唤醒次数"""
        count = self.get_wake_count() + 1
        data = struct.pack('II', RTC_MAGIC, count)
        self.state_mgr.save(data)
        return count
    
    def reset_wake_count(self):
        """重置唤醒次数"""
        data = struct.pack('II', RTC_MAGIC, 0)
        self.state_mgr.save(data)
    
    def schedule_next_wake(self, default_interval=300):
        """
        调度下一次唤醒，对齐到指定的分钟时刻（如每 5 分钟）
        """
        from config import ALIGN_MINUTES, TIMEZONE_OFFSET
        self.increment_wake_count()
        
        try:
            # 获取当前时间（已通过 ntp 同步）
            now = utime.time()
            # 调节到本地时间进行计算比较直观
            local_now = now + (TIMEZONE_OFFSET * 3600)
            tm = utime.localtime(local_now)
            
            # 计算距离下一个整 5 分钟还有多少秒
            current_min = tm[4]
            current_sec = tm[5]
            
            passed_seconds_in_interval = (current_min % ALIGN_MINUTES) * 60 + current_sec
            sleep_seconds = (ALIGN_MINUTES * 60) - passed_seconds_in_interval
            
            # 基础保护：如果剩下时间太短（比如 < 10s），则跳到下一个周期
            if sleep_seconds < 10:
                sleep_seconds += ALIGN_MINUTES * 60
                
            print(f"Aligning wake: Current {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}, Sleep {sleep_seconds}s")
            deep_sleep(sleep_seconds)
        except Exception as e:
            print(f"Schedule alignment failed: {e}, using default {default_interval}s")
            deep_sleep(default_interval)
