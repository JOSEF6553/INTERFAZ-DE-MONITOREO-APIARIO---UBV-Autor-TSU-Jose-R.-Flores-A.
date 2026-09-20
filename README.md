# 🐝 Sistema de Monitoreo Apiario IoT - UBV 2026

> Proyecto de grado para el PFG Informática para la Gestión Social  
> **Universidad Bolivariana de Venezuela (UBV)**  
> **Autor:** TSU Jose R. Flores A.

## 📋 Descripción
Sistema IoT distribuido para el monitoreo en tiempo real de colmenas de abejas (*Apis mellifera*). Utiliza una arquitectura de dos nodos ESP32 (Servidor y Cliente) que miden temperatura, humedad, presión atmosférica y nivel de lluvia, enviando los datos a un dashboard moderno en Python para su visualización, análisis y almacenamiento en base de datos.

## 🏗️ Arquitectura del Sistema
1. **Nodo Cliente (ESP32):** Ubicado en la colmena remota. Lee sensores y envía datos vía WiFi UDP.
2. **Nodo Servidor (ESP32):** Crea su propia red WiFi (Access Point), recibe los datos del cliente, lee sus propios sensores, muestra la información en una pantalla LCD I2C 2x16 y reenvía todo vía Serial USB a la laptop.
3. **Dashboard (Python):** Aplicación de escritorio con interfaz moderna (Dark Theme) que grafica los datos en tiempo real, muestra alertas biológicas y guarda el historial en PostgreSQL.

## 🛠️ Tecnologías Utilizadas

### Hardware
- 2x Módulos ESP32 WROOM
- Sensores DHT22 (Temperatura y Humedad)
- Sensor de Lluvia/Agua Analógico
- Pantalla LCD I2C 2x16
- Cajas estancas IP65/IP68

### Software & Firmware
- **Firmware:** C++ (Arduino IDE), WiFi UDP, ArduinoJson
- **Dashboard:** Python 3, Tkinter, Matplotlib, PySerial
- **Base de Datos:** PostgreSQL
- **Control de Versiones:** Git & GitHub

## ⚙️ Requisitos Previos

### Hardware
- Conexiones: DHT22 en GPIO 4, Sensor de Agua en GPIO 34 (VP), LCD I2C en GPIO 21 (SDA) y 22 (SCL).

### Software (Dashboard Python)
Instala las dependencias necesarias ejecutando en tu terminal:
```bash
pip install -r dashboard/requirements.txt

<img width="1365" height="715" alt="Captura de pantalla 2026-09-20 174250" src="https://github.com/user-attachments/assets/a4721b27-1235-497f-9d8c-707056d8a67c" />
<img width="1365" height="715" alt="Captura de pantalla 2026-09-20 174250" src="https://github.com/user-attachments/assets/f054fec8-f2d4-433b-bac3-b736e3f74198" />
