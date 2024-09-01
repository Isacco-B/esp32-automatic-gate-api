from machine import Pin, SoftI2C
import network
import ntptime
import time
from secrets import WLAN_SSID, WLAN_PASSWORD


WIFI_RETRY_INTERVAL = 1

led_wifi = Pin(32, Pin.OUT)
led_i2c = Pin(33, Pin.OUT)

i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=1500)
arduino_address = 0x08


def sync_time():
    try:
        ntptime.settime()
        print("Time synchronized and adjusted to timezone")
    except Exception as e:
        print(f"Failed to sync time: {e}")

def validate_data(data):
    if (
        len(data) == 8 and
        data[0].isdigit() and 0 <= int(data[0]) <= 4 and
        len(data[1]) <= 3 and data[1].isdigit() and 0 <= int(data[1]) <= 100 and
        all(data in {'0', '1'} for data in data[2:6]) and
        float(data[6]) <= 9.99 and
        data[7] in {'0', '1'}
    ):
        return True
    return False

def send_data_i2c(command, response_byte=4):
    result = {}
    try:
        i2c.writeto(arduino_address, command)
        response = i2c.readfrom(arduino_address, response_byte)
        result['data'] = response
        return result
    except Exception as e:
        result['err'] = str(e)
        return result
    
def test_i2c_connection():
    try:
        i2c.writeto(arduino_address, b"0")
        response = i2c.readfrom(arduino_address, 4).decode("utf8")
        print("Test I2C success!")
        led_i2c.off()
    except Exception as e:
        led_i2c.on()
        print("Test I2C error!")

def connect_to_wifi():
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
    
def is_wifi_connected():
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()