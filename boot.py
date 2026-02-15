# boot.py - runs on boot-up
import gc
import system.power

# Enable garbage collection
gc.enable()

print("Booting E-Paper Dashboard...")

if system.power.is_cold_boot():
    print("Cold boot detected.")
else:
    print("Wake from deep sleep detected.")
