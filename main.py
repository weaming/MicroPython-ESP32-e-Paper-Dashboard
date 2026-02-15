"""
主程序：E-Paper Dashboard
"""

import gc
import utime
import system.hardware as hw

# 关键优化：在导入其他大模块之前，尽早分配大块内存（帧缓冲区）
# 避免模块加载导致的堆内存碎片化
gc.collect()
try:
    BUF = hw.get_buffer()
except MemoryError:
    print("CRITICAL: Buffer allocation failed at startup!")
    raise

# 缓冲区分配成功后，再导入其他业务模块
import system.network as net
import system.power as pwr
import system.sensor as sensor
from lib.epaper7in5b import black, white

RESTART_DELAY = 10

def format_time(t):
    """格式化时间为字符串"""
    return f"{t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"

def draw_dashboard(epd, buf, data):
    """
    绘制仪表盘内容
    注意：延迟导入 FrameBuffer 以节省启动时的内存
    """
    from lib.framebuf2 import FrameBuffer, MHMSB
    
    fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
    
    fb.fill(white)
    
    # 标题使用大字体
    fb.text("墨水屏仪表盘", 30, 30, black, size=2)
    
    if data.get('time'):
        time_str = format_time(data['time'])
        fb.text(time_str, 30, 70, black, size=1)
    
    y_pos = 110
    
    # 使用统一的行间距和字体大小
    items = [
        ("温度", data.get('temp'), "°C", 1),
        ("湿度", data.get('humi'), "%", 1),
        ("电池", data.get('battery_voltage'), "V", 2),
        ("电量", data.get('battery_percentage'), "%", 0),
        ("唤醒次数", data.get('wake_count'), "", 0),
    ]
    
    for label, value, unit, precision in items:
        if value is not None:
            if precision == 0:
                text = f"{label}: {value}{unit}"
            elif precision == 1:
                text = f"{label}: {value:.1f}{unit}"
            else:
                text = f"{label}: {value:.2f}{unit}"
            
            fb.text(text, 30, y_pos, black, size=1)
            y_pos += 30
    
    fb.rect(20, 20, 760, 440, black)
    
    epd.write_black_layer(buf)
    
    fb.fill(white)
    fb.text("状态: 运行中", 30, 420, black, size=1)
    
    epd.write_yellow_layer(buf, refresh=True)


def main():
    try:
        print(f"Free memory: {gc.mem_free()} bytes")
        
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
            sensor.cleanup()
        else:
            print("Sensor not available")
        
        gc.collect()
        
        voltage = pwr.read_battery_voltage()
        if voltage:
            data['battery_voltage'] = voltage
            data['battery_percentage'] = pwr.get_battery_percentage(voltage)
            print(f"Battery: {voltage:.2f}V ({data['battery_percentage']}%)")
        
        gc.collect()
        
        # 初始化显示屏
        epd = hw.init_display()
        
        # 清除缓冲区
        epd.clear_frame(BUF)
        
        # 绘制
        draw_dashboard(epd, BUF, data)
        
        print("Display updated.")
        
        # 测试模式：禁用深度睡眠
        print("Test mode: Deep sleep disabled for debugging")
        print("Device will stay awake. Press Ctrl-C to stop.")
        
    except Exception as e:
        print(f"Critical Error: {e}")
        import sys
        sys.print_exception(e)
        
        utime.sleep(RESTART_DELAY)
        pwr.restart()

if __name__ == "__main__":
    main()
