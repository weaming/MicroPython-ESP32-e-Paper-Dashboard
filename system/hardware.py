from machine import Pin, SPI
from lib import epaper7in5b
import gc

# Pin Definitions
# CS: Chip Select (GPIO 5)
# DC: Data/Command (GPIO 19)
# RST: Reset (GPIO 16)
# BUSY: Busy status (GPIO 17, LOW=busy)
# SCK: Serial Clock (GPIO 18)
# MOSI: Master Out Slave In (GPIO 23)
# MISO: GPIO 12 (墨水屏只写，不使用 MISO，但 SPI 构造函数需要)

PIN_CS = 5
PIN_DC = 19
PIN_RST = 16
PIN_BUSY = 17
PIN_SCK = 18
PIN_MOSI = 23
PIN_MISO = 19

# Global Buffer
# Shared buffer to save memory, sized for 800x480 resolution (1-bit depth)
_buf = None


def get_buffer():
    global _buf
    if _buf is None:
        # 分配缓冲区前先释放内存
        gc.collect()
        free_before = gc.mem_free()
        print(f"Free memory before buffer allocation: {free_before} bytes")
        
        # 800 * 480 / 8 = 48000 bytes
        buffer_size = epaper7in5b.EPD_WIDTH * epaper7in5b.EPD_HEIGHT // 8
        
        try:
            _buf = bytearray(buffer_size)
            print(f"Buffer allocated: {buffer_size} bytes")
        except MemoryError as e:
            print(f"Failed to allocate buffer: {buffer_size} bytes")
            print(f"Free memory: {gc.mem_free()} bytes")
            raise
    return _buf


def init_display():
    """Initialize and return the EPD instance."""
    try:
        cs = Pin(PIN_CS)
        dc = Pin(PIN_DC)
        rst = Pin(PIN_RST)
        busy = Pin(PIN_BUSY)
        
        spi = SPI(2, baudrate=20000000, polarity=0, phase=0, 
                  sck=Pin(PIN_SCK), miso=Pin(12), mosi=Pin(PIN_MOSI))
        
        epd = epaper7in5b.EPD(spi, cs, dc, rst, busy)
        epd.init()
        return epd
    except Exception as e:
        print(f"Display initialization failed: {e}")
        raise
