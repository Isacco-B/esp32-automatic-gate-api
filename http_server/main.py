from micropyserver import MicroPyServer
from machine import Pin, SoftI2C
from secrets import WLAN_SSID, WLAN_PASSWORD, AUTH_TOKEN, PORT
import network
import time
import json
import utils

# Pin Out Config
led_wifi = Pin(32, Pin.OUT)
led_i2c = Pin(33, Pin.OUT)

# I2c Config
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=10000)
arduino_address = 0x08

# ======================================================================================

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
    

def send_data_i2c(command, timeout=5, response_byte=4):
    start_time = time.time()
    try:
        i2c.writeto(arduino_address, command)
        while True:
            if time.time() - start_time > timeout:
                raise Exception("Timeout waiting for response from Arduino")
            
            try:
                response = i2c.readfrom(arduino_address, response_byte)
                led_i2c.off()
                if not response:
                    raise Exception("No response from Arduino")
                return response
            except OSError as e:
                pass
            time.sleep(0.01)
          
    except Exception as e:
        error_message = "No response from Arduino"
        if str(e) != "[Errno 19] ENODEV":
            error_message = e
        error_message = json.dumps({"error": str(error_message)})
        utils.send_response(server, error_message, 400, content_type="application/json")
        led_i2c.on()



        
def test_i2c_connection():
    print("Testing i2c...")
    try:
        led_i2c.off()
        i2c.writeto(arduino_address, b"Hello Arduino!")
        time.sleep(2)
        response = i2c.readfrom(arduino_address, timeout=5, response_byte=12)
        print(response)
        print("i2c connected")
    except Exception as e:
        led_i2c.on()
        print("i2c error")
            
# ======================================================================================

# Controllers
def ping(request):
    data = send_data_i2c(command="p", timeout=5, response_byte=32)
    if data is not None:
        response_message = json.dumps({"response": data})
        utils.send_response(server, response_message, 200, content_type="application/json")
    


def gate(request):
    data = send_data_i2c("g")
    if data is not None:
        response_message = json.dumps({"response": data})
        utils.send_response(server, response_message, 200, content_type="application/json")


        
def small_gate(request):
    data = send_data_i2c("small_gate")
    if data is not None:
        response_message = json.dumps({"response": data})
        utils.send_response(server, response_message, 200, content_type="application/json")
        

def garage_light(request):
    data = send_data_i2c("garage_light")
    if data is not None:
        response_message = json.dumps({"response": data})
        utils.send_response(server, response_message, 200, content_type="application/json")
        

def status(request):
    data = send_data_i2c("status")
    if data is not None:
        response_message = json.dumps({"response": data})
        utils.send_response(server, response_message, 200, content_type="application/json")
        

def advanced_status(request):
    data = send_data_i2c("advanced_status")
    if data is not None:
        response_message = json.dumps({"response": data})
        utils.send_response(server, response_message, 200, content_type="application/json")

# ======================================================================================

# Middleware
def require_auth(request):
    token = utils.get_bearer_token(request)
    error_message = json.dumps({"error": "Unauthorized"})
    utils.send_response(server, error_message, 401, content_type="application/json")


def page_not_found(request):
    error_message = json.dumps({"error": "Page Not found"})
    utils.send_response(server, error_message, 404, content_type="application/json")


def server_error(request):
    error_message = json.dumps({"error": "Internal server error"})
    utils.send_response(server, error_message, 500, content_type="application/json")
    
# ======================================================================================


test_i2c_connection()
connect_to_wifi()


# Server Config
server = MicroPyServer(host="192.168.178.102", port=PORT)


# Server Routes
server.add_route("/ping", ping)
server.add_route("/gate", gate)
server.add_route("/small_gate", small_gate)
server.add_route("/garage_light", garage_light)
server.add_route("/status", status)
server.add_route("/advanced_status", advanced_status)

# Server Handler
#server.on_request(require_auth)
server.on_not_found(page_not_found)
server.on_error(server_error)

# Start Server
server.start()





