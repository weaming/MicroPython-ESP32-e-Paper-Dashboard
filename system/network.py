import network
import utime
import ntptime
from config import WIFI_SSID, WIFI_PASSWORD

def connect_wifi(retries=10):
    """Connect to Wi-Fi with retries."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("WiFi already connected:", wlan.ifconfig())
        return True
        
    print(f"Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    for i in range(retries):
        if wlan.isconnected():
            print("WiFi connected:", wlan.ifconfig())
            return True
        print(".", end="")
        utime.sleep(1)
        
    print("\nWiFi connection failed.")
    return False


def sync_time():
    """Synchronize time using NTP."""
    print("Synchronizing time...")
    try:
        # Use Aliyun NTP server for better connectivity in CN
        ntptime.host = 'ntp.aliyun.com'
        # Adjust for UTC+8 (Beijing Time)
        # Note: ntptime.settime() normally sets UTC. 
        # We can either handle offset here or in display logic.
        # Let's just set the system time to UTC first.
        ntptime.settime()
        
        # Apply UTC+8 offset manually to system time if needed, 
        # or just verify we have correct UTC time.
        # For display ease, let's assume valid UTC and format later.
        print("Time synchronized:", utime.localtime())
        return True
    except Exception as e:
        print("Time sync failed:", e)
        return False
