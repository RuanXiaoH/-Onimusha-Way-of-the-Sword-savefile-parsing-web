from pathlib import Path
import json, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_save import TypeDb, parse_save

ROOT = Path(r"d:\开学！\react\onimusha")
src = Path(sys.argv[1])
if src.suffix == ".json":
    parsed = json.loads(src.read_text(encoding="utf-8"))
else:
    db = TypeDb(
        json.loads((ROOT / "dumps/REasy/resources/data/dumps/rszoniwots.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "dumps/oniwots_enums.json").read_text(encoding="utf-8")),
    )
    parsed = parse_save(src.read_bytes(), db)

root = parsed["roots"][0]["data"]
print("root keys", [k for k in root if not str(k).startswith("$")])
for k, v in root.items():
    if "Achiev" in str(k) or (isinstance(v, list) and v and isinstance(v[0], dict) and "IsUnlocked" in v[0]):
        print("top", k, type(v), len(v) if isinstance(v, list) else "")

users = root.get("_UserSaveData") or []
print("users", len(users))
for i, user in enumerate(users[:3]):
    sub = user.get("Subtitle")
    d = user.get("_Data") or {}
    ach = d.get("_Achievement") or []
    print(f"\nuser[{i}] subtitle={sub!r} ach={len(ach)}")
    for j, it in enumerate(ach[:8]):
        print(" ", j, {k: it[k] for k in it if not str(k).startswith("$")})
    unlocked = sum(1 for it in ach if it.get("IsUnlocked") not in (0, None, False))
    print(" unlocked_nonzero", unlocked)

# system save if present
for key in root:
    val = root[key]
    if isinstance(val, dict) and "Achievement" in str(val.keys()) or key.lower().find("system") >= 0:
        if isinstance(val, dict):
            print("dict", key, [k for k in val if not str(k).startswith('$')][:30])
        elif isinstance(val, list) and val and isinstance(val[0], dict):
            print("list", key, val[0].get("$type"), list(val[0])[:12])
