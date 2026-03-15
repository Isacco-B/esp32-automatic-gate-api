# ESP32 Automatic Gate API

MicroPython firmware for ESP32 that exposes an MQTT API for remote control of an automatic gate. The ESP32 communicates with an Arduino over I2C to send commands and read the gate's status.

## How it works

1. The ESP32 connects to WiFi and an MQTT broker.
2. It listens on several MQTT topics and, upon receiving a command, sends instructions to the Arduino via I2C.
3. The Arduino physically controls the gate motor and responds with the current state (position, limit switches, photocells, etc.).
4. The ESP32 publishes notifications and updated status to response MQTT topics.

## MQTT Topics

| Topic | Description |
|---|---|
| `api/gate` | Open/close main gate |
| `api/gate/partial` | Partial opening |
| `api/gate/status` | Request status (streamed for 60s) |
| `api/gate/statistics` | Request usage statistics |
| `api/gate/statistics/reset` | Reset counters (`24h`, `total`, `all`) |
| `api/gate/learning` | Learning mode |
| `api/small_gate` | Pedestrian gate |
| `api/garage/light` | Garage light |

## Message Format

Payloads are accepted in two formats:

```json
{"cmd": "on", "user": "username"}
```

or as a plain string: `on:username`

## I2C Commands to Arduino

| Byte | Action |
|---|---|
| `1` | Trigger main gate |
| `2` | Partial opening |
| `3` | Read gate state |
| `4` | Learning mode |

## Configuration

Create a `secrets.py` file with your credentials:

```python
SERVER = "mqtt-broker-address"
USER = "username"
PASSWORD = "password"
```

## Key Features

- **Debouncing**: prevents repeated command execution (minimum 1s between commands)
- **Counters**: tracks activations in the last 24h and all-time, with automatic daily reset at 23:59
- **Auto-reconnect**: automatically reconnects to WiFi and MQTT on disconnection
- **Notifications**: every action publishes a notification to `api/notification/<command>` with status and timestamp
