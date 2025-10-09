# GTERI — Expand Fixed Report Information (GV350CEU)

**Comando:** `+RESP:GTERI` / `+BUFF:GTERI`  
**Modelo:** GV350CEU  
**Referencia:** Sección 4.2.3 *ERI (Expand Fixed Report Information)* del documento **GV350CEU_GTERI.pdf**  

---

## Descripción general

El mensaje **GTERI** (Expand Fixed Report Information) amplía la información de posición del reporte **GTFRI**, permitiendo incluir campos opcionales adicionales definidos por el **ERI Mask** y el **Position Append Mask**.

Este mensaje se transmite como respuesta a eventos de reporte periódico, de movimiento, encendido, apagado u otros, y puede reemplazar completamente el formato **GTFRI** cuando la función ERI está habilitada.

---

## Formato general

+RESP:GTERI,<ProtocolVersion>,<IMEI>,<DeviceName>,<ERIMask>,<ExtPower>,<ReportType>,<Number>,<GNSSAcc>,<Speed>,<Azimuth>,<Altitude>,<Longitude>,<Latitude>,<GNSS_UTC>,<MCC>,<MNC>,<LAC>,<CellID>,<PosAppendMask>,<Satellites>,<GNSS_TriggerType>,<GNSS_JammingState>,<Mileage>,<HourMeter>,<AnalogIN1>,<AnalogIN2>,<AnalogIN3>,<BackupBattery>,<DeviceStatus>,<UARTDeviceType>,<DigitalFuelSensorData>,<OneWireData>,<CANData>,<FuelSensorData>,<RF433Data>,<BLEData>,<RATBand>,<SendTime>,<Count>,$


---

## Campos principales

| Campo | Tipo | Longitud / Rango | Descripción |
|:------|:-----|:-----------------|:-------------|
| **ProtocolVersion** | HEX(6) | `000000–FFFFFF` | Versión completa del protocolo. |
| **IMEI** | Numérico(15) | 15 dígitos | Identificador único del dispositivo. |
| **DeviceName** | Texto | hasta 20 caracteres | Nombre del modelo del dispositivo. |
| **ERIMask** | HEX(8) | 8 dígitos | Controla qué bloques opcionales se incluyen. |
| **ExtPower** | Int | 0–32000 mV | Voltaje externo (mV). |
| **ReportType** | Cadena | formato X(1–5)Y(0–6) | Tipo de reporte. |
| **Number** | Int | 1–15 | Número de evento. |
| **GNSSAcc** | Int | 0–50 | Precisión GNSS (metros). |
| **Speed** | Float | 0.0–999.9 km/h | Velocidad actual. |
| **Azimuth** | Int | 0–359° | Dirección del movimiento. |
| **Altitude** | Float | (-)xxxxx.x | Altitud sobre el nivel del mar (m). |
| **Longitude** | Float | (-)xxx.xxxxxx | Longitud en grados decimales. |
| **Latitude** | Float | (-)xx.xxxxxx | Latitud en grados decimales. |
| **GNSS_UTC** | FechaHora | `YYYYMMDDHHMMSS` | Fecha y hora GNSS (UTC). |
| **MCC** | Numérico(4) | Ej: `0460` | Mobile Country Code. |
| **MNC** | Numérico(4) | Ej: `0000` | Mobile Network Code. |
| **LAC** | HEX(4) | Ej: `550B` | Local Area Code. |
| **CellID** | HEX(4/8) | Ej: `085BE2AA` | Identificador de celda. |
| **PosAppendMask** | HEX(2) | Ej: `01` | Controla campos opcionales posteriores. |
| **Satellites** | Int | 0–72 | Número de satélites en uso *(opcional, bit0=1)*. |
| **GNSS_JammingState** | Enum | 0–3 | Estado del receptor GNSS *(opcional, bit4=1)*. |
| **Mileage** | Float | 0.0–4,294,967 km | Odómetro acumulado. |
| **HourMeter** | HH:MM:SS | 0000000:00:00–1193000:00:00 | Horómetro. |
| **AnalogIN1–3** | String | mV o F(0–100) | Valores analógicos. |
| **BackupBattery** | % | 0–100 | Nivel batería interna. |
| **DeviceStatus** | HEX(6–10) | Ej: `210100` | Estado digital general. |
| **UARTDeviceType** | Enum | 0,1,7 | Tipo de accesorio conectado por UART. |
| **DigitalFuelSensorData** | String | variable | Datos crudos del sensor digital de combustible *(ERI bit0)*. |

---

## Campos opcionales

### 1-Wire Data

Presente si hay sensores conectados y/o **ERI Mask bit1=1**.

| Campo | Tipo | Descripción |
|:------|:-----|:-------------|
| **OneWireDeviceNumber** | Int(0–19) | Número de sensor. |
| **OneWireDeviceID** | HEX(16) | ID único. |
| **OneWireDeviceType** | Int(1) | 1 = Sensor de temperatura. |
| **OneWireDeviceData** | HEX | Temperatura en complemento a dos. |

> Temperatura real = valor decimal × 0.0625 °C

---

### CAN Data

Presente si **ERI Mask bit2=1**.

| Campo | Tipo | Descripción |
|:------|:-----|:-------------|
| **CANData** | String | Datos crudos leídos desde el bus CAN. |

---

### Fuel Sensor Data

Presente según **ERI Mask** y tipo de sensor.

