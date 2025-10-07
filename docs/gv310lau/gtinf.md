# +RESP/+BUFF:GTINF — GV310LAU

> **Fuente:** "GV310LAU @Track Air Interface Protocol v0705"  
> Sección 4.2.1 — Información del Dispositivo (GTINF)

---

## 1️⃣ Descripción general

El mensaje **GTINF** entrega información del dispositivo, firmware, hardware, IMSI, ICCID, operador y otros parámetros de red.  
Puede ser enviado como:
- `+RESP:GTINF` → respuesta normal.  
- `+BUFF:GTINF` → mensaje almacenado en buffer.

---

## 2️⃣ Estructura general

+RESP:GTINF,<ProtocolVersion>,<IMEI>,<DeviceName>,<DeviceType>,
<HDVersion>,<FWVersion>,<IMEI>,<SIM1_IMSI>,<SIM2_IMSI>,
<ICCID>,<Network>,<Band>,<OperatorName>,<CSQ>,<ServiceStatus>,
<Roaming>,<ReportInterval>,<SendTime>,<Count>$


> Los campos pueden variar ligeramente según la versión de firmware.

---

## 3️⃣ Campos principales

| Campo | Descripción | Ejemplo | Tipo |
|:--|:--|:--|:--|
| **Header** | `+RESP:GTINF` o `+BUFF:GTINF` | `+RESP:GTINF` | string |
| **ProtocolVersion** | Versión del protocolo (6 dígitos HEX) | `050602` | hex |
| **IMEI** | Identificador único del dispositivo | `868589060792986` | string |
| **DeviceName** | Modelo de hardware | `GV310LAU` | string |
| **DeviceType** | Código interno de tipo de dispositivo | `06` | int |
| **HDVersion** | Versión de hardware | `A02` | string |
| **FWVersion** | Versión de firmware | `A08V21` | string |
| **SIM1_IMSI** | IMSI de la SIM 1 | `724999123456789` | string |
| **SIM2_IMSI** | IMSI de la SIM 2 (si aplica) | — | string |
| **ICCID** | ICCID de la SIM activa | `8935711001088072605` | string |
| **Network** | Tipo de red (LTE, WCDMA, GSM, etc.) | `LTE` | string |
| **Band** | Banda o frecuencia de red | `B7` | string |
| **OperatorName** | Nombre del operador de red | `ENTEL` | string |
| **CSQ** | Nivel de señal (0–31, 99=desconocido) | `23` | int |
| **ServiceStatus** | Estado de servicio (0=sin red, 1=registrado) | `1` | int |
| **Roaming** | 1 si está en roaming | `0` | int |
| **ReportInterval** | Intervalo de envío en segundos | `60` | int |
| **SendTime** | Fecha/hora de envío UTC | `20250921223813` | datetime |
| **Count** | Número secuencial del paquete (HEX) | `3C24` | hex |

---

## 4️⃣ Ejemplo real (tomado del protocolo)

+RESP:GTINF,050602,868589060792986,GV310LAU,06,A02,A08V21,868589060792986,724999123456789,,8935711001088072605,LTE,B7,ENTEL,23,1,0,60,20250921223813,3C24$


---

## 5️⃣ Notas y validaciones
- Si `+BUFF:GTINF`, el comportamiento y los campos son idénticos, pero el mensaje fue almacenado previamente.  
- `Network`, `Band` y `OperatorName` se usan para determinar la tecnología activa (2G, 3G o 4G).  
- El `ICCID` permite identificar la SIM activa cuando el equipo soporta multi-IMSI.  
- `CSQ` se convierte a dBm aproximados mediante la fórmula: `dBm = -113 + (CSQ × 2)`.

---

## 6️⃣ Recomendaciones para parser

- Tokenizar por `,` y eliminar `$` final.  
- Validar longitud mínima de campos.  
- Permitir `None` o vacío en IMSI2 o ICCID.  
- Normalizar hora UTC a ISO-8601 antes de guardar.  
- Detectar si el prefijo es `+BUFF:` o `+RESP:` y marcar `is_buffer`.

---

## 7️⃣ Próximos pasos

- Crear `spec/gv310lau/gtinf.yml` con esquema de validación.  
- Crear `tests/gv310lau/test_gtinf_parser.py` con al menos un caso base de parseo.  
- Validar integración en `queclink_tramas.py → parse_gtinf()`.
