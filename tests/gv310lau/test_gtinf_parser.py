import re
import datetime as dt

# Import flexible: ajusta si tu función vive en otro módulo
try:
    from queclink_tramas import parse_gtinf
except Exception:
    try:
        from queclink.gtinfs import parse_gtinf
    except Exception:
        from src.gtinf_parser import parse_gtinf  # último fallback


RAW_RESP = (
    "+RESP:GTINF,6E0C03,868589060361840,GV310LAU,11,89999112400719079703,32,0,0,0,3,"
    "3.81,0,1,2,0,20251007214015,3,,0,,00,00,+0000,0,20251007215025,BD2C$"
)

RAW_BUFF = (
    "+BUFF:GTINF,6E0C03,868589060716712,GV310LAU,21,89999112400719021127,15,0,1,27999,2,"
    "4.16,0,1,2,0,20251007194843,3,,0,,01,00,+0000,0,20251007194845,32B0$"
)


def _assert_basicos(d: dict):
    # Claves mínimas del contrato
    for k in ("device", "imei", "protocol_version", "source"):
        assert k in d, f"Falta clave '{k}' en {d.keys()}"

    assert d["device"] == "GV310LAU"
    assert re.fullmatch(r"[0-9]{15}", d["imei"])
    assert re.fullmatch(r"[0-9A-Fa-f]{6}", d["protocol_version"])

    # Al menos un timestamp crudo de 14 dígitos
    hay_ts_14 = any(
        isinstance(v, str) and re.fullmatch(r"\d{14}", v or "")
        for v in d.values()
    )
    assert hay_ts_14, "No se encontró ningún timestamp de 14 dígitos en el parseo"

    # Si el parser expone ISO (opcional), validar formato básico UTC
    iso = d.get("send_time_iso") or d.get("last_fix_iso")
    if iso:
        dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def test_gtinf_resp_ok():
    d = parse_gtinf(RAW_RESP)
    _assert_basicos(d)
    assert d["source"] == "RESP"
    # Validaciones específicas del RESP
    assert d["protocol_version"].upper() == "6E0C03"
    # count_hex al final
    assert d.get("count_hex", "").upper() == "BD2C"


def test_gtinf_buff_ok():
    d = parse_gtinf(RAW_BUFF)
    _assert_basicos(d)
    assert d["source"] == "BUFF"
    # Validaciones específicas del BUFF
    assert d["protocol_version"].upper() == "6E0C03"
    assert d.get("count_hex", "").upper() == "32B0"


def test_campos_numericos_en_rango_si_existen():
    # Campos que suelen venir en GTINF (si tu parser los expone con estos nombres)
    d = parse_gtinf(RAW_RESP)
    for k in ("csq", "roaming", "service_status"):
        if k in d and d[k] is not None:
            assert isinstance(d[k], int)

    # Voltajes típicos si los expones (por ejemplo backup_batt_v)
    if "backup_batt_v" in d and d["backup_batt_v"] is not None:
        assert 0.0 <= float(d["backup_batt_v"]) <= 10.0