| Campo | Tipo | Descripción |
|:------|:-----|:-------------|
| **SensorNumber** | Int(0–100) | Número del sensor. |
| **SensorType** | Enum | 0–6, 20–22 | Tipo de sensor. |
| **Percentage** | Float(%) | Nivel de combustible. |
| **VolumeLiters** | Float | Volumen estimado. |
| **FuelTemperature** | °C | Si bit10=1 y tipo 2/6 (DUT-E o DUT-E SUM). |

---

### RF433 Accessory Data

Presente si hay accesorios RF433 (ej. WTS100, WTH100).

| Campo | Tipo | Descripción |
|:------|:-----|:-------------|
| **AccessoryNumber** | Int(0–10) | Identificador. |
| **AccessorySerial** | HEX(5) | Serial RF433. |
| **AccessoryType** | Enum | 1: WTS100, 2: WTH100. |
| **Temperature** | °C | -20 a 60 °C |
| **Humidity** | % | 0–100 % (solo WTH100). |

---

### Bluetooth Accessory Data (BLE)

Presente si hay accesorios BLE o **ERI Mask** lo habilita.

Incluye sensores BLE como WTS100-B, BLE-Relay, BLE-TPMS, BLE-Magnet, etc.

| Campo | Tipo | Descripción |
|:------|:-----|:-------------|
| **AccessoryType** | Int | Tipo de accesorio BLE. |
| **AccessoryModel** | Int | Modelo. |
| **AccessoryName** | Texto | Nombre del accesorio *(bit0)*. |
| **AccessoryMAC** | HEX(12) | Dirección MAC *(bit1)*. |
| **AccessoryStatus** | Int | Estado *(bit2)*. |
| **AccessoryBattery_mV** | Int | Voltaje batería *(bit3)*. |
| **AccessoryTemp_C** | Int | Temperatura *(bit4)*. |
| **AccessoryHumidity_%** | Int | Humedad *(bit5)*. |
| **AccessoryIOStatus** | HEX(2) | Datos de E/S *(bit7)*. |
| **AccessoryEvent/Mode** | Int | Evento BLE *(bit8–bit10)*. |
| **EnhancedTemperature** | Float | Temperatura extendida *(bit11)*. |
| **MagnetID / State / Counter** | HEX / Int | Información de magneto *(bit12)*. |
| **RelayState** | 0/1 | Estado del relay *(bit14)*. |
| **TriAxisAccel** | HEX(12) | Datos de aceleración *(bit16)*. |

#### BLE Accessory Append Mask
- Bits 0–15: campos base
- Bit15: habilita expansión
- Bits 16–31: campos extendidos

Ejemplo: `0x881F0007` → `(15..0)=0x881F`, `(31..16)=0x0007`

---

### RAT / Band

Presente si disponible en firmware reciente.

| Campo | Tipo | Descripción |
|:------|:-----|:-------------|
| **RAT** | Enum | 0: No Service, 1: EGPRS, 4: LTE Cat1 |
| **Band** | String | Banda celular activa (LTE/GSM). |

---

## Máscaras

### ERI Mask

Controla la inclusión de secciones opcionales:

| Bit | Significado |
|:----|:-------------|
| **0** | Digital Fuel Sensor Data |
| **1** | One-Wire Data (datos visibles) |
| **2** | CAN Data |
| **10** | Fuel Temperature (para tipo 2 o 6) |

---

### Position Append Mask

Define la presencia de campos después del `<CellID>`:

| Bit | Campo opcional |
|:----|:----------------|
| **0** | Satellites in Use |
| **4** | GNSS Jamming State |

---

## Ejemplo de trama

+RESP:GTERI,740904,862524060204589,GV350CEU,00000100,,10,1,1,0.0,355,97.7,117.129252,31.839388,20240415054037,0460,0000,550B,085BE2AA,01,11,3.6,,,,,0,210100,0,1,00,11,0,0000001E,100F,,D325C2B2A2F8,1,2967,0,15,0,20240415154438,405C$


### Decodificación parcial

| Campo | Valor | Descripción |
|:------|:------|:-------------|
| ProtocolVersion | 740904 | Versión del protocolo |
| IMEI | 862524060204589 | Identificador único |
| DeviceName | GV350CEU | Modelo del dispositivo |
| ERIMask | 00000100 | Indica inclusión de bloques ERI |
| MCC/MNC | 0460 / 0000 | China Unicom |
| LAC / CellID | 550B / 085BE2AA | Identificadores de celda |
| PosAppendMask | 01 | Incluye satélites |
| Mileage | 3.6 km | Odómetro |
| DeviceStatus | 210100 | Estado digital |
| SendTime | 20240415154438 | Fecha de envío (UTC) |
| Count | 405C | Contador de mensaje |

---

## Observaciones

- El mensaje **GTERI** reemplaza a **GTFRI** cuando la opción *ERI Enable* está activa.  
- Campos adicionales aparecen solo si los bits correspondientes en **ERI Mask** o **Position Append Mask** están habilitados.  
- La decodificación correcta depende de interpretar la longitud y presencia condicional de los bloques opcionales.  
- En firmware recientes, se puede incluir información adicional como **RAT**, **Band**, **BLE Expanded Fields** y **DOPs (HDOP, PDOP, VDOP)** cuando están configurados.  

---

**Última actualización:** Octubre 2025  
**Fuente:** `GV350CEU_GTERI.pdf – Sección 4.2.3 ERI`
