#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// WiFi credentials
const char* ssid = "TT_6028";
const char* password = "Ch10827178@@";

// Server URL (HTTPS)
const char* serverName = "http://web-production-66a96.up.railway.app/add_data";

// LED pins
const int greenPin = 2;  // ✅
const int yellowPin = 4; // 🟡

// BLE scan object
BLEScan* pBLEScan;

// LCD object (I2C address 0x27, 16 cols x 2 rows)
LiquidCrystal_I2C lcd(0x27, 16, 2);

void setStatusLED(bool ok, bool noTagOrError) {
  digitalWrite(greenPin, ok ? HIGH : LOW);
  digitalWrite(yellowPin, noTagOrError ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Setup started");

  pinMode(greenPin, OUTPUT);
  pinMode(yellowPin, OUTPUT);
  setStatusLED(false, true); // Au départ : problème (jaune)

  // LCD init
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");

  // Connect to WiFi
  WiFi.begin(ssid, password);
  int wifiTry = 0;
  while (WiFi.status() != WL_CONNECTED && wifiTry < 30) { // Timeout ~15s max
    delay(500);
    Serial.print(".");
    setStatusLED(false, true);
    wifiTry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected");
    setStatusLED(true, false);
  } else {
    Serial.println("\n❌ WiFi Failed");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed");
    setStatusLED(false, true);
  }

  // BLE init
  BLEDevice::init("");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  Serial.println("Loop start");

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi disconnected!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Disconnected");
    setStatusLED(false, true);
    delay(5000);
    return;
  }

  bool tagDetected = false;

  class LocalAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
    public:
      bool* detected;
      LocalAdvertisedDeviceCallbacks(bool* d) { detected = d; }

      void onResult(BLEAdvertisedDevice advertisedDevice) override {
        String deviceName = advertisedDevice.getName().c_str();
        if (deviceName.length() == 0) deviceName = "Unknown";

        int rssi = advertisedDevice.getRSSI();
        String esp32_mac = WiFi.macAddress();

        if (rssi > -65) { // distance < ~2m
          *detected = true;

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

  Serial.println("➡ Scanning BLE...");
  pBLEScan->setAdvertisedDeviceCallbacks(new LocalAdvertisedDeviceCallbacks(&tagDetected), false);
  pBLEScan->start(5, false); // scan 5s pour éviter surcharge
  pBLEScan->clearResults();

  if (!tagDetected) {
    Serial.println("❌ No Tag Found");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("No Tag Found");
    setStatusLED(false, true);
  }

  delay(2000); // Petit délai pour laisser respirer la boucle
}

void sendDataToServer(String deviceName, int rssi, String esp32_mac) {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClientSecure client;
    client.setInsecure();  // TEST uniquement: ignore la validation certificat HTTPS

    HTTPClient http;
    if (http.begin(client, serverName)) {
      http.addHeader("Content-Type", "application/json");

      String jsonPayload = "{\"instrument_name\":\"" + deviceName + "\",\"rssi\":" + String(rssi) + ",\"mac_address\":\"" + esp32_mac + "\"}";

      int httpResponseCode = http.POST(jsonPayload);

      if (httpResponseCode > 0) {
        Serial.println("✅ Data sent. Code: " + String(httpResponseCode));
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Server OK");
        lcd.setCursor(0, 1);
        lcd.print("Code: " + String(httpResponseCode));
        setStatusLED(true, false);
      } else {
        Serial.println("❌ Server error. Code: " + String(httpResponseCode));
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Server Error!");
        lcd.setCursor(0, 1);
        lcd.print("Code: " + String(httpResponseCode));
        setStatusLED(false, true);
      }
      http.end();
    } else {
      Serial.println("❌ Unable to connect to server");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Connect Err");
      setStatusLED(false, true);
    }
  } else {
    Serial.println("❌ WiFi Lost");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Lost");
    setStatusLED(false, true);
  }
}
