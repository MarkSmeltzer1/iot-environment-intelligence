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
firmware/esp32/
```

Keep local Wi-Fi and broker credentials in `secrets.h`. The committed `secrets_template.h` file documents the values needed by the firmware without committing real credentials.
