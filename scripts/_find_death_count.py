"""Find integer fields that look like a real death counter."""
from __future__ import annotations

import json
import struct
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_save import TypeDb, murmur3_32, parse_save  # noqa: E402

ROOT = Path(r"d:\开学！\react\onimusha")
SKIP = {"$type", "$typeHash", "$fieldCount"}
WANT = {"1", "5", "6", "7", "8", "10"}


def decode_guid(value):
    if isinstance(value, int):
        return value
    if not isinstance(value, str) or "-" not in value:
        return None
    try:
        v, m = struct.unpack("<2q", uuid.UUID(value).bytes_le)
    except Exception:
        return None
    if v == 0:
        return 0
    if m == 0 or v % m != 0:
        return None
    return v // m


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def walk_ints(obj, path, acc, depth=0):
    if depth > 5:
        return
    if isinstance(obj, dict):
        if obj.get("$type") == "ace.Bitset":
            return
        for k, v in obj.items():
            if k in SKIP:
                continue
            here = f"{path}.{k}"
            if isinstance(v, str) and "-" in v:
                dec = decode_guid(v)
                if dec is not None and 0 <= dec <= 500:
                    acc[here + "#md"] = dec
            elif isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 500:
                acc[here] = v
            elif isinstance(v, dict) and "value" in v and isinstance(v.get("value"), int):
                n = v["value"]
                if 0 <= n <= 500:
                    acc[here] = n
            else:
                walk_ints(v, here, acc, depth + 1)
    elif isinstance(obj, list) and len(obj) <= 40:
        for i, item in enumerate(obj):
            walk_ints(item, f"{path}[{i}]", acc, depth + 1)


def main():
    src = Path(sys.argv[1])
    if src.suffix == ".json":
        parsed = json.loads(src.read_text(encoding="utf-8"))
    else:
        db = TypeDb(
            json.loads((ROOT / "dumps/REasy/resources/data/dumps/rszoniwots.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "dumps/oniwots_enums.json").read_text(encoding="utf-8")),
        )
        parsed = parse_save(src.read_bytes(), db)

    users = parsed["roots"][0]["data"]["_UserSaveData"]
    maps = {}
    meta = {}
    for user in users:
        n = slot_no(user)
        if n not in WANT:
            continue
        d = user["_Data"]
        acc = {}
        walk_ints(d.get("_UserSystemParam") or {}, "sys", acc)
        walk_ints(d.get("_PlayerStatus") or {}, "pl", acc)
        walk_ints(d.get("_Tips") or {}, "tips", acc)
        walk_ints(d.get("_NpcParam") or {}, "npc", acc)
        walk_ints(d.get("_EventParam") or {}, "ev", acc)
        walk_ints(d.get("_StageStatus") or {}, "st", acc)
        maps[n] = acc
        us = d.get("_UserSystemParam") or {}
        st = d.get("_PlayerStatus") or {}
        sub = user.get("Subtitle") or ""
        detail = user.get("Detail") or ""
        meta[n] = {
            "sub": sub,
            "detail": detail.split("\t")[:4],
            "sys_keys": [k for k in us if k not in SKIP],
            "pl_counts": {k: st[k] for k in st if "Count" in k or k.startswith("field_")},
        }

    print("=== meta ===")
    for n in sorted(WANT, key=lambda x: int(x) if x.isdigit() else 0):
        print(n, meta.get(n))

    names = [
        "GameOverCount",
        "ClearCount",
        "Packed",
        "Padding0",
        "UniqueID",
        "TrialCounterIssenCount",
        "DeathCount",
        "DeadCount",
        "DieCount",
        "RetryCount",
        "ContinueCount",
        "PlayerDeadCount",
        "TotalDeath",
        "GameOverNum",
    ]
    print("\n=== hashes ===")
    for name in names:
        print(f"{name:28s} {murmur3_32(name):08x}")

    all_paths = set()
    for acc in maps.values():
        all_paths |= set(acc)

    print("\n=== ints that rise 1->7 and slot8 not tiny ===")
    for path in sorted(all_paths):
        vals = [maps.get(s, {}).get(path) for s in ["1", "5", "6", "7", "8"]]
        if None in vals[:4]:
            continue
        if not all(isinstance(v, int) for v in vals if v is not None):
            continue
        if vals[0] == vals[1] == vals[2] == vals[3]:
            continue
        if vals[3] >= vals[0] and (vals[4] or 0) >= 3:
            print(f"{path:50s} 1={vals[0]} 5={vals[1]} 6={vals[2]} 7={vals[3]} 8={vals[4]}")

    print("\n=== all 1-200 differing across 1/7/8 ===")
    for path in sorted(all_paths):
        a, b, c = maps.get("1", {}).get(path), maps.get("7", {}).get(path), maps.get("8", {}).get(path)
        if a is None and b is None and c is None:
            continue
        if a == b == c:
            continue
        if all(v is None or (isinstance(v, int) and 0 <= v <= 200) for v in (a, b, c)):
            print(f"{path:50s} 1={a} 7={b} 8={c}")


if __name__ == "__main__":
    main()
