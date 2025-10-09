# GTERI (Expand Fixed Report Information) — GV350CEU

**Mensajes cubiertos:** `+RESP:GTERI` y `+BUFF:GTERI`  
**Formato base:** ASCII, campos separados por `,`, terminador `$`  
**Estructura general:** `Head → Body → Tail`  
**Compatibilidad:** Alineado con `spec/gv350ceu/gteri.yml` y estilo de `gtinf.yml`

---

## 1) Estructura del mensaje
+RESP/+BUFF:GTERI,
<full_protocol_version>,
<imei>,
<device_name>,
<eri_mask>,
<external_power_mv>,
<report_type>,
<number>,
<gnss_accuracy>,
<speed_kmh>,
<azimuth>,
<lon>,
<lat>,
<gnss_utc_time>,
<mcc>,
<mnc>,
<lac_hex>,
<cell_id_hex>,
<position_append_mask>,
[anexos controlados por position_append_mask],
<mileage_km>,
<hour_meter>,
<analog_in_1>,
<analog_in_2>,
<analog_in_3>,
<backup_batt_percent>,
<device_status>,
<uart_device_type>,
[ERl Mask blocks (1-Wire, CAN, Fuel, RF433, BLE, RAT/Band, etc.)...],
<send_time>,
<count_hex>$


> Notas:
> - Los campos “anexos” se habilitan por **máscaras** que se indican en el propio mensaje.
> - La lista de anexos y su orden debe seguir exactamente la configuración de las máscaras.

---

## 2) Campos por sección

### Head

| Campo | Tipo | Formato/Rango | Descripción |
|---|---|---|---|
| `header` | string | `+RESP:GT` / `+BUFF:GT` | Tipo de mensaje y origen. |
| `message` | string | `ERI` | Nombre del mensaje. |
| `full_protocol_version` | hex | 6 o 7 chars | Versión de protocolo (p. ej. `740904`). |
| `imei` | string | 15 dígitos | Identificador único del equipo. |
| `device_name` | string | ≤20 chars o vacío | Nombre del dispositivo. |

### Body (básicos siempre presentes)

| Campo | Tipo | Formato/Rango | Descripción |
|---|---|---|---|
| `eri_mask` | hex | 8 chars | Bitmask que habilita bloques ERI opcionales. |
| `external_power_mv` | int | 0–32000 | Voltaje externo (mV). |
| `report_type` | string | 2 hex chars | Tipo de evento (X(1-5)Y(0-6)). |
| `number` | int | 1–15 | Número interno de reporte. |
| `gnss_accuracy` | int | 0–50 | Precisión GNSS (m). |
| `speed_kmh` | float | 0.0–999.9 | Velocidad en km/h. |
| `azimuth` | int | 0–359 | Dirección del movimiento. |
| `altitude_m` | float | opcional | Altitud en metros. |
| `lon` | float | -180..180 | Longitud. |
| `lat` | float | -90..90 | Latitud. |
| `gnss_utc_time` | datetime | `YYYYMMDDHHMMSS` | Hora UTC GNSS. |
| `mcc` | string | `0xxx` | Código de país. |
| `mnc` | string | `0xxx` | Código de red. |
| `lac_hex` | hex | 4 chars | Local Area Code. |
| `cell_id_hex` | hex | 4 u 8 chars | Cell ID. |
| `position_append_mask` | hex | 2 chars | Controla anexos GNSS y celda. |

---

## 3) Máscaras y bloques opcionales

### 3.1 Position Append Mask (2 hex chars)

Controla campos GNSS/celda después de `cell_id_hex`.

| Bit | Campo | Tipo | Descripción |
|---|---|---|---|
| 0 | `satellites_in_use` | int | Número de satélites utilizados. |
| 1 | `gnss_trigger_type` | int | Tipo de trigger GNSS. |
| 4 | `gnss_jamming_state` | int | Estado de interferencia GNSS (0=Unknown, 1=OK, 2=Warning, 3=Critical). |

> Si el bit no está activo, el campo **no aparece** en la trama.

---

