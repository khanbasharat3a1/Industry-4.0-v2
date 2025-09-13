// --------------------------------------------------------------------------------------------------------------------
// Arduino Nano Sketch: RPM, DHT, Current/Voltage, Relays, and SoftwareSerial Communication
// --------------------------------------------------------------------------------------------------------------------

#include <Arduino.h>
#include <SoftwareSerial.h>   // For communication with ESP-01 or other serial devices

// --- SoftwareSerial Configuration ---
// Connect Arduino Nano Digital Pin 3 to ESP-01 RX
// Connect Arduino Nano Digital Pin 4 to ESP-01 TX
SoftwareSerial esp(3, 4);

// --- DHT Sensor Libraries ---
// Removed Adafruit_Sensor.h and DHT_U.h as they are not needed for the standard DHT.h library
#include <DHT.h>              // Standard DHT library (includes computeHeatIndex)

#define DHTPIN 5              // Digital pin connected to the DHT sensor
#define DHTTYPE DHT22         // DHT 11 sensor type

// DHT sensor instance (using the simpler DHT library for computeHeatIndex)
DHT dht(DHTPIN, DHTTYPE);

// --- Relay Pin Definitions ---
const int RLY1 = 10; // Digital Pin 10
const int RLY2 = 11; // Digital Pin 11
const int RLY3 = 12; // Digital Pin 12

// --- Sensor Pin Definitions ---
const int CURRENT_SENSOR_PIN = A0; // Analog pin for current sensor
const int VOLTAGE_SENSOR_PIN = A1; // Analog pin for voltage sensor
const int SPEED_SENSOR_PIN = 2;    // Digital pin for speed sensor (External Interrupt 0)

// --- RPM Measurement Variables ---
volatile int pulseCount = 0;      // Use volatile for interrupt-driven counting
unsigned long startTime = 0;
const unsigned long MEASUREMENT_DURATION_MS = 10000; // Measure speed over 10 seconds (10000 milliseconds)

int rpm = 0;  // Current calculated RPM
int prpm = 0; // Previous calculated RPM (for averaging)

// --- Sensor Reading Variables ---
unsigned int Sensor1_Val = 0; // Stores Current Sensor value
unsigned int Sensor2_Val = 0; // Stores Voltage Sensor value
unsigned int Sensor3_Val = 0; // Stores RPM value
unsigned int Sensor4_Val = 0; // Stores DHT Temperature (Celsius)
unsigned int Sensor5_Val = 0; // Stores DHT Humidity
unsigned int Sensor6_Val = 0; // Stores DHT Temperature (Fahrenheit)
unsigned int Sensor7_Val = 0; // Stores DHT Heat Index (Celsius)
unsigned int Sensor8_Val = 0; // Stores DHT Heat Index (Fahrenheit)

// --- Relay Status Variables ---
unsigned int RLY1_STATUS = 0;
unsigned int RLY2_STATUS = 0;
unsigned int RLY3_STATUS = 0;

// --- Control Flags/Delays ---
unsigned int ADC_send_delay = 0; // Keeping for consistency, though not actively used in this loop structure
unsigned int ADC_send = 1;       // Set to 1 to ensure initial sensor read and send

// --- Sensor Thresholds ---
#define CURRENT_NORMAL 230 // Analog value: Below this is considered normal
#define CURRENT_ALARM  700  // Analog value: Above this is considered an alarm
#define CURRENT_BUZZER 800 // Analog value: Above this for buzzer (if used)

#define VOLTAGE_NORMAL 10000  // Analog value: Below this is considered normal
#define VOLTAGE_ALARM 20000   // Analog value: Above this is considered an alarm
#define VOLTAGE_BUZZER 12000  // Analog value: Above this for buzzer (if used)

#define DHT11_NORMAL 30    // Temperature threshold in Celsius
#define DHT11_ALARM 30     // Temperature alarm threshold
#define DHT11_BUZZER 35    // Temperature buzzer threshold

