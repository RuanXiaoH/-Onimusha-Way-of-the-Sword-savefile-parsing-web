"""Dump RecordBook and late unknown fields; list slot7 bitsets with n==23."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _scan_collect_flags import (  # noqa: E402
    TYPE_BITSET,
    TYPE_MYSTERY,
    Reader,
    bits_of_words,
    bits_of_u64,
    data_of,
    murmur3_32,
    read_class,
    subtitle_of,
)

ORDER = ["1", "2", "3", "4", "5", "6", "7"]
WANT = {
    murmur3_32("_RecordBook"): "RecordBook",
    murmur3_32("_NpcParam"): "NpcParam",
    murmur3_32("_Tips"): "Tips",
    murmur3_32("_ItemGUI"): "ItemGUI",
    0xCAD768A6: "cad768a6",
    0xDEF45888: "def45888",
    0x70D830F7: "70d830f7",
    0xB9BAA74B: "b9baa74b",
    0x29E4BE6E: "NoticeStorage",
    0x299A4B78: "GUI299a",
    0x43B2CA45: "MysteryParam",
}


def dump_obj(obj, indent=0):
    pref = "  " * indent
    if not isinstance(obj, dict) or "fields" not in obj:
        return [f"{pref}{obj!r}"[:200]]
    lines = [f"{pref}type={obj.get('$typeHash'):08x} fc={obj.get('$fieldCount')}"]
    for fh, ft, val in obj["fields"]:
        if isinstance(val, dict) and val.get("$typeHash") == TYPE_BITSET:
            words, mx = [], None
            for _a, _b, sv in val["fields"]:
                if isinstance(sv, list) and sv and isinstance(sv[0], int):
                    words = sv
                elif isinstance(sv, int):
                    mx = sv
            bits = bits_of_words(words)
            lines.append(f"{pref}  {fh:08x} bitset n={len(bits)} max={mx} {bits}")
        elif isinstance(val, dict) and "fields" in val:
            lines.append(f"{pref}  {fh:08x} obj")
            lines.extend(dump_obj(val, indent + 2))
        elif isinstance(val, list) and val and all(isinstance(x, int) for x in val):
            nz = [x for x in val if x not in (0,)]
            lines.append(f"{pref}  {fh:08x} ints[{len(val)}] nz={len(nz)} {nz[:30]}")
        elif isinstance(val, list) and val and isinstance(val[0], dict):
            lines.append(f"{pref}  {fh:08x} objs[{len(val)}]")
            # summarize first object and unlock-like fields
            if len(val) <= 8:
                for i, item in enumerate(val):
                    lines.append(f"{pref}    [{i}]")
                    lines.extend(dump_obj(item, indent + 3))
        elif isinstance(val, int):
            bits = bits_of_u64(val & ((1 << 64) - 1))
            extra = f" bits={bits}" if 1 <= len(bits) <= 24 else ""
            lines.append(f"{pref}  {fh:08x} i={val}{extra}")
        else:
            lines.append(f"{pref}  {fh:08x} t{ft} {type(val).__name__}")
    return lines


def walk_bitsets(obj, path, acc):
    if isinstance(obj, dict) and "fields" in obj:
        if obj.get("$typeHash") == TYPE_BITSET:
            words, mx = [], None
            for _a, _b, sv in obj["fields"]:
                if isinstance(sv, list) and sv and isinstance(sv[0], int):
                    words = sv
                elif isinstance(sv, int):
                    mx = sv
            acc.append((path, bits_of_words(words), mx))
            return
        for fh, ft, val in obj["fields"]:
            walk_bitsets(val, f"{path}.{fh:08x}", acc)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk_bitsets(item, f"{path}[{i}]", acc)


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
        if n in ORDER:
            slots[n] = data_of(user)

    for name_h, name in WANT.items():
        print(f"\n######## {name} {name_h:08x} ########", flush=True)
        for s in ORDER:
            found = None
            for fh, ft, val in slots[s]["fields"]:
                if fh == name_h:
                    found = val
                    break
            print(f"--- slot {s} ---", flush=True)
            if found is None:
                print("  MISSING", flush=True)
            else:
                print("\n".join(dump_obj(found)), flush=True)

    print("\n######## slot7 bitsets n==23 or max in (22,23,24,36,37) ########", flush=True)
    acc = []
    walk_bitsets(slots["7"], "d", acc)
    for path, bits, mx in acc:
        if len(bits) == 23 or mx in (22, 23, 24, 35, 36, 37):
            print(f"{path} n={len(bits)} max={mx} {bits}", flush=True)

    print("\n######## all RecordBook-like across slots pops ########", flush=True)
    rec_h = murmur3_32("_RecordBook")
    for s in ORDER:
        rec = None
        for fh, ft, val in slots[s]["fields"]:
            if fh == rec_h:
                rec = val
                break
        acc = []
        if rec:
            walk_bitsets(rec, "r", acc)
        print(s, acc, flush=True)


if __name__ == "__main__":
    main()
