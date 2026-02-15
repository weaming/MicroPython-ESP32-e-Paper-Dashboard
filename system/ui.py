import gc
import utime
from lib.epaper7in5b import black, white
from lib.framebuf2 import FrameBuffer, MHMSB

# 字间距配置 (0 为不额外增加间距)
SPACING_TITLE = 2
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
            # 优先找空格（英文单词换行），其次找连字符（-）
            last_space_idx = current_line.rfind(' ')
            last_hyphen_idx = current_line.rfind('-')
            
            valid_break = False
            
            # 检测是否为列表项开头 (- 或 1. )，如果是，则保护其不被切断
            safe_len = 0
            # 简单检测：- 或 * 开头
            if current_line.startswith('- ') or current_line.startswith('* '):
                safe_len = 2
            else:
                # 检测数字列表 1. 
                # 寻找第一个空格
                first_space = current_line.find(' ')
                if first_space > 1 and current_line[first_space-1] == '.' and \
                   current_line[:first_space-1].isdigit():
                     safe_len = first_space + 1

            # 比较哪个分割点更靠后（更优填充），且不在保护范围内
            # 保护范围：safe_len (例如 "- " 长度为 2，索引 0,1。space 在 1。我们不希望在 index < safe_len 处断开)
            # 但实际上，如果 content="- Item", last_space_idx=1. 
            # 我们希望 "Item" 换行吗？用户说 "如果是行首的 - ... 不要在这里换行"
            # 意思是不要把 "- " 留在上一行，而 "Item" 放到下一行？
            # 也就是：禁止在 safe_len 之前的 space/hyphen 处断行。
            
            # 修正逻辑：必须 > safe_len 才能断行？
            # 如果 "- Item" 太长，不在这里断，就会导致 "- Item" 整体作为 current_line (硬切)
            # 这样 "- " 和 "I" 还是在一起的。
            
            can_break_space = (last_space_idx != -1 and last_space_idx >= safe_len)
            can_break_hyphen = (last_hyphen_idx != -1 and last_hyphen_idx >= safe_len)
            
            if can_break_space and (not can_break_hyphen or last_space_idx > last_hyphen_idx):
                # 在空格处换行（空格丢弃）
                prefix = current_line[:last_space_idx]
                suffix = current_line[last_space_idx+1:] + char
                valid_break = True
            elif can_break_hyphen:
                # 在连字符后换行（连字符保留在上一行末尾）
                prefix = current_line[:last_hyphen_idx+1]
                suffix = current_line[last_hyphen_idx+1:] + char
                valid_break = True
            
            if valid_break:
                lines.append(prefix)
                current_line = suffix
                
                # 重新计算新一行的宽度
                current_width = 0
                for c in current_line:
                    current_width += get_char_width(c, size, spacing)
            else:
                # 没合适的断点，只能硬切
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
        MAX_WIDTH = 360 # 优化：利用更多宽度 (380 - 20)
        
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
            fb.line(x_offset + 20, 65, x_offset + 380, 65, black)
            fb.line(x_offset + 20, 66, x_offset + 380, 66, black)
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
