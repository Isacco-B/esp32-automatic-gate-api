import json
import time
from secrets import CLIENT_ID, PASSWORD, SERVER, USER

import machine

from libs.umqtt import MQTTClient
from utils.messages import (
    DEFAULT_USER,
    MESSAGES,
    OPTION_DESCRIPTIONS,
    STATE_DESCRIPTIONS,
)
from utils.utils import (
    connect_to_wifi,
    is_wifi_connected,
    send_data_i2c,
    sync_time,
    validate_data,
)

SLEEP_INTERVAL = 0.1
MQTT_RETRY_INTERVAL = 1
DEBOUNCE_TIME = 1000
NOTIFICATION_TIMEOUT = 60

GATE_PULSE_DURATION = 0.1
STATUS_SEND_INTERVAL = 500
KEEP_ALIVE_INTERVAL = 10

VALID_COMMANDS = {"gate", "partial_gate", "small_gate", "garage_light", "get_status"}

TOPICS = {
    "GATE": b"api/gate",
    "PARTIAL_GATE": b"api/gate/partial",
    "SMALL_GATE": b"api/small_gate",
    "GARAGE_LIGHT": b"api/garage/light",
    "GET_GATE_STATUS": b"api/gate/get_status",
}

small_gate = machine.Pin(12, machine.Pin.OUT)
garage_light = machine.Pin(14, machine.Pin.OUT)

mqtt_client = None
status_requested = False
status_end_time = 0
last_execution_time = {}


def cleanup_pins() -> None:
    """
    Clean up GPIO pins state by turning them off.
    Used during initialization and shutdown.
    """
    try:
        small_gate.off()
        garage_light.off()
    except Exception as e:
        print(f"Error cleaning up pins: {e}")


def parse_message_payload(msg: bytes) -> tuple[str, str]:
    """
    Parse MQTT message payload to extract command and username.

    Expected format: "on" or "on:username" or JSON {"cmd": "on", "user": "username"}

    Args:
        msg: Raw message bytes

    Returns:
        Tuple of (command, username)
    """
    try:
        msg_str = msg.decode("utf-8")

        if msg_str.startswith("{"):
            try:
                data = json.loads(msg_str)
                command = data.get("cmd", "on")
                username = data.get("user", DEFAULT_USER)
                return command, username
            except json.JSONDecodeError:
                pass

        if ":" in msg_str:
            parts = msg_str.split(":", 1)
            command = parts[0]
            username = parts[1] if len(parts) > 1 and parts[1] else DEFAULT_USER
            return command, username

        return msg_str, DEFAULT_USER

    except Exception as e:
        print(f"Error parsing message: {e}")
        return "on", DEFAULT_USER


def send_notification(topic: bytes | str, message: str, success: bool = True) -> None:
    """
    Send MQTT notification with status.

    Args:
        topic: MQTT topic as bytes or string
        message: Message to send
        success: Whether the operation was successful
    """
    try:
        if isinstance(topic, str):
            topic = topic.encode()

        payload = {
            "data": message,
            "status": "success" if success else "error",
            "timestamp": time.time(),
        }

        mqtt_client.publish(topic, json.dumps(payload))
    except Exception as e:
        print(f"Error sending notification: {topic}, error: {e}")


def format_message(
    message_key: str, username: str, message_type: str = "success"
) -> str:
    """
    Format message with username from templates.

    Args:
        message_key: Key in MESSAGES dict
        username: Username to insert
        message_type: Type of message (success/error/info)

    Returns:
        Formatted message string
    """
    try:
        if message_key in MESSAGES:
            if message_type in MESSAGES[message_key]:
                return MESSAGES[message_key][message_type].format(user=username)
        return f"{username} sta eseguendo un'operazione"
    except Exception as e:
        print(f"Error formatting message: {e}")
        return "Operazione in corso"