// --- Buffers for sprintf (for sending data via SoftwareSerial) ---
char foo[10]; // For Sensor1_Val (CURRENT)
char bar[10]; // For Sensor2_Val (VOLTAGE)
char goo[10]; // For Sensor3_Val (RPM)
char har[10]; // For Sensor4_Val (DHT Temp C)
char ioo[10]; // For Sensor5_Val (DHT Humidity)
char jar[10]; // For Sensor6_Val (DHT Temp F)
char loo[10]; // For Sensor7_Val (DHT Heat Index C)
char mar[10]; // For Sensor8_Val (DHT Heat Index F)
char nob[10]; // For RLY1_STATUS ("ON"/"OFF")
char tot[10]; // For RLY2_STATUS ("ON"/"OFF")
char zar[10]; // For RLY3_STATUS ("ON"/"OFF")
char yar[10]; // For Combined Relay Status ("NOR"/"ALM"/"BUZ")
char uar[10]; // For "RSV" (Reserved)

// --- Function Prototypes (Declarations) ---
void countPulse();        // ISR for RPM sensor
void Cal_RPM();           // Calculates RPM
void ReadSensor_values(); // Reads Current, Voltage, and DHT sensors
void RelayOperation();    // Controls relays based on sensor values
void DHT11_init();        // Initializes DHT sensor
void DHT11_read();        // Reads DHT sensor data

// --------------------------------------------------------------------------------------------------------------------
// Setup Function: Runs once when you press reset or power the board
// --------------------------------------------------------------------------------------------------------------------
void setup() {
  Serial.begin(9600); // Initialize hardware serial for debugging output
  esp.begin(9600);    // Initialize software serial for communication with ESP-01

  // Initialize Relay Pins as OUTPUTs
  pinMode(RLY1, OUTPUT);
  pinMode(RLY2, OUTPUT);
  pinMode(RLY3, OUTPUT);

  // Set all relays OFF initially (assuming HIGH means OFF for your relays)
  digitalWrite(RLY1, HIGH);
  digitalWrite(RLY2, HIGH);
  digitalWrite(RLY3, HIGH);

  // Initialize Analog Sensor Input Pins
  pinMode(CURRENT_SENSOR_PIN, INPUT); // Analog input
  pinMode(VOLTAGE_SENSOR_PIN, INPUT); // Analog input

  // Initialize DHT11 Sensor
  DHT11_init();

  // Configure the Speed Sensor input pin
  pinMode(SPEED_SENSOR_PIN, INPUT_PULLUP); // Enable internal pull-up resistor

  // Attach the interrupt for the speed sensor
  // Digital Pin 2 corresponds to External Interrupt 0 (INT0) on Arduino Nano.
  // RISING means the interrupt triggers when the signal goes from LOW to HIGH.
  attachInterrupt(digitalPinToInterrupt(SPEED_SENSOR_PIN), countPulse, RISING);

  // Initialize startTime for the first measurement window
  startTime = millis() + MEASUREMENT_DURATION_MS;

  Serial.println("\nArduino Nano Setup Complete.");
  Serial.println("Waiting for sensor readings and RPM pulses...");
}

