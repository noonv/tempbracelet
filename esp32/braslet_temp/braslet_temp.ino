/*
    Program for braslet temperature

    Scheme:

    ESP32 ---- (GPIO 16) <--- DS18B20
    ^
    |
    +----- Battery

    Program:
    
    init
    go to sleep

    start Wi-Fi
    send temperature to server
    go to sleep
 */
#include "WiFi.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include <HTTPClient.h>

#define TEMPERATURE_THRESHOLD 29
#define SEND_ONLY_THRESHOLD_DATA 0

#include "esp_wpa2.h"
#define USE_WPA2 1
#define EAP_ID "username"
#define EAP_USERNAME "username"
#define EAP_PASSWORD "userpasswd"

//const char* ssid = "REPLACE_WITH_YOUR_SSID";
//const char* password = "REPLACE_WITH_YOUR_PASSWORD";
const char *ssid = "WiFi_ap_name";
const char *password = "";

//Your Domain name with URL path or IP address with path
//String serverName = "http://10.252.65.23:8000/update";
String serverName = "http://tempbracelet.herokuapp.com/api/update";

String userId = "1";
String userIdCode = "";

#define MAX_AP_CONNECT_COUNT 10

#define uS_TO_S_FACTOR 1000000ULL /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP 60          /* Time ESP32 will go to sleep (in seconds) */

// GPIO where the DS18B20 is connected to
const int oneWireBus = 16;

OneWire oneWire(oneWireBus);
DallasTemperature sensors(&oneWire);

int numberOfDevices;
DeviceAddress tempDeviceAddress;

// function to print a device address
void printAddress(DeviceAddress deviceAddress)
{
    for (uint8_t i = 0; i < 8; i++)
    {
        if (deviceAddress[i] < 16)
            Serial.print("0");
        Serial.print(deviceAddress[i], HEX);
    }
}

/*
Method to print the reason by which ESP32
has been awaken from sleep
*/
void print_wakeup_reason()
{
    esp_sleep_wakeup_cause_t wakeup_reason;

    wakeup_reason = esp_sleep_get_wakeup_cause();

    switch (wakeup_reason)
    {
    case ESP_SLEEP_WAKEUP_EXT0:
        Serial.println("Wakeup caused by external signal using RTC_IO");
        break;
    case ESP_SLEEP_WAKEUP_EXT1:
        Serial.println("Wakeup caused by external signal using RTC_CNTL");
        break;
    case ESP_SLEEP_WAKEUP_TIMER:
        Serial.println("Wakeup caused by timer");
        break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD:
        Serial.println("Wakeup caused by touchpad");
        break;
    case ESP_SLEEP_WAKEUP_ULP:
        Serial.println("Wakeup caused by ULP program");
        break;
    default:
        Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason);
        break;
    }
}

void wifiScan()
{
    Serial.println("scan start");

    // WiFi.scanNetworks will return the number of networks found
    int n = WiFi.scanNetworks();
    Serial.println("scan done");
    if (n == 0)
    {
        Serial.println("no networks found");
    }
    else
    {
        Serial.print(n);
        Serial.println(" networks found");
        for (int i = 0; i < n; ++i)
        {
            // Print SSID and RSSI for each network found
            Serial.print(i + 1);
            Serial.print(": ");
            Serial.print(WiFi.SSID(i));
            Serial.print(" (");
            Serial.print(WiFi.RSSI(i));
            Serial.print(")");
            Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? " " : "*");
            delay(10);
        }
    }
    Serial.println("");
}

void sensorsScan()
{
    // Grab a count of devices on the wire
    numberOfDevices = sensors.getDeviceCount();

    // locate devices on the bus
    Serial.print("Locating devices...");
    Serial.print("Found ");
    Serial.print(numberOfDevices, DEC);
    Serial.println(" devices.");

    if (!numberOfDevices)
    {
        numberOfDevices = 1;
        Serial.print("Try ");
        Serial.println(numberOfDevices);
    }

    // Loop through each device, print out address
    for (int i = 0; i < numberOfDevices; i++)
    {
        // Search the wire for address
        if (sensors.getAddress(tempDeviceAddress, i))
        {
            Serial.print("Found device ");
            Serial.print(i, DEC);
            Serial.print(" with address: ");
            printAddress(tempDeviceAddress);
            Serial.println();
        }
        else
        {
            Serial.print("Found ghost device at ");
            Serial.print(i, DEC);
            Serial.print(" but could not detect address. Check power and cabling");
        }
    }
}