def can_execute(command: str) -> bool:
    """
    Check if a command can be executed using debouncing mechanism.
    Prevents command flooding by enforcing minimum time between executions.

    Args:
        command: Command name to check

    Returns:
        True if command can be executed, False otherwise
    """
    if command not in VALID_COMMANDS:
        print(f"Invalid command: {command}")
        return False

    ms_current_time = time.ticks_ms()

    if command not in last_execution_time:
        last_execution_time[command] = ms_current_time
        return True

    if time.ticks_diff(ms_current_time, last_execution_time[command]) >= DEBOUNCE_TIME:
        last_execution_time[command] = ms_current_time
        return True

    return False


def handle_message(topic: bytes, msg: bytes) -> None:
    """
    Handle incoming MQTT messages and trigger appropriate actions.

    Args:
        topic: MQTT topic of received message
        msg: Message payload
    """
    print(f"Received - Topic: {topic}, Message: {msg}")
    global status_requested, status_end_time

    command, username = parse_message_payload(msg)

    if command != "on":
        return

    if topic == TOPICS["GATE"] and can_execute("gate"):
        process_gate_command(b"1", "gate", username)

    elif topic == TOPICS["PARTIAL_GATE"] and can_execute("partial_gate"):
        process_gate_command(b"2", "gate/partial", username, "gate_partial")

    elif topic == TOPICS["SMALL_GATE"] and can_execute("small_gate"):
        message = format_message("small_gate", username, "success")
        send_notification(b"api/notification/small_gate", message, True)
        small_gate.on()
        time.sleep(GATE_PULSE_DURATION)
        small_gate.off()

    elif topic == TOPICS["GARAGE_LIGHT"] and can_execute("garage_light"):
        message = format_message("garage_light", username, "success")
        send_notification(b"api/notification/garage/light", message, True)
        garage_light.on()
        time.sleep(GATE_PULSE_DURATION)
        garage_light.off()

    elif topic == TOPICS["GET_GATE_STATUS"] and can_execute("get_status"):
        status_requested = True
        status_end_time = time.time() + NOTIFICATION_TIMEOUT


def process_gate_command(
    command: bytes, notification_suffix: str, username: str, message_key: str = "gate"
) -> None:
    """
    Process gate commands by sending I2C data and notifications.

    Args:
        command: I2C command bytes to send
        notification_suffix: Suffix for notification topic
        username: Username who triggered the command
        message_key: Key for message template
    """
    try:
        data = send_data_i2c(command, response_byte=2)

        if "err" in data:
            print(f"I2C error: {data}")
            message = format_message(message_key, username, "error")
            topic = f"api/notification/{notification_suffix}/error".encode()
            send_notification(topic, message, False)
            return

        message = format_message(message_key, username, "success")
        topic = f"api/notification/{notification_suffix}".encode()
        send_notification(topic, message, True)

    except Exception as e:
        print(f"Error processing gate command: {e}")
        message = format_message(message_key, username, "error")
        topic = f"api/notification/{notification_suffix}/error".encode()
        send_notification(topic, message, False)


def send_gate_status() -> None:
    """
    Request gate status via I2C and send it through MQTT.
    """
    try:
        data = send_data_i2c(b"3", response_byte=20)
        if "err" in data:
            print(f"Error getting gate status: {data}")
            return

        status_json = process_gate_status(data)
        if status_json:
            send_notification(b"api/notification/gate/status", status_json)
    except Exception as e:
        print(f"Error sending gate status: {e}")


