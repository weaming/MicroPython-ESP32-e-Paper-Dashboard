#!/usr/bin/env python3
"""
统一字体生成工具

生成包含 ASCII + 中文的 16×16 位图字体文件
- ASCII: 32-126 (95 个字符)
- 中文: CJK 统一汉字 (约 20902 个字符)
- 总计: 约 2.1w 字符，约 780KB
"""

import struct
import os
import sys
from PIL import Image, ImageDraw, ImageFont


FONT_WIDTH = 16
FONT_HEIGHT = 16
MAGIC_NUMBER = 0x5546

ASCII_START = 32
ASCII_END = 126
ASCII_COUNT = ASCII_END - ASCII_START + 1


def get_system_font():
    """获取选定的中文字体（优先使用 ChillBitmap）"""
    font_paths = [
        'fonts/16px/ChillBitmap_16px.ttf',
        'fonts/12px/fusion-pixel-12px-monospaced-zh_hans.ttf',
        'fonts/12px/zpix-12px.ttf',
        'fonts/16px/WenQuanYi.Bitmap.Song.16px.ttf',
        '/System/Library/Fonts/PingFang.ttc',
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            print(f"Using fonts: {font_path}")
            try:
                # 对于原生就是 16px 的点阵字体，使用其原生高
                size = 16 if '16px' in font_path else 12
                f = ImageFont.truetype(font_path, size)
                f.path = font_path # PIL 某些版本可能没有这个属性，手动补一下
                return f
            except Exception as e:
                print(f"Failed to load {font_path}: {e}")
                continue
    
    raise RuntimeError("无法找到合适的中文字体，请手动指定字体路径")


def render_char_to_bitmap(char, font):
    """将字符渲染为 16×16 位图，优化垂直对齐（基准线对齐）"""
    # 背景为白(1)，画笔为黑(0)
    img = Image.new('1', (FONT_WIDTH, FONT_HEIGHT), 1)
    draw = ImageDraw.Draw(img)
    
    # 垂直对齐策略：
    # 1. ASCII 字符 (如 'j', 'g', 'p', 'y')：通常这些字有下沉部 (descender)，
    #    但上面有大量留白。为了不切掉尾巴，我们需要将其向上平移 2~3 像素。
    # 2. 中文字符：通常是 16x16 满格的。如果向上平移太多，顶部会被切掉。
    #    所以中文字符保持不动 (y=0) 或仅微调。
    
    if ord(char) < 128:
        # ASCII: 向上平移 1 像素以容纳下沉部 (折衷方案：保留大部分尾巴，且与中文对齐更好)
        x, y = 0, -1
    else:
        # 中文/全角: 保持原位（或者 -1 如果字库本身偏下）
        # 经观察 ChillBitmap 16px 中文垂直居中较好，无需偏移，否则削头
        x, y = 0, 0
    
    draw.text((x, y), char, font=font, fill=0)
    
    bitmap = []
    for row in range(FONT_HEIGHT):
        row_bytes = []
        for col_byte in range(FONT_WIDTH // 8):
            byte_val = 0
            for bit in range(8):
                col = col_byte * 8 + bit
                pixel = img.getpixel((col, row))
                if pixel == 0:
                    byte_val |= (1 << (7 - bit))
            row_bytes.append(byte_val)
        bitmap.extend(row_bytes)
    
    return bytes(bitmap)




def get_common_chinese_chars():
    """获取完整的 CJK 统一汉字范围，确保覆盖所有常用字"""
    chars_set = set()
    
    # Dashboard 必须包含的字
    dashboard_chars = "墨水屏仪表盘温度湿度电压电量唤醒次数状态运行中"
    for c in dashboard_chars:
        chars_set.add(c)
    
    # CJK 统一汉字基本区 (U+4E00 - U+9FA5)
    for code in range(0x4E00, 0x9FA5 + 1):
        chars_set.add(chr(code))
    
    # 常用符号 (包括摄氏度符号 ° 等)
    symbols = "°±×÷αβγδεζηθικλμνξοπρστυφχψω"
    # 中文标点
    punctuation = "，。、；：？！“”‘’（）【】《》…—·～"
    
    for c in symbols + punctuation:
        chars_set.add(c)
        
    return sorted(list(chars_set))


def generate_unified_font(output_path):
    """生成统一字体文件"""
    print("正在加载字体...")
    font = get_system_font()
    
    print("正在生成字符列表...")
    ascii_chars = [chr(i) for i in range(ASCII_START, ASCII_END + 1)]
    chinese_chars = get_common_chinese_chars()
    
    all_chars = sorted(list(set(ascii_chars + chinese_chars)), key=lambda x: ord(x))
    total_chars = len(all_chars)
    
    print(f"总字符数: {total_chars}")
    
    with open(output_path, 'wb') as f:
        print("正在写入文件头...")
        f.write(struct.pack('<H', MAGIC_NUMBER))
        f.write(struct.pack('<H', FONT_WIDTH))
        f.write(struct.pack('<H', FONT_HEIGHT))
        f.write(struct.pack('<H', total_chars))
        
        print("正在生成索引表...")
        data_start_offset = 8 + total_chars * 6
        
        for i, char in enumerate(all_chars):
            unicode_val = ord(char)
            offset = data_start_offset + i * 32
            f.write(struct.pack('<H', unicode_val))
            f.write(struct.pack('<I', offset))
        
        print("正在渲染并写入字符位图...")
        for i, char in enumerate(all_chars):
            if (i + 1) % 1000 == 0:
                print(f"  进度: {i + 1}/{total_chars}")
            
            bitmap = render_char_to_bitmap(char, font)
            f.write(bitmap)
    
    file_size = os.path.getsize(output_path)
    print(f"\n✓ 字体文件生成成功: {output_path}")
    print(f"  文件大小: {file_size / 1024:.1f} KB")


if __name__ == '__main__':
    output_file = './unified_font.bin'
    generate_unified_font(output_file)
