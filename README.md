# Queclinck-Homlogador-Tramas

Herramientas para homologar y analizar tramas Queclink (`+RESP:GTERI`) de los modelos
GV310LAU, GV58LAU y GV350CEU. Permite convertir archivos de texto/CSV/XLSX a una base de datos
SQLite y, a partir de ella, generar mapas diarios con los recorridos diferenciando entre
reportes buffer y no buffer.

## Requisitos

- Python 3.9 o superior.
- Dependencias opcionales del parser: `pandas` y `openpyxl` (para leer CSV/XLSX).
- Dependencias del módulo de visualización: `folium`, `pytz`, `python-dateutil`.

Instala los paquetes mínimos para los mapas con:

```bash
pip install folium pytz python-dateutil
```

## Parser de tramas GTERI

Ejemplo rápido para convertir un archivo de tramas a SQLite:

```bash
python queclink_tramas.py --in datos.txt --out salida.db
```

Consulta la carpeta `docs/` para detalles del protocolo y campos disponibles.

## Visualización de recorridos diarios

El módulo `viz` entrega un CLI que genera un mapa HTML (Folium) y un GeoJSON agrupando los
recorridos por día local (`America/Santiago`). Los puntos buffer se dibujan en rojo y los
reportes directos en azul, incluyendo tooltips con hora local y coordenadas.

```bash
python -m viz.cli \
  --db salida.db \
  --imei 864696060004173 \
  --date 2023-08-01 \
  --provider "CartoDB Positron" \
  --out mapas/gv310lau_2023-08-01
```

En Windows puedes usar los siguientes equivalentes:

- **PowerShell**

  ```powershell
  py -m viz.cli `
    --db salida.db `
    --imei 864696060004173 `
    --date 2023-08-01 `
    --provider "CartoDB Positron" `
    --out mapas/gv310lau_2023-08-01
  ```

- **CMD**

  ```cmd
  py -m viz.cli ^
    --db salida.db ^
    --imei 864696060004173 ^
    --date 2023-08-01 ^
    --provider "CartoDB Positron" ^
    --out mapas/gv310lau_2023-08-01
  ```

> ℹ️ Consulta `docs/viz/windows.md` para más consejos y captura de pantalla del resultado.

El comando anterior creará los archivos:

- `mapas/gv310lau_2023-08-01.html`: mapa interactivo listo para compartir.
- `mapas/gv310lau_2023-08-01.geojson`: puntos del recorrido con hora local y tipo de reporte.

Para más ejemplos y capturas de pantalla revisa `docs/viz/mapas.md`.

## Pruebas

Ejecuta los tests (incluye las validaciones del módulo de visualización):

```bash
pytest
```
