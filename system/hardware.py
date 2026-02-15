from machine import Pin, SPI
from lib import epaper7in5b
import gc

# Pin Definitions
# CS: Chip Select (GPIO 5)
# DC: Data/Command (GPIO 19)
# RST: Reset (GPIO 16)
# BUSY: Busy status (GPIO 17)
# SCK: Serial Clock (GPIO 18)
# MOSI: Master Out Slave In (GPIO 23)
# MISO: Master In Slave Out (GPIO 19)

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
        # Allocate buffer if not exists
        # 800 * 480 / 8 = 48000 bytes
        try:
            _buf = bytearray(epaper7in5b.EPD_WIDTH * epaper7in5b.EPD_HEIGHT // 8)
        except MemoryError:
            gc.collect()
            _buf = bytearray(epaper7in5b.EPD_WIDTH * epaper7in5b.EPD_HEIGHT // 8)
    return _buf


def init_display():
    """Initialize and return the EPD instance."""
    cs = Pin(PIN_CS)
    dc = Pin(PIN_DC)
    rst = Pin(PIN_RST)
    busy = Pin(PIN_BUSY)
    
    # SPI Configuration
    # Baudrate: 20MHz
    # MISO is not used by E-Paper (Write Enabled only), but SPI requires a pin. 
    # specific 'None' or unused pin. mapping MISO to 12 (MTDI, usually safe if not strapped) or similar unwanted.
    # actually, just removing it or setting to a non-conflicting pin. 
    # Let's map MISO to 12 to avoid 19 (DC)
    spi = SPI(2, baudrate=20000000, polarity=0, phase=0, 
              sck=Pin(PIN_SCK), miso=Pin(12), mosi=Pin(PIN_MOSI))
    
    epd = epaper7in5b.EPD(spi, cs, dc, rst, busy)
    epd.init()
    return epd
