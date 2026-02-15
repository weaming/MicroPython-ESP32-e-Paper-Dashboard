"""
copy from https://github.com/mcauser/micropython-waveshare-epaper/blob/master/epaper7in5b.py

MicroPython Waveshare 7.5" Black/White/Red GDEY075Z08 e-paper display driver
MicroPython Waveshare 7.5" Black/White/Yellow GDEW075C64 e-paper display driver
"""

from micropython import const
from utime import sleep_ms
import ustruct

# Display resolution
# https://www.e-paper-display.cn/products_detail/productId=474.html
EPD_WIDTH = const(800)
EPD_HEIGHT = const(480)

# Display commands, copy from https://github.com/zhufucdev/gdey075z08_driver/blob/main/src/gdey075z08_driver/driver.py
PANEL_SETTING = 0x00
POWER_SETTING = 0x01
POWER_OFF = 0x02
POWER_OFF_SEQUENCE_SETTING = 0x03
POWER_ON = 0x04
POWER_ON_MEASURE = 0x05
BOOSTER_SOFT_START = 0x06
DEEP_SLEEP = 0x07
DATA_START_TRANSMISSION_1 = 0x10
DATA_STOP = 0x11
DISPLAY_REFRESH = 0x12
DATA_START_TRANSMISSION_2 = 0x13
LUT_FOR_VCOM = 0x20
LUT_BLUE = 0x21
LUT_WHITE = 0x22
LUT_GRAY_1 = 0x23
LUT_GRAY_2 = 0x24
LUT_RED_0 = 0x25
LUT_RED_1 = 0x26
LUT_RED_2 = 0x27
LUT_RED_3 = 0x28
LUT_XON = 0x29
PLL_CONTROL = 0x30
TEMPERATURE_SENSOR_COMMAND = 0x40
TEMPERATURE_CALIBRATION = 0x41
TEMPERATURE_SENSOR_WRITE = 0x42
TEMPERATURE_SENSOR_READ = 0x43
VCOM_AND_DATA_INTERVAL_SETTING = 0x50
LOW_POWER_DETECTION = 0x51
TCON_SETTING = 0x60
TCON_RESOLUTION = 0x61
SPI_FLASH_CONTROL = 0x65
REVISION = 0x70
GET_STATUS = 0x71
AUTO_MEASUREMENT_VCOM = 0x80
READ_VCOM_VALUE = 0x81
VCM_DC_SETTING = 0x82
FLASH_MODE = const(0xE5)

BUSY = const(0)  # 0=busy, 1=idle
WHITE = const(0xFF)

black = yellow = 0
white = 1

DEBUG = False


class EPD:
    def __init__(self, spi, cs, dc, rst, busy, yellow_bounds=(64, 192)):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.busy = busy
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=0)
        self.busy.init(self.busy.IN)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.yellow_bounds = yellow_bounds
        self._inited = False

    def _command(self, command, data=None):
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([command]))
        self.cs(1)
        if data is not None:
            self._data(data)

    def _data(self, data):
        self.dc(1)
        self.cs(0)
        if isinstance(data, int):
            data = data.to_bytes(1, 'big')
        self.spi.write(data)
        self.cs(1)

    def init(self):
        if self._inited:
            return
        self._inited = True

        print('init...')
        self.reset()
        self._command(POWER_SETTING, b'\x37\x00')
        self._command(PANEL_SETTING, b'\xCF\x08')
        self._command(BOOSTER_SOFT_START, b'\xC7\xCC\x28')
        self._command(POWER_ON)
        self.wait_until_idle()
        self._command(PLL_CONTROL, b'\x3C')
        self._command(TEMPERATURE_CALIBRATION, b'\x00')
        self._command(VCOM_AND_DATA_INTERVAL_SETTING, b'\x77')
        self._command(TCON_SETTING, b'\x22')
        self._command(TCON_RESOLUTION, ustruct.pack(">HH", EPD_WIDTH, EPD_HEIGHT))
        self._command(VCM_DC_SETTING, b'\x1E')  # decide by LUT file
        self._command(FLASH_MODE, b'\x03')
        print('inited.')

    def wait_until_idle(self):
        ms = 100
        ms_max = 3000
        while self.busy.value() == BUSY:
            if ms < ms_max:
                ms *= 2
            sleep_ms(min(ms, ms_max))

    def reset(self):
        self.rst(0)
        sleep_ms(200)
        self.rst(1)
        sleep_ms(200)

    # to wake call reset() or init()
    def sleep(self):
        self._command(POWER_OFF)
        self.wait_until_idle()
        self._command(DEEP_SLEEP, b'\xA5')

    # functions for display

    def clear_frame(self, buf_black, buf_yellow=None):
        for i in range(int(self.width * self.height / 8)):
            buf_black[i] = WHITE
            if buf_yellow is not None:
                buf_yellow[i] = WHITE

    # copy from https://github.com/zhufucdev/gdey075z08_driver/blob/main/src/gdey075z08_driver/driver.py#L155
    # pixels of 8bit image with 256 colors of each pixel
    def get_frame_buffer(self, pixels: [bytes]):
        buf_black = [WHITE] * int(self.height * self.width / 8)
        buf_yellow = [0x00] * int(self.height * self.width / 8)

        for y in range(self.height):
            for x in range(int(self.width / 8)):
                sign_w = WHITE
                sign_y = 0x00
                for i in range(0, 8):
                    p = pixels[x * 8 + i, y]
                    # 0x80 = 0b10000000
                    if p < self.yellow_bounds[0]:
                        sign_w &= ~(0x80 >> i)  # set from black to black
                    elif p < self.yellow_bounds[1]:
                        sign_y |= 0x80 >> i  # set from black to yellow
                index = x + int(y * self.width / 8)
                buf_black[index] = sign_w
                buf_yellow[index] = sign_y
        return buf_black, buf_yellow

    def write_buffer(self, buf):
        for data in buf:
            self._data(data)
        sleep_ms(100)

    def write_black_layer(self, buf, refresh=False):
        print('write_black_layer...')
        self._command(DATA_START_TRANSMISSION_1)
        self.write_buffer(buf)
        if refresh:
            print('display refresh ...')
            self._command(DISPLAY_REFRESH)
            self.wait_until_idle()

    def write_yellow_layer(self, buf, refresh=False):
        print('write_yellow_layer...')
        self._command(DATA_START_TRANSMISSION_2)
        self.write_buffer(buf)
        if refresh:
            print('display refresh ...')
            self._command(DISPLAY_REFRESH)
            self.wait_until_idle()

    def clear_screen(self):
        print('clear_screen...')
        self.clear_black_layer()
        self.clear_yellow_layer()
        print('screen cleared.')

    def clear_black_layer(self):
        self._command(DATA_START_TRANSMISSION_1)
        for _ in range(0, self.width * self.height // 8):
            self._data(WHITE)

    def clear_yellow_layer(self):
        self._command(DATA_START_TRANSMISSION_2)
        for _ in range(0, self.width * self.height // 8):
            self._data(WHITE)

    def display_frame(self, buf_black, buf_yellow=None):
        print('display_frame...')

        if buf_black:
            self.write_black_layer(buf_black)
        elif buf_yellow:
            self.clear_yellow_layer()

        if buf_yellow:
            self.write_yellow_layer(buf_yellow)
        elif buf_black:
            self.clear_black_layer()

        print('display refresh ...')
        self._command(DISPLAY_REFRESH)
        self.wait_until_idle()
