# IoT Environmental Intelligence Pipeline

Production-style IoT capstone project for collecting environmental data from an ESP32 device, processing it in real time, storing it in InfluxDB, and visualizing actionable room-environment insights.

## What It Does

This project turns raw room sensor readings into useful decisions:

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

## Project Layout

```text
config/       Runtime configuration and thresholds
docker/       Local service configuration for Docker Compose
docs/         Architecture, schema, setup, and hardware notes
examples/     Sample MQTT payloads for manual testing and demos
firmware/     ESP32 firmware and device-specific templates
logs/         Runtime log files created by the Python services
scripts/      Entrypoints for storage checks, consumer, and dashboard
src/          Python application code
tests/        Unit tests for processing, ingestion, and storage behavior
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Local InfluxDB + Dashboard

Start the local MQTT broker and InfluxDB:

```bash
docker compose up -d mqtt influxdb
```

Verify the app can connect:

```bash
docker compose run --rm app python scripts/init_storage.py
```

Start the MQTT consumer:

```bash
docker compose up -d consumer
```

Start the Streamlit dashboard:

```bash
docker compose up -d app
```

Open:

```text
Streamlit: http://localhost:8501
InfluxDB:  http://localhost:8086
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
python scripts/publish_example.py examples/valid_reading.json
```

Test InfluxDB connectivity:

```bash
python scripts/init_storage.py
```

Start the dashboard without Docker:

```bash
python scripts/run_dashboard.py
```

Runtime logs are written to `logs/` and printed to the terminal. Log files are ignored by Git, but the folder is kept so the project structure is visible.

## More Detail

- [Architecture](docs/architecture.md)
- [Data schema](docs/data_schema.md)
- [Local setup](docs/local_setup.md)
- [Hardware plan](docs/hardware_plan.md)

## Current Status

Completed:

- Modular Python application structure
- YAML configuration
- Validation layer
- Rule-based event detection
- Transformer layer
- MQTT consumer
- InfluxDB writer/query modules
- Streamlit dashboard
- Docker Compose runtime
- Unit tests

Current test status:

```text
25 passed
```

Next:

- Fill in ESP32 firmware once hardware is ready
- Connect a live MQTT broker
- Collect 10,000+ real sensor records
- Demonstrate induced failures such as skipped sends, bad values, duplicates, or delayed transmissions
