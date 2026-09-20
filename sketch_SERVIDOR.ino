#include <WiFi.h>
#include <WiFiAP.h>
#include <WiFiUDP.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <DHT.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>

// CONFIGURACION DE RED (Access Point)
const char* ssidAP = "Apiario";
const char* passwordAP = "12345678";
const int puertoUDP = 8888;
WiFiUDP udp;
WebServer server(80);  // Servidor web en puerto 80

// CONFIGURACION DE PINES
#define DHTPIN 4
#define DHTTYPE DHT11
#define PIN_NIVEL_AGUA 34

// PRESION BAROMETRICA 
const float PRESION_FIJA = 1013.25;

// INICIALIZACION DE SENSORES Y LCD
DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// CONFIGURACION DEL NODO SERVIDOR
const int NODE_ID_SERVIDOR = 0;
const unsigned long INTERVALO = 5000;

// Variables para datos del esclavo
float nodoTemp = 0, nodoHum = 0, nodoPres = 0, nodoAgua = 0;
unsigned long ultimoRecibidoNodo = 0;
bool hayDatosNodo = false;

// Control de rotación LCD
unsigned long ultimoCambioLCD = 0;
bool mostrarServidor = true;

// Variables para sensores propios
float tempServidor = 0, humServidor = 0, aguaServidor = 0;
unsigned long ultimoLectura = 0;

