# +RESP/+BUFF:GTINF — GV58LAU


## Descripción
Reporte informativo del dispositivo (firmware, red, SIM/ICCID, señal, etc.).
- Prefijos admitidos: `+RESP:GTINF` y `+BUFF:GTINF` (mismo payload, diferente origen).
- Versión de protocolo (GV58LAU): **10 hex** (p.ej. `8020040900`).


## Ejemplos reales (proporcionados)

**RESP**
+RESP:GTINF,8020040900,866314061635635,GV58LAU,11,89999202003110001341,58,0,1,12943,3,4.15,0,1,,,20251007213819,0,,,,00,00,+0000,0,20251007215523,48D6$

**BUFF**
+BUFF:GTINF,8020040305,866314060965330,GV58LAU,22,89999112400719088191,26,0,1,13742,0,4.22,0,1,,,20250930110413,0,,,,01,00,+0000,0,20250930110413,ED27$

## Notas de parsing
- Tokenizar por `,` y quitar el `$` final.
- `protocol_version`: 10 hex.
- Detectar `source`: `RESP` o `BUFF` por el prefijo.
- Campos numéricos: convertir a `int/float` cuando aplique (CSQ, band/idx, voltajes, etc.).
- Normalizar timestamps (14 dígitos) a ISO‑8601 UTC si deseas exponer `*_iso`.
