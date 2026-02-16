
def get_char_width(char, size=1, spacing=0):
    if ord(char) < 128 or ord(char) == 176:
        return (8 * size) + spacing
    else:
        return (16 * size) + spacing

def wrap_text(text, max_width, size=1, spacing=0):
    HEAD_FORBIDDEN = "，。、；：？！）》】'\"”’〉》」』】〕〗"
    TAIL_FORBIDDEN = "《（【“‘〈《「『【〔〖"
    lines = []
    current_line = ""
    current_width = 0
    last_soft_break = None 
    i = 0
    while i < len(text):
        char = text[i]
        cw = get_char_width(char, size, spacing)
        
        is_space = (char == ' ' or char == '\u3000')
        is_hyphen = (char == '-')
        is_boundary = False
        if i > 0:
            prev_char = text[i-1]
            curr_is_en = (ord(char) < 128 and char.isalpha())
            prev_is_en = (ord(prev_char) < 128 and prev_char.isalpha())
            if curr_is_en != prev_is_en:
                is_boundary = True

        if is_space or is_hyphen or is_boundary:
            safe_to_break = True
            if current_line.startswith('- ') or current_line.startswith('* '):
                if len(current_line) < 2: safe_to_break = False
            elif i > 0:
                first_space = current_line.find(' ')
                if first_space != -1 and first_space > 0 and current_line[first_space-1] == '.' and current_line[:first_space-1].isdigit():
                    if len(current_line) <= first_space: safe_to_break = False
            if safe_to_break:
                last_soft_break = (i, len(current_line), current_width, char)

        if current_width + cw > max_width:
            if last_soft_break:
                b_text_idx, b_line_len, b_width, b_char = last_soft_break
                # 断点必须不在行首才有意义
                if b_line_len > 0 and max_width - b_width <= 32:
                    next_char_idx = b_text_idx + 1 if (b_char == ' ' or b_char == '\u3000') else b_text_idx
                    if next_char_idx < len(text) and text[next_char_idx] in HEAD_FORBIDDEN and b_line_len > 1:
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
            
            move_to_next = char 
            temp_line = current_line
            if char in HEAD_FORBIDDEN and len(temp_line) > 0:
                move_to_next = temp_line[-1] + move_to_next
                temp_line = temp_line[:-1]
            if len(temp_line) > 0 and temp_line[-1] in TAIL_FORBIDDEN:
                move_to_next = temp_line[-1] + move_to_next
                temp_line = temp_line[:-1]
            
            if len(move_to_next) == 1 and temp_line and \
               ord(move_to_next) < 128 and move_to_next.isalpha() and \
               ord(temp_line[-1]) < 128 and temp_line[-1].isalpha():
                hyphen_w = get_char_width('-', size, spacing)
                if current_width + hyphen_w <= max_width:
                    temp_line += '-'
                elif len(temp_line) > 1:
                    move_to_next = temp_line[-1] + move_to_next
                    temp_line = temp_line[:-1] + '-'
            
            lines.append(temp_line)
            current_line = move_to_next
            current_width = 0
            for c in current_line:
                current_width += get_char_width(c, size, spacing)
            i += 1
            last_soft_break = None
        else:
            current_line += char
            current_width += cw
            i += 1
            
    if current_line:
        lines.append(current_line)
    return lines

# --- 测试用例 ---

def test(name, text, width):
    print(f"--- {name} (Width: {width}) ---")
    res = wrap_text(text, width)
    for idx, l in enumerate(res):
        print(f"L{idx+1}: |{l}|")

test("避头测试 1 (Boundary)", "数据ABC。", 48) # 在边界处断开
test("避头测试 2 (标点挪移)", "测试数据。", 64) # 据。应该一起移到下一行
test("避尾测试", "看看《重点内容", 64) # 《 应该移到下一行
test("全角空格", "中文\u3000测试", 32)
test("中英混合紧凑性", "中文测试Abcdefg", 80)
test("英文连字符", "Supercalifragilistic", 32)
test("列表项保护", "- ItemVeryLong", 24)