### 3.2 ERI Mask (8 hex chars)

Activa bloques completos opcionales del ERI.  
Cada bit controla un grupo de datos. Solo se incluyen si el bit está activo.

| Bit | Bloque | Campos incluidos | Descripción |
|---|---|---|---|
| 0 | Digital Fuel Sensor | `digital_fuel_sensor_raw` | Valor o trama cruda del sensor de combustible digital. |
| 1 | 1-Wire | `onewire_device_count`, `onewire_device_id`, `onewire_device_type`, `onewire_device_data` | Sensores de temperatura 1-Wire. |
| 2 | CAN | `can_data` | Datos CAN crudos o resumidos. |
| 10 | Fuel Sensor | `fuel_sensor_count`, `fuel_sensor_type`, `fuel_percentage`, `fuel_volume_l`, `fuel_temperature_c` | Sensores de combustible analógicos o digitales. |
| 11 | RF433 | `rf433_count`, `rf433_serial`, `rf433_type`, `rf433_temperature_c`, `rf433_humidity_pct` | Sensores inalámbricos 433 MHz. |
| 12 | BLE Accessories | Campos según BLE Append Mask | Sensores Bluetooth (WTS300, WTD200, TPMS, etc.). |
| 13 | RAT/Band | `rat`, `band` | Tipo de red y banda LTE/2G/3G. |

> Los bits no listados se reservan para futuras expansiones o funciones específicas.

---

### 3.3 BLE Append Mask (0–31 bits)

Controla los campos de cada accesorio BLE.

#### Base (bits 0–15)

| Bit | Campo | Descripción |
|---|---|---|
| 0 | `ble_name` | Nombre del accesorio BLE. |
| 1 | `ble_mac` | Dirección MAC BLE. |
| 2 | `ble_status` | Estado (0=off, 1=on). |
| 3 | `ble_batt_mv` | Voltaje batería BLE. |
| 4 | `ble_temp_c` | Temperatura (°C). |
| 5 | `ble_humidity_pct` | Humedad (%). |
| 6 | — | Reservado. |
| 7 | `ble_io_output`, `ble_io_input`, `ble_io_analog_mv` | Entradas/Salidas digitales y analógicas. |
| 8 | `ble_mode`, `ble_event` | Modo de operación y tipo de evento. |
| 9 | `ble_tire_pressure_kpa` | Presión neumático (TPMS). |
| 10 | `ble_timestamp` | Timestamp del accesorio. |
| 11 | `ble_temp_enh_c` | Temperatura mejorada. |
| 12 | `ble_magnet_id`, `ble_mag_event_counter`, `ble_magnet_state` | Datos de sensores magnéticos. |
| 13 | `ble_batt_pct` | Porcentaje batería BLE. |
| 14 | `ble_relay_state` | Estado del relé BLE. |
| 15 | **Expansión activa (habilita bits 16–31)** | — |

#### Extensión (bits 16–31)

| Bit | Campo | Descripción |
|---|---|---|
| 16 | `ble_triax_accel_hex` | Aceleración triaxial (X,Y,Z). |
| 17 | `ble_angles_hex` | Ángulos Pitch/Roll/Yaw. |
| 18 | `ble_sensor_event_mask`, `ble_tilt_event_hex`, `ble_motion_event_hex`, `ble_crash_event_hex`, `ble_falling_event_hex` | Eventos de movimiento o inclinación. |
| 19 | `ble_move_event_hex` | Evento de movimiento. |
| 20–31 | — | Reservado para futuras extensiones. |

---

## 4) Body (otros campos comunes)

| Campo | Tipo | Descripción |
|---|---|---|
| `mileage_km` | float | Odómetro (km). |
| `hour_meter` | string | Horas de motor `ddddddd:hh:mm`. |
| `analog_in_1` | string | Entrada analógica 1 (mV o F%). |
| `analog_in_2` | string | Entrada analógica 2 (mV o F%). |
| `analog_in_3` | string | Entrada analógica 3 (mV o F%). |
| `backup_batt_percent` | int | % batería interna. |
| `device_status` | hex | Estado general del equipo (6 o 10 chars). |
| `uart_device_type` | int | Tipo de dispositivo conectado por UART. |

