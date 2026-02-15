"""
传感器模块 - 简化版，只支持 SHT30

硬件配置：
- SHT30 温湿度传感器
- I2C 接口：SCL=GPIO22, SDA=GPIO21
- I2C 地址：0x44
"""

import utime
from machine import Pin, I2C

_i2c = None
_address = 0x44
_last_reading = None
_last_reading_time = 0
CACHE_DURATION = 2000

I2C_SCL = 22
I2C_SDA = 21


def init_sensor():
    """
    初始化 SHT30 传感器
    
    Returns:
        True 如果成功，False 如果失败
    """
    global _i2c
    
    try:
        _i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=100000)
        
        devices = _i2c.scan()
        if _address not in devices:
            print(f"SHT30 not found at address 0x{_address:02x}")
            print(f"I2C devices found: {[hex(d) for d in devices]}")
            return False
        
        print(f"SHT30 initialized on I2C (SCL={I2C_SCL}, SDA={I2C_SDA})")
        return True
    except Exception as e:
        print(f"SHT30 init failed: {e}")
        return False


def read_sensor(use_cache=True):
    """
    读取温湿度数据
    
    Args:
        use_cache: 是否使用缓存数据（避免频繁读取）
    
    Returns:
        (temperature, humidity) 或 (None, None) 如果读取失败
    """
    global _last_reading, _last_reading_time
    
    if _i2c is None:
        return None, None
    
    now = utime.ticks_ms()
    if use_cache and _last_reading and utime.ticks_diff(now, _last_reading_time) < CACHE_DURATION:
        return _last_reading
    
    try:
        # 发送测量命令（高重复性）
        _i2c.writeto(_address, b'\x2C\x06')
        utime.sleep_ms(20)
        
        # 读取 6 字节数据
        data = _i2c.readfrom(_address, 6)
        
        # 解析温度（前 2 字节）
        temp_raw = (data[0] << 8) | data[1]
        temp = -45 + (175 * temp_raw / 65535.0)
        
        # 解析湿度（后 2 字节，跳过 CRC）
        humi_raw = (data[3] << 8) | data[4]
        humi = 100 * humi_raw / 65535.0
        
        _last_reading = (temp, humi)
        _last_reading_time = now
        return temp, humi
        
    except Exception as e:
        print(f"Sensor read failed: {e}")
        return None, None


def cleanup():
    """释放 I2C 资源"""
    global _i2c
    if _i2c:
        del _i2c
        _i2c = None
        import gc
        gc.collect()
        print("I2C resources released")


def is_initialized():
    """检查传感器是否已初始化"""
    return _i2c is not None
