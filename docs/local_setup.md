# Local Setup

## Python Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Docker Runtime

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

Open:

```text
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
python scripts/init_storage.py
python scripts/run_dashboard.py
```
