import machine
import utime

# Identified Button Pins for this device
BTN_MAP = {
    "Button 1": "Reset (EN Pin)",
    "Button 2": 34,
    "Button 3": 35,
    "Button 4": 39
}

# Exhaustive scan pins (excluding flash and UART)
SCAN_PINS = [
    0, 2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 
    21, 22, 23, 25, 26, 27, 32, 33, 34, 35, 36, 39
]

INPUT_ONLY_PINS = {34, 35, 36, 39}

def main():
    print("=== Hardware Button & GPIO Test ===")
    print("Identified Buttons:")
    for name, pin in BTN_MAP.items():
        print(f"  - {name}: {pin}")
    
    print("\nInitializing exhaustive scan on all potential pins...")
    
    pins = {}
    last_states = {}
    
    for pin_num in SCAN_PINS:
        try:
            if pin_num in INPUT_ONLY_PINS:
                p = machine.Pin(pin_num, machine.Pin.IN)
            else:
                p = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
            
            pins[pin_num] = p
            last_states[pin_num] = p.value()
        except:
            pass

    print(f"Monitoring {len(pins)} pins. Press buttons to see activity.")
    print("Listening... (Ctrl+C to exit)\n")

    try:
        while True:
            for pin_num, pin_obj in pins.items():
                try:
                    val = pin_obj.value()
                    if val != last_states[pin_num]:
                        state = "HIGH" if val == 1 else "LOW"
                        # Extra info for identified buttons
                        info = ""
                        for name, p_num in BTN_MAP.items():
                            if p_num == pin_num:
                                info = f" ({name})"
                                break
                        
                        print(f"[{utime.ticks_ms()}] Pin({pin_num:02d}) -> {state}{info}")
                        last_states[pin_num] = val
                except:
                    pass
            utime.sleep_ms(20)
    except KeyboardInterrupt:
        print("\nExit.")

if __name__ == "__main__":
    main()
