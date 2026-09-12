import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]
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


def walk(obj, path, acc):
    if isinstance(obj, dict):
        if obj.get("$type") == "ace.Bitset":
            acc.append((path, bits_of(obj), obj.get("_MaxElement")))
            return
        for k, v in obj.items():
            if k in SKIP or str(k).endswith("_ver"):
                continue
            walk(v, f"{path}.{k}", acc)
    elif isinstance(obj, list) and len(obj) < 25:
        for i, v in enumerate(obj):
            walk(v, f"{path}[{i}]", acc)


slots = {}
for user in users:
    n = slot_no(user)
    if n and user.get("Subtitle"):
        slots[n] = user["_Data"]

order = ["1", "2", "3", "4", "5", "6", "7", "9"]
maps = {s: [] for s in order}
for s in order:
    walk(slots[s], "d", maps[s])
    maps[s] = {p: (bits, mx) for p, bits, mx in maps[s]}

# focus small bitsets max<=64 and popcount <= 12
print("=== small bitsets changing 1-3 ===")
paths = set()
for s in order:
    paths |= set(maps[s])
for path in sorted(paths):
    rows = []
    maxes = []
    for s in order:
        cell = maps[s].get(path)
        if cell:
            rows.append(tuple(cell[0]))
            maxes.append(cell[1])
        else:
            rows.append(None)
    if rows[0] == rows[1] == rows[2]:
        continue
    mx = maxes[0] if maxes else 999
    if mx and mx > 96:
        continue
    pops = [len(r) if r is not None else None for r in rows]
    if all(p is None or p > 16 for p in pops[:3]):
        continue
    short = path.replace("d.", "")
    print(f"\n{short} max={mx} pops={pops}")
    for s, r in zip(order, rows):
        print(f"  {s}: {list(r) if r is not None else None}")

print("\n=== EquipItems LastIndex / ItemId ===")
for s in order:
    eq = slots[s].get("_EquipItems") or {}
    ids = [x for x in (eq.get("ItemId") or []) if x not in (0, 46)]
    print(s, "LastIndex", eq.get("LastIndex"), "ids", eq.get("ItemId"), "used", ids)