// PAGINA HTML DEL DASHBOARD  
const char* paginaHTML = R"rawliteral(
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoreo Apiario IoT</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
            color: #e8eaed;
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(26, 35, 50, 0.8);
            border-radius: 15px;
            border: 1px solid #2d3e50;
        }
        
        .header h1 {
            color: #f4b400;
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #9aa0a6;
            font-size: 1.1em;
        }
        
        .nodo-container {
            margin-bottom: 30px;
        }
        
        .nodo-title {
            color: #f4b400;
            font-size: 1.5em;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #f4b400;
        }
        
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(26, 35, 50, 0.9);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid #2d3e50;
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            border-color: #f4b400;
        }
        
        .card-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .card-icon {
            font-size: 2em;
            margin-right: 10px;
        }
        
        .card-title {
            color: #9aa0a6;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .card-unit {
            color: #9aa0a6;
            font-size: 1em;
        }
        
        .card-status {
            margin-top: 10px;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            display: inline-block;
        }
        
        .status-normal {
            background: #34a853;
            color: white;
        }
        
        .status-warning {
            background: #fbbc04;
            color: black;
        }
        
        .status-alert {
            background: #ea4335;
            color: white;
        }
        
        .temp-color { color: #ea4335; }
        .hum-color { color: #4285f4; }
        .pres-color { color: #34a853; }
        .agua-color { color: #fbbc04; }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #9aa0a6;
            font-size: 0.9em;
        }
        
        .last-update {
            color: #f4b400;
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.5em;
            }
            
            .card-value {
                font-size: 2em;
            }
            
            .cards-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 Sistema de Monitoreo Apiario IoT</h1>
        <p>Universidad Bolivariana de Venezuela - PFG Informática</p>
    </div>
    
    <div id="nodo-servidor" class="nodo-container">
        <h2 class="nodo-title">📡 Nodo Servidor (Local)</h2>
        <div class="cards-grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🌡️</span>
                    <span class="card-title">Temperatura</span>
                </div>
                <div class="card-value temp-color" id="serv-temp">--</div>
                <div class="card-unit">°C</div>
                <div class="card-status status-normal" id="serv-temp-status">Normal</div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">💧</span>
                    <span class="card-title">Humedad</span>
                </div>
                <div class="card-value hum-color" id="serv-hum">--</div>
                <div class="card-unit">%</div>
                <div class="card-status status-normal" id="serv-hum-status">Normal</div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-icon"></span>
                    <span class="card-title">Presión</span>
                </div>
                <div class="card-value pres-color" id="serv-pres">--</div>
                <div class="card-unit">hPa</div>
                <div class="card-status status-normal" id="serv-pres-status">Normal</div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">💦</span>
                    <span class="card-title">Nivel Agua</span>
                </div>
                <div class="card-value agua-color" id="serv-agua">--</div>
                <div class="card-unit">%</div>
                <div class="card-status status-normal" id="serv-agua-status">Normal</div>
            </div>
        </div>
    </div>
    
    <div id="nodo-esclavo" class="nodo-container">
        <h2 class="nodo-title">📡 Nodo Esclavo (Remoto)</h2>
        <div class="cards-grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">️</span>
                    <span class="card-title">Temperatura</span>
                </div>
                <div class="card-value temp-color" id="esc-temp">--</div>
                <div class="card-unit">°C</div>
                <div class="card-status status-normal" id="esc-temp-status">Normal</div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">💧</span>
                    <span class="card-title">Humedad</span>
                </div>
                <div class="card-value hum-color" id="esc-hum">--</div>
                <div class="card-unit">%</div>
                <div class="card-status status-normal" id="esc-hum-status">Normal</div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-icon"></span>
                    <span class="card-title">Presión</span>
                </div>
                <div class="card-value pres-color" id="esc-pres">--</div>
                <div class="card-unit">hPa</div>
                <div class="card-status status-normal" id="esc-pres-status">Normal</div>
            </div>
            
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">💦</span>
                    <span class="card-title">Nivel Agua</span>
                </div>
                <div class="card-value agua-color" id="esc-agua">--</div>
                <div class="card-unit">%</div>
                <div class="card-status status-normal" id="esc-agua-status">Normal</div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Última actualización: <span class="last-update" id="last-update">--:--:--</span></p>
        <p>Red: Apiario | Servidor: 192.168.4.1</p>
    </div>
    
    <script>
        // Rangos óptimos para abejas
        const rangos = {
            temp: { min: 33, max: 36 },
            hum: { min: 45, max: 65 },
            pres: { min: 1005, max: 1025 },
            agua: { min: 30, max: 90 }
        };
        
        function getStatus(valor, parametro) {
            const rango = rangos[parametro];
            if (valor < rango.min || valor > rango.max) {
                return { text: 'Alerta', class: 'status-alert' };
            } else if (valor < (rango.min + (rango.max - rango.min) * 0.2) || 
                       valor > (rango.max - (rango.max - rango.min) * 0.2)) {
                return { text: 'Precaución', class: 'status-warning' };
            } else {
                return { text: 'Normal', class: 'status-normal' };
            }
        }
        
        function actualizarDashboard(datos) {
            // Actualizar Nodo Servidor
            document.getElementById('serv-temp').textContent = datos.servidor.temperature.toFixed(1);
            document.getElementById('serv-hum').textContent = datos.servidor.humidity.toFixed(1);
            document.getElementById('serv-pres').textContent = datos.servidor.pressure.toFixed(1);
            document.getElementById('serv-agua').textContent = datos.servidor.water_level.toFixed(1);
            
            // Estados del servidor
            const servTempStatus = getStatus(datos.servidor.temperature, 'temp');
            document.getElementById('serv-temp-status').textContent = servTempStatus.text;
            document.getElementById('serv-temp-status').className = 'card-status ' + servTempStatus.class;
            
            const servHumStatus = getStatus(datos.servidor.humidity, 'hum');
            document.getElementById('serv-hum-status').textContent = servHumStatus.text;
            document.getElementById('serv-hum-status').className = 'card-status ' + servHumStatus.class;
            
            const servPresStatus = getStatus(datos.servidor.pressure, 'pres');
            document.getElementById('serv-pres-status').textContent = servPresStatus.text;
            document.getElementById('serv-pres-status').className = 'card-status ' + servPresStatus.class;
            
            const servAguaStatus = getStatus(datos.servidor.water_level, 'agua');
            document.getElementById('serv-agua-status').textContent = servAguaStatus.text;
            document.getElementById('serv-agua-status').className = 'card-status ' + servAguaStatus.class;
            
            // Actualizar Nodo Esclavo
            if (datos.esclavo && datos.esclavo.temperature > 0) {
                document.getElementById('esc-temp').textContent = datos.esclavo.temperature.toFixed(1);
                document.getElementById('esc-hum').textContent = datos.esclavo.humidity.toFixed(1);
                document.getElementById('esc-pres').textContent = datos.esclavo.pressure.toFixed(1);
                document.getElementById('esc-agua').textContent = datos.esclavo.water_level.toFixed(1);
                
                // Estados del esclavo
                const escTempStatus = getStatus(datos.esclavo.temperature, 'temp');
                document.getElementById('esc-temp-status').textContent = escTempStatus.text;
                document.getElementById('esc-temp-status').className = 'card-status ' + escTempStatus.class;
                
                const escHumStatus = getStatus(datos.esclavo.humidity, 'hum');
                document.getElementById('esc-hum-status').textContent = escHumStatus.text;
                document.getElementById('esc-hum-status').className = 'card-status ' + escHumStatus.class;
                
                const escPresStatus = getStatus(datos.esclavo.pressure, 'pres');
                document.getElementById('esc-pres-status').textContent = escPresStatus.text;
                document.getElementById('esc-pres-status').className = 'card-status ' + escPresStatus.class;
                
                const escAguaStatus = getStatus(datos.esclavo.water_level, 'agua');
                document.getElementById('esc-agua-status').textContent = escAguaStatus.text;
                document.getElementById('esc-agua-status').className = 'card-status ' + escAguaStatus.class;
            }
            
            // Actualizar hora
            const ahora = new Date();
            document.getElementById('last-update').textContent = ahora.toLocaleTimeString();
        }
        
        async function cargarDatos() {
            try {
                const response = await fetch('/datos');
                const datos = await response.json();
                actualizarDashboard(datos);
            } catch (error) {
                console.error('Error al cargar datos:', error);
            }
        }
        
        // Cargar datos cada 2 segundos
        setInterval(cargarDatos, 2000);
        cargarDatos(); // Carga inicial
    </script>
</body>
</html>
)rawliteral";

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("Iniciando ESP32 SERVIDOR con Dashboard Web...");
  
  // Inicializar I2C y LCD
  Wire.begin();
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Iniciando...");
  lcd.setCursor(0, 1);
  lcd.print("Servidor AP+Web");
  delay(2000);
  
  // Inicializar sensores
  dht.begin();
  analogReadResolution(12);
  
  // CREAR RED WIFI (ACCESS POINT)
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Creando red...");
  lcd.setCursor(0, 1);
  lcd.print(ssidAP);
  
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssidAP, passwordAP);
  
  IPAddress IP = WiFi.softAPIP();
  Serial.print("Red creada! IP del servidor: ");
  Serial.println(IP);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Red:");
  lcd.print(ssidAP);
  lcd.setCursor(0, 1);
  lcd.print("IP:");
  lcd.print(IP);
  delay(2000);
  
  // CONFIGURAR SERVIDOR WEB
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", paginaHTML);
  });
  
  server.on("/datos", HTTP_GET, []() {
    // Crear JSON con datos de ambos nodos
    StaticJsonDocument<512> doc;
    
    JsonObject servidor = doc.createNestedObject("servidor");
    servidor["temperature"] = tempServidor;
    servidor["humidity"] = humServidor;
    servidor["pressure"] = PRESION_FIJA;
    servidor["water_level"] = aguaServidor;
    
    if (hayDatosNodo) {
      JsonObject esclavo = doc.createNestedObject("esclavo");
      esclavo["temperature"] = nodoTemp;
      esclavo["humidity"] = nodoHum;
      esclavo["pressure"] = nodoPres;
      esclavo["water_level"] = nodoAgua;
    } else {
      JsonObject esclavo = doc.createNestedObject("esclavo");
      esclavo["temperature"] = 0;
      esclavo["humidity"] = 0;
      esclavo["pressure"] = 0;
      esclavo["water_level"] = 0;
    }
    
    char jsonBuffer[512];
    serializeJson(doc, jsonBuffer);
    server.send(200, "application/json", jsonBuffer);
  });
  
  server.begin();
  Serial.println("Servidor web iniciado en http://192.168.4.1");
  
  // Iniciar UDP
  udp.begin(puertoUDP);
  Serial.print("Escuchando UDP puerto: ");
  Serial.println(puertoUDP);
  
  Serial.println("Servidor listo. Presion simulada: " + String(PRESION_FIJA) + " hPa");
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Web:192.168.4.1");
  lcd.setCursor(0, 1);
  lcd.print("Esperando...");
  delay(2000);
}

