#include <Wire.h>

constexpr int SDA_PIN = 21;
constexpr int SCL_PIN = 22;

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

void printBoschSensorId(byte address) {
  int chipId = readRegister(address, 0xD0);
  if (chipId < 0) {
    Serial.println("  Could not read Bosch sensor chip ID");
    return;
  }

  Serial.print("  Bosch chip ID register 0xD0 = 0x");
  if (chipId < 16) {
    Serial.print("0");
  }
  Serial.println(chipId, HEX);

  if (chipId == 0x60) {
    Serial.println("  Detected sensor type: BME280");
  } else if (chipId == 0x58) {
    Serial.println("  Detected sensor type: BMP280");
  } else {
    Serial.println("  Detected sensor type: unknown Bosch-compatible sensor");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Wire.begin(SDA_PIN, SCL_PIN);
  Serial.println("I2C scanner started on ESP32 GPIO21=SDA, GPIO22=SCL");
}

void loop() {
  byte error;
  int devices = 0;

  Serial.println("Scanning...");

  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("I2C device found at 0x");
      if (address < 16) {
        Serial.print("0");
      }
      Serial.println(address, HEX);

      if (address == 0x76 || address == 0x77) {
        printBoschSensorId(address);
      }

      devices++;
    }
  }

  if (devices == 0) {
    Serial.println("No I2C devices found");
  } else {
    Serial.print("Done. Devices found: ");
    Serial.println(devices);
  }

  delay(3000);
}
