# copy from https://github.com/lijiachang/MicroPython-ESP32-e-Paper-Crypto-Display/blob/main/newframebuf.py
# full version: https://github.com/adafruit/Adafruit_CircuitPython_framebuf/blob/main/adafruit_framebuf.py

import os
import struct

# Framebuf format constants:
MHMSB = 1  # Single bit displays like the Sharp Memory


class FrameBuffer:
    def __init__(self, buf, width, height, buf_format=MHMSB, stride=None):
        # pylint: disable=too-many-arguments
        self.buf = buf
        self.width = width
        self.height = height
        self.stride = stride
        self._font = None
        if self.stride is None:
            self.stride = width
        if buf_format == MHMSB:
            self.format = MHMSBFormat()
        else:
            raise ValueError("invalid format")
        self._rotation = 0

    @property
    def rotation(self):
        """The rotation setting of the display, can be one of (0, 1, 2, 3)"""
        return self._rotation

    @rotation.setter
    def rotation(self, val):
        if not val in (0, 1, 2, 3):
            raise RuntimeError("Bad rotation setting")
        self._rotation = val

    def fill(self, color):
        """Fill the entire FrameBuffer with the specified color."""
        self.format.fill(self, color)

    def fill_rect(self, x, y, width, height, color):
        """Draw a rectangle at the given location, size and color. The ``fill_rect`` method draws
        both the outline and interior."""
        # pylint: disable=too-many-arguments, too-many-boolean-expressions
        self.rect(x, y, width, height, color, fill=True)

    def pixel(self, x, y, color=None):
        """If ``color`` is not given, get the color value of the specified pixel. If ``color`` is
        given, set the specified pixel to the given color."""
        if self.rotation == 1:
            x, y = y, x
            x = self.width - x - 1
        if self.rotation == 2:
            x = self.width - x - 1
            y = self.height - y - 1
        if self.rotation == 3:
            x, y = y, x
            y = self.height - y - 1

        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return None
        if color is None:
            return self.format.get_pixel(self, x, y)
        self.format.set_pixel(self, x, y, color)
        return None

    def hline(self, x, y, width, color):
        """Draw a horizontal line up to a given length."""
        self.rect(x, y, width, 1, color, fill=True)

    def vline(self, x, y, height, color):
        """Draw a vertical line up to a given length."""
        self.rect(x, y, 1, height, color, fill=True)

    def circle(self, center_x, center_y, radius, color):
        """Draw a circle at the given midpoint location, radius and color.
        The ```circle``` method draws only a 1 pixel outline."""
        x = radius - 1
        y = 0
        d_x = 1
        d_y = 1
        err = d_x - (radius << 1)
        while x >= y:
            self.pixel(center_x + x, center_y + y, color)
            self.pixel(center_x + y, center_y + x, color)
            self.pixel(center_x - y, center_y + x, color)
            self.pixel(center_x - x, center_y + y, color)
            self.pixel(center_x - x, center_y - y, color)
            self.pixel(center_x - y, center_y - x, color)
            self.pixel(center_x + y, center_y - x, color)
            self.pixel(center_x + x, center_y - y, color)
            if err <= 0:
                y += 1
                err += d_y
                d_y += 2
            if err > 0:
                x -= 1
                d_x += 2
                err += d_x - (radius << 1)

    def rect(self, x, y, width, height, color, *, fill=False):
        """Draw a rectangle at the given location, size and color. The ```rect``` method draws only
        a 1 pixel outline."""
        # pylint: disable=too-many-arguments
        if self.rotation == 1:
            x, y = y, x
            width, height = height, width
            x = self.width - x - width
        if self.rotation == 2:
            x = self.width - x - width
            y = self.height - y - height
        if self.rotation == 3:
            x, y = y, x
            width, height = height, width
            y = self.height - y - height

        # pylint: disable=too-many-boolean-expressions
        if width < 1 or height < 1 or (x + width) <= 0 or (y + height) <= 0 or y >= self.height or x >= self.width:
            return
        x_end = min(self.width - 1, x + width - 1)
        y_end = min(self.height - 1, y + height - 1)
        x = max(x, 0)
        y = max(y, 0)
        if fill:
            self.format.fill_rect(self, x, y, x_end - x + 1, y_end - y + 1, color)
        else:
            self.format.fill_rect(self, x, y, x_end - x + 1, 1, color)
            self.format.fill_rect(self, x, y, 1, y_end - y + 1, color)
            self.format.fill_rect(self, x, y_end, x_end - x + 1, 1, color)
            self.format.fill_rect(self, x_end, y, 1, y_end - y + 1, color)

    def line(self, x_0, y_0, x_1, y_1, color):
        # pylint: disable=too-many-arguments
        """Bresenham's line algorithm"""
        d_x = abs(x_1 - x_0)
        d_y = abs(y_1 - y_0)
        x, y = x_0, y_0
        s_x = -1 if x_0 > x_1 else 1
        s_y = -1 if y_0 > y_1 else 1
        if d_x > d_y:
            err = d_x / 2.0
            while x != x_1:
                self.pixel(x, y, color)
                err -= d_y
                if err < 0:
                    y += s_y
                    err += d_x
                x += s_x
        else:
            err = d_y / 2.0
            while y != y_1:
                self.pixel(x, y, color)
                err -= d_x
                if err < 0:
                    x += s_x
                    err += d_y
                y += s_y
        self.pixel(x, y, color)

    def blit(self):
        """blit is not yet implemented"""
        raise NotImplementedError()

    def scroll(self, delta_x, delta_y):
        """shifts framebuf in x and y direction"""
        if delta_x < 0:
            shift_x = 0
            xend = self.width + delta_x
            dt_x = 1
        else:
            shift_x = self.width - 1
            xend = delta_x - 1
            dt_x = -1
        if delta_y < 0:
            y = 0
            yend = self.height + delta_y
            dt_y = 1
        else:
            y = self.height - 1
            yend = delta_y - 1
            dt_y = -1
        while y != yend:
            x = shift_x
            while x != xend:
                self.format.set_pixel(self, x, y, self.format.get_pixel(self, x - delta_x, y - delta_y))
                x += dt_x
            y += dt_y

    # pylint: disable=too-many-arguments
    def text(self, string, x, y, color, *, font_name="font5x8.bin", size=1, spacing=0):
        """Place text on the screen in variables sizes. Breaks on \n to next line.
        Does not break on line going off screen.
        """
        try:
            from config import ENABLE_UNIFIED_FONT, UNIFIED_FONT_FILE
            use_unified = ENABLE_UNIFIED_FONT
            unified_font_file = UNIFIED_FONT_FILE
        except ImportError:
            use_unified = False
            unified_font_file = "unified_font.bin"
        
        frame_width = self.width
        frame_height = self.height
        if self.rotation in (1, 3):
            frame_width, frame_height = frame_height, frame_width

        for chunk in string.split("\n"):
            if use_unified:
                if not self._font or not isinstance(self._font, UnifiedBitmapFont):
                    self._font = UnifiedBitmapFont(unified_font_file)
                width = self._font.font_width
                height = self._font.font_height
            else:
                if not self._font or self._font.font_name != font_name:
                    self._font = BitmapFont(font_name)
                width = self._font.font_width
                height = self._font.font_height
            
            cursor_x = x
            for char in chunk:
                if (
                    cursor_x + (width * size) > 0
                    and cursor_x < frame_width
                    and y + (height * size) > 0
                    and y < frame_height
                ):
                    self._font.draw_char(char, cursor_x, y, self, color, size=size)
                
                # 双步进逻辑：ASCII 半角 (8px)，中文 全角 (16px)
                if use_unified and ord(char) < 128:
                    cursor_x += (width // 2) * size + spacing
                else:
                    cursor_x += (width + (0 if use_unified else 1)) * size + spacing
            y += height * size

    # pylint: enable=too-many-arguments

    def image(self, img):
        """Set buffer to value of Python Imaging Library image.  The image should
        be in 1 bit mode and a size equal to the display size."""
        # determine our effective width/height, taking rotation into account
        width = self.width
        height = self.height
        if self.rotation in (1, 3):
            width, height = height, width

        imwidth, imheight = img.size
        if imwidth != width or imheight != height:
            raise ValueError("Image must be same dimensions as display ({0}x{1}).".format(width, height))
        # Grab all the pixels from the image, faster than getpixel.
        pixels = img.load()
        # Clear buffer
        for i in range(len(self.buf)):  # pylint: disable=consider-using-enumerate
            self.buf[i] = 0
        # Iterate through the pixels
        for x in range(width):  # yes this double loop is slow,
            for y in range(height):  #  but these displays are small!
                if img.mode == "RGB":
                    self.pixel(x, y, pixels[(x, y)])
                elif pixels[(x, y)]:
                    self.pixel(x, y, 1)  # only write if pixel is true

    def print(self):
        print("." * (self.width + 2))
        for y in range(self.height):
            print(".", end="")
            prev = '*'
            n = 0
            for x in range(self.width):
                if self.pixel(x, y):
                    if prev != '*':
                        print(f'{n}*', end='')
                        n = 0
                        prev = '*'
                    n += 1
                    # print("*", end="")
                else:
                    if prev != ' ':
                        print(f'{n} ', end='')
                        n = 0
                        prev = ' '
                    n += 1
                    # print(" ", end="")
            print(".")
        print("." * (self.width + 2))


class MHMSBFormat:
    """MHMSBFormat"""

    @staticmethod
    def set_pixel(framebuf: FrameBuffer, x, y, color):
        """Set a given pixel to a color."""
        index = (y * framebuf.stride + x) // 8
        offset = 7 - x & 0x07
        framebuf.buf[index] = (framebuf.buf[index] & ~(0x01 << offset)) | ((color != 0) << offset)

    @staticmethod
    def get_pixel(framebuf: FrameBuffer, x, y):
        """Get the color of a given pixel"""
        index = (y * framebuf.stride + x) // 8
        offset = 7 - x & 0x07
        return (framebuf.buf[index] >> offset) & 0x01

    @staticmethod
    def fill(framebuf: FrameBuffer, color):
        """completely fill/clear the buffer with a color"""
        if color:
            fill = 0xFF
        else:
            fill = 0x00
        for i in range(len(framebuf.buf)):  # pylint: disable=consider-using-enumerate
            framebuf.buf[i] = fill

    @staticmethod
    def fill_rect(framebuf: FrameBuffer, x, y, width, height, color):
        """Draw a rectangle at the given location, size and color. The ``fill_rect`` method draws
        both the outline and interior."""
        # pylint: disable=too-many-arguments
        for _x in range(x, x + width):
            offset = 7 - _x & 0x07
            for _y in range(y, y + height):
                index = (_y * framebuf.stride + _x) // 8
                framebuf.buf[index] = (framebuf.buf[index] & ~(0x01 << offset)) | ((color != 0) << offset)


# MicroPython basic bitmap font renderer.
# Author: Tony DiCola
# License: MIT License (https://opensource.org/licenses/MIT)
class BitmapFont:
    """A helper class to read binary font tiles and 'seek' through them as a
    file to display in a framebuffer. We use file access so we dont waste 1KB
    of RAM on a font!"""

    def __init__(self, font_name="font5x8.bin"):
        # Specify the drawing area width and height, and the pixel function to
        # call when drawing pixels (should take an x and y param at least).
        # Optionally specify font_name to override the font file to use (default
        # is font5x8.bin).  The font format is a binary file with the following
        # format:
        # - 1 unsigned byte: font character width in pixels
        # - 1 unsigned byte: font character height in pixels
        # - x bytes: font data, in ASCII order covering all 255 characters.
        #            Each character should have a byte for each pixel column of
        #            data (i.e. a 5x8 font has 5 bytes per character).
        self.font_name = font_name

        # Open the font file and grab the character width and height values.
        # Note that only fonts up to 8 pixels tall are currently supported.
        try:
            self._font = open(self.font_name, "rb")  # pylint: disable=consider-using-with
            self.font_width, self.font_height = struct.unpack("BB", self._font.read(2))
            # simple font file validation check based on expected file size
            if 2 + 256 * self.font_width != os.stat(font_name)[6]:
                raise RuntimeError("Invalid font file: " + font_name)
        except OSError:
            print("Could not find font file", font_name)
            raise
        except OverflowError:
            # os.stat can throw this on boards without long int support
            # just hope the font file is valid and press on
            pass

    def deinit(self):
        """Close the font file as cleanup."""
        self._font.close()

    def __enter__(self):
        """Initialize/open the font file"""
        self.__init__()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """cleanup on exit"""
        self.deinit()

    def draw_char(self, char, x, y, framebuffer, color, size=1):  # pylint: disable=too-many-arguments
        """Draw one character at position (x,y) to a framebuffer in a given color"""
        size = max(size, 1)
        # Don't draw the character if it will be clipped off the visible area.
        # if x < -self.font_width or x >= framebuffer.width or \
        #   y < -self.font_height or y >= framebuffer.height:
        #    return
        # Go through each column of the character.
        for char_x in range(self.font_width):
            # Grab the byte for the current column of font data.
            self._font.seek(2 + (ord(char) * self.font_width) + char_x)
            try:
                line = struct.unpack("B", self._font.read(1))[0]
            except RuntimeError:
                continue  # maybe character isnt there? go to next
            # Go through each row in the column byte.
            for char_y in range(self.font_height):
                # Draw a pixel for each bit that's flipped on.
                if (line >> char_y) & 0x1:
                    framebuffer.fill_rect(x + char_x * size, y + char_y * size, size, size, color)

    def width(self, text):
        """Return the pixel width of the specified text message."""
        return len(text) * (self.font_width + 1)


class UnifiedBitmapFont:
    """
    统一字体类，支持 ASCII + 中文的 16×16 位图字体
    使用按需加载和 LRU 缓存机制
    """
    
    def __init__(self, font_name="unified_font.bin", cache_size=30):
        self.font_name = font_name
        self.cache_size = cache_size
        self.font_width = 16
        self.font_height = 16
        self._cache = {}
        self._cache_order = []
        self.char_count = 0
        self.index_offset = 8
        self._f = None
        
        try:
            self._f = open(self.font_name, "rb")
            magic = struct.unpack('<H', self._f.read(2))[0]
            if magic != 0x5546:
                raise RuntimeError("Invalid unified font file")
            
            self.font_width = struct.unpack('<H', self._f.read(2))[0]
            self.font_height = struct.unpack('<H', self._f.read(2))[0]
            self.char_count = struct.unpack('<H', self._f.read(2))[0]
        except OSError:
            print(f"Could not find font file {font_name}")
            if self._f: self._f.close()
            raise
    
    def _find_char_offset(self, char_code):
        """使用二分查找在文件中查找字符偏移量"""
        if not self._f: return None
        try:
            left = 0
            right = self.char_count - 1
            
            while left <= right:
                mid = (left + right) // 2
                self._f.seek(self.index_offset + mid * 6)
                
                unicode_val = struct.unpack('<H', self._f.read(2))[0]
                
                if unicode_val == char_code:
                    offset = struct.unpack('<I', self._f.read(4))[0]
                    return offset
                elif unicode_val < char_code:
                    left = mid + 1
                else:
                    right = mid - 1
            
            return None
        except Exception as e:
            print(f"Error finding char {char_code}: {e}")
            return None
    
    def _load_char(self, char_code):
        """从文件加载字符位图"""
        if char_code in self._cache:
            self._cache_order.remove(char_code)
            self._cache_order.append(char_code)
            return self._cache[char_code]
        
        offset = self._find_char_offset(char_code)
        if offset is None:
            return None
        
        try:
            self._f.seek(offset)
            bitmap = self._f.read(32)
            
            if len(self._cache) >= self.cache_size:
                oldest = self._cache_order.pop(0)
                del self._cache[oldest]
            
            self._cache[char_code] = bitmap
            self._cache_order.append(char_code)
            
            return bitmap
        except Exception as e:
            print(f"Error loading char {char_code}: {e}")
            return None
    
    def draw_char(self, char, x, y, framebuffer, color, size=1):
        """绘制单个字符"""
        size = max(size, 1)
        char_code = ord(char)
        
        bitmap = self._load_char(char_code)
        if bitmap is None:
            return
        
        for row in range(self.font_height):
            for col_byte in range(self.font_width // 8):
                byte_idx = row * (self.font_width // 8) + col_byte
                if byte_idx >= len(bitmap):
                    continue
                
                byte_val = bitmap[byte_idx]
                
                for bit in range(8):
                    if byte_val & (1 << (7 - bit)):
                        px = x + (col_byte * 8 + bit) * size
                        py = y + row * size
                        framebuffer.fill_rect(px, py, size, size, color)
    
    def width(self, text):
        """返回文本的像素宽度（支持 ASCII 半宽和中文全宽）"""
        total_w = 0
        for char in text:
            if ord(char) < 128:
                total_w += self.font_width // 2
            else:
                total_w += self.font_width
        return total_w
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_order.clear()
    
    def deinit(self):
        """清理资源"""
        self.clear_cache()
        if self._f:
            self._f.close()
            self._f = None
