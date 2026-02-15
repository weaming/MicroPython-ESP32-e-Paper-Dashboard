import machine
import utime
import struct

# RTC Memory Layout
# We use RTC memory to persist state across deep sleep cycles.
# - Magic Header (4 bytes): To verify valid data
# - Task State (variable): Application specific state

RTC_MAGIC = 0xDEADBEEF


def deep_sleep(seconds):
    """Enter deep sleep for the specified number of seconds."""
    print(f"Entering deep sleep for {seconds} seconds...")
    # Configure wake up source
    machine.deepsleep(seconds * 1000)


def restart():
    """Soft reset the device."""
    machine.soft_reset()


def is_cold_boot():
    """Check if the device started from a complete power-off state."""
    return machine.wake_reason() != machine.DEEPSLEEP_RESET


class StateManager:
    """Manage persistent state in RTC memory."""
    def __init__(self):
        self.rtc = machine.RTC()
    
    def save(self, data):
        """Save bytes to RTC memory."""
        self.rtc.memory(data)
        
    def load(self):
        """Load bytes from RTC memory."""
        return self.rtc.memory()
    
    def clear(self):
        """Clear RTC memory."""
        self.rtc.memory(b'')