// --------------------------------------------------------------------------------------------------------------------
// Loop Function: Runs over and over again forever
// --------------------------------------------------------------------------------------------------------------------
void loop() {
  // Check if the measurement duration has passed
  if (millis() - startTime >= MEASUREMENT_DURATION_MS) {
    // Perform all readings and operations
    Cal_RPM();           // Calculate RPM
    ReadSensor_values(); // Read Current, Voltage, and DHT sensors
    RelayOperation();    // Control relays based on sensor values

    // Populate char arrays with sensor status/values for sending via SoftwareSerial
    sprintf(foo, "%d", Sensor1_Val);   // CURRENT
    sprintf(bar, "%d", Sensor2_Val);   // VOLTAGE
    sprintf(goo, "%d", Sensor3_Val);   // RPM
    sprintf(har, "%d", Sensor4_Val);   // DHT Temp C
    sprintf(ioo, "%d", Sensor5_Val);   // DHT Humidity
    sprintf(jar, "%d", Sensor6_Val);   // DHT Temp F
    sprintf(loo, "%d", Sensor7_Val);   // DHT Heat Index C
    sprintf(mar, "%d", Sensor8_Val);   // DHT Heat Index F

    // Relay Status strings
    if (RLY1_STATUS == 0) { sprintf(nob, "%s", "OFF"); } else { sprintf(nob, "%s", "ON"); }
    if (RLY2_STATUS == 0) { sprintf(tot, "%s", "OFF"); } else { sprintf(tot, "%s", "ON"); }
    if (RLY3_STATUS == 0) { sprintf(zar, "%s", "OFF"); } else { sprintf(zar, "%s", "ON"); }

    /*// Combined Relay Status (based on your logic)
    if ((RLY1_STATUS == 1) && (RLY2_STATUS == 0) && (RLY3_STATUS == 0)) {
      sprintf(yar, "%s", "NOR"); // Normal
    } else if ((RLY1_STATUS == 0) && (RLY2_STATUS == 1) && (RLY3_STATUS == 0)) {
      sprintf(yar, "%s", "ALM"); // Alarm
    } else if ((RLY1_STATUS == 0) && (RLY2_STATUS == 0) && (RLY3_STATUS == 1)) {
      sprintf(yar, "%s", "BUZ"); // Buzzer/Shutdown
    } else {
      sprintf(yar, "%s", "INV"); // Invalid State (or another default)
    }*/
    if ((RLY1_STATUS == 0) && (RLY2_STATUS == 0) && (RLY3_STATUS == 0)) {
      sprintf(yar, "%s", "NOR"); // Normal
    } else if ((RLY1_STATUS == 1) || (RLY2_STATUS == 1) || (RLY3_STATUS == 1)) {
      sprintf(yar, "%s", "BUZ"); // Alarm
    }
    sprintf(uar, "%s", "RSV"); // Reserved

    // Construct the full serial string to send to ESP-01
    char str[200]; // Increased buffer size for the concatenated string
    strcpy(str, "ADU_TEXT&");
    strcat(str, foo); // CURRENT
    strcat(str, "&");
    strcat(str, bar); // VOLTAGE
    strcat(str, "&");
    strcat(str, goo); // RPM
    strcat(str, "&");
    strcat(str, har); // DHT Temp C
    strcat(str, "&");
    strcat(str, ioo); // DHT Humidity
    strcat(str, "&");
    strcat(str, jar); // DHT Temp F
    strcat(str, "&");
    strcat(str, loo); // DHT Heat Index C
    strcat(str, "&");
    strcat(str, mar); // DHT Heat Index F
    strcat(str, "&");
    strcat(str, nob); // RLY1_STATUS
    strcat(str, "&");
    strcat(str, tot); // RLY2_STATUS
    strcat(str, "&");
    strcat(str, zar); // RLY3_STATUS
    strcat(str, "&");
    strcat(str, yar); // Combined Relay Status
    strcat(str, "&");
    strcat(str, uar); // Reserved

    Serial.print("\nSending to ESP: ");
    Serial.println(str);
    esp.print(str); // Send data to ESP-01 via SoftwareSerial

    // Reset startTime for the next measurement window
    startTime = millis();
  }

  // Small delay for stability
  delay(10);
}

// --------------------------------------------------------------------------------------------------------------------
// Helper Functions (Definitions)
// --------------------------------------------------------------------------------------------------------------------

/**
 * @brief Interrupt Service Routine (ISR) for the speed sensor.
 * Increments pulseCount on each rising edge.
 */
void countPulse() {
  pulseCount++;
}

/**
 * @brief Calculates RPM based on pulseCount over the measurement duration.
 * Resets pulseCount and restarts the measurement window.
 */
