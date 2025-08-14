import gc
import time

import machine

from utils.utils import connect_to_wifi, sync_time, test_i2c_connection

BOOT_DELAY = 2
WIFI_TIMEOUT = 30
ENABLE_WEBREPL = False


def show_boot_info():
    """Display boot information."""
    print("\n" + "=" * 50)
    print("ESP32 Gate Controller - Booting...")
    print("=" * 50)

    gc.collect()
    print(f"Free memory: {gc.mem_free()} bytes")
    print(f"Used memory: {gc.mem_alloc()} bytes")

    print(f"CPU Frequency: {machine.freq()/1000000:.0f} MHz")
    print("=" * 50 + "\n")


def boot_sequence():
    """Main boot sequence with error handling."""

    print(f"Waiting {BOOT_DELAY} seconds for system stability...")
    time.sleep(BOOT_DELAY)

    print("\n[1/3] Testing I2C connection with Arduino...")
    i2c_ok = test_i2c_connection()
    if i2c_ok:
        print("✓ I2C connection successful")
    else:
        print("✗ I2C connection failed - Arduino may not be ready")
        print("  Main program will retry I2C connection")

    print("\n[2/3] Connecting to WiFi...")
    wifi_connected = connect_to_wifi(timeout=WIFI_TIMEOUT)
    if wifi_connected:
        print("✓ WiFi connected successfully")

        print("\n[3/3] Synchronizing time...")
        sync_time()
    else:
        print("✗ WiFi connection failed")
        print("  Main program will retry WiFi connection")

    gc.collect()
    print(f"\nFree memory after boot: {gc.mem_free()} bytes")
    print("\nBoot sequence completed. Starting main program...\n")
    print("=" * 50 + "\n")


def setup_webrepl():
    """Setup WebREPL for remote access (optional)."""
    try:
        import webrepl

        webrepl.start()
        print("WebREPL started")
    except ImportError:
        print("WebREPL not available")
    except Exception as e:
        print(f"WebREPL error: {e}")


try:
    show_boot_info()

    if ENABLE_WEBREPL:
        setup_webrepl()

    boot_sequence()

except Exception as e:
    print(f"\nBoot error: {e}")
    print("Continuing to main program anyway...")
    time.sleep(2)
