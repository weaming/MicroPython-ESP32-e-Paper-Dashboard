"""
硬件调试脚本

测试所有硬件功能：
- 墨水屏显示
- 网络连接
- 时间同步
- 传感器读取
- 电池电量
- 内存使用
"""

import system.hardware as hw
import system.network as net
import system.sensor as sensor
import system.power as pwr
import utime
import gc
from lib.framebuf2 import FrameBuffer, MHMSB
from lib.epaper7in5b import black, white


def test_memory():
    """测试内存使用情况"""
    print("\n=== Memory Test ===")
    gc.collect()
    free_mem = gc.mem_free()
    print(f"Free memory: {free_mem} bytes ({free_mem // 1024} KB)")


def test_battery():
    """测试电池电量"""
    print("\n=== Battery Test ===")
    from machine import Pin
    pwr_en = Pin(25, Pin.OUT)
    pwr_en.value(1) # Enable
    utime.sleep_ms(50)
    
    voltage = pwr.read_battery_voltage()
    
    pwr_en.value(0) # Disable
    Pin(25, Pin.IN)
    
    if voltage:
        percentage = pwr.get_battery_percentage(voltage)
        print(f"Battery voltage: {voltage:.2f}V")
        print(f"Battery percentage: {percentage}%")
    else:
        print("Battery read failed")


def test_sensor():
    """测试温湿度传感器"""
    print("\n=== Sensor Test ===")
    
    if sensor.init_sensor():
        temp, humi = sensor.read_sensor()
        if temp is not None:
            print(f"Temperature: {temp:.1f}°C")
            print(f"Humidity: {humi:.1f}%")
            print("Sensor type: SHT30")
        else:
            print("Sensor read failed")
        sensor.cleanup()
    else:
        print("Sensor not available")


def test_display():
    """测试墨水屏显示"""
    print("\n=== Display Test ===")
    
    print("1. Initializing Display...")
    epd = hw.init_display()
    buf = hw.get_buffer()
    
    print("2. Clearing Screen...")
    epd.clear_screen()
    
    print("3. Drawing Test Pattern...")
    fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
    
    fb.fill(white)
    fb.text("DEBUG MODE", 50, 50, black, size=4)
    fb.text("Hardware Test", 50, 100, black, size=3)
    fb.rect(0, 0, 800, 480, black)
    fb.line(0, 0, 800, 480, black)
    fb.line(800, 0, 0, 480, black)
    epd.write_black_layer(buf)
    
    fb.fill(white)
    fb.text("Yellow Layer Test", 50, 150, black, size=2)
    fb.fill_rect(400, 200, 100, 100, black)
    fb.circle(200, 300, 50, black)
    epd.write_yellow_layer(buf, refresh=True)
    
    print("4. Display Test Complete.")


def test_network():
    """测试网络连接"""
    print("\n=== Network Test ===")
    if net.connect_wifi():
        net.sync_time()
        print("Network Test Complete.")
    else:
        print("Network Test Failed.")


def test_wake_scheduler():
    """测试唤醒调度器"""
    print("\n=== Wake Scheduler Test ===")
    scheduler = pwr.WakeScheduler()
    wake_count = scheduler.get_wake_count()
    print(f"Wake count: {wake_count}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("Hardware Debug Test Suite")
    print("=" * 50)
    
    test_memory()
    test_battery()
    test_sensor()
    test_network()
    test_display()
    test_wake_scheduler()
    
    print("\n" + "=" * 50)
    print("All Tests Complete")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
