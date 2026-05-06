#pragma once

// Copy this file to secrets.h in the same folder and fill in values for your local network.
// Do not commit secrets.h.

const char* WIFI_SSID = "your-wifi-name";
const char* WIFI_PASSWORD = "your-wifi-password";

// Use the IP address of the computer running docker compose / Mosquitto.
// Example: "192.168.1.25"
const char* MQTT_BROKER = "your-mqtt-broker-ip";
const int MQTT_PORT = 1883;

const char* DEVICE_ID = "esp32_room_1";
const char* DEVICE_LOCATION = "bedroom";
const char* MQTT_TOPIC_RAW = "iot/environment/raw";
