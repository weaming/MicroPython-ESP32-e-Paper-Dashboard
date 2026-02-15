# main.py
import utime
import system.network as net
import system.hardware as hw
import system.power as pwr
from lib.framebuf2 import FrameBuffer, MHMSB
from lib.epaper7in5b import black, white

# Refresh Interval (in seconds)
REFRESH_INTERVAL = 300  # 5 minutes

def main():
    try:
        # 1. Connect to Network
        if not net.connect_wifi():
            print("Error: Could not connect to WiFi. Sleeping.")
            pwr.deep_sleep(60) 
            return

        # 2. Sync Time
        net.sync_time()

        # 3. Initialize Display
        epd = hw.init_display()
        buf = hw.get_buffer()
        
        # 4. Draw Content (Placeholder for now)
        print("Drawing test content...")
        
        # Create FrameBuffer wrapper around the buffer
        # Note: We need to clear buffer for black layer first
        epd.clear_frame(buf)
        
        fb = FrameBuffer(buf, epd.width, epd.height, MHMSB)
        
        # Draw Black Content
        fb.fill(white)
        fb.text("E-Paper Dashboard", 30, 30, black, size=4)
        fb.text(f"Time: {utime.localtime()}", 30, 80, black, size=2)
        fb.rect(20, 20, 760, 440, black)
        
        # Write Black Layer
        epd.write_black_layer(buf)
        
        # Draw Yellow/Red Content 
        # (Re-use buffer, clear it first)
        fb.fill(white)
        fb.text("Status: Active", 30, 120, black, size=2) # 'black' maps to colored pixel in yellow layer
        
        # Write Yellow Layer and Refresh
        epd.write_yellow_layer(buf, refresh=True)
        
        print("Display updated. Going to sleep.")
        
        # 5. Sleep
        epd.sleep()
        pwr.deep_sleep(REFRESH_INTERVAL)

    except Exception as e:
        print(f"Critical Error: {e}")
        # Sleep a bit before retry to avoid crash loops
        utime.sleep(10)
        pwr.restart()

if __name__ == "__main__":
    main()
