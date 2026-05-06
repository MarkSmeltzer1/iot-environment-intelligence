# Hardware Plan

Phase 1 uses one physical sensor device:

- ESP32 development board
- BME280 sensor for temperature, humidity, and pressure
- BH1750 light sensor for ambient light
- Breadboard and jumper wires

Phase 2 can add a second ESP32 device for multi-room comparison using the same message schema.

## Protocol

MQTT is used because it is lightweight, common in IoT systems, and well-suited for continuous telemetry from small devices over Wi-Fi.

## Firmware Location

ESP32 firmware lives in:

```text
firmware/esp32/main/main.ino
```

Keep local Wi-Fi and broker credentials in `firmware/esp32/main/secrets.h`. The committed `firmware/esp32/main/secrets_template.h` file documents the values needed by the firmware without committing real credentials.

## Firmware Setup

The sketch publishes one JSON reading per second to:

```text
iot/environment/raw
```

Install these Arduino libraries before uploading:

- PubSubClient
- ArduinoJson
- Adafruit BME280 Library
- Adafruit Unified Sensor
- BH1750

Create local credentials:

```bash
cp firmware/esp32/main/secrets_template.h firmware/esp32/main/secrets.h
```

Edit `firmware/esp32/main/secrets.h` with Wi-Fi credentials and the IP address of the computer running the MQTT broker. Then upload `firmware/esp32/main/main.ino` to the ESP32.

## Diagnostic Controls

Open the Arduino serial monitor at `115200` baud. Send one of these commands:

```text
n = normal readings
h = high temperature and high light event
b = out-of-range bad temperature value
d = one skipped publish / dropout
u = one duplicate message
```

These controls make it possible to verify the pipeline against normal telemetry, environmental anomalies, malformed readings, skipped publishes, and duplicate messages.