def process_gate_status(data: dict) -> str | None:
    """
    Process gate status data received from I2C.

    Args:
        data: Dictionary containing I2C response data

    Returns:
        JSON string with gate status or None if processing fails
    """
    try:
        decoded_string = data["data"].decode("utf8")
        status_parts = decoded_string.split(",")

        if len(status_parts) < 8:
            print(f"Incomplete status data: {status_parts}")
            return None

        if not validate_data(status_parts):
            print("Invalid status data!")
            return None

        if len(status_parts[1]) > 1 and status_parts[1][0] == "0":
            status_parts[1] = status_parts[1][1:]

        status_dict = {
            "stato": STATE_DESCRIPTIONS.get(
                status_parts[0], STATE_DESCRIPTIONS["unknown"]
            ),
            "posizione": f"{status_parts[1]}%",
            "fcApertura": OPTION_DESCRIPTIONS.get(
                status_parts[2], OPTION_DESCRIPTIONS["unknown"]
            ),
            "fcChiusura": OPTION_DESCRIPTIONS.get(
                status_parts[3], OPTION_DESCRIPTIONS["unknown"]
            ),
            "fotocellule": OPTION_DESCRIPTIONS.get(
                status_parts[4], OPTION_DESCRIPTIONS["unknown"]
            ),
            "coste": OPTION_DESCRIPTIONS.get(
                status_parts[5], OPTION_DESCRIPTIONS["unknown"]
            ),
            "consumo": f"{status_parts[6]}A",
            "ricevente": OPTION_DESCRIPTIONS.get(
                status_parts[7], OPTION_DESCRIPTIONS["unknown"]
            ),
        }
        return json.dumps(status_dict)
    except Exception as e:
        print(f"Error processing gate status: {e}")
        return None


def connect_to_mqtt() -> bool:
    """
    Connect to MQTT.
    Handles WiFi connection and previous MQTT session cleanup.

    Returns:
        True if connection successful, False otherwise
    """
    global mqtt_client

    if mqtt_client:
        try:
            mqtt_client.disconnect()
        except:
            pass
        mqtt_client = None

    while not is_wifi_connected():
        print("WiFi not connected, attempting connection...")
        connect_to_wifi()
        time.sleep(1)

    try:
        client = MQTTClient(
            client_id=CLIENT_ID, user=USER, password=PASSWORD, server=SERVER
        )
        client.set_callback(handle_message)
        client.connect()
        time.sleep(0.2)

        for topic_name, topic in TOPICS.items():
            client.subscribe(topic)
            print(f"Subscribed to {topic_name}")

        print(f"Connected to MQTT broker at {SERVER}")
        mqtt_client = client
        return True
    except Exception as e:
        print(f"Failed to connect to MQTT: {e}")
        return False


def keep_connection_active() -> None:
    """
    Keep MQTT connection alive by sending ping.
    Raises exception if ping fails to trigger reconnection.
    """
    try:
        mqtt_client.publish(b"api/ping", b"ping")
    except Exception as e:
        print(f"Error sending ping to broker: {e}")
        raise


def main() -> None:
    global status_requested

    sync_time()
    cleanup_pins()

    last_send_status = time.ticks_ms()
    last_keep_alive = time.time()

    while True:
        try:
            if not connect_to_mqtt():
                print("Failed to connect to MQTT, retrying...")
                time.sleep(MQTT_RETRY_INTERVAL)
                continue

            while True:
                current_time = time.time()
                ms_current_time = time.ticks_ms()

                mqtt_client.check_msg()

                if status_requested:
                    if (
                        time.ticks_diff(ms_current_time, last_send_status)
                        >= STATUS_SEND_INTERVAL
                    ):
                        send_gate_status()
                        last_send_status = ms_current_time

                    if current_time >= status_end_time:
                        status_requested = False
                        print("Status request timeout")

                if current_time - last_keep_alive >= KEEP_ALIVE_INTERVAL:
                    keep_connection_active()
                    last_keep_alive = current_time

                time.sleep(SLEEP_INTERVAL)

        except KeyboardInterrupt:
            print("Program interrupted by user")
            break

        except Exception as e:
            print(f"MQTT communication error: {e}")

        finally:
            try:
                if mqtt_client:
                    mqtt_client.disconnect()
                    mqtt_client = None
            except Exception as e:
                print(f"Error disconnecting client: {e}")

            time.sleep(MQTT_RETRY_INTERVAL)

    cleanup_pins()
    print("Program terminated")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        cleanup_pins()
        machine.reset()
