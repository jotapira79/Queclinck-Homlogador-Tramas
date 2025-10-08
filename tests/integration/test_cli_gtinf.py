"""Tests de integración para la ejecución CLI del homologador GTINF."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path


def test_cli_ingests_gtinf_messages(tmp_path: Path) -> None:
    """Ejecuta la CLI end-to-end y valida la ingesta GTINF."""

    input_path = tmp_path / "datos.txt"
    output_path = tmp_path / "salida.db"

    lines = [
        "+RESP:GTINF,6E1203,135790246811220,GV310LAU,16,898600810906F8048812,16,0,1,12000,1,4.40,0,0,1,1,20230214013254,,2,6,,1260,0000,0001,+0800,0,20230214093254,11F0$",
        "+BUFF:GTINF,6E0C03,868589060716712,GV310LAU,21,89999112400719021127,15,0,1,27999,2,4.16,0,1,2,0,20251007194843,3,,0,,01,00,+0000,0,20251007194845,32B0$",
        "+RESP:GTINF,8020040900,866314061635635,GV58LAU,11,89999202003110001341,58,0,1,12943,3,4.15,0,1,,,20251007213819,0,,,,00,00,+0000,0,20251007215523,48D6$",
        "+BUFF:GTINF,8020040305,866314060965330,GV58LAU,22,89999112400719088191,26,0,1,13742,0,4.22,0,1,,,20250930110413,0,,,,01,00,+0000,0,20250930110413,ED27$",
        "+RESP:GTINF,74040A,862524060748775,GV350CEU,11,89999112400719062394,37,0,1,13074,,4.19,0,1,,,20251007213710,,0,0,0,00,00,+0000,0,20251007213751,6B91$",
        "+BUFF:GTINF,740904,862524060876527,GV350CEU,22,8935711001088072340f,38,0,1,28018,3,4.11,0,1,,,20251007143611,,0,0,0,11,00,+0000,0,20251007143612,34DA$",
    ]
    input_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "queclink_tramas.py",
            "--in",
            str(input_path),
            "--out",
            str(output_path),
            "--message",
            "GTINF",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert output_path.is_file(), "La base de datos de salida debe existir"

    conn = sqlite3.connect(output_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name='telemetry_messages'"
        )
        assert cursor.fetchone(), "La tabla/vista telemetry_messages debe existir"

        total_rows = conn.execute("SELECT COUNT(*) FROM telemetry_messages").fetchone()[0]
        assert total_rows == 6, "Deben haberse insertado 6 tramas GTINF"

        rows_per_device = dict(
            conn.execute(
                "SELECT device, COUNT(*) FROM telemetry_messages WHERE report='GTINF' GROUP BY device"
            ).fetchall()
        )
    finally:
        conn.close()

    assert rows_per_device == {
        "GV310LAU": 2,
        "GV58LAU": 2,
        "GV350CEU": 2,
    }
    assert "[OK] 6 tramas insertadas" in result.stdout
