from umqtt.simple import MQTTClient
from machine import Pin, SoftI2C
import ubinascii
import machine
import micropython
import time
import json
import uasyncio as asyncio
import network
from secrets import WLAN_SSID, WLAN_PASSWORD, AUTH_TOKEN

# PinOut
led_wifi = Pin(32, Pin.OUT)
led_i2c = Pin(33, Pin.OUT)

# I2c Config
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=5000)
arduino_address = 0x08


def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        led_wifi.on()
        print('wifi connection...')
        wlan.connect(WLAN_SSID, WLAN_PASSWORD)
        while not wlan.isconnected():
            pass
    print('Connected to:', WLAN_SSID)
    print('Connection details:', wlan.ifconfig())
    led_wifi.off()
    
    
async def send_data_i2c(command, timeout=5, response_byte=4):
    start_time = time.time()
    result = {}
    try:
        i2c.writeto(arduino_address, command)
        while True:
            if time.time() - start_time > timeout:
                result['err'] = "Timeout waiting for response from Arduino"
                led_i2c.on()
                return result

            try:
                response = i2c.readfrom(arduino_address, response_byte)
                await asyncio.sleep(0.2)
                if not response:
                    result['err'] = "No response from Arduino"
                    led_i2c.on()
                    return result
                result['data'] = response
                led_i2c.off()
                return result
            except OSError as e:
                pass
            await asyncio.sleep(0.02)
    except Exception as e:
        result['err'] = str(e)
        return result

        
def test_i2c_connection():
    print("Testing i2c...")
    try:
        i2c.writeto(arduino_address, b"0")
        time.sleep(0.2)
        response = i2c.readfrom(arduino_address, 4)
        print(response)
        print("i2c connected")
        led_i2c.off()
    except Exception as e:
        led_i2c.on()
        print("i2c error")


test_i2c_connection()
connect_to_wifi()


# Config MQTT Server
SERVER = "162.19.254.223"
CLIENT_ID = ubinascii.hexlify(machine.unique_id())

# Topic
GATE_TOPIC = b"api/gate"
PARTIAL_GATE_TOPIC = b"api/gate/partial"
SMALL_GATE_TOPIC = b"api/small_gate"
GARAGE_LIGHT_TOPIC = b"api/garage/light"

# PinOut
small_gate = Pin(12, Pin.OUT)
garage_light = Pin(14, Pin.OUT)

async def toggle_garage_light(msg):
    if msg == b"on":
        garage_light.on()
        await asyncio.sleep(2)
        garage_light.off()
        
async def toggle_small_gate(msg):
    if msg == b"on":
        small_gate.on()
        await asyncio.sleep(2)
        small_gate.off()
        

async def handle_message(topic, msg, client):
    print((topic, msg))
    if topic == GATE_TOPIC:
        data = await send_data_i2c(b"1", timeout=5, response_byte=2)
        if 'err' in data:
            error_message = json.dumps(data)
            await send_notification(client, b"api/notification/gate", error_message)
        else:
            response = json.dumps(data)
            print(response)
            await send_notification(client, b"api/notification/gate", response)
        
    elif topic == PARTIAL_GATE_TOPIC:
        data = await send_data_i2c(b"2", timeout=5, response_byte=2)
        if 'err' in data:
            error_message = json.dumps(data)
            await send_notification(client, b"api/notification/gate/partial", error_message)
        else:
            response = json.dumps(data)
            print(response)
            await send_notification(client, b"api/notification/gate/partial", response)
        
    elif topic == SMALL_GATE_TOPIC:
        await toggle_small_gate(msg)
        await send_notification(client, b"api/notification/small_gate", b"Small gate toggled successfully")
        
    elif topic == GARAGE_LIGHT_TOPIC:
        await toggle_garage_light(msg)
        await send_notification(client, b"api/notification/garage/light", b"Garage light toggled successfully")


async def send_notification(client, topic, message):
    client.publish(topic, message)

    
def sub_cb_closure(client):
    def sub_cb(topic, msg):
        asyncio.create_task(handle_message(topic, msg, client))
    return sub_cb


async def main():
    c = MQTTClient(CLIENT_ID, SERVER)
    c.set_callback(sub_cb_closure(c))
    c.connect()
    c.subscribe(GATE_TOPIC)
    c.subscribe(PARTIAL_GATE_TOPIC)
    c.subscribe(SMALL_GATE_TOPIC)
    c.subscribe(GARAGE_LIGHT_TOPIC)
    print("Connesso a %s, sottoscritto ai topic" % SERVER)
    asyncio.create_task(send_gate_status(c))
    try:
        while True:
            await asyncio.sleep(1)
            c.check_msg()
    finally:
        c.disconnect()
        
async def send_gate_status(client):
    
    while True:
        data = await send_data_i2c(b"3", timeout=5, response_byte=18)
        if 'err' in data:
            error_message = json.dumps(data)
            await send_notification(client, b"api/notification/gate/partial", error_message)
        else:
            status_data = data
            print(status_data)
            
            decoded_string = status_data["data"].decode("utf8")
            status_parts = decoded_string.split(',')
            print(status_parts)
            status_dict = {}
            
            state_translation = {"0": "chiuso", "1": "aperto", "2": "stop", "3": "in apertura", "4": "in chiusura"}
            option_translation = {"0": "disattivo", "1": "attivo"}
            
            status_dict["stato"] = state_translation.get(status_parts[0], "sconosciuto")
            status_dict["posizione"] = status_parts[1]
            status_dict["fcApertura"] = option_translation.get(status_parts[2], "sconosciuto")
            status_dict["fcChiusura"] = option_translation.get(status_parts[3], "sconosciuto")
            status_dict["fotocellule"] = option_translation.get(status_parts[4], "sconosciuto")
            status_dict["coste"] = option_translation.get(status_parts[5], "sconosciuto")
            status_dict["consumo"] = float(status_parts[6]) 
            status_dict["ricevente"] = option_translation.get(status_parts[7], "sconosciuto")
            
            status_json = json.dumps(status_dict)
            client.publish(b"api/gate/status", status_json)

        await asyncio.sleep(1)

asyncio.run(main())