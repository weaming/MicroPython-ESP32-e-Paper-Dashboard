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
    高性能 O(n) 换行算法
    支持：1. 避头尾 2. 紧凑换行 3. 中英文混合 4. 英文连字符 5. 列表项保护 6. 全角空格
    """
    # 避头尾配置
    HEAD_FORBIDDEN = "，。、；：？！）》】'\"”’〉》」』】〕〗"
    TAIL_FORBIDDEN = "《（【“‘〈《「『【〔〖"
    
    lines = []
    current_line = ""
    current_width = 0
    
    # 记录最后一次“好”的断点位置 (以便回溯)
    # (index_in_text, current_line_length, current_width_at_break, break_type)
    last_soft_break = None 
    
    i = 0
    while i < len(text):
        char = text[i]
        cw = get_char_width(char, size, spacing)
        
        # 记录潜在断点：空格、全角空格、连字符、或是中英文边界
        is_space = (char == ' ' or char == '\u3000')
        is_hyphen = (char == '-')
        
        # 边界检测：当前是英文/数字，且前一个是非英文/数字
        is_boundary = False
        if i > 0:
            prev_char = text[i-1]
            curr_is_en = (ord(char) < 128 and char.isalpha())
            prev_is_en = (ord(prev_char) < 128 and prev_char.isalpha())
            if curr_is_en != prev_is_en:
                is_boundary = True

        # 如果当前是一个合法的断开点
        if is_space or is_hyphen or is_boundary:
            # 记录断点信息。如果是空格，断点在空格前；如果是连字符，断点在连字符后。
            # 这里简化记录：记录当前已累积的长度和宽度
            # marker 保护：如果处于列表标记内，不记录断点
            safe_to_break = True
            if current_line.startswith('- ') or current_line.startswith('* '):
                if len(current_line) < 2: safe_to_break = False
            elif i > 0:
                # 简单数字列表检测 (1. )
                first_space = current_line.find(' ')
                if first_space != -1 and first_space > 0 and current_line[first_space-1] == '.' and current_line[:first_space-1].isdigit():
                    if len(current_line) <= first_space: safe_to_break = False

            if safe_to_break:
                last_soft_break = (i, len(current_line), current_width, char)

        if current_width + cw > max_width:
            # 需要换行！
            break_idx = -1
            
            # --- 方案 A: 尝试之前的软断点 ---
            if last_soft_break:
                b_text_idx, b_line_len, b_width, b_char = last_soft_break
                # 断点必须不在行首才有意义
                if b_line_len > 0 and max_width - b_width <= 32:
                    # 检查 Kinsoku：如果断点后的第一个字是避头标点
                    next_char_idx = b_text_idx + 1 if (b_char == ' ' or b_char == '\u3000') else b_text_idx
                    if next_char_idx < len(text) and text[next_char_idx] in HEAD_FORBIDDEN and b_line_len > 1:
                        # 触发避头：再往前挪一个字
                        # 注意：这里我们简单地放弃该软断点，走方案 B (硬切+避头处理)
                        pass 
                    else:
                        if b_char == ' ' or b_char == '\u3000':
                            prefix = current_line[:b_line_len]
                            lines.append(prefix)
                            current_line = ""
                            current_width = 0
                            i = b_text_idx + 1 
                            last_soft_break = None
                            continue
                        else:
                            prefix = current_line[:b_line_len]
                            lines.append(prefix)
                            current_line = ""
                            current_width = 0
                            i = b_text_idx
                            last_soft_break = None
                            continue
            
            # --- 方案 B: 避头尾与硬切 ---
            # 这里的逻辑是：如果当前字 char 是“避头”标点，则把上一行的最后一个字挪到下一行。
            # 如果上一行末尾是“避尾”标点，则把该标点也挪到下一行。
            move_to_next = char 
            temp_line = current_line
            
            # 避头处理
            if char in HEAD_FORBIDDEN and len(temp_line) > 0:
                move_to_next = temp_line[-1] + move_to_next
                temp_line = temp_line[:-1]
            
            # 避尾处理 (检查 temp_line 末尾)
            if len(temp_line) > 0 and temp_line[-1] in TAIL_FORBIDDEN:
                move_to_next = temp_line[-1] + move_to_next
                temp_line = temp_line[:-1]
            
            # --- 方案 C: 英文连字符补全 ---
            # 只有在没有进行避头尾挪动，且是在英文单词中间切断时才加连字符
            if len(move_to_next) == 1 and temp_line and \
               ord(move_to_next) < 128 and move_to_next.isalpha() and \
               ord(temp_line[-1]) < 128 and temp_line[-1].isalpha():
                
                hyphen_w = get_char_width('-', size, spacing)
                if current_width + hyphen_w <= max_width:
                    temp_line += '-'
                elif len(temp_line) > 1:
                    # 挪一个字母走，补连字符
                    move_to_next = temp_line[-1] + move_to_next
                    temp_line = temp_line[:-1] + '-'
            
            lines.append(temp_line)
            current_line = move_to_next
            current_width = 0
            for c in current_line:
                current_width += get_char_width(c, size, spacing)
            
            i += 1 # 消费了当前的 char
            last_soft_break = None
        else:
            current_line += char
            current_width += cw
            i += 1
            
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
