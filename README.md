# Queclinck-Homlogador-Tramas

Herramientas para homologar y analizar tramas Queclink (`+RESP:GTERI` y `+RESP:GTINF`) de los
modelos GV310LAU, GV58LAU y GV350CEU. Permite convertir archivos de texto/CSV/XLSX a una base de
datos SQLite y, a partir de ella, generar mapas diarios con los recorridos diferenciando entre
reportes buffer y no buffer.

## Requisitos

- Python 3.9 o superior.
- Dependencias opcionales del parser: `pandas` y `openpyxl` (para leer CSV/XLSX).
- Dependencias del módulo de visualización: `folium`, `pytz`, `python-dateutil`.

Instala los paquetes mínimos para los mapas con:

```bash
pip install folium pytz python-dateutil
```

## Homologación de tramas GTINF/GTERI

Ejemplo rápido para convertir un archivo de tramas a SQLite:

```bash
python queclink_tramas.py --in datos.txt --out salida.db
```

### Filtrado por tipo de homologación

El CLI acepta la opción `--message` para limitar el procesamiento a un tipo de trama concreto:

```bash
python queclink_tramas.py --in datos.txt --out salida.db --message GTINF
```

Admite los valores `GTINF` y `GTERI`. Esto permite homologar lotes mixtos reutilizando la misma
especificación YAML cargada automáticamente según el modelo detectado.

### Identificación del modelo

El homologador determina el modelo a partir de los **primeros ocho dígitos del IMEI**,
un valor fijo que no depende de la personalización del `DeviceName`. Los prefijos
actualmente soportados son:

- `86631406` → **GV58LAU**
- `86858906` → **GV310LAU**
- `86252406` → **GV350CEU**

Esto aplica para todos los reportes (`GTINF`, `GTERI`, etc.) ingresados a la base de datos.

### Campos soportados en GTERI

El parser de `+RESP:+/BUFF:GTERI` reconoce la totalidad de la estructura definida en los archivos
`spec/<modelo>/gteri.yml`, incluyendo:

- Normalización de coordenadas, máscaras y odómetro/horómetro.
- Valores analógicos con conservación de datos crudos (`analog_in_*_raw`), milivoltios y
  porcentajes.
- Máscaras GNSS (`position_append_mask`) y cálculo auxiliar de `hdop` cuando solo se reportan
  VDOP/PDOP.
- Bloques ERI: sensores de combustible digitales, accesorios RF433 y BLE (con iteración de
  accesorios y máscara de campos anexos).
- Compatibilidad ampliada con los modelos **GV350CEU** y **GV58LAU**, incluyendo conteo de
  accesorios BLE, campos reservados, máscaras extendidas y los nuevos datos de RAT/Band
  definidos en `spec/gv350ceu/gteri.yml` y `spec/gv58lau/gteri.yml`.
- Campos extendidos como `device_status_*`, `backup_battery_pct`, listas de advertencias de
  validación y la ruta al archivo de especificación usado (`spec_path`).

Consulta la carpeta `docs/` para detalles del protocolo y campos disponibles.

## Visualización de recorridos diarios

El módulo `viz` entrega un CLI que genera un mapa HTML (Folium) y un GeoJSON agrupando los
recorridos por día local (`America/Santiago`). Los puntos buffer se dibujan en rojo y los
reportes directos en azul, incluyendo tooltips con hora local y coordenadas.


### Ejemplos de uso

**Linux/macOS**

```bash
python -m viz.cli \
  --db salida.db \
  --imei 8646960600004173 \
  --date 2023-08-01 \
  --provider "CartoDB Positron" \
  --out mapas/gv310lau_2023-08-01


```bash
python -m viz.cli \
  --db salida.db \
  --imei 864696060004173 \
  --date 2023-08-01 \
  --provider "CartoDB Positron" \
  --out mapas/gv310lau_2023-08-01
```


**Windows (PowerShell)** – usa el acento grave `` ` `` como continuador y el lanzador `py`:

```powershell
py -m viz.cli `
  --db salida.db `
  --imei 8646960600004173 `
  --date 2023-08-01 `
  --provider "CartoDB Positron" `
  --out mapas/gv310lau_2023-08-01
```

**Windows (CMD)** – usa `^` como continuador:

```cmd
py -m viz.cli ^
  --db salida.db ^
  --imei 8646960600004173 ^
  --date 2023-08-01 ^
  --provider "CartoDB Positron" ^
  --out mapas/gv310lau_2023-08-01
```

Consulta `docs/viz/windows.md` para más consejos y una captura de pantalla del resultado.

El comando anterior creará los archivos:

- `mapas/gv310lau_2023-08-01.html`: mapa interactivo listo para compartir.
- `mapas/gv310lau_2023-08-01.geojson`: puntos del recorrido con hora local y tipo de reporte.

Para más ejemplos y capturas de pantalla revisa `docs/viz/mapas.md`.

## Pruebas

Ejecuta los tests (incluye las validaciones del módulo de visualización):

```bash
pytest
```
