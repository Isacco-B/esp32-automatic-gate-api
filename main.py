from libs.umqtt import MQTTClient
from utils.utils import (
    validate_data,
    send_data_i2c,
    connect_to_wifi,
    is_wifi_connected,
    sync_time,
)
import machine
import time
import json
from secrets import SERVER, USER, PASSWORD, CLIENT_ID

sync_time()

SLEEP_INTERVAL = 0.1
MQTT_RETRY_INTERVAL = 1
DEBOUNCE_TIME = 1000
NOTIFICATION_TIMEOUT = 60

REBOOT_INTERVAL = 86400

small_gate = machine.Pin(12, machine.Pin.OUT)
garage_light = machine.Pin(14, machine.Pin.OUT)

TOPICS = {
    "GATE": b"api/gate",
    "PARTIAL_GATE": b"api/gate/partial",
    "SMALL_GATE": b"api/small_gate",
    "GARAGE_LIGHT": b"api/garage/light",
    "GET_GATE_STATUS": b"api/gate/get_status",
}

mqtt_client = None
current_message = None
status_requested = False
status_end_time = 0
last_execution_time = {}


def send_notification(topic, message):
    try:
        mqtt_client.publish(topic, message)
    except Exception as e:
        print(f"Error sending notification: {topic}")


def can_execute(command):
    ms_current_time = time.ticks_ms()
    if (
        command not in last_execution_time
        or ms_current_time - last_execution_time[command] >= DEBOUNCE_TIME
    ):
        last_execution_time[command] = ms_current_time
        return True
    return False


def handle_message(topic, msg):
    print(topic)
    global current_message, status_end_time, status_requested

    if topic == TOPICS["GATE"] and msg == b"on" and can_execute("gate"):
        current_message = ("gate", b"1", "gate")
        process_gate_command(b"1", "gate")
    elif (
        topic == TOPICS["PARTIAL_GATE"] and msg == b"on" and can_execute("partial_gate")
    ):
        current_message = ("partial_gate", b"2", "gate/partial")
        process_gate_command(b"2", "gate/partial")
    elif topic == TOPICS["SMALL_GATE"] and msg == b"on" and can_execute("small_gate"):
        response = {"data": "Cancellino: Eseguito con successo"}
        send_notification(b"api/notification/small_gate", json.dumps(response))
        small_gate.on()
        time.sleep(0.1)
        small_gate.off()
    elif (
        topic == TOPICS["GARAGE_LIGHT"] and msg == b"on" and can_execute("garage_light")
    ):
        response = {"data": "Luce Garage: Eseguito con successo"}
        send_notification(b"api/notification/garage/light", json.dumps(response))
        garage_light.on()
        time.sleep(0.1)
        garage_light.off()
    elif (
        topic == TOPICS["GET_GATE_STATUS"]
        and msg == b"on"
        and can_execute("get_status")
    ):
        status_requested = True
        status_end_time = time.time() + 60


def process_gate_command(command, notification_suffix):
    data = send_data_i2c(command, response_byte=2)
    if "err" in data:
        print(data)
        return
    response = {"data": "Pedonabile: Eseguito con successo"}
    if notification_suffix == "gate":
        response = {"data": "Cancello: Eseguito con successo"}
    send_notification(f"api/notification/{notification_suffix}", json.dumps(response))


def send_gate_status():
    try:
        data = send_data_i2c(b"3", response_byte=20)
        if "err" in data:
            print("ERRORE")
            return
        status_json = process_gate_status(data)
        if status_json:
            send_notification(b"api/notification/gate/status", status_json)
    except Exception as e:
        print(f"Error sending gate status: {e}")


def process_gate_status(data):
    decoded_string = data["data"].decode("utf8")
    status_parts = decoded_string.split(",")

    if not validate_data(status_parts):
        print("Invalid status data!")
        return None

    state_translation = {
        "0": "chiuso",
        "1": "aperto",
        "2": "stop",
        "3": "in apertura",
        "4": "in chiusura",
    }
    option_translation = {"0": "disattivo", "1": "attivo"}

    if status_parts[1][0] == "0":
        status_parts[1] = status_parts[1][1:]

    status_dict = {
        "stato": state_translation.get(status_parts[0], "sconosciuto"),
        "posizione": status_parts[1],
        "fcApertura": option_translation.get(status_parts[2], "sconosciuto"),
        "fcChiusura": option_translation.get(status_parts[3], "sconosciuto"),
        "fotocellule": option_translation.get(status_parts[4], "sconosciuto"),
        "coste": option_translation.get(status_parts[5], "sconosciuto"),
        "consumo": status_parts[6],
        "ricevente": option_translation.get(status_parts[7], "sconosciuto"),
    }
    return json.dumps(status_dict)


def connect_to_mqtt():
    global mqtt_client

    while not is_wifi_connected():
        connect_to_wifi()

    client = MQTTClient(
        client_id=CLIENT_ID, user=USER, password=PASSWORD, server=SERVER
    )
    client.set_callback(handle_message)
    client.connect()
    time.sleep(0.2)
    for topic in TOPICS.values():
        client.subscribe(topic)
    print(f"Connected to {SERVER}")
    mqtt_client = client


def keep_connection_active():
    try:
        mqtt_client.publish("api/ping", "ping")
    except Exception as e:
        print(f"Error sending ping to broker: {e}")


def main():
    global status_requested
    last_send_status = time.ticks_ms()
    last_keep_alive = time.time()
    start_time = time.time()
    print(start_time)

    while True:
        try:
            connect_to_mqtt()
            while True:
                current_time = time.time()
                ms_current_time = time.ticks_ms()

                mqtt_client.check_msg()

                if status_requested:
                    send_gate_status()

                    if ms_current_time - last_send_status >= 500:
                        send_gate_status()
                        last_send_status = ms_current_time

                    if current_time >= status_end_time:
                        status_requested = False

                if current_time - last_keep_alive >= 10:
                    keep_connection_active()
                    last_keep_alive = current_time

                if current_time - start_time >= REBOOT_INTERVAL:
                    machine.reset()

                time.sleep(SLEEP_INTERVAL)

        except Exception as e:
            print(f"MQTT communication error: {e}")

        finally:
            try:
                mqtt_client.disconnect()
            except Exception as e:
                print(f"Error disconnecting client: {e}")

            time.sleep(MQTT_RETRY_INTERVAL)


if __name__ == "__main__":
    main()
