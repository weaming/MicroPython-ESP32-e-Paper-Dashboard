import machine
import utime

# ADC1 pins on ESP32
ADC_PINS = [32, 33, 34, 35, 36, 39]

def main():
    print("=== Battery & Analog Discovery Tool ===")
    print("This tool shows raw ADC values to help calibrate voltage dividers.")
    
    adcs = {}
    for pin_num in ADC_PINS:
        try:
            p = machine.Pin(pin_num, machine.Pin.IN)
            adc = machine.ADC(p)
            adc.atten(machine.ADC.ATTN_11DB)
            adcs[pin_num] = adc
        except:
            pass

    print("\nReading... (Raw / 4095) | Press Button 3 to see P35 drop")
    print("-" * 60)
    
    try:
        while True:
            results = []
            for pin_num, adc in adcs.items():
                raw = adc.read()
                # 3.6V is the max range for 11dB attenuation
                v_raw = (raw / 4095.0) * 3.6
                results.append(f"P{pin_num}:{v_raw:.2f}V")
            
            print("  ".join(results), end="\r")
            utime.sleep_ms(200)
    except KeyboardInterrupt:
        print("\n\nExit.")

if __name__ == "__main__":
    main()
