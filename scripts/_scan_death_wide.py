"""Wider scan for a real death/retry counter across slot + system save."""
from __future__ import annotations

import json
import struct
import sys
import uuid
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_save import TypeDb, murmur3_32, parse_save  # noqa: E402

ROOT = Path(r"d:\开学！\react\onimusha")
WANT = {"1", "5", "6", "7", "8", "10"}
SKIP = {"$type", "$typeHash", "$fieldCount"}


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


def walk(obj, path, acc, depth=0):
    if depth > 8:
        return
    if isinstance(obj, dict):
        if obj.get("$type") == "ace.Bitset":
            words = obj.get("_Value") or []
            ones = 0
            for w in words:
                if isinstance(w, int):
                    ones += w.bit_count()
            acc[path + "#bits"] = ones
            return
        for k, v in obj.items():
            if k in SKIP:
                continue
            here = f"{path}.{k}" if path else k
            if isinstance(v, bool):
                continue
            if isinstance(v, int) and 0 <= v <= 20000:
                acc[here] = v
            elif isinstance(v, float) and v.is_integer() and 0 <= v <= 20000:
                acc[here] = int(v)
            elif isinstance(v, str) and "-" in v:
                dec = decode_guid(v)
                if dec is not None and 0 <= dec <= 20000:
                    acc[here + "#md"] = dec
            elif isinstance(v, dict) and "value" in v and isinstance(v.get("value"), int):
                n = v["value"]
                if 0 <= n <= 20000:
                    acc[here] = n
                else:
                    walk(v, here, acc, depth + 1)
            else:
                walk(v, here, acc, depth + 1)
    elif isinstance(obj, list):
        if len(obj) > 80:
            ints = [x for x in obj if isinstance(x, int) and 0 < x <= 20000]
            if ints:
                acc[path + "#sum"] = sum(ints)
                acc[path + "#max"] = max(ints)
            return
        for i, item in enumerate(obj):
            walk(item, f"{path}[{i}]", acc, depth + 1)


