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

def draw_dashboard(epd, buf, info1_data, info2_data, sensors):
    """
    绘制双屏仪表盘内容：文字用黑色，分割线用黄色
    """
    from lib.framebuf2 import FrameBuffer, MHMSB
    gc.collect() # 绘制前清理
    
    fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
    
    def bold_text(text, x, y, color, size=1, spacing=0):
        """绘制加粗且支持字间距的文本"""
        fb.text(text, x, y, color, size=size, spacing=spacing)
        fb.text(text, x + 1, y, color, size=size, spacing=spacing)

    def render_content(x_offset, default_title, content, err, only_lines=False):
        title = default_title
        start_idx = 0
        
        # 使用更省内存的方式处理每一行
        if err:
            if not only_lines:
                fb.text(f"Error: {err}", x_offset + 20, 90, black, size=1, spacing=1)
            return

        if not content:
            if not only_lines:
                fb.text("No data", x_offset + 20, 90, black, size=1, spacing=1)
            return

        # 找到第一行标题
        first_newline = content.find('\n')
        first_line = content[:first_newline] if first_newline != -1 else content
        
        if first_line.startswith('# '):
            title = first_line[2:].strip()
            rest = content[first_newline+1:] if first_newline != -1 else ""
        else:
            rest = content

        if only_lines:
            fb.line(x_offset + 20, 65, x_offset + 350, 65, black)
            fb.line(x_offset + 20, 66, x_offset + 350, 66, black)
            return

        bold_text(title, x_offset + 20, 30, black, size=2, spacing=4)
        
        y = 90
        # 逐行读取，避免一次性 split 产生大切片
        last_pos = 0
        while last_pos < len(rest):
            next_newline = rest.find('\n', last_pos)
            if next_newline == -1:
                line = rest[last_pos:].strip()
                last_pos = len(rest)
            else:
                line = rest[last_pos:next_newline].strip()
                last_pos = next_newline + 1
            
            if not line:
                y += 10
                continue
            
            if y > 440: break
            
            if line.startswith('#'):
                h_text = line.lstrip('#').strip()
                # 子标题加粗，增加间距防止重叠
                bold_text(h_text, x_offset + 20, y, black, size=1, spacing=3)
                y += 32
            else:
                # 正文使用常规字体，基础间隔设为 2px
                fb.text(line, x_offset + 20, y, black, size=1, spacing=2)
                y += 28

    # --- 第一阶段：绘制黑色图层（文字） ---
    fb.fill(white)
    render_content(0, "INFO 1", info1_data[0], info1_data[1], only_lines=False)
    render_content(400, "INFO 2", info2_data[0], info2_data[1], only_lines=False)
    
    # 底部状态栏
    tm = utime.localtime()
    date_str = f"{tm[0]}-{tm[1]:02d}-{tm[2]:02d} {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
    
    parts = [date_str]
    if sensors.get('temp') is not None:
        parts.append(f"{sensors['temp']:.1f}°C")
    if sensors.get('humi') is not None:
        parts.append(f"湿度{sensors['humi']:.1f}%")
    if sensors.get('bat_v') is not None:
        # 显示格式：电量xx%(x.xv)
        parts.append(f"电量{sensors['bat_p']:.1f}%({sensors.get('bat_raw', 0):.2f}V)")
    
    status_str = " | ".join(parts)
    # 状态栏使用常规字体，间隔 2px
    fb.text(status_str, 20, 460, black, size=1, spacing=2)
    
    epd.write_black_layer(buf)
    gc.collect() # 黑色层刷完后清理

    # --- 第二阶段：绘制黄色图层（分割线） ---
    fb.fill(white)
    render_content(0, "INFO 1", info1_data[0], info1_data[1], only_lines=True)
    render_content(400, "INFO 2", info2_data[0], info2_data[1], only_lines=True)
    
    epd.write_yellow_layer(buf, refresh=True)
    gc.collect()


def main():
    # 启动延时，确保串口监视器能够捕获到后续所有日志
    print("\n>>> Dashboard App Starting (waiting for monitor...)")
    utime.sleep(2)
    
    try:
        from config import KV_BASE_URL
        import system.sensor as sensor
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
        
        # 初始化显示屏
        epd = hw.init_display()
        epd.clear_frame(BUF)
        
        # 绘制双屏
        draw_dashboard(epd, BUF, info1, info2, sensor_data)
        
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
