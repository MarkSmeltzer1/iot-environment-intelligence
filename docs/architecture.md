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

`firmware/esp32/main/` contains the ESP32 runtime sketch and secrets template. `firmware/esp32/i2c_scanner/` contains a small hardware diagnostic sketch for checking I2C sensor addresses.

`docker/` contains local service configuration, including the Mosquitto MQTT broker used during development.

`src/ingestion/` receives MQTT messages. The consumer parses JSON, tracks message counts, remembers the previous reading, and passes processed results to a callback.

`src/monitor/` subscribes to the raw MQTT topic and serves a local browser page for watching live device payloads.

`src/processing/` validates sensor messages and assigns event labels. The transformer combines validation and rule-based event detection into one processed record.

`src/simulation/` publishes realistic MQTT data for local pipeline testing before hardware is connected or when repeatable load tests are needed.

`src/storage/` writes processed records to InfluxDB and provides reusable query methods for dashboard views.

`src/dashboard/` contains the Streamlit app. It reads from the storage query layer instead of talking directly to raw processing code.

## Component Rationale

MQTT is used for device communication because it is lightweight, works well with intermittent publishers, and decouples the ESP32 from storage and visualization services.

The Python consumer acts as the processing layer so firmware can stay focused on sensor collection while validation, event detection, logging, and storage behavior remain testable and configurable.

InfluxDB is used because the workload is time-series oriented: each reading has a timestamp, tags for filtering, and numeric fields that need recent-window trend queries.

Streamlit and Plotly are used for the output layer because they make it straightforward to build a live operational view from query-layer data without adding a larger web application stack.

## Why This Shape

The structure keeps hardware, ingestion, processing, storage, and presentation separate. That makes the project easier to test, operate, and extend when more devices or event rules are added.
