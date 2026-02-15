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
import system.ui as ui

RESTART_DELAY = 10


def main():
    # 启动延时，确保串口监视器能够捕获到后续所有日志
    print("\n>>> Dashboard App Starting (waiting for monitor...)")
    utime.sleep(2)
    
    try:
        from config import KV_BASE_URL
        gc.collect()
        
        scheduler = pwr.WakeScheduler()
        
        # 1. 优先读取电池数据
        sensor_data = {}
        voltage_info = pwr.read_battery_info()
        if voltage_info['v_bat'] is not None:
            sensor_data['bat_v'] = voltage_info['v_bat']
            sensor_data['bat_raw'] = voltage_info['v_raw']
            sensor_data['bat_p'] = pwr.get_battery_percentage(voltage_info['v_bat'])
        
        # 2. 连接 WiFi
        if not net.connect_wifi():
            print("WiFi failed. Sleeping.")
            scheduler.schedule_next_wake(60)
            return
        
        net.sync_time()
        
        # 3. 读取温湿度传感器
        if sensor.init_sensor():
            t, h = sensor.read_sensor()
            if t is not None:
                sensor_data['temp'] = t
                sensor_data['humi'] = h
            sensor.cleanup()
        
        gc.collect()
        
        # 获取远程数据
        info1 = net.fetch_content(KV_BASE_URL + "info1")
        info2 = net.fetch_content(KV_BASE_URL + "info2")
        
        gc.collect()
        
        # 4. 初始化显示屏并绘制
        epd = hw.init_display()
        epd.clear_frame(BUF)
        
        ui.draw_dashboard(epd, BUF, info1, info2, sensor_data)
        
        from config import DEEP_SLEEP_ENABLED
        if DEEP_SLEEP_ENABLED:
            scheduler.schedule_next_wake()
        else:
            print("Deep sleep disabled. Waiting 30s...")
            utime.sleep(30)
            pwr.restart()
        
    except Exception as e:
        print(f"Critical Error: {e}")
        import sys
        sys.print_exception(e)
        utime.sleep(RESTART_DELAY)
        pwr.restart()

if __name__ == "__main__":
    main()