---

## 5) Tail

| Campo | Tipo | Descripción |
|---|---|---|
| `send_time` | datetime | Hora de envío (`YYYYMMDDHHMMSS`). |
| `count_hex` | hex | Contador incremental del mensaje. |

---

## 6) Reglas de validación recomendadas

1. `header` debe ser `+RESP:GT` o `+BUFF:GT`.  
2. `message` debe ser exactamente `ERI`.  
3. La línea **debe terminar** con `$`.  
4. `lat` y `lon` deben estar dentro de los rangos válidos.  
5. Si una máscara no activa un bloque, esos campos **no deben parsearse**.  
6. El orden de los campos sigue el orden natural del protocolo y las máscaras.

---

## 7) Ejemplos

### Ejemplo 1 — con anexos

+RESP:GTERI,740904,862524060204589,GV350CEU,00000100,,10,1,1,0.0,355,97.7,117.129252,31.839388,20240415054037,0460,0000,550B,085BE2AA,01,11,3.6,,,,,0,210100,0,1,00,11,0,0000001E,100F,,D325C2B2A2F8,1,2967,0,15,0,20240415154438,405C$


**Campos clave detectables:**
- `imei=862524060204589`
- `eri_mask=00000100`
- `lon=117.129252`, `lat=31.839388`
- `position_append_mask=01`
- `send_time=20240415154438`

### Ejemplo 2 — sin anexos
+RESP:GTERI,040A00,862524060204589,,00000000,12000,10,1,5,12.3,180,-70.650000,-33.450000,20250101080000,0732,0002,1A2B,00,1234.5,0000001:00:15,1200,2300,1500,90,210100,0,20250101080100,00AF$


---

## 8) Notas de implementación

- El parser debe respetar el orden y evaluar las máscaras bit a bit.  
- Las listas (1-Wire, RF433, BLE) comienzan con un `count` seguido de grupos repetidos.  
- `hour_meter` tiene formato fijo `ddddddd:hh:mm`.  
- Si `ble_append_mask` ≥ `0x8000`, activar extensión bits 16–31.  
- `device_status` puede tener longitud 6 o 10 hex.  
- `rat` y `band` pueden omitirse si el bit ERI correspondiente no está activo.  

---

## 9) Mapeo sugerido a base de datos

| Campo | Tipo SQL | Comentario |
|---|---|---|
| imei | TEXT | Índice principal |
| gnss_utc_time | TEXT | Timestamp GNSS |
| send_time | TEXT | Timestamp de envío |
| lat | REAL | Latitud |
| lon | REAL | Longitud |
| eri_mask | TEXT | Hex 8 chars |
| position_append_mask | TEXT | Hex 2 chars |
| device_status | TEXT | Estado del equipo |
| report_type | TEXT | Tipo de reporte |
| rat | INTEGER | Tecnología de red |
| band | TEXT | Banda de transmisión |

---

## 10) Referencias

- `spec/gv350ceu/gteri.yml` — definición técnica estructurada del mensaje  
- `GV350CEU_GTERI.pdf` — documento oficial Queclink (Sección 4.2.3 ERI)  
- `spec/gv350ceu/gtinf.yml` — referencia de formato y convenciones de documentación  
- Parser: `queclink/messages/gteri.py`  
- Ingestor: `ingestor_sqlite.py`  

---

## 11) Resumen

El mensaje **GTERI (Expand Fixed Report Information)** permite transmitir información extendida de posición y sensores opcionales del GV350CEU.  
A diferencia de **GTINF**, su estructura se adapta dinámicamente a las **máscaras de datos (ERI Mask y Position Append Mask)**, lo que permite al dispositivo enviar datos adicionales solo cuando están habilitados, optimizando el uso del ancho de banda.

Head → Body (datos fijos + opcionales) → Tail
Máscaras: ERI Mask, Position Append Mask y BLE Append Mask

---
