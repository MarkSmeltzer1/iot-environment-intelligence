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
- `reasons`

## Event Labels

- `normal`
- `high_temp_alert`
- `high_humidity_alert`
- `sunlight_heating`
- `sudden_cooling`
- `unknown`

`unknown` is used when a reading fails validation.

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
