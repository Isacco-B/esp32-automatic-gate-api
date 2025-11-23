import time
from secrets import WLAN_PASSWORD, WLAN_SSID

import network
import ntptime
from machine import Pin, SoftI2C

WIFI_RETRY_INTERVAL = 1
WIFI_MAX_RETRIES = 30
I2C_FREQUENCY = 1500
ARDUINO_ADDRESS = 0x08

led_wifi = Pin(32, Pin.OUT)
led_i2c = Pin(33, Pin.OUT)

led_wifi.off()
led_i2c.off()

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=I2C_FREQUENCY)


def sync_time(retries: int = 5) -> None:
    """
    Synchronize system time with an NTP server.
    """
    ntptime.host = "pool.ntp.org"

    for attempt in range(retries):
        try:
            print(f"Sync attempt {attempt+1}/{retries}...")
            ntptime.settime()
            time.sleep(1)

            if time.time() < 1000000000:
                print("Invalid time received, retrying...")
                continue

            rtc = machine.RTC()
            dt = list(rtc.datetime())
            dt[4] += 1  # add +1 hour for CET (no DST)
            rtc.datetime(tuple(dt))

            print("Time synchronized correctly:", time.localtime())
            return

        except Exception as e:
            print("Error syncing time:", e)
            time.sleep(1)

    print("Failed to sync time after retries")


def validate_data(data: list) -> bool:
    """
    Validate gate status data format and ranges.

    Args:
        data: List of status data strings from I2C

    Returns:
        True if data is valid, False otherwise
    """
    try:
        if len(data) != 8:
            return False

        if not data[0].isdigit() or not (0 <= int(data[0]) <= 4):
            return False

        if len(data[1]) > 3 or not data[1].isdigit() or not (0 <= int(data[1]) <= 100):
            return False

        if not all(item in {"0", "1"} for item in data[2:6]):
            return False

        try:
            consumption = float(data[6])
            if consumption > 9.99:
                return False
        except (ValueError, TypeError):
            return False

        if data[7] not in {"0", "1"}:
            return False

        return True

    except Exception as e:
        print(f"Validation error: {e}")
        return False


def send_data_i2c(command: bytes, response_byte: int = 4) -> dict:
    """
    Send command via I2C and receive response.

    Args:
        command: Command bytes to send
        response_byte: Number of bytes to read in response

    Returns:
        Dictionary with 'data' key on success or 'err' key on failure
    """
    result = {}
    try:
        i2c.writeto(ARDUINO_ADDRESS, command)
        time.sleep_ms(10)

        response = i2c.readfrom(ARDUINO_ADDRESS, response_byte)
        result["data"] = response

        led_i2c.off()
        return result

    except OSError as e:
        result["err"] = f"I2C error: {str(e)}"
        led_i2c.on()
        return result
    except Exception as e:
        result["err"] = f"Unexpected error: {str(e)}"
        led_i2c.on()
        return result


def test_i2c_connection() -> bool:
    """
    Test I2C connection with Arduino.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        i2c.writeto(ARDUINO_ADDRESS, b"0")
        time.sleep_ms(10)

        response_bytes = i2c.readfrom(ARDUINO_ADDRESS, 4)

        try:
            response_str = response_bytes.decode("utf8")
            print(f"I2C test successful! Response: {response_str}")
        except UnicodeDecodeError:
            print(f"I2C test successful! Raw response: {response_bytes.hex()}")

        led_i2c.off()
        return True

    except Exception as e:
        print(f"I2C test failed: {e}")
        led_i2c.on()
        return False


def connect_to_wifi(timeout: int = 30) -> bool:
    """
    Connect to WiFi network with timeout.

    Args:
        timeout: Maximum time to wait for connection in seconds

    Returns:
        True if connected successfully, False if timeout
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        led_wifi.off()
        print(f"Already connected to: {WLAN_SSID}")
        print(f"Connection details: {wlan.ifconfig()}")
        return True

    led_wifi.on()
    print(f"Connecting to WiFi: {WLAN_SSID}")
    wlan.connect(WLAN_SSID, WLAN_PASSWORD)

    start_time = time.time()
    while not wlan.isconnected():
        if time.time() - start_time > timeout:
            led_wifi.on()
            print(f"WiFi connection timeout after {timeout} seconds")
            return False

        led_wifi.value(not led_wifi.value())
        time.sleep(WIFI_RETRY_INTERVAL)
        print(f"Connecting... ({int(time.time() - start_time)}s)")

    led_wifi.off()
    print(f"Connected to: {WLAN_SSID}")
    print(f"Connection details: {wlan.ifconfig()}")
    return True


def is_wifi_connected() -> bool:
    """
    Check if WiFi is currently connected.
    Updates LED status accordingly.

    Returns:
        True if connected, False otherwise
    """
    wlan = network.WLAN(network.STA_IF)
    connected = wlan.isconnected()

    if connected:
        led_wifi.off()
    else:
        led_wifi.on()

    return connected
