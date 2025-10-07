# +RESP/+BUFF:GTINF — GV350CEU


## Descripción
Reporte informativo del dispositivo para la serie GV350. Prefijos `+RESP`/`+BUFF`.
- Versión de protocolo (GV350CEU): **6 hex** (p.ej. `74040A`).
- Suele incluir dos timestamps y máscaras de IO.


## Ejemplos reales (proporcionados)

**RESP**
+RESP:GTINF,74040A,862524060748775,GV350CEU,11,89999112400719062394,37,0,1,13074,,4.19,0,1,,,20251007213710,,0,0,0,00,00,+0000,0,20251007213751,6B91$

**BUFF**
+BUFF:GTINF,740904,862524060876527,GV350CEU,22,8935711001088072340f,38,0,1,28018,3,4.11,0,1,,,20251007143611,,0,0,0,11,00,+0000,0,20251007143612,34DA$

## Notas de parsing
- `protocol_version`: 6 hex.
- Detectar `source` RESP/BUFF.
- Convertir numéricos; normalizar timestamps a ISO‑8601 si se expone.
