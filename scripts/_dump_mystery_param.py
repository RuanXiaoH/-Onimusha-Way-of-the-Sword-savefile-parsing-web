"""Dump MysteryParam + encyclopedia GUI bitsets from an already-parsed save."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKIP = {"$type", "$typeHash", "$fieldCount"}


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


def brief(v):
    if isinstance(v, dict) and v.get("$type") == "ace.Bitset":
        return {"bits": bits_of(v), "max": v.get("_MaxElement"), "n": len(bits_of(v))}
    if isinstance(v, dict) and "value" in v and isinstance(v.get("value"), int):
        bits = u64_bits(v)
        return {"value": v.get("value"), "enum": v.get("enum"), "bits": bits, "n": len(bits)}
    if isinstance(v, int):
        bits = u64_bits(v)
        return {"value": v, "bits": bits, "n": len(bits)}
    if isinstance(v, dict):
        return {k: brief(x) for k, x in v.items() if k not in SKIP}
    return v


def main():
    src = Path(sys.argv[1])
    print("load", src, flush=True)
    parsed = json.loads(src.read_text(encoding="utf-8"))
    users = parsed["roots"][0]["data"]["_UserSaveData"]
    for user in users:
        n = slot_no(user)
        if not n or not user.get("Subtitle"):
            continue
        data = user["_Data"]
        keys = [k for k in data if k not in SKIP and not str(k).endswith("_ver")]
        print(f"\n===== slot {n} {user.get('Subtitle')!r} =====", flush=True)
        if n == "1":
            print("data keys", keys, flush=True)
            if "field_299a4b78" in keys:
                i = keys.index("field_299a4b78")
                print("around 299a", keys[max(0, i - 2) : i + 6], flush=True)
        myst = data.get("_MysteryParam") or {}
        print("MysteryParam", json.dumps(brief(myst), ensure_ascii=False), flush=True)
        gui = data.get("field_299a4b78") or {}
        print("GUI299a", json.dumps(brief(gui), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
