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
"+RESP:GTINF,74040A,862524060748775,GV350CEU,11,89999112400719062394,37,0,1,13074,,4.19,0,1,,,"
"20251007213710,,0,0,0,00,00,+0000,0,20251007213751,6B91$"
)


RAW_BUFF = (
"+BUFF:GTINF,740904,862524060876527,GV350CEU,22,8935711001088072340f,38,0,1,28018,3,4.11,0,1,,,"
"20251007143611,,0,0,0,11,00,+0000,0,20251007143612,34DA$"
)




def _assert_basicos(d: dict):
for k in ("device", "imei", "protocol_version", "source"):
assert k in d
assert d["device"] == "GV350CEU"
assert re.fullmatch(r"[0-9]{15}", d["imei"])
assert re.fullmatch(r"[0-9A-Fa-f]{6}", d["protocol_version"]) # 6 hex en GV350CEU
assert any(re.fullmatch(r"\d{14}", v or "") for v in map(str, d.values()))
if iso := (d.get("send_time_iso") or d.get("last_fix_iso")):
dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))




def test_gtinf_resp_ok():
d = parse_gtinf(RAW_RESP)
_assert_basicos(d)
assert d["source"] == "RESP"
assert d.get("count_hex", "").upper() == "6B91"




def test_gtinf_buff_ok():
d = parse_gtinf(RAW_BUFF)
_assert_basicos(d)
assert d["source"] == "BUFF"
assert d.get("count_hex", "").upper() == "34DA"
