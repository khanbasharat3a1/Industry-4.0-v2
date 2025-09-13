#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

// --- WiFi Credentials ---
const char* ssid = "CMF2P";
const char* password = "basharat";

// --- Server Configuration ---
// Replace with your PC's local IP and port for the Flask server
const char* serverUrl = "http://10.91.43.21:5000/send-data";

// --- Data Buffers for Serial Input ---
// Max size for each data segment, allowing for null terminator
// Using char arrays for fixed-size strings.
char data1[30] = "";  // e.g., "ADU_TEXT"
char data2[30] = "";  // e.g., IR1 status
char data3[30] = "";  // e.g., IR2 status
char data4[30] = "";  // e.g., IR3 status
char data5[30] = "";  // e.g., IR4 status
char data6[30] = "";  // e.g., FLAME status
char data7[30] = "";  // e.g., TEMP value
char data8[30] = "";  // e.g., HUMIDITY value
char data9[30] = "";  // e.g., ALARM status
char data10[30] = ""; // e.g., GATE status
char data11[30] = ""; // e.g., SMOKE status
char data12[30] = ""; // e.g., TSTS status
char data13[30] = ""; // e.g., Extra data
char data14[30] = ""; // e.g., Extra data

// --- Function Prototypes ---
void sendData();
void RelayOperation(); // Prototype for the relay control function


// --- Setup Function ---
void setup() {
  Serial.begin(9600); // Initialize serial communication
  
  // Connect to Wi-Fi
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); // Reduced delay for faster connection attempts
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

}

// --- sendData Function: Handles HTTP POST Request ---
void sendData() {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    Serial.println("Attempting HTTP POST...");

    // Start HTTP connection
    if (http.begin(client, serverUrl)) {
      http.addHeader("Content-Type", "application/json"); // Set content type for JSON

      // Construct JSON data string with all 13 parsed values
      // Ensure the keys match what your Flask server expects.
      // I've used generic keys for data1 and data13.
      char jsonBuffer[300]; // Increased buffer size for more data
      sprintf(jsonBuffer, "{\"TYPE\": \"%s\", \"VAL1\": \"%s\", \"VAL2\": \"%s\", \"VAL3\": \"%s\", \"VAL4\": \"%s\", \"VAL5\": \"%s\", \"VAL6\": \"%s\", \"VAL7\": \"%s\", \"VAL8\": \"%s\", \"VAL9\": \"%s\", \"VAL10\": \"%s\", \"VAL11\": \"%s\", \"VAL12\": \"%s\"}",
              data1, data2, data3, data4, data5, data6, data7, data8, data9, data10, data11, data12, data13 );

      Serial.print("Sending JSON: ");
      Serial.println(jsonBuffer);

      // Send the POST request
      int httpResponseCode = http.POST(jsonBuffer);

      // Process HTTP response
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.printf("HTTP Response Code: %d\n", httpResponseCode);
        Serial.println("Server Response: " + response);
      } else {
        Serial.printf("HTTP POST failed. Error code: %d - %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
      }

      http.end(); // Free resources
    } else {
      Serial.println("HTTP begin failed. Check serverUrl or network.");
    }
  } else {
    Serial.println("WiFi not connected. Attempting to reconnect...");
    WiFi.begin(ssid, password); // Attempt to reconnect if WiFi is lost
  }
}

// --- Loop Function ---
void loop() {
  // Check if there's data available in the Serial buffer
  if (Serial.available() > 0) {
    char receivedBuffer[501]; // Buffer to store received serial data
    memset(receivedBuffer, 0, sizeof(receivedBuffer)); // Clear buffer

    // Read bytes until newline character or buffer is full
    // Reads up to 500 characters + null terminator
    size_t bytesRead = Serial.readBytesUntil('\n', receivedBuffer, 500);
    receivedBuffer[bytesRead] = '\0'; // Ensure null-termination

    Serial.print("Received from Serial: ");
    Serial.println(receivedBuffer);

    // Parse the received string using sscanf
    // IMPORTANT: Specify max field width to prevent buffer overflows!
    // Example: %29[^&] reads up to 29 characters into a 30-byte buffer.
  int numParsed = sscanf(receivedBuffer, "%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29[^&]&%29s",
                           data1, data2, data3, data4, data5, data6, data7, data8, data9, data10, data11, data12, data13, data14);

    Serial.printf("Parsed %d data segments.\n", numParsed);
    Serial.printf("data1 (TYPE): %s\n", data1);
    Serial.printf("data2 (VAL1): %s, data3 (VAL2): %s, data4 (VAL3): %s, data5 (VAL4): %s\n", data2, data3, data4, data5);
    Serial.printf("data6 (VAL5): %s, data7 (VAL6): %s, data8 (VAL7): %s\n", data6, data7, data8);
    Serial.printf("data9 (VAL8): %s, data10 (VAL9): %s, data11 (VAL10): %s\n", data9, data10, data11);
    Serial.printf("data12 (VAL11): %s, data13 (VAL12): %s, data14 (VAL13): %s\\n", data12, data13 ,data14);


    // After parsing, send the data
    sendData();
    
    delay(100); // Small delay to prevent watchdog timer resets
  }
}
