"""Find 幻魔杂记 (23) vs 狛犬 (36) flag fields in a parsed or encrypted slot file."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SKIP = {"$type", "$typeHash", "$fieldCount"}
EXPECT = {
    "1": 3,
    "2": 4,
    "3": 5,
    "4": 8,
    "5": 14,
    "6": 15,
    "7": 23,
}


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def bits_of(bs):
    out = []
    if not isinstance(bs, dict):
        return out
    for i, word in enumerate(bs.get("_Value") or []):
        if not isinstance(word, int):
            continue
        for b in range(32):
            if word & (1 << b):
                out.append(i * 32 + b)
    return out


def u64_bits(value, total=64):
    if isinstance(value, dict):
        value = value.get("value", 0)
    try:
        v = int(value) & ((1 << 64) - 1)
    except (TypeError, ValueError):
        return []
    return [i for i in range(total) if v & (1 << i)]


def walk(obj, path, acc):
    if isinstance(obj, dict):
        if obj.get("$type") == "ace.Bitset":
            acc.append((path, "bitset", bits_of(obj), obj.get("_MaxElement")))
            return
        for k, v in obj.items():
            if k in SKIP or str(k).endswith("_ver"):
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                bits = u64_bits(v, 64)
                if 1 <= len(bits) <= 40:
                    acc.append((f"{path}.{k}", "u64", bits, 64))
            elif isinstance(v, dict) and "value" in v and isinstance(v.get("value"), int):
                bits = u64_bits(v, 64)
                if 1 <= len(bits) <= 40:
                    acc.append((f"{path}.{k}", "enum64", bits, 64))
            walk(v, f"{path}.{k}" if path else k, acc)
    elif isinstance(obj, list) and len(obj) <= 40:
        for i, v in enumerate(obj):
            walk(v, f"{path}[{i}]", acc)


def load_parsed(path: Path) -> dict:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    from analyze_bin import DUMP, ENUMS, decrypt_bin, looks_encrypted
    from parse_save import TypeDb, parse_save

    raw = path.read_bytes()
    work = path.with_suffix(".plain.tmp")
    if looks_encrypted(raw):
        decrypt_bin(path, work)
        data = work.read_bytes()
        work.unlink(missing_ok=True)
    else:
        data = raw
    dump = json.loads(DUMP.read_text(encoding="utf-8"))
    enums = json.loads(ENUMS.read_text(encoding="utf-8"))
    return parse_save(data, TypeDb(dump, enums))


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"d:\开学！\react\onimusha\test_data\data001Slot_1045.bin"
    )
    print("load", src, flush=True)
    parsed = load_parsed(src)
    users = parsed["roots"][0]["data"]["_UserSaveData"]
    slots = {}
    for user in users:
        n = slot_no(user)
        if n and user.get("Subtitle"):
            slots[n] = user["_Data"]
    order = [s for s in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"] if s in slots]
    print("slots", [(s, (slots[s].get and None) or s) for s in order], flush=True)
    for s in order:
        keys = [k for k in slots[s] if k not in SKIP and not str(k).endswith("_ver")]
        print(f"\n=== slot {s} data keys ({len(keys)}) ===", flush=True)
        if s == "1":
            print(keys, flush=True)

    maps = {s: [] for s in order}
    for s in order:
        walk(slots[s], "d", maps[s])

    by_path = defaultdict(dict)
    for s in order:
        for path, kind, bits, mx in maps[s]:
            by_path[path][s] = (kind, bits, mx)

    print("\n=== popcount match 3,4,5,8,14,15,23 ===", flush=True)
    for path, per in sorted(by_path.items()):
        pops = {s: len(per[s][1]) if s in per else None for s in order}
        target = [EXPECT.get(s) for s in order if s in EXPECT]
        got = [pops.get(s) for s in order if s in EXPECT]
        if got == target:
            print(f"MATCH {path}", flush=True)
            for s in order:
                if s in per:
                    print(f"  {s}: n={len(per[s][1])} max={per[s][2]} {per[s][1]}", flush=True)
        elif all(g == t for g, t in zip(got, target) if t is not None and g is not None) and any(
            g == t for g, t in zip(got, target) if t is not None
        ):
            # partial
            if sum(1 for g, t in zip(got, target) if g == t) >= 5:
                print(f"NEAR {path} pops={got}", flush=True)
                for s in order:
                    if s in per:
                        print(f"  {s}: n={len(per[s][1])} {per[s][1]}", flush=True)

    print("\n=== max~36 or pop~36 changing across 1-7 ===", flush=True)
    for path, per in sorted(by_path.items()):
        maxes = [per[s][2] for s in order if s in per]
        pops = [len(per[s][1]) for s in order if s in per]
        if not maxes:
            continue
        mx = maxes[0]
        if mx not in (32, 34, 36, 37, 40, 48, 64) and max(pops) < 20:
            continue
        if len(set(pops)) <= 1 and max(pops) not in (36, 35, 34, 21):
            continue
        if mx and mx > 80:
            continue
        print(f"{path} max={mx} pops={[len(per[s][1]) if s in per else None for s in order]}", flush=True)
        for s in ["1", "2", "3", "4", "7"]:
            if s in per:
                print(f"  {s}: {per[s][1]}", flush=True)

    print("\n=== field_299a4b78 and neighbors slot1 ===", flush=True)
    d1 = slots.get("1") or {}
    keys = [k for k in d1 if k not in SKIP]
    if "field_299a4b78" in keys:
        i = keys.index("field_299a4b78")
        print("around 299a", keys[max(0, i - 3) : i + 8], flush=True)
    myst = d1.get("_MysteryParam")
    print("MysteryParam", {k: myst[k] for k in myst if k not in SKIP} if myst else None, flush=True)


if __name__ == "__main__":
    main()
