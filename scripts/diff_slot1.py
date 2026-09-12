import json
import re
from pathlib import Path

SKIP = {"$type", "$typeHash", "$fieldCount"}
TAG_RE = re.compile(r"<[^>]+>")


def load_users(path):
    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    return parsed["roots"][0]["data"].get("_UserSaveData") or []


def slot_no(user):
    sub = (user.get("Subtitle") or "").split("\t")
    return sub[0] if sub and sub[0] else ""


def find_slot(users, number="1"):
    for i, user in enumerate(users):
        if slot_no(user) == number:
            return i, user
    return 0, users[0]


def primitives(a, b, prefix=""):
    diffs = []
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        diffs.append((prefix, a, b))
        return diffs
    if isinstance(a, dict) and isinstance(b, dict):
        keys = [k for k in sorted(set(a) | set(b)) if k not in SKIP]
        for k in keys:
            if k not in a:
                diffs.append((f"{prefix}.{k}" if prefix else k, "<missing>", b[k]))
            elif k not in b:
                diffs.append((f"{prefix}.{k}" if prefix else k, a[k], "<missing>"))
            else:
                diffs.extend(primitives(a[k], b[k], f"{prefix}.{k}" if prefix else k))
        return diffs
    if isinstance(a, list) and isinstance(b, list):
        if a == b:
            return diffs
        if a and b and isinstance(a[0], dict) and isinstance(b[0], dict):
            return diffs  # handled separately for known arrays
        if len(a) != len(b) or a != b:
            diffs.append((prefix, f"list[{len(a)}]", f"list[{len(b)}]"))
        return diffs
    if a != b:
        diffs.append((prefix, a, b))
    return diffs


def item_key(it):
    return (it.get("ItemID"), it.get("ObtainUid"))


def index_items(items):
    out = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        out.setdefault(item_key(it), []).append(it)
    return out


def slim(it):
    return {k: it.get(k) for k in ("ItemID", "EquipNum", "BoxNum", "HasObtainNum", "ObtainUid") if k in it}


old_users = load_users(r"d:\开学！\react\onimusha\data001Slot.parsed.json")
new_users = load_users(r"d:\开学！\react\onimusha\data001Slot_822.parsed.json")
oi, old = find_slot(old_users, "1")
ni, new = find_slot(new_users, "1")

print("=== all slots in 822 ===")
for i, u in enumerate(new_users):
    res = ((u.get("_Data") or {}).get("_ResourceData") or {})
    print(f"{i:02d} slot={slot_no(u)!r} sub={(u.get('Subtitle') or '')!r} soul={res.get('SoulAmount')} money={res.get('Money')}")

print("\n=== slot 1 header ===")
print("old", old.get("Subtitle"), "|", old.get("Detail"))
print("new", new.get("Subtitle"), "|", new.get("Detail"))

old_data = old.get("_Data") or {}
new_data = new.get("_Data") or {}
print("\n=== player / resource primitive diffs ===")
for path in ("_PlayerStatus", "_ResourceData", "_StoryParam"):
    diffs = primitives(old_data.get(path) or {}, new_data.get(path) or {}, path)
    for p, a, b in diffs:
        if isinstance(a, (list, dict)) or isinstance(b, (list, dict)):
            continue
        print(f"  {p}: {a!r} -> {b!r}")

old_items = index_items(old_data.get("_Items"))
new_items = index_items(new_data.get("_Items"))
print("\n=== items changed ===")
keys = sorted(set(old_items) | set(new_items), key=lambda x: (x[1] or 0, x[0] or 0))
item_changes = 0
for key in keys:
    o = (old_items.get(key) or [{}])[0]
    n = (new_items.get(key) or [{}])[0]
    if key not in old_items:
        print("  +", slim(n))
        item_changes += 1
    elif key not in new_items:
        print("  -", slim(o))
        item_changes += 1
    elif slim(o) != slim(n):
        print("  ~", slim(o), "->", slim(n))
        item_changes += 1
print("item_change_count", item_changes)

print("\n=== amulets / bags / equipment counts ===")
for name in ("_Amulets", "_MedicineBags", "_Equipments"):
    print(name, "old", len(old_data.get(name) or []), "new", len(new_data.get(name) or []))

print("\n=== other top-level _Data keys with any primitive diff ===")
shown = {"_PlayerStatus", "_ResourceData", "_StoryParam", "_Items", "_Amulets", "_MedicineBags", "_Equipments"}
for k in sorted(set(old_data) | set(new_data)):
    if k in shown or str(k).startswith("$"):
        continue
    diffs = primitives(old_data.get(k), new_data.get(k), k)
    prim = [d for d in diffs if not isinstance(d[1], (list, dict)) and not isinstance(d[2], (list, dict))]
    if prim:
        print(k, "primitive_diffs", len(prim))
        for p, a, b in prim[:20]:
            sa, sb = repr(a), repr(b)
            if len(sa) > 80:
                sa = sa[:80] + "..."
            if len(sb) > 80:
                sb = sb[:80] + "..."
            print(f"  {p}: {sa} -> {sb}")
    elif diffs:
        print(k, "structural_diffs", len(diffs), "example", diffs[0][0])
