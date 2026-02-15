# debug.py
import system.hardware as hw
import system.network as net
import utime
from lib.framebuf2 import FrameBuffer, MHMSB
from lib.epaper7in5b import black, white

def test_hardware():
    print("Testing Hardware...")
    
    print("1. Initializing Display...")
    epd = hw.init_display()
    buf = hw.get_buffer()
    
    print("2. Clearing Screen...")
    epd.clear_screen()
    
    print("3. Drawing Pattern...")
    fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
    
    # Black Layer
    fb.fill(white)
    fb.text("DEBUG MODE", 50, 50, black, size=4)
    fb.rect(0, 0, 800, 480, black)
    fb.line(0, 0, 800, 480, black)
    epd.write_black_layer(buf)
    
    # Yellow Layer
    fb.fill(white)
    fb.text("Check Colors", 50, 100, black, size=3)
    fb.fill_rect(400, 200, 100, 100, black)
    epd.write_yellow_layer(buf, refresh=True)
    
    print("4. Display Test Complete.")
    
    print("5. Testing Network...")
    if net.connect_wifi():
        net.sync_time()
        print("Network Test Complete.")
    else:
        print("Network Test Failed.")
        
    print("Debug Sequence Finished.")

if __name__ == "__main__":
    test_hardware()
