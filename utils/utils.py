from machine import Pin, SoftI2C
import network
import uasyncio as asyncio
import time
from secrets import WLAN_SSID, WLAN_PASSWORD

# Constants
WIFI_RETRY_INTERVAL = 2

# PinOut
led_wifi = Pin(32, Pin.OUT)
led_i2c = Pin(33, Pin.OUT)


def validate_data(parts):
    """Validate the structure and content of the input data parts."""
    if (
        len(parts) == 8 and
        parts[0].isdigit() and 0 <= int(parts[0]) <= 4 and
        len(parts[1]) <= 3 and parts[1].isdigit() and 0 <= int(parts[1]) <= 100 and
        all(part in {'0', '1'} for part in parts[2:6]) and
        float(parts[6]) <= 9.99 and
        parts[7] in {'0', '1'}
    ):
        return True
    else:
        return False
    
# I2C Initialization
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=250)
arduino_address = 0x08


async def send_data_i2c(command, timeout=5, response_byte=4):
    """Send data to the I2C device and await a response."""
    start_time = time.time()
    result = {}
    try:
        i2c.writeto(arduino_address, command)
        while True:
            if time.time() - start_time > timeout:
                result['err'] = "Timeout waiting for response from Arduino"
                led_i2c.on()
                return result

            response = i2c.readfrom(arduino_address, response_byte)
            if not response:
                result['err'] = "No response from Arduino"
                led_i2c.on()
                return result
            result['data'] = response
            led_i2c.off()
            return result
    except Exception as e:
        result['err'] = str(e)
        await asyncio.sleep(1)
        return result
    
        
def test_i2c_connection():
    """Test the I2C connection with the Arduino device."""
    print("------------------------------------")
    print("Testing I2C connection...")
    print("Sending ping to arduino...")
    try:
        i2c.writeto(arduino_address, b"0")
        time.sleep(0.2)
        response = i2c.readfrom(arduino_address, 4).decode("utf8")
        print(f"Arduino responds with {response}")
        print("I2C connected")
        print("------------------------------------")
        led_i2c.off()
    except Exception as e:
        led_i2c.on()
        print("I2C error!")
        print("------------------------------------")


# Wifi
def connect_to_wifi():
    """Connect to the specified WiFi network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        led_wifi.on()
        print('wifi connection...')
        wlan.connect(WLAN_SSID, WLAN_PASSWORD)
        while not wlan.isconnected():
            led_wifi.on()
            time.sleep(WIFI_RETRY_INTERVAL)
            print('Retrying WiFi connection...')
    led_wifi.off()
    print('Connected to:', WLAN_SSID)
    print('Connection details:', wlan.ifconfig())
    print("------------------------------------")
    
def is_wifi_connected():
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()