def slim(obj, depth=0):
    if depth > 3:
        return "..."
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in SKIP:
                continue
            if isinstance(v, list) and len(v) > 8 and all(isinstance(x, int) for x in v):
                out[k] = v[:8] + (["..."] if len(v) > 8 else [])
            else:
                out[k] = slim(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [slim(x, depth + 1) for x in obj[:6]]
    return obj


def main():
    src = Path(sys.argv[1])
    db = TypeDb(
        json.loads((ROOT / "dumps/REasy/resources/data/dumps/rszoniwots.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "dumps/oniwots_enums.json").read_text(encoding="utf-8")),
    )
    parsed = parse_save(src.read_bytes(), db)
    root = parsed["roots"][0]["data"]
    users = root["_UserSaveData"]

    names = [
        "ClearCount",
        "Packed",
        "GameOverCount",
        "UniqueID",
        "TrialCounterIssenCount",
        "_ExtraContent",
        "ExtraContent",
        "IdLinked",
        "_ExtraContent_ver",
        "ExtraContent_ver",
        "_IdLinked",
        "SoulBoostValue",
        "JustDodgeAttackValue",
        "PlayTime",
        "PlayTimeSecond",
        "TotalPlayTime",
        "DeathCount",
        "DeadCount",
        "_DeadCount",
        "DieCount",
        "_DieCount",
        "RetryCount",
        "_RetryCount",
        "ContinueCount",
        "PlayerDeadCount",
        "PlayerDieCount",
        "TotalDeath",
        "GameOverNum",
        "GameOverTimes",
        "FallCount",
        "DownCount",
        "ResurrectionCount",
        "ReviveCount",
        "RespawnCount",
        "CheckPointRetryCount",
        "RetryNum",
        "FailedCount",
        "FailCount",
        "LoseCount",
        "PlayerGameOverCount",
        "TotalGameOverCount",
        "v_GameOverCount",
        "_GameOverCount",
    ]
    print("=== hashes ===")
    for name in names:
        print(f"{name:32s} {murmur3_32(name):08x}")

    maps = {}
    meta = {}
    for user in users:
        n = slot_no(user)
        if n not in WANT:
            continue
        d = user["_Data"]
        acc = {}
        walk(d, "", acc)
        maps[n] = acc
        us = d.get("_UserSystemParam") or {}
        extra = us.get("field_e5009ec0") or []
        extra_slim = []
        for it in extra:
            if not isinstance(it, dict):
                continue
            extra_slim.append(
                {
                    k: v
                    for k, v in it.items()
                    if k not in SKIP
                    and not (isinstance(v, list) and len(v) > 4 and all(isinstance(x, int) and x == 0 for x in v[1:]))
                }
            )
        meta[n] = {
            "sub": user.get("Subtitle"),
            "detail": (user.get("Detail") or "").split("\t")[:4],
            "sys": {k: us[k] for k in us if k not in SKIP and k != "field_e5009ec0"},
            "extra": extra_slim,
            "pl_keys": [k for k in (d.get("_PlayerStatus") or {}) if k not in SKIP],
        }

    print("\n=== slot meta ===")
    for n in sorted(WANT, key=int):
        print(n, json.dumps(meta[n], ensure_ascii=False, default=str)[:2000])

    # candidate: 2-400, differ, slot8 not tiny vs slot1 if slot1 tiny
    print("\n=== candidates 2-400 differing, slot8>=3 or rising 1->7 ===")
    all_paths = set()
    for acc in maps.values():
        all_paths |= set(acc)
    shown = 0
    for path in sorted(all_paths):
        vals = {s: maps[s].get(path) for s in ["1", "5", "6", "7", "8", "10"] if s in maps}
        nums = [v for v in vals.values() if isinstance(v, int)]
        if len(set(nums)) <= 1:
            continue
        if any(v is None for v in (vals.get("1"), vals.get("7"), vals.get("8"))):
            continue
        a, b, c = vals["1"], vals["7"], vals["8"]
        if not all(isinstance(v, int) and 0 <= v <= 400 for v in (a, b, c)):
            continue
        # skip obvious IDs / costume / packed flags
        if any(x in path for x in ("Costume", "Equip", "UniqueID", "Packed", "FixedId", "SeriesId", "itemId", "ItemId")):
            continue
        rising = b >= a and (c >= 3 or (a <= 2 and c > a) or (b - a >= 3))
        if not rising and not (c >= 5 and c != a):
            continue
        print(f"{path:70s} 1={a} 5={vals.get('5')} 6={vals.get('6')} 7={b} 8={c} 10={vals.get('10')}")
        shown += 1
    print("shown", shown)

    print("\n=== all differing 1-80 excluding huge trees ===")
    for path in sorted(all_paths):
        if path.count("[") > 2:
            continue
        if any(x in path for x in ("_Items", "_Amulets", "Costume", "Equip", "Activated", "SkillOrder", "itemId")):
            continue
        a, b, c = maps.get("1", {}).get(path), maps.get("7", {}).get(path), maps.get("8", {}).get(path)
        if a == b == c:
            continue
        if all(isinstance(v, int) and 1 <= v <= 80 for v in (a, b, c) if v is not None) and len({a, b, c} - {None}) >= 2:
            print(f"{path:70s} 1={a} 7={b} 8={c}")

    sysd = root.get("_SystemSaveData") or {}
    sys_acc = {}
    walk(sysd, "sys", sys_acc)
    print("\n=== system ints 1-400 ===")
    for k, v in sorted(sys_acc.items()):
        if isinstance(v, int) and 1 <= v <= 400:
            print(f"{k:70s} {v}")

    # achievement counts
    ach = ((sysd.get("_Data") or {}).get("_Achievement") or [])
    print("\n=== achievement counts ===")
    if isinstance(ach, list):
        for it in ach:
            if not isinstance(it, dict):
                continue
            eid = it.get("EnumId") or it.get("Id")
            cnt = it.get("Count") or it.get("count")
            unlocked = it.get("Unlocked") or it.get("IsUnlocked")
            if cnt not in (None, 0):
                print(eid, "count", cnt, "unlock", unlocked)


if __name__ == "__main__":
    main()