void Cal_RPM() {
  //pulseCount = 0 ;
  // Temporarily disable interrupts to safely read and reset pulseCount
  detachInterrupt(digitalPinToInterrupt(SPEED_SENSOR_PIN));

  Serial.print("\nRaw Pulse Count: ");
  Serial.print(pulseCount);

  // Your original RPM calculation logic was commented out,
  // and you have a new custom calculation based on pulseCount/400.
  // I'm using your new logic directly.
  if (pulseCount == 0) {
    prpm = 0;
  } else {
    if (prpm == 0) {
      prpm = pulseCount * 3; // Initial calculation
    } else {
      prpm = (prpm + (pulseCount *3)) / 2; // Averaging
    }
  }

  Serial.print("\tCalculated RPM (prpm): ");
  Serial.println(prpm);
  Sensor3_Val = prpm; // Store calculated RPM in Sensor3_Val
  Serial.print("Sensor3_Val (RPM): ");
  Serial.println(Sensor3_Val);

  pulseCount = 0; // Reset pulse counter
  // startTime is reset in loop() after all operations for the current window.
  // Re-enable interrupts to continue counting pulses for the next window
  attachInterrupt(digitalPinToInterrupt(SPEED_SENSOR_PIN), countPulse, RISING);
}

/**
 * @brief Reads values from Current, Voltage, and DHT sensors.
 */
void ReadSensor_values() {
  Serial.println("\n--------------------------------");
  Sensor1_Val = 0 ;
  Sensor2_Val = 0 ;

  // Read Current Sensor (Analog)
  Sensor1_Val = analogRead(CURRENT_SENSOR_PIN);
  Serial.print("Current Sensor Value (raw): ");
  Serial.println(Sensor1_Val);
  // Apply your scaling factor (multiplied by 6)
  if( Sensor1_Val < 20)
    { Sensor1_Val = 0 ; }
  else  
    { Sensor1_Val = Sensor1_Val /3.4; }
  Serial.print("Current Sensor Value (Sensor1_Val): ");
  Serial.println(Sensor1_Val);
  delay(10); // Small delay after reading analog

  // Read Voltage Sensor (Analog)
  Sensor2_Val = analogRead(VOLTAGE_SENSOR_PIN);
  Serial.print("Voltage Sensor Value (raw): ");
  Serial.println(Sensor2_Val);
  // Apply your scaling factor (divided by 45, then multiplied by 1000)
  Sensor2_Val = (unsigned int)((float)Sensor2_Val / 42.8 * 1000.0);
  if(Sensor2_Val <= 1000)
     {  Sensor2_Val = 0 ; }
  Serial.print("Voltage Sensor Value (Sensor2_Val): ");
  Serial.println(Sensor2_Val);
  delay(10); // Small delay after reading analog

  // Read DHT sensor
  DHT11_read();
  delay(10); // Small delay after DHT read
}

/**
 * @brief Controls relays based on Current, Voltage, and DHT Temperature values.
 */
