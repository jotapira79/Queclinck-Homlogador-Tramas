import re
import datetime as dt


try:
from queclink_tramas import parse_gtinf
except Exception:
try:
from queclink.gtinfs import parse_gtinf
except Exception:
from src.gtinf_parser import parse_gtinf


RAW_RESP = (
"+RESP:GTINF,8020040900,866314061635635,GV58LAU,11,89999202003110001341,58,0,1,12943,3,4.15,0,1,,,"
"20251007213819,0,,,,00,00,+0000,0,20251007215523,48D6$"
)


RAW_BUFF = (
"+BUFF:GTINF,8020040305,866314060965330,GV58LAU,22,89999112400719088191,26,0,1,13742,0,4.22,0,1,,,"
"20250930110413,0,,,,01,00,+0000,0,20250930110413,ED27$"
)




def _assert_basicos(d: dict):
for k in ("device", "imei", "protocol_version", "source"):
assert k in d
assert d["device"] == "GV58LAU"
assert re.fullmatch(r"[0-9]{15}", d["imei"])
assert re.fullmatch(r"[0-9A-Fa-f]{10}", d["protocol_version"]) # 10 hex en GV58LAU
# Al menos un timestamp de 14 dígitos
assert any(re.fullmatch(r"\d{14}", v or "") for v in map(str, d.values()))
# ISO opcional
if iso := (d.get("send_time_iso") or d.get("last_fix_iso")):
dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))




def test_gtinf_resp_ok():
d = parse_gtinf(RAW_RESP)
_assert_basicos(d)
assert d["source"] == "RESP"
assert d.get("count_hex", "").upper() == "48D6"




def test_gtinf_buff_ok():
d = parse_gtinf(RAW_BUFF)
_assert_basicos(d)
assert d["source"] == "BUFF"
assert d.get("count_hex", "").upper() == "ED27"
