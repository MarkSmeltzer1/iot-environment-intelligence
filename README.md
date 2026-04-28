# IoT Environmental Intelligence Pipeline

Production-style IoT capstone project for collecting environmental data from an ESP32 device, processing it in real time, storing it in InfluxDB, and visualizing actionable room-environment insights.

## Problem

Indoor conditions can change quickly because of sunlight, airflow, open doors/windows, or sensor failures. A person can notice some of these changes by looking around, but an IoT pipeline can detect and label them automatically from real-time data.

This project turns raw sensor readings into decisions such as:

- Is the room becoming too hot or humid?
- Is sunlight likely causing the room to heat up?
- Did temperature drop suddenly, suggesting airflow or a location change?
- Are incoming readings malformed, missing, or outside realistic ranges?

## Architecture

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

## Hardware Plan

Phase 1 uses one physical sensor device:

- ESP32 development board
- BME280 sensor for temperature, humidity, and pressure
- BH1750 light sensor for ambient light
- Breadboard and jumper wires

Phase 2 can add a second ESP32 device for multi-room comparison using the same message schema.

## Protocol Choice

MQTT is used because it is lightweight, common in IoT systems, and well-suited for continuous telemetry from small devices over Wi-Fi.

## Data Schema

Raw ESP32 messages use JSON:

```json
{
  "timestamp": "2026-04-28T10:00:00Z",
  "device_id": "esp32_room_1",
  "location": "bedroom",
  "temperature_f": 72.0,
  "humidity": 45.0,
  "pressure_hpa": 1013.0,
  "light_lux": 500
}
```

Processed records add:

- `valid`
- `errors`
- `event_label`
- `anomaly_flag`
- `reasons`

## Processing

The processing layer currently supports:

- Required-field validation
- Timestamp validation
- Numeric type validation
- Realistic range validation
- Rule-based event detection for:
  - `normal`
  - `high_temp_alert`
  - `high_humidity_alert`
  - `sunlight_heating`
  - `sudden_cooling`

## Storage Design

InfluxDB stores one measurement: `environment_readings`.

Tags:

- `device_id`
- `location`
- `valid_status`

Fields:

- `temperature_f`
- `humidity`
- `pressure_hpa`
- `light_lux`
- `event_label`
- `anomaly_flag`

This design fits time-series workloads because timestamps are first-class, numeric sensor values can be queried over time, and tags support efficient filtering by device and location.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Local InfluxDB + Dashboard With Docker

Start InfluxDB:

```bash
docker compose up -d influxdb
```

Verify the app can connect to InfluxDB:

```bash
docker compose run --rm app python scripts/init_storage.py
```

Start the Streamlit dashboard:

```bash
docker compose up -d app
```

Open Streamlit at:

```text
http://localhost:8501
```

Open the InfluxDB UI at:

```text
http://localhost:8086
```

Local InfluxDB credentials are configured through `.env`:

```text
username: admin
password: local-password-123
org: iot-project
bucket: environment_data
token: local-dev-token
```

Stop local services:

```bash
docker compose down
```

## Run Commands

Start the MQTT consumer:

```bash
python scripts/run_consumer.py
```

Test InfluxDB connectivity:

```bash
python scripts/init_storage.py
```

Start the dashboard:

```bash
streamlit run src/dashboard/app.py
```

or:

```bash
python scripts/run_dashboard.py
```

## Current Status

Completed:

- Modular folder structure
- YAML configuration
- Validation layer
- Rule-based event detection
- Transformer layer
- MQTT consumer skeleton
- InfluxDB writer/query modules
- Unit tests

Current test status:

```text
25 passed
```

Next:

- Add ESP32 firmware once hardware arrives
- Connect live MQTT broker
- Run InfluxDB locally
- Build dashboard visualizations
- Collect 10,000+ real sensor records
- Demonstrate induced failures such as skipped sends, bad values, duplicates, or delayed transmissions
