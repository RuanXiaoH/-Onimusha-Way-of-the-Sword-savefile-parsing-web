from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_bin import DUMP, ENUMS
from make_display_data import build_display
from parse_save import TypeDb, parse_save

plain = Path(r"d:\开学！\react\onimusha\test_data\data001Slot_1045.decrypted.bin")
print("parse", flush=True)
db = TypeDb(json.loads(DUMP.read_text(encoding="utf-8")), json.loads(ENUMS.read_text(encoding="utf-8")))
parsed = parse_save(plain.read_bytes(), db)
print("build", flush=True)
display = build_display(parsed)
for s in display.get("slots") or []:
    c = s["collections"]
    print(
        s["slotIndex"],
        s.get("location"),
        "mystery",
        c["mysteries"]["owned"],
        c["mysteries"]["bits"],
        "komainu",
        c["komainu"]["owned"],
        flush=True,
    )
out = Path(r"d:\开学！\react\onimusha\web\src\data\save.json")
out.write_text(json.dumps(display, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out, flush=True)