float leerNivelAgua() {
  int suma = 0;
  for (int i = 0; i < 10; i++) {
    suma += analogRead(PIN_NIVEL_AGUA);
    delay(10);
  }
  int valorADC = suma / 10;
  float porcentaje = map(valorADC, 0, 4095, 0, 100);
  return constrain(porcentaje, 0, 100);
}

void mostrarDatosServidorEnLCD(float temp, float hum, float pres, float agua) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("S T:");
  lcd.print(temp, 1);
  lcd.print((char)223);
  lcd.print(" H:");
  lcd.print(hum, 0);
  lcd.print("%");
  
  lcd.setCursor(0, 1);
  lcd.print("P:");
  lcd.print(pres, 0);
  lcd.print(" A:");
  lcd.print(agua, 0);
  lcd.print("%");
}

void mostrarDatosNodoEnLCD() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("N1 T:");
  lcd.print(nodoTemp, 1);
  lcd.print((char)223);
  lcd.print(" H:");
  lcd.print(nodoHum, 0);
  lcd.print("%");
  
  lcd.setCursor(0, 1);
  lcd.print("P:");
  lcd.print(nodoPres, 0);
  lcd.print(" A:");
  lcd.print(nodoAgua, 0);
  lcd.print("%");
}

void loop() {
  // 1. ATENDER PETICIONES WEB
  server.handleClient();
  
  unsigned long ahora = millis();
  
  // 2. LEER SENSORES PROPIOS (cada 5 segundos)
  if (ahora - ultimoLectura >= INTERVALO) {
    ultimoLectura = ahora;
    
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    float pressure = PRESION_FIJA;
    float water_level = leerNivelAgua();
    
    if (!isnan(temperature) && !isnan(humidity)) {
      tempServidor = temperature;
      humServidor = humidity;
      aguaServidor = water_level;
      
      // Crear JSON del servidor
      StaticJsonDocument<256> doc;
      doc["node_id"] = NODE_ID_SERVIDOR;
      doc["timestamp"] = millis();
      doc["temperature"] = temperature;
      doc["humidity"] = humidity;
      doc["pressure"] = pressure;
      doc["water_level"] = water_level;
      doc["role"] = "servidor";
      
      char jsonBuffer[256];
      serializeJson(doc, jsonBuffer);
      
      // Enviar por Serial a la laptop
      Serial.println(jsonBuffer);
      
      // Mostrar en LCD si es el turno del servidor
      if (mostrarServidor) {
        mostrarDatosServidorEnLCD(temperature, humidity, pressure, water_level);
      }
      
      Serial.print("Servidor -> ");
      Serial.println(jsonBuffer);
    } else {
      if (mostrarServidor) {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("ERROR DHT22!");
      }
      Serial.println("ERROR: Fallo al leer DHT22");
    }
  }
  
  // 3. RECIBIR DATOS DEL ESCLAVO (UDP)
  int packetSize = udp.parsePacket();
  
  if (packetSize) {
    char buffer[256];
    int len = udp.read(buffer, sizeof(buffer) - 1);
    buffer[len] = '\0';
    
    IPAddress remoteIP = udp.remoteIP();
    Serial.print("UDP de ");
    Serial.print(remoteIP);
    Serial.print(": ");
    Serial.println(buffer);
    
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, buffer);
    
    if (!error) {
      nodoTemp = doc["temperature"] | 0;
      nodoHum = doc["humidity"] | 0;
      nodoPres = doc["pressure"] | 0;
      nodoAgua = doc["water_level"] | 0;
      hayDatosNodo = true;
      ultimoRecibidoNodo = ahora;
      
      // Reenviar por Serial a la laptop
      Serial.println(buffer);
      
      // Mostrar en LCD si es el turno del nodo
      if (!mostrarServidor) {
        mostrarDatosNodoEnLCD();
      }
    }
  }
  
  // 4. ROTAR LCD CADA 3 SEGUNDOS
  if (ahora - ultimoCambioLCD >= 3000 && hayDatosNodo) {
    ultimoCambioLCD = ahora;
    mostrarServidor = !mostrarServidor;
    
    if (mostrarServidor) {
      mostrarDatosServidorEnLCD(tempServidor, humServidor, PRESION_FIJA, aguaServidor);
    } else {
      mostrarDatosNodoEnLCD();
    }
  }
  
  // 5. ALERTA SI ESCLAVO NO RESPONDE
  if (hayDatosNodo && (ahora - ultimoRecibidoNodo > 15000)) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("ESCLAVO OFFLINE");
    lcd.setCursor(0, 1);
    lcd.print(">15s sin datos");
    hayDatosNodo = false;
  }
  
  delay(100);
}