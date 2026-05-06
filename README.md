# IoT Environmental Intelligence

Production-style IoT data pipeline for collecting environmental readings from an ESP32 device, processing telemetry in real time, storing time-series data in InfluxDB, and visualizing actionable room-environment insights.

## Overview

This system monitors local environmental conditions around a room, window, or equipment area and turns raw sensor readings into operational signals:

- Is the room becoming too hot or humid?
- Is sunlight likely causing the room to heat up?
- Did temperature drop suddenly, suggesting airflow or a location change?
- Are incoming readings malformed, missing, or outside realistic ranges?

The pipeline is designed to be reproducible locally while keeping device firmware, ingestion, processing, storage, and presentation concerns separated.

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

## Design Choices

- **MQTT:** Lightweight publish/subscribe messaging fits small devices that send frequent telemetry and need decoupling from downstream consumers.
- **Python processing service:** Keeps validation, enrichment, event detection, and storage writes in a testable service layer instead of embedding all logic in firmware.
- **InfluxDB:** Time-series storage matches the workload: timestamped sensor readings, recent-window queries, trend analysis, and high-volume append writes.
- **Streamlit + Plotly:** Provides a fast operational dashboard for live trends, event counts, anomaly review, and record-volume checks.
- **Docker Compose:** Packages MQTT, InfluxDB, the consumer, dashboard, and monitor into a reproducible local runtime.

## Data And Outputs

Each device reading includes timestamp, device ID, location, temperature, humidity, pressure, and light level. The processing layer validates each message and adds event labels such as `normal`, `high_temp_alert`, `high_humidity_alert`, `sunlight_heating`, and `sudden_cooling`. The dashboard also derives rapid-change labels such as `rapid_light_change`, `rapid_humidity_change`, and `rapid_temp_change` from stored sensor trends so visible spikes and drops are explained clearly.

The Streamlit dashboard includes:

- Live sensor trends for temperature, humidity, pressure, and light
- Event count summary
- Anomaly timeline with event labels and readable explanations
- Total record count for stored readings

The MQTT monitor provides a raw live view of incoming device payloads for local inspection.

## Project Layout

```text
config/       Runtime configuration, thresholds, and validation ranges
docker/       Local service configuration for Docker Compose
docs/         Architecture, schema, setup, and hardware notes
examples/     Sample MQTT payloads for manual testing
firmware/     ESP32 firmware and device-specific templates
logs/         Runtime log directory for Python services
scripts/      Operational entrypoints for services and checks
src/          Python application code
tests/        Unit tests for processing, ingestion, storage, and monitoring
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Docker Runtime

Start all local services:

```bash
docker compose up -d mqtt influxdb consumer app monitor
```

Verify the app can connect:

```bash
docker compose run --rm app python scripts/init_storage.py
```

Publish test messages through the Docker network:

```bash
docker compose exec -T consumer python scripts/publish_example.py examples/valid_reading.json --use-current-time --repeat 5
docker compose exec -T consumer python scripts/publish_example.py examples/high_temp_reading.json --use-current-time
docker compose exec -T consumer python scripts/publish_example.py examples/invalid_reading.json
```

Publish a realistic simulated stream for local testing:

```bash
docker compose exec -T consumer python scripts/run_simulator.py --count 60 --interval-seconds 1 --include-failures
```

Show total stored records:

```bash
docker compose exec -T app python scripts/show_record_count.py
```

Open:

```text
MQTT monitor: http://localhost:8600
Streamlit: http://localhost:8501
InfluxDB:  http://localhost:8086
```

## ESP32 Firmware

The ESP32 sketch lives in `firmware/esp32/main/main.ino` and publishes BME280/BH1750 readings to `iot/environment/raw`.

Install these Arduino libraries:

- PubSubClient
- ArduinoJson
- Adafruit BME280 Library
- Adafruit Unified Sensor
- BH1750

Create local firmware secrets:

```bash
cp firmware/esp32/main/secrets_template.h firmware/esp32/main/secrets.h
```

Edit `secrets.h` with Wi-Fi credentials and the MQTT broker IP address, then upload the sketch. The firmware includes serial diagnostic controls at `115200` baud:

```text
n = normal readings
h = high temperature and high light event
b = out-of-range bad value
d = one skipped publish / dropout
u = one duplicate message
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

Publish one example MQTT message:

```bash
python scripts/publish_example.py examples/valid_reading.json --use-current-time
```

Test InfluxDB connectivity:

```bash
python scripts/init_storage.py
```

Show total stored records:

```bash
python scripts/show_record_count.py
```

Publish a local simulated stream:

```bash
python scripts/run_simulator.py --count 60 --interval-seconds 1 --include-failures
```

Start the dashboard without Docker:

```bash
python scripts/run_dashboard.py
```

Start the live MQTT web monitor without Docker:

```bash
python scripts/run_mqtt_monitor.py
```

Runtime logs are written to `logs/` and printed to the terminal. Log files are ignored by Git, but the folder is kept so the project structure is visible.

## Configuration

Runtime settings live in `config/settings.yaml`, with local secrets and service credentials supplied through environment variables or `.env`. The committed `.env.example` documents the expected local values without committing private credentials.

## More Detail

- [Architecture](docs/architecture.md)
- [Data schema](docs/data_schema.md)
- [Local setup](docs/local_setup.md)
- [Hardware plan](docs/hardware_plan.md)

## Engineering Highlights

- Modular Python application structure with clear ingestion, processing, storage, monitoring, and dashboard layers
- YAML and environment-driven configuration
- MQTT ingestion with structured logging and recoverable connection handling
- Validation for malformed payloads, missing fields, invalid timestamps, and out-of-range sensor values
- Rule-based event detection for environmental risk signals
- InfluxDB writer/query modules with schema documentation
- Streamlit dashboard with live trends, event counts, anomaly timeline, and record totals
- Docker Compose runtime for reproducible local operation
- Unit test coverage for processing, ingestion, simulator, storage, and monitoring behavior
