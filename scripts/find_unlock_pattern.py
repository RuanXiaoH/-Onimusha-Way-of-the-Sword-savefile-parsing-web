import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]
SKIP = {"$type", "$typeHash", "$fieldCount"}


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


slots = {}
for user in users:
    n = slot_no(user)
    if n and user.get("Subtitle"):
        slots[n] = user["_Data"]

order = [s for s in ["1", "2", "3", "4", "5", "6", "7", "8", "9"] if s in slots]


def bit_pop(v):
    n = 0
    for word in v.get("_Value") or []:
        if isinstance(word, int):
            n += bin(word & 0xFFFFFFFF).count("1")
    return n


def collect_ints(obj, path, acc, depth=0):
    if depth > 6:
        return
    if isinstance(obj, dict):
        if obj.get("$type") == "ace.Bitset" and "_Value" in obj:
            acc[path] = ("bit", bit_pop(obj), obj.get("_MaxElement"))
            return
        if path.endswith("SkillOrder") and isinstance(obj, list):
            acc[path] = ("list", len([x for x in obj if x]), None)
            return
        for k, v in obj.items():
            if k in SKIP:
                continue
            collect_ints(v, f"{path}.{k}", acc, depth + 1)
    elif isinstance(obj, list):
        if obj and all(isinstance(x, int) for x in obj[:20]):
            nonzero = [x for x in obj if x not in (0, 46)]
            acc[path] = ("ilist", len(nonzero), len(obj))
            return
        if len(obj) <= 30:
            for i, v in enumerate(obj):
                collect_ints(v, f"{path}[{i}]", acc, depth + 1)
        elif obj and isinstance(obj[0], dict):
            used = 0
            for v in obj:
                if not isinstance(v, dict):
                    continue
                if any(v.get(k) not in (0, None, 46, -1) for k in v if k not in SKIP):
                    used += 1
            acc[path] = ("objarr", used, len(obj))
    elif isinstance(obj, int) and obj not in (0, 1) and abs(obj) < 100000:
        acc[path] = ("int", obj, None)


# collect per slot
maps = {}
for s in order:
    acc = {}
    collect_ints(slots[s], "d", acc, 0)
    maps[s] = acc

all_paths = set()
for s in order:
    all_paths |= set(maps[s])

print("=== values matching 2,2,3 on slots 1,2,3 ===")
hits = []
for path in sorted(all_paths):
    vals = []
    kinds = []
    for s in order:
        cell = maps[s].get(path)
        if cell:
            kinds.append(cell[0])
            vals.append(cell[1])
        else:
            vals.append(None)
    if vals[0] == 2 and vals[1] == 2 and vals[2] == 3:
        hits.append((path, vals, kinds[0] if kinds else "?"))
    # also 2,2,3,4...
print("exact 2,2,3 count", len(hits))
for path, vals, kind in hits:
    print(f"  [{kind}] {path}: {vals}")

print("\n=== ints that increase 1->3 by 1 and stay >= ===")
for path in sorted(all_paths):
    vals = [maps[s].get(path, (None, None))[1] if maps[s].get(path) else None for s in order]
    if None in vals[:3]:
        continue
    if vals[0] == vals[1] and vals[2] == vals[0] + 1 and all(isinstance(v, int) for v in vals[:7]):
        print(path, vals)

print("\n=== EquipEquipments / GUI / switch ===")
for s in order:
    d = slots[s]
    eq = d.get("_EquipEquipments") or {}
    gui = d.get("_EquipGUI") or {}
    sw = d.get("_SetSwitchParam") or {}
    flag = sw.get("_ActiveSwitchFlag") or {}
    print(
        f"slot {s} SkillOrder={gui.get('SkillOrder')} Tab={gui.get('Tab')} Sort={gui.get('SortType')} "
        f"LastSub={eq.get('LastSubWeaponIndex')} SubWeapon={eq.get('SubWeapon')} "
        f"switch_pop={bit_pop(flag) if flag else None} max={flag.get('_MaxElement')}"
    )

print("\n=== cAchievement used ===")
for s in order:
    ach = slots[s].get("_Achievement") or []
    used = []
    for it in ach:
        if isinstance(it, dict) and (it.get("Count") or it.get("FixedId") not in (0, None)):
            used.append((it.get("FixedId"), it.get("Count"), {k: it[k] for k in it if k not in SKIP}))
    print(s, "n=", len(used), used[:8], "..." if len(used) > 8 else "")
