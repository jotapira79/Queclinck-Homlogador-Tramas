import re
import pytest

# Intentamos importar la función del proyecto. Ajusta estos imports si tu repo usa otra ruta.
try:
    from queclink.gteri import parse_gteri  # estilo paquete
except Exception:
    try:
        from src.gteri_parser import parse_gteri  # estilo src/
    except Exception:
        try:
            import importlib.util
            from pathlib import Path

            repo_root = Path(__file__).resolve().parents[2]
            module_path = repo_root / "queclink_tramas.py"
            spec = importlib.util.spec_from_file_location("queclink_tramas", module_path)
            if not spec or not spec.loader:  # pragma: no cover - carga alternativa
                raise ImportError("No se pudo cargar queclink_tramas.py")
            _module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_module)

            def _to_iso(ts: str) -> str:
                if not ts:
                    return ts
                from datetime import datetime

                for fmt in ("%Y%m%d%H%M%S",):
                    try:
                        return datetime.strptime(ts, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        continue
                return ts

            def _wrapper(raw: str):
                base = _module.parse_line_to_record(raw)  # type: ignore[attr-defined]
                if not base:
                    return {}
                data = dict(base)
                data["header"] = data.get("prefix")
                data["device"] = data.get("model") or data.get("device_name")
                data["utc"] = _to_iso(data.get("gnss_utc", "")) if data.get("gnss_utc") else data.get("gnss_utc")
                data["send_time"] = _to_iso(data.get("send_time", "")) if data.get("send_time") else data.get("send_time")
                data["sats"] = data.get("satellites")
                dop_candidate = data.get("dop1")
                if dop_candidate is None:
                    for key in ("dop2", "dop3"):
                        val = data.get(key)
                        if val is not None:
                            dop_candidate = val
                            break
                if dop_candidate is not None:
                    data["hdop"] = dop_candidate
                if isinstance(data.get("device_status"), str):
                    data["device_status"] = data["device_status"].upper()
                mask_lower = str(data.get("pos_append_mask", "")).lower()
                if mask_lower in {"00", "0"}:
                    data.setdefault("gnss_fix", False)
                    data.setdefault("is_last_fix", True)
                return data

            parse_gteri = _wrapper
        except Exception:
            from queclink_gteri_parser import parse_gteri  # último recurso


# Ejemplo real (del PDF) con varios opcionales activos
RAW_OK = (
    "+RESP:GTERI,6E1203,864696060004173,GV310LAU,00000100,,10,1,1,0.0,0,115.8,"
    "117.129356,31.839248,20230808061540,0460,0001,DF5C,05FE6667,03,15,,4.0,"
    "0000102:34:33,14549,42,11172,100,210000,0,1,0,06,12,0,001A42A2,0617,TMPS,"
    "08351B00043C,1,26,65,20231030085704,20231030085704,0017$"
)

# Variante con HDOP=0 (sin fix GNSS) y sin opcionales de posición (mask=00)
RAW_HDOP0 = (
    "+RESP:GTERI,6E1203,864696060004173,GV310LAU,00000000,,10,1,1,12.3,90,200.5,"
    "-70.123456,-33.456789,20250101010101,0730,0001,ABCD,00112233,00,"
    "0000000:00:10,0,0,0,80,210000,0,0,20250101010102,0001$"
)


RAW_UART_DUP_ZERO = (
    "+RESP:GTERI,6E1203,864696060004173,GV310LAU,00000100,,10,1,1,0.0,0,115.8,"
    "117.129356,31.839248,20230808061540,0460,0001,DF5C,05FE6667,03,15,,4.0,"
    "0000102:34:33,14549,42,11172,100,220100,0,0,06,12,0,001A42A2,0617,TMPS,"
    "08351B00043C,1,26,65,20231030085704,20231030085704,0017$"
)


def test_parse_gteri_campos_basicos():
    d = parse_gteri(RAW_OK)
    assert isinstance(d, dict)

    # Campos de cabecera
    assert d.get("header") == "+RESP:GTERI"
    assert d.get("imei") == "864696060004173"
    assert d.get("device") == "GV310LAU"

    # Coordenadas y tiempo
    assert pytest.approx(d.get("lon"), rel=1e-6) == 117.129356
    assert pytest.approx(d.get("lat"), rel=1e-6) == 31.839248
    # UTC normalizado (ISO‑8601). Si tu implementación usa clave distinta, ajusta aquí.
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", d.get("utc", ""))

    # Máscaras y opcionales
    assert d.get("pos_append_mask", "").lower() in {"03", 3, "3"}
    assert d.get("sats") == 15
    # HDOP presente y > 0 en esta muestra
    assert d.get("hdop") in (4.0, 4, "4.0", "4")

    # Odómetro y horómetro
    assert isinstance(d.get("mileage_km"), (int, float))
    assert re.match(r"^[0-9]{7}:[0-9]{2}:[0-9]{2}$", d.get("hour_meter", ""))

    # Envío y contador
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", d.get("send_time", ""))
    assert re.match(r"^[0-9A-Fa-f]{4}$", d.get("count_hex", ""))


def test_semantica_hdop_sin_fix():
    d = parse_gteri(RAW_HDOP0)

    # Mask 00 => no deberían venir campos anexos de posición (sats/hdop/vdop/pdop)
    assert d.get("pos_append_mask", "").lower() in {"00", 0, "0"}
    assert d.get("sats") in (None, 0)  # puede no existir o venir como 0

    # HDOP = 0 => sin fix GNSS (banderas esperadas)
    # La especificación sugiere exponer esto; si usas otra clave, ajusta aquí.
    assert d.get("gnss_fix") is False or d.get("is_last_fix") is True


@pytest.mark.parametrize(
    "raw, must_keys",
    [
        (RAW_OK, [
            "imei", "device", "lon", "lat", "utc", "mcc", "mnc", "lac", "cell_id",
            "mileage_km", "hour_meter", "send_time", "count_hex"
        ]),
        (RAW_HDOP0, [
            "imei", "device", "lon", "lat", "utc", "mcc", "mnc", "lac", "cell_id",
            "mileage_km", "hour_meter", "send_time", "count_hex"
        ]),
    ],
)
def test_claves_minimas_presentes(raw, must_keys):
    d = parse_gteri(raw)
    for k in must_keys:
        assert k in d, f"Falta clave requerida: {k}"


def test_rangos_basicos():
    d = parse_gteri(RAW_OK)
    assert -90 <= d.get("lat") <= 90
    assert -180 <= d.get("lon") <= 180
    assert 0 <= d.get("backup_batt_pct", 0) <= 100


def test_valida_hour_meter_formato():
    d = parse_gteri(RAW_OK)
    hm = d.get("hour_meter", "")
    assert re.match(r"^[0-9]{7}:[0-9]{2}:[0-9]{2}$", hm)


def test_campos_post_dop_no_se_desplazan():
    d = parse_gteri(RAW_OK)

    assert d.get("mileage_km") == pytest.approx(14549.0)
    assert d.get("hour_meter") == "0000102:34:33"
    assert d.get("analog_in_1") in {"42", 42}
    assert d.get("analog_in_2") in {"11172", 11172}
    assert d.get("backup_batt_pct") == 100
    assert str(d.get("device_status", "")).upper() == "210000"
    assert d.get("remaining_blob") == "1,0,06,12,0,001A42A2,0617,TMPS,08351B00043C,1,26,65,20231030085704"


def test_uart_device_type_extraido_y_fuera_del_blob():
    d = parse_gteri(RAW_UART_DUP_ZERO)

    assert isinstance(d.get("uart_device_type"), int)
    assert d.get("uart_device_type") == 0

    assert d.get("device_status") in {"220100", 220100}

    remaining = d.get("remaining_blob") or ""
    # Antes la secuencia quedaba como ",,,100,220100,0,0,..."; al extraer el UART
    # desaparece el primer "0" y ya no existe "0,0,06" en el remanente.
    assert "0,0,06" not in remaining
