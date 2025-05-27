#include <WiFi.h>
#include <HTTPClient.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// WiFi credentials
const char* ssid = "TT_6028";
const char* password = "Ch10827178@@";

// Flask server URL
const char* serverName = "http://192.168.1.15:5000/add_data";

// LED pins
const int greenPin = 2;  // ✅
const int yellowPin = 4; // 🟡

BLEScan* pBLEScan;
LiquidCrystal_I2C lcd(0x27, 16, 2); // LCD I2C

void setStatusLED(bool ok, bool noTagOrError) {
  digitalWrite(greenPin, ok ? HIGH : LOW);
  digitalWrite(yellowPin, noTagOrError ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);

  pinMode(greenPin, OUTPUT);
  pinMode(yellowPin, OUTPUT);
  setStatusLED(false, true); //Au départ, il est supposé qu'il y a un problème.

  // LCD init
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    setStatusLED(false, true); // jaune
  }

  Serial.println("\n✅ WiFi Connected!");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi Connected");

  setStatusLED(true, false); // vert

  // BLE init
  BLEDevice::init("");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi disconnected!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Disconnected");
    setStatusLED(false, true); // jaune
    delay(5000);
    return;
  }

  // Tag detection flag
  bool tagDetected = false;

  // BLE Callback Class
  class LocalAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
    public:
      bool* detected;
      LocalAdvertisedDeviceCallbacks(bool* d) { detected = d; }

      void onResult(BLEAdvertisedDevice advertisedDevice) override {
        String deviceName = advertisedDevice.getName().c_str();
        if (deviceName.length() == 0) deviceName = "Unknown";

        int rssi = advertisedDevice.getRSSI();
        String esp32_mac = WiFi.macAddress();

        if (rssi > -65) {
          *detected = true; // ✅ tag detected

          Serial.println("🔍 Tag detected (<= 2m):");
          Serial.println("Name: " + deviceName);
          Serial.println("RSSI: " + String(rssi));
          Serial.println("ESP32 MAC: " + esp32_mac);
          Serial.println("-----");

          lcd.clear();
          lcd.setCursor(0, 0);
          lcd.print("Tag: " + deviceName);
          lcd.setCursor(0, 1);
          lcd.print("RSSI: " + String(rssi));

          sendDataToServer(deviceName, rssi, esp32_mac);
        }
      }
  };

  // Start BLE scan
  Serial.println("➡ Scanning BLE...");
  pBLEScan->setAdvertisedDeviceCallbacks(new LocalAdvertisedDeviceCallbacks(&tagDetected), false);
  pBLEScan->start(10, false);
  pBLEScan->clearResults();

  if (!tagDetected) {
    Serial.println("❌ No Tag Found");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("No Tag Found");
    setStatusLED(false, true); // jaune
  }

  delay(2000);
}

void sendDataToServer(String deviceName, int rssi, String esp32_mac) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);

    String jsonPayload = "{\"instrument_name\":\"" + deviceName + "\",\"rssi\":" + String(rssi) + ",\"mac_address\":\"" + esp32_mac + "\"}";

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      Serial.println("✅ Data sent. Code: " + String(httpResponseCode));
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Server OK");
      lcd.setCursor(0, 1);
      lcd.print("Code: " + String(httpResponseCode));
      setStatusLED(true, false); // vert
    } else {
      Serial.println("❌ Server error. Code: " + String(httpResponseCode));
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Server Error!");
      lcd.setCursor(0, 1);
      lcd.print("Code: " + String(httpResponseCode));
      setStatusLED(false, true); // jaune
    }

    http.end();
  } else {
    Serial.println("❌ WiFi Lost");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Lost");
    setStatusLED(false, true); // jaune
}
}
