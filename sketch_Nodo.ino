#include <WiFi.h>
#include <WiFiUDP.h>
#include <DHT.h>
#include <ArduinoJson.h>

// CONFIGURACION WIFI
const char* ssid = "Apiario";
const char* password = "12345678";

// CONFIGURACION DE RED
const char* servidorIP = "192.168.4.1";  // IP del ESP32 Servidor
const int puertoUDP = 8888;

WiFiUDP udp;

// CONFIGURACION DE PINES
#define DHTPIN 4
#define DHTTYPE DHT22
#define PIN_NIVEL_AGUA 34

// INICIALIZACION DE SENSORES
DHT dht(DHTPIN, DHTTYPE);

// CONFIGURACION DEL NODO
const int NODE_ID = 1;
const unsigned long INTERVALO = 5000;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("Iniciando ESP32 ESCLAVO (Nodo 1)...");
  
  dht.begin();
  analogReadResolution(12);
  
  // Conectar a la red "Apiario"
  Serial.print("Conectando a red: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 30) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("Conectado! IP Esclavo: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" ERROR: No se pudo conectar a la red Apiario");
    while (1) {}
  }
  
  Serial.println("Esclavo listo. Enviando datos cada 5 segundos...");
}

// Función para leer sensor de agua con promedio
float leerNivelAgua() {
  int suma = 0;
  int lecturas = 10;
  
  for (int i = 0; i < lecturas; i++) {
    suma += analogRead(PIN_NIVEL_AGUA);
    delay(10);
  }
  
  int valorADC = suma / lecturas;
  float porcentaje = map(valorADC, 0, 4095, 0, 100);
  return constrain(porcentaje, 0, 100);
}

void loop() {
  // 1. LEER SENSORES (con valores por defecto = 0)
  float temperature = 0;
  float humidity = 0;
  float water_level = 0;
  float pressure = 1013.25;  // Presión fija simulada
  
  // Leer DHT22 - si falla, deja los valores en 0
  float tempRead = dht.readTemperature();
  float humRead = dht.readHumidity();
  
  if (!isnan(tempRead) && !isnan(humRead)) {
    temperature = tempRead;
    humidity = humRead;
  } else {
    Serial.println("⚠️ DHT22 falló - Enviando 0 en Temp y Hum");
  }
  
  // Leer sensor de agua - si da error, deja en 0
  water_level = leerNivelAgua();
  // Si el valor es inválido (nan), forzar a 0
  if (isnan(water_level)) {
    water_level = 0;
    Serial.println("⚠️ Sensor de agua falló - Enviando 0");
  }
  
  // 2. CREAR JSON 
  StaticJsonDocument<256> doc;
  doc["node_id"] = NODE_ID;
  doc["timestamp"] = millis();
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["pressure"] = pressure;
  doc["water_level"] = water_level;
  doc["role"] = "esclavo";
  
  char jsonBuffer[256];
  serializeJson(doc, jsonBuffer);
  
  // 3. ENVIAR POR UDP 
  udp.beginPacket(servidorIP, puertoUDP);
  udp.print(jsonBuffer);  
  udp.endPacket();
  
  Serial.print("Enviado: ");
  Serial.println(jsonBuffer);
  
  // 4. ESPERAR 5 SEGUNDOS
  delay(INTERVALO);
}