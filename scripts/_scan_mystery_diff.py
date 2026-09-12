"""Diff slots in a decrypted save to find 幻魔杂记 3/4/5/8/14/15/23."""
from __future__ import annotations

import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _scan_collect_flags import (  # noqa: E402
    TYPE_BITSET,
    Reader,
    bits_of_u64,
    bits_of_words,
    data_of,
    find_objs,
    murmur3_32,
    read_class,
    subtitle_of,
)

EXPECT = {"1": 3, "2": 4, "3": 5, "4": 8, "5": 14, "6": 15, "7": 23}
ORDER = ["1", "2", "3", "4", "5", "6", "7"]


def flatten_ints(obj, path, acc):
    if isinstance(obj, dict) and "fields" in obj:
        if obj.get("$typeHash") == TYPE_BITSET:
            words, mx = [], None
            for _fh, _ft, val in obj["fields"]:
                if isinstance(val, list) and val and isinstance(val[0], int):
                    words = val
                elif isinstance(val, int):
                    mx = val
            acc.append((path, "bitset", bits_of_words(words), mx, words))
            return
        for fh, ft, val in obj["fields"]:
            here = f"{path}.{fh:08x}"
            flatten_ints(val, here, acc)
    elif isinstance(obj, list):
        if obj and all(isinstance(x, int) for x in obj):
            acc.append((path, f"iarr{len(obj)}", obj, len(obj), obj))
            bits = bits_of_words(obj) if all(x < 2**32 for x in obj) else []
            if 1 <= len(bits) <= 40 and len(obj) <= 8:
                acc.append((path + "#asbits", "iarrbits", bits, len(obj), obj))
        elif obj and all(isinstance(x, bool) for x in obj):
            bits = [i for i, x in enumerate(obj) if x]
            acc.append((path, "barr", bits, len(obj), obj))
        else:
            for i, item in enumerate(obj[:80]):
                flatten_ints(item, f"{path}[{i}]", acc)
    elif isinstance(obj, int):
        bits = bits_of_u64(obj & ((1 << 64) - 1))
        if 1 <= len(bits) <= 40:
            acc.append((path, "int", bits, 64, obj))


def summarize_class(obj, depth=0):
    if not isinstance(obj, dict) or "fields" not in obj:
        return type(obj).__name__
    parts = []
    for fh, ft, val in obj["fields"]:
        if isinstance(val, dict) and "fields" in val:
            if val.get("$typeHash") == TYPE_BITSET:
                words, mx = [], None
                for _a, _b, sv in val["fields"]:
                    if isinstance(sv, list) and sv and isinstance(sv[0], int):
                        words = sv
                    elif isinstance(sv, int):
                        mx = sv
                parts.append(f"{fh:08x}:bs n={len(bits_of_words(words))} max={mx}")
            else:
                parts.append(f"{fh:08x}:obj t={val.get('$typeHash'):08x} fc={val.get('$fieldCount')}")
        elif isinstance(val, list):
            if val and all(isinstance(x, int) for x in val):
                parts.append(f"{fh:08x}:ints[{len(val)}]")
            elif val and isinstance(val[0], dict):
                parts.append(f"{fh:08x}:objs[{len(val)}] t={val[0].get('$typeHash', 0):08x}")
            else:
                parts.append(f"{fh:08x}:list[{len(val)}]")
        elif isinstance(val, int):
            parts.append(f"{fh:08x}:i={val}")
        elif isinstance(val, str):
            parts.append(f"{fh:08x}:s={val[:20]!r}")
        else:
            parts.append(f"{fh:08x}:{type(val).__name__}")
    return parts


def item_ids(data_obj):
    h = murmur3_32("_Items")
    for fh, ft, val in data_obj["fields"]:
        if fh == h and isinstance(val, list):
            ids = []
            id_hash = murmur3_32("ItemID")
            for it in val:
                if not isinstance(it, dict):
                    continue
                for sfh, _sft, sval in it["fields"]:
                    if sfh == id_hash and isinstance(sval, int) and sval not in (0, 46):
                        ids.append(sval)
                        break
            return ids
    return []


