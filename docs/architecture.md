# Architecture

The project is organized as a small end-to-end IoT data pipeline.

```text
ESP32 + BME280 + BH1750
        |
        | MQTT JSON messages
        v
Python MQTT Consumer
        |
        v
Validation + Transformation + Event Rules
        |
        v
InfluxDB Time-Series Storage
        |
        v
Streamlit Dashboard
```

## Runtime Layers

`firmware/esp32/` contains device code and secrets templates for the ESP32 runtime.

`docker/` contains local service configuration, including the Mosquitto MQTT broker used during development.

`src/ingestion/` receives MQTT messages. The consumer parses JSON, tracks message counts, remembers the previous reading, and passes processed results to a callback.

`src/monitor/` subscribes to the raw MQTT topic and serves a local browser page for watching live device payloads.

`src/processing/` validates sensor messages and assigns event labels. The transformer combines validation and rule-based event detection into one processed record.

`src/simulation/` publishes realistic pre-device MQTT data for pipeline testing. It is a development aid only; the final capstone device layer is the ESP32.

`src/storage/` writes processed records to InfluxDB and provides reusable query methods for dashboard views.

`src/dashboard/` contains the Streamlit app. It reads from the storage query layer instead of talking directly to raw processing code.

## Why This Shape

The structure keeps hardware, ingestion, processing, storage, and presentation separate. That makes the project easier to test, easier to demo, and easier to extend when more devices or event rules are added.
