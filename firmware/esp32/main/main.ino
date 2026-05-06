#include <ArduinoJson.h>
#include <BH1750.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_BME280.h>

#include "secrets.h"

namespace {
constexpr unsigned long PUBLISH_INTERVAL_MS = 1000;
constexpr unsigned long WIFI_RETRY_MS = 500;
constexpr unsigned long MQTT_RETRY_MS = 2000;
constexpr int JSON_CAPACITY = 384;
constexpr int SDA_PIN = 21;
constexpr int SCL_PIN = 22;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Adafruit_BME280 bme;
BH1750 lightMeter;

unsigned long lastPublishMs = 0;
unsigned long sequenceNumber = 0;
bool bmeReady = false;
bool lightReady = false;

enum DiagnosticMode {
  MODE_NORMAL,
  MODE_HIGH_TEMP,
  MODE_BAD_VALUE,
  MODE_DROPOUT,
  MODE_DUPLICATE
};

DiagnosticMode diagnosticMode = MODE_NORMAL;
String lastPayload;

int readRegister(byte address, byte reg) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return -1;
  }

  if (Wire.requestFrom(address, (byte)1) != 1) {
    return -1;
  }

  return Wire.read();
}

bool i2cDevicePresent(byte address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

String isoTimestamp() {
  time_t now = time(nullptr);
  struct tm timeInfo;
  if (!gmtime_r(&now, &timeInfo) || now < 1700000000) {
    return "1970-01-01T00:00:00Z";
  }

  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(buffer);
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(WIFI_RETRY_MS);
    Serial.print(".");
  }

  Serial.print("\nWiFi connected: ");
  Serial.println(WiFi.localIP());
}

void connectMqtt() {
  if (mqttClient.connected()) {
    return;
  }

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);

  while (!mqttClient.connected()) {
    Serial.print("Connecting to MQTT...");
    String clientId = String(DEVICE_ID) + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);

    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed rc=");
      Serial.print(mqttClient.state());
      Serial.println(", retrying");
      delay(MQTT_RETRY_MS);
    }
  }
}

void initializeSensors() {
  Wire.begin(SDA_PIN, SCL_PIN);
  Serial.println("I2C initialized on GPIO21=SDA, GPIO22=SCL");
  delay(300);

  if (i2cDevicePresent(0x76)) {
    Serial.println("I2C device present at 0x76");
    int chipId = readRegister(0x76, 0xD0);
    Serial.print("Bosch chip ID at 0x76: 0x");
    Serial.println(chipId, HEX);
  }

  if (i2cDevicePresent(0x77)) {
    Serial.println("I2C device present at 0x77");
    int chipId = readRegister(0x77, 0xD0);
    Serial.print("Bosch chip ID at 0x77: 0x");
    Serial.println(chipId, HEX);
  }

  bmeReady = bme.begin(0x76, &Wire);
  if (!bmeReady) {
    bmeReady = bme.begin(0x77, &Wire);
  }
  Serial.println(bmeReady ? "BME280 ready" : "BME280 not detected");

  lightReady = lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  Serial.println(lightReady ? "BH1750 ready" : "BH1750 not detected");
}

float celsiusToFahrenheit(float celsius) {
  return (celsius * 9.0 / 5.0) + 32.0;
}

float readTemperatureF() {
  if (!bmeReady) {
    return NAN;
  }
  return celsiusToFahrenheit(bme.readTemperature());
}

float readHumidity() {
  if (!bmeReady) {
    return NAN;
  }
  return bme.readHumidity();
}

float readPressureHpa() {
  if (!bmeReady) {
    return NAN;
  }
  return bme.readPressure() / 100.0;
}

float readLightLux() {
  if (!lightReady) {
    return 500.0;
  }
  return lightMeter.readLightLevel();
}

void applyDemoControls(float& temperatureF, float& humidity, float& pressureHpa, float& lightLux) {
  while (Serial.available() > 0) {
    char command = Serial.read();
    if (command == 'n') {
      diagnosticMode = MODE_NORMAL;
      Serial.println("Diagnostic mode: normal");
    } else if (command == 'h') {
      diagnosticMode = MODE_HIGH_TEMP;
      Serial.println("Diagnostic mode: high temperature/light");
    } else if (command == 'b') {
      diagnosticMode = MODE_BAD_VALUE;
      Serial.println("Diagnostic mode: bad out-of-range value");
    } else if (command == 'd') {
      diagnosticMode = MODE_DROPOUT;
      Serial.println("Diagnostic mode: dropout");
    } else if (command == 'u') {
      diagnosticMode = MODE_DUPLICATE;
      Serial.println("Diagnostic mode: duplicate");
    }
  }

  if (diagnosticMode == MODE_HIGH_TEMP) {
    temperatureF = 86.0;
    lightLux = 900.0;
  } else if (diagnosticMode == MODE_BAD_VALUE) {
    temperatureF = 130.0;
  }

  humidity = constrain(humidity, 0.0, 100.0);
  pressureHpa = constrain(pressureHpa, 800.0, 1200.0);
  lightLux = max(lightLux, 0.0f);
}

bool buildPayload(String& payload) {
  float temperatureF = readTemperatureF();
  float humidity = readHumidity();
  float pressureHpa = readPressureHpa();
  float lightLux = readLightLux();

  if (!bmeReady) {
    Serial.println("BME280 unavailable: skipping publish to avoid fake temperature/humidity/pressure data");
    return false;
  }

  applyDemoControls(temperatureF, humidity, pressureHpa, lightLux);

  Serial.print("Sensor reading: temp_f=");
  Serial.print(temperatureF);
  Serial.print(" humidity=");
  Serial.print(humidity);
  Serial.print(" pressure_hpa=");
  Serial.print(pressureHpa);
  Serial.print(" light_lux=");
  Serial.println(lightLux);

  if (diagnosticMode == MODE_DROPOUT) {
    Serial.println("Simulated dropout: skipping publish");
    diagnosticMode = MODE_NORMAL;
    return false;
  }

  if (diagnosticMode == MODE_DUPLICATE && lastPayload.length() > 0) {
    payload = lastPayload;
    diagnosticMode = MODE_NORMAL;
    return true;
  }

  StaticJsonDocument<JSON_CAPACITY> doc;
  doc["timestamp"] = isoTimestamp();
  doc["device_id"] = DEVICE_ID;
  doc["location"] = DEVICE_LOCATION;
  doc["temperature_f"] = round(temperatureF * 100.0) / 100.0;
  doc["humidity"] = round(humidity * 100.0) / 100.0;
  doc["pressure_hpa"] = round(pressureHpa * 100.0) / 100.0;
  doc["light_lux"] = round(lightLux);
  doc["sequence"] = sequenceNumber++;

  payload = "";
  serializeJson(doc, payload);
  lastPayload = payload;
  return true;
}

void publishReading() {
  String payload;
  if (!buildPayload(payload)) {
    return;
  }

  bool published = mqttClient.publish(MQTT_TOPIC_RAW, payload.c_str());
  Serial.print(published ? "Published: " : "Publish failed: ");
  Serial.println(payload);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);

  initializeSensors();
  connectWifi();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  connectMqtt();

  Serial.println("Commands: n=normal, h=high temp/light, b=bad value, d=dropout, u=duplicate");
}

void loop() {
  connectWifi();
  connectMqtt();
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastPublishMs >= PUBLISH_INTERVAL_MS) {
    lastPublishMs = now;
    publishReading();
  }
}