void RelayOperation() {
  Serial.println("\n--- Performing Relay Operations ---");

  Serial.print("Current RLY1_STATUS = "); Serial.print(RLY1_STATUS);
  Serial.print(", RLY2_STATUS = "); Serial.print(RLY2_STATUS);
  Serial.print(", RLY3_STATUS = "); Serial.print(RLY3_STATUS);

  // Logic for relay control based on sensor thresholds
  // All sensors normal
  //if ((Sensor1_Val <= CURRENT_NORMAL) && (Sensor2_Val <= VOLTAGE_NORMAL) && (Sensor4_Val <= DHT11_NORMAL)) {
  if ((Sensor2_Val <= VOLTAGE_NORMAL) ) {  
    Serial.println("\n Voltage values is normal.");
    if(RLY2_STATUS == 1)
    {
       digitalWrite(RLY2, HIGH);  // RLY1 ON
       Serial.print("RLY2 = OFF");
    }   
    RLY2_STATUS = 0;
    
  }
  else if ((Sensor2_Val > VOLTAGE_NORMAL) ) {  
    Serial.println("\nVoltage values are above normal.");
    if(RLY2_STATUS == 0)
    {
        digitalWrite(RLY2, LOW);  // RLY1 ON
        Serial.print("RLY2 = ON");
    }    
    RLY2_STATUS = 1;
    
  }
  // Alarm condition (Current OR Voltage in alarm range)
  if (Sensor1_Val <= CURRENT_NORMAL) {
    Serial.println("\nCurrent value is normal.");
    if(RLY1_STATUS == 1)
    {
      digitalWrite(RLY1, HIGH); // RLY1 OFF
      Serial.print("RLY1 = OFF");
    }
    RLY1_STATUS = 0;
    
  }
  else if (Sensor1_Val > CURRENT_NORMAL) {
    Serial.println("\nCurrent value above normal\.");
    if(RLY1_STATUS == 0)
    {
       digitalWrite(RLY1, LOW); // RLY1 OFF
       Serial.print("RLY1 = ON");
    }   
    RLY1_STATUS = 1;
    
  }
  
  // Shutdown condition (Current OR Voltage above alarm, OR DHT Temp above normal)
  if ( (Sensor4_Val <= DHT11_NORMAL)) {
    Serial.println("\nTemperature is normal.");
    if(RLY3_STATUS == 1)
    {
      digitalWrite(RLY3, HIGH);  // RLY3 ON
      Serial.print("RLY3 = OFF");
    }
    RLY3_STATUS = 0;
  }
  else if ( (Sensor4_Val > DHT11_NORMAL)) {
    Serial.println("\nTemperature above normal.");
    if(RLY3_STATUS == 0)
    {
        digitalWrite(RLY3, LOW);  // RLY3 ON
        Serial.print("RLY3 = ON");
    }
    RLY3_STATUS = 1;
  }


  Serial.print("\nFinal RLY1_STATUS = "); Serial.print(RLY1_STATUS);
  Serial.print(", RLY2_STATUS = "); Serial.print(RLY2_STATUS);
  Serial.print(", RLY3_STATUS = "); Serial.println(RLY3_STATUS);
}

/**
 * @brief Initializes the DHT sensor.
 */
void DHT11_init() {
  dht.begin(); // Initialize the DHT sensor
  Serial.println(F("DHT Sensor Initialized."));
}

/**
 * @brief Reads temperature and humidity from the DHT sensor using DHT methods.
 * Stores values in Sensor4_Val to Sensor8_Val, including calculated Heat Index.
 */
void DHT11_read() {
  // Reading temperature or humidity takes about 250 milliseconds!
  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)

  // Read humidity as percentage (the default)
  float h = dht.readHumidity();
  // Read temperature as Celsius (the default)
  float t = dht.readTemperature();
  // Read temperature as Fahrenheit (isFahrenheit = true)
  float f = dht.readTemperature(true);

  // Check if any reads failed and exit early (to try again).
  if (isnan(h) || isnan(t) || isnan(f)) {
    Serial.println(F("Failed to read from DHT sensor!"));
    return;
  }

  // Compute heat index in Fahrenheit (the default)
  float hif = dht.computeHeatIndex(f, h);
  // Compute heat index in Celsius (isFahreheit = false)
  float hic = dht.computeHeatIndex(t, h, false);

  // Store values in global Sensor variables
  Sensor4_Val = (unsigned int)t;   // Temperature in Celsius
  Sensor5_Val = (unsigned int)h;   // Humidity
  Sensor6_Val = (unsigned int)f;   // Temperature in Fahrenheit
  Sensor7_Val = (unsigned int)hic; // Heat Index in Celsius
  Sensor8_Val = (unsigned int)hif; // Heat Index in Fahrenheit

  // Print all readings to Serial Monitor for debugging
  Serial.print(F("Humidity: "));
  Serial.print(h);
  Serial.print(F("% \tTemperature: "));
  Serial.print(t);
  Serial.print(F("°C "));
  Serial.print(f);
  Serial.print(F("°F \tHeat index: "));
  Serial.print(hic);
  Serial.print(F("°C "));
  Serial.print(hif);
  Serial.println(F("°F"));
}
