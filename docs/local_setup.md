# Local Setup

## Python Environment

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

Verify the app can connect to InfluxDB:

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

Stop local services:

```bash
docker compose down
```

## Local Credentials

Local InfluxDB credentials are configured through `.env`.

```text
username: admin
password: local-password-123
org: iot-project
bucket: environment_data
token: local-dev-token
```

The committed `.env.example` shows the expected variable names without requiring real secrets.

## Useful Commands

```bash
python scripts/run_consumer.py
python scripts/publish_example.py examples/valid_reading.json --use-current-time
python scripts/run_simulator.py --count 60 --interval-seconds 1 --include-failures
python scripts/init_storage.py
python scripts/show_record_count.py
python scripts/run_dashboard.py
python scripts/run_mqtt_monitor.py
```

## Load Testing

With the ESP32 firmware publishing once per second, a 10,000-record data set takes about 2 hours and 47 minutes of continuous runtime.

The simulator can publish the same volume faster when repeatable local load testing is useful:

```bash
docker compose exec -T consumer python scripts/run_simulator.py --count 10000 --interval-seconds 0 --include-failures
docker compose exec -T app python scripts/show_record_count.py
```

Use `scripts/show_record_count.py` to verify stored volume after long-running device or simulator sessions.
