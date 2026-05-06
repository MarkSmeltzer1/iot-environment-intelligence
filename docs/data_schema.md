# Data Schema

Raw ESP32 messages are JSON payloads sent over MQTT.

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

## Required Fields

- `timestamp`
- `device_id`
- `location`
- `temperature_f`
- `humidity`
- `pressure_hpa`
- `light_lux`

## Processed Fields

The processing layer adds:

- `valid`
- `errors`
- `event_label`
- `anomaly_flag`
- `event_reason`
- `reasons`

## Event Labels

- `normal`
- `high_temp_alert`
- `high_humidity_alert`
- `rapid_temp_change`
- `rapid_humidity_change`
- `rapid_light_change`
- `sunlight_heating`
- `sudden_cooling`
- `unknown`

`unknown` is used when a reading fails validation.

The dashboard also derives rapid-change anomaly labels from stored sensor values so visible spikes and drops in temperature, humidity, and light are explained in the anomaly timeline.

## InfluxDB Storage

InfluxDB stores one measurement:

```text
environment_readings
```

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
- `event_reason`

This layout keeps stable, low-cardinality attributes as tags for filtering and grouping. Sensor measurements and event outputs are fields because they change frequently and are queried as values over time.

## Sample Queries

Recent temperature, humidity, pressure, and light trends:

```flux
from(bucket: "environment_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "environment_readings")
  |> filter(fn: (r) => r._field == "temperature_f" or r._field == "humidity" or r._field == "pressure_hpa" or r._field == "light_lux")
```

Recent anomaly events:

```flux
from(bucket: "environment_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "environment_readings")
  |> filter(fn: (r) => r._field == "anomaly_flag")
  |> filter(fn: (r) => r._value == 1)
```

Stored record count:

```flux
from(bucket: "environment_data")
  |> range(start: 0)
  |> filter(fn: (r) => r._measurement == "environment_readings")
  |> filter(fn: (r) => r._field == "temperature_f")
  |> count()
```