void setup()
{
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH);

    Serial.begin(115200);
    delay(1000); //Take some time to open up the Serial Monitor

    //Print the wakeup reason for ESP32
    print_wakeup_reason();

    /*
  First we configure the wake up source
  We set our ESP32 to wake up every 5 seconds
  */
    esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
    Serial.println("Setup ESP32 to sleep for every " + String(TIME_TO_SLEEP) +
                   " Seconds");

    // Start the DS18B20 sensor
    sensors.begin();

    Serial.println("Setup done");

    sensorsScan();

    sensors.requestTemperatures();
    float temperatureC = sensors.getTempCByIndex(0);
    Serial.print("T = ");
    Serial.print(temperatureC);
    Serial.println("ºC");

    bool is_send_wifi_data = false;

    if (temperatureC > TEMPERATURE_THRESHOLD)
    {
#if SEND_ONLY_THRESHOLD_DATA        
        is_send_wifi_data = true;
#endif
        // blink
        for(int i=0; i<10; i++) {
            digitalWrite(LED_BUILTIN, LOW);
            delay(100);
            digitalWrite(LED_BUILTIN, HIGH);
            delay(100);
        }
    }
#if !SEND_ONLY_THRESHOLD_DATA
    is_send_wifi_data = true;
#endif

    if (is_send_wifi_data)
    {
        Serial.println("Try send data.");

        // Set WiFi to station mode and disconnect from an AP if it was previously connected
        WiFi.disconnect();
        WiFi.mode(WIFI_STA);
        delay(1000);

        wifiScan();

#if USE_WPA2
        esp_wifi_sta_wpa2_ent_set_identity((uint8_t *)EAP_ID, strlen(EAP_ID));
        esp_wifi_sta_wpa2_ent_set_username((uint8_t *)EAP_USERNAME, strlen(EAP_USERNAME));
        esp_wifi_sta_wpa2_ent_set_password((uint8_t *)EAP_PASSWORD, strlen(EAP_PASSWORD));
        esp_wpa2_config_t config = WPA2_CONFIG_INIT_DEFAULT(); //set config settings to default
        esp_wifi_sta_wpa2_ent_enable(&config);                 //set config settings to enable function

        WiFi.begin(ssid);
#else
        WiFi.begin(ssid, password);
#endif //#if USE_WPA2

        Serial.print("Connecting to ");
        Serial.println(ssid);
        uint32_t connect_count = 0;
        while (WiFi.status() != WL_CONNECTED)
        {
            delay(500);
            Serial.print(".");
            connect_count++;
            if (connect_count > MAX_AP_CONNECT_COUNT)
            {
                Serial.println("");
                Serial.println("WiFi.satus() break");
                break;
            }
        }
        Serial.println("");
        Serial.print("Connected to WiFi network with IP Address: ");
        Serial.println(WiFi.localIP());

        if (WiFi.status() == WL_CONNECTED)
        {
            HTTPClient http;

            String serverPath = serverName + "?id=" + userId + "&code=" + userIdCode + "&temperature=" + String(temperatureC);

            Serial.print("Request: ");
            Serial.println(serverPath);

            // Your Domain name with URL path or IP address with path
            http.begin(serverPath.c_str());

            // Send HTTP GET request
            int httpResponseCode = http.GET();

            if (httpResponseCode > 0)
            {
                Serial.print("HTTP Response code: ");
                Serial.println(httpResponseCode);
                String payload = http.getString();
                Serial.println(payload);
            }
            else
            {
                Serial.print("Error code: ");
                Serial.println(httpResponseCode);
            }
            // Free resources
            http.end();
        }
        else
        {
            Serial.println("WiFi Disconnected");
        }
    } //if(is_send_wifi_data) {

    digitalWrite(LED_BUILTIN, LOW);

    Serial.println("Going to sleep now");
    Serial.flush();
    esp_deep_sleep_start();
    Serial.println("This will never be printed");
}

void loop()
{
    //This is not going to be called
    Serial.println("loop");
}