def main():
    src = Path(sys.argv[1])
    data = src.read_bytes()
    r = Reader(data)
    end = max(0, len(data) - 7)
    roots = []
    while r.pos < end and r.remaining() >= 8:
        r.u32()
        roots.append(read_class(r))
    users = []
    uh = murmur3_32("_UserSaveData")
    for root in roots:
        for fh, ft, val in root["fields"]:
            if fh == uh and isinstance(val, list):
                users = val
    slots = {}
    for user in users:
        sub = subtitle_of(user)
        n = (sub.split("\t") or [""])[0]
        if n in EXPECT:
            slots[n] = data_of(user)

    print("data fields slot1:", flush=True)
    for line in summarize_class(slots["1"]):
        print(" ", line, flush=True)

    acc = {s: [] for s in ORDER}
    for s in ORDER:
        flatten_ints(slots[s], "d", acc[s])

    by_path = defaultdict(dict)
    for s in ORDER:
        for path, kind, bits_or_arr, mx, raw in acc[s]:
            by_path[path][s] = (kind, bits_or_arr, mx, raw)

    print("\n=== exact pop 3,4,5,8,14,15,23 ===", flush=True)
    hits = 0
    for path, per in sorted(by_path.items()):
        pops = []
        for s in ORDER:
            if s not in per:
                pops.append(None)
                continue
            kind, val, mx, raw = per[s]
            if kind in ("bitset", "int", "iarrbits", "barr"):
                pops.append(len(val))
            elif kind.startswith("iarr"):
                pops.append(len([x for x in val if x not in (0,)]))
            else:
                pops.append(None)
        if pops == [EXPECT[s] for s in ORDER]:
            hits += 1
            print("MATCH", path, per[ORDER[0]][0], flush=True)
            for s in ORDER:
                print(f"  {s}: {per[s][1]}", flush=True)
        elif sum(1 for g, t in zip(pops, [EXPECT[s] for s in ORDER]) if g == t) >= 5:
            print("NEAR", path, pops, flush=True)
    print("hits", hits, flush=True)

    print("\n=== paths whose popcount strictly increases and slot7==23 ===", flush=True)
    for path, per in sorted(by_path.items()):
        pops = []
        vals = []
        for s in ORDER:
            if s not in per:
                pops.append(None)
                vals.append(None)
                continue
            kind, val, mx, raw = per[s]
            if kind in ("bitset", "int", "iarrbits", "barr"):
                pops.append(len(val))
                vals.append(val)
            else:
                pops.append(None)
                vals.append(val)
        if pops[-1] != 23:
            continue
        nums = [p for p in pops if p is not None]
        if nums != sorted(nums):
            continue
        if pops[0] not in (0, 1, 2, 3):
            continue
        print(path, pops, flush=True)
        for s, v in zip(ORDER, vals):
            print(f"  {s}: {v}", flush=True)

    print("\n=== ObjectFlags / unknown neighbors ===", flush=True)
    interesting = {
        murmur3_32("_ObjectFlags"),
        murmur3_32("_MapCache"),
        murmur3_32("_SetSwitchParam"),
        murmur3_32("_MysteryParam"),
        0x4FF43890,
        0xBA432551,
        0xCAD768A6,
        0xDEF45888,
        0x3ECB34DD,
        0x87FA23FF,
    }
    for s in ORDER:
        d = slots[s]
        print(f"\n-- slot {s} --", flush=True)
        for fh, ft, val in d["fields"]:
            if fh not in interesting and not (isinstance(val, dict) and val.get("$fieldCount", 0) >= 8):
                continue
            if fh == murmur3_32("_MysteryParam"):
                continue
            if isinstance(val, dict) and "fields" in val:
                print(f" {fh:08x} t={val.get('$typeHash'):08x}", summarize_class(val)[:30], flush=True)
            elif isinstance(val, list):
                print(f" {fh:08x} list {len(val)}", flush=True)

    print("\n=== item id set sizes / new ids ===", flush=True)
    prev = set()
    for s in ORDER:
        ids = set(item_ids(slots[s]))
        print(f" {s}: n={len(ids)} +{sorted(ids-prev)[:20]}", flush=True)
        prev = ids

    print("\n=== bitsets max 20-40 changing ===", flush=True)
    for path, per in sorted(by_path.items()):
        kinds = {per[s][0] for s in per}
        if "bitset" not in kinds:
            continue
        mx = next((per[s][2] for s in ORDER if s in per), None)
        pops = [len(per[s][1]) if s in per and per[s][0] == "bitset" else None for s in ORDER]
        if mx is None or mx > 64 or mx < 16:
            continue
        if len(set(p for p in pops if p is not None)) <= 1:
            continue
        print(f"{path} max={mx} pops={pops}", flush=True)


if __name__ == "__main__":
    main()
