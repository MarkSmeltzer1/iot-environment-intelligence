# Demo Plan

This plan keeps the final video under seven minutes and maps directly to the rubric.

## Before Recording

Start the local services:

```bash
docker compose up -d mqtt influxdb consumer app monitor
```

Open:

```text
MQTT monitor: http://localhost:8600
Streamlit: http://localhost:8501
InfluxDB:  http://localhost:8086
```

For pre-device testing only, publish simulated data:

```bash
docker compose exec -T consumer python scripts/run_simulator.py --count 60 --interval-seconds 1 --include-failures
```

The final submission should use the ESP32 as the real device layer.

## Video Flow

1. Show the problem and physical ESP32 device.
2. Show live MQTT payloads arriving in the MQTT monitor.
3. Show consumer logs validating and classifying messages.
4. Show InfluxDB bucket, measurement, tags, fields, and sample query.
5. Show Streamlit dashboard with trends, event counts, anomaly timeline, and record count.
6. Demonstrate at least one induced change or failure.
7. Finish with challenges, lessons learned, and how the design would scale.

## Scaling Notes

For an enterprise version, the design would need authenticated MQTT, TLS, device identity management, retry queues, monitoring/alerting, and managed time-series storage.
