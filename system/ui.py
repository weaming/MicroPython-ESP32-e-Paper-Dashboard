import gc
import utime
from lib.epaper7in5b import black, white
from lib.framebuf2 import FrameBuffer, MHMSB

# 字间距配置 (0 为不额外增加间距)
SPACING_TITLE = 4
SPACING_SUBHEADER = 2
SPACING_BODY = 0
SPACING_STATUS = 0

def get_char_width(char, size=1, spacing=0):
    """获取单个字符的显示宽度 (与 framebuf2 逻辑保持一致)"""
    # ASCII(及一度)使用半宽 (8px), 其他使用全宽 (16px)
    # 假设基础字体宽度为 16
    if ord(char) < 128 or ord(char) == 176:
        return (8 * size) + spacing
    else:
        return (16 * size) + spacing

def wrap_text(text, max_width, size=1, spacing=0):
    """
    将文本按指定宽度自动换行
    支持英文按单词换行 (Word Wrap)
    """
    lines = []
    current_line = ""
    current_width = 0
    
    for char in text:
        cw = get_char_width(char, size, spacing)
        
        if current_width + cw > max_width:
            # 需要换行
            # 尝试在当前行找到最后一个空格，以实现英文单词完整换行
            last_space_idx = current_line.rfind(' ')
            
            # 如果能找到空格，且空格后不是空的（避免 text="   " 这种情况死循环）
            # 并且当前累积的行也不是纯长单词（如果一整行都没空格，就只能硬切了）
            if last_space_idx != -1:
                # 将空格前的内容作为一行
                prefix = current_line[:last_space_idx]
                # 空格后的内容（半截单词）+ 当前字符 放到下一行
                suffix = current_line[last_space_idx+1:] + char
                
                lines.append(prefix)
                current_line = suffix
                
                # 重新计算新一行的宽度
                current_width = 0
                for c in current_line:
                    current_width += get_char_width(c, size, spacing)
            else:
                # 没空格（如长中文或超长英文单词），只能硬切
                lines.append(current_line)
                current_line = char
                current_width = cw
        else:
            current_line += char
            current_width += cw
            
    if current_line:
        lines.append(current_line)
    return lines



def draw_dashboard(epd, buf, info1_data, info2_data, sensors):
    """
    绘制双屏仪表盘内容：文字用黑色，分割线用黄色
    """
    gc.collect() # 绘制前清理
    
    fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
    
    def bold_text(text, x, y, color, size=1, spacing=0):
        """绘制加粗且支持字间距的文本"""
        fb.text(text, x, y, color, size=size, spacing=spacing)
        fb.text(text, x + 1, y, color, size=size, spacing=spacing)

    def render_content(x_offset, default_title, content, err, only_lines=False):
        title = default_title
        MAX_WIDTH = 330 # 内容最大宽度 (350 - 20)
        
        # 使用更省内存的方式处理每一行
        if err:
            if not only_lines:
                fb.text(f"Error: {err}", x_offset + 20, 90, black, size=1, spacing=SPACING_BODY)
            return

        if not content:
            if not only_lines:
                fb.text("No data", x_offset + 20, 90, black, size=1, spacing=SPACING_BODY)
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

        # 绘制主标题 (支持换行，虽然通常不应换行)
        title_lines = wrap_text(title, MAX_WIDTH, size=2, spacing=SPACING_TITLE)
        ty = 30
        for t_line in title_lines:
            bold_text(t_line, x_offset + 20, ty, black, size=2, spacing=SPACING_TITLE)
            ty += 32 # 大标题行高
            
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
                # 子标题加粗，增加间距防止重叠，支持自动换行
                h_lines = wrap_text(h_text, MAX_WIDTH, size=1, spacing=SPACING_SUBHEADER)
                for h_line in h_lines:
                    if y > 440: break
                    bold_text(h_line, x_offset + 20, y, black, size=1, spacing=SPACING_SUBHEADER)
                    y += 32
            else:
                # 正文使用常规字体，支持自动换行
                b_lines = wrap_text(line, MAX_WIDTH, size=1, spacing=SPACING_BODY)
                for b_line in b_lines:
                    if y > 440: break
                    fb.text(b_line, x_offset + 20, y, black, size=1, spacing=SPACING_BODY)
                    y += 28

    # --- 第一阶段：绘制黑色图层（文字） ---
    fb.fill(white)
    render_content(0, "INFO 1", info1_data[0], info1_data[1], only_lines=False)
    render_content(400, "INFO 2", info2_data[0], info2_data[1], only_lines=False)
    
    # 底部状态栏
    from config import TIMEZONE_OFFSET
    # ntptime.settime() 设置的是 UTC 时间，显示时需要加上偏移
    now_utc = utime.time()
    now_local = now_utc + (TIMEZONE_OFFSET * 3600)
    tm = utime.localtime(now_local)
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
    # 状态栏使用常规字体
    fb.text(status_str, 20, 460, black, size=1, spacing=SPACING_STATUS)
    
    epd.write_black_layer(buf)
    gc.collect() # 黑色层刷完后清理

    # --- 第二阶段：绘制黄色图层（分割线） ---
    fb.fill(white)
    render_content(0, "INFO 1", info1_data[0], info1_data[1], only_lines=True)
    render_content(400, "INFO 2", info2_data[0], info2_data[1], only_lines=True)
    
    epd.write_yellow_layer(buf, refresh=True)
    gc.collect()
