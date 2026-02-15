"""
主程序：E-Paper Dashboard

功能流程：
1. 连接 WiFi
2. 同步时间
3. 读取传感器数据
4. 读取电池电量
5. 绘制仪表盘
6. 进入深度睡眠
"""

import utime
import gc
import system.network as net
import system.hardware as hw
import system.power as pwr
import system.sensor as sensor
from lib.framebuf2 import FrameBuffer, MHMSB
from lib.epaper7in5b import black, white

REFRESH_INTERVAL = 300
SENSOR_PIN = 4
SENSOR_TYPE = 'DHT22'


def format_time(t):
    """格式化时间为字符串"""
    return f"{t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"


def draw_dashboard(epd, buf, data):
    """
    绘制仪表盘内容
    
    Args:
        epd: 墨水屏实例
        buf: 帧缓冲区
        data: 数据字典 {time, temp, humi, battery_voltage, battery_percentage, wake_count}
    """
    fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
    
    fb.fill(white)
    
    fb.text("E-Paper Dashboard", 30, 30, black, size=4)
    
    if data.get('time'):
        time_str = format_time(data['time'])
        fb.text(time_str, 30, 90, black, size=2)
    
    y_pos = 140
    if data.get('temp') is not None:
        fb.text(f"Temperature: {data['temp']:.1f} C", 30, y_pos, black, size=2)
        y_pos += 40
    
    if data.get('humi') is not None:
        fb.text(f"Humidity: {data['humi']:.1f} %", 30, y_pos, black, size=2)
        y_pos += 40
    
    if data.get('battery_voltage'):
        fb.text(f"Battery: {data['battery_voltage']:.2f}V", 30, y_pos, black, size=2)
        y_pos += 40
    
    if data.get('battery_percentage') is not None:
        fb.text(f"Charge: {data['battery_percentage']}%", 30, y_pos, black, size=2)
        y_pos += 40
    
    if data.get('wake_count') is not None:
        fb.text(f"Wake Count: {data['wake_count']}", 30, y_pos, black, size=2)
    
    fb.rect(20, 20, 760, 440, black)
    
    epd.write_black_layer(buf)
    
    fb.fill(white)
    fb.text("Status: Active", 30, 420, black, size=2)
    
    epd.write_yellow_layer(buf, refresh=True)


def main():
    try:
        gc.collect()
        print(f"Free memory: {gc.mem_free()} bytes")
        
        # 立即分配缓冲区，避免内存碎片化
        buf = hw.get_buffer()
        print(f"Buffer allocated, free memory: {gc.mem_free()} bytes")
        
        scheduler = pwr.WakeScheduler()
        wake_count = scheduler.get_wake_count()
        print(f"Wake count: {wake_count}")
        
        if not net.connect_wifi():
            print("Error: Could not connect to WiFi. Sleeping.")
            scheduler.schedule_next_wake(60)
            return
        
        net.sync_time()
        
        data = {
            'time': utime.localtime(),
            'wake_count': wake_count
        }
        
        
        # 初始化传感器
        if sensor.init_sensor():
            temp, humi = sensor.read_sensor()
            if temp is not None:
                data['temp'] = temp
                data['humi'] = humi
                print(f"Sensor: {temp:.1f}°C, {humi:.1f}%")
            # 释放 I2C 资源
            sensor.cleanup()
        else:
            print("Sensor not available")
        
        gc.collect()
        print(f"Free memory after sensor: {gc.mem_free()} bytes")
        
        voltage = pwr.read_battery_voltage()
        if voltage:
            data['battery_voltage'] = voltage
            data['battery_percentage'] = pwr.get_battery_percentage(voltage)
            print(f"Battery: {voltage:.2f}V ({data['battery_percentage']}%)")
        
        gc.collect()
        print(f"Free memory before display: {gc.mem_free()} bytes")
        
        epd = hw.init_display()
        
        epd.clear_frame(buf)
        
        draw_dashboard(epd, buf, data)
        
        print("Display updated.")
        
        # 测试模式：禁用深度睡眠，方便调试
        print("Test mode: Deep sleep disabled for debugging")
        print("Device will stay awake. Press Ctrl-C to stop.")
        
        # epd.sleep()
        # gc.collect()
        # scheduler.schedule_next_wake(REFRESH_INTERVAL)
        
    except Exception as e:
        print(f"Critical Error: {e}")
        import sys
        sys.print_exception(e)
        
        utime.sleep(10)
        pwr.restart()


if __name__ == "__main__":
    main()
