import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]

WEAPON = {
    -1122577408: "二天",
    1100475904: "风卷",
    -1061520576: "地鸣",
    -1617688704: "火鸟",
    559907904: "闪空",
    -2048213632: "止水",
}
WEAPON_U = {k & 0xFFFFFFFF: v for k, v in WEAPON.items()}
HAMMER = -1061520576
SKIP = {"$type", "$typeHash", "$fieldCount"}


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def find(n):
    for u in users:
        if slot_no(u) == n:
            return u
    raise SystemExit(n)


def summarize(v, depth=0):
    if isinstance(v, dict):
        t = v.get("$type", "dict")
        if "_Value" in v:
            return f"bitset {v.get('_Value')} max={v.get('_MaxElement')}"
        keys = [k for k in v if k not in SKIP]
        return f"{t}{{{','.join(keys[:8])}{'...' if len(keys)>8 else ''}}}"
    if isinstance(v, list):
        return f"list[{len(v)}]"
    return v


def walk_hits(obj, path, hits, target_ids):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP:
                continue
            walk_hits(v, f"{path}.{k}", hits, target_ids)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if i > 80 and not isinstance(v, (int, dict)):
                continue
            walk_hits(v, f"{path}[{i}]", hits, target_ids)
    elif isinstance(obj, int):
        u = obj & 0xFFFFFFFF if obj < 0 else obj
        if obj in target_ids or u in WEAPON_U:
            hits.append((path, obj, WEAPON.get(obj) or WEAPON_U.get(u)))


def bitset_pop(v):
    if not isinstance(v, dict) or "_Value" not in v:
        return None
    n = 0
    bits = []
    for i, word in enumerate(v.get("_Value") or []):
        if not isinstance(word, int):
            continue
        n += bin(word & 0xFFFFFFFF).count("1")
        for b in range(32):
            if word & (1 << b):
                bits.append(i * 32 + b)
    return n, bits[:40], v.get("_MaxElement")


def flatten_diff(a, b, prefix, out, limit=400):
    if len(out) >= limit:
        return
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        out.append((prefix, summarize(a), summarize(b)))
        return
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(k for k in set(a) | set(b) if k not in SKIP)
        for k in keys:
            if k not in a:
                out.append((f"{prefix}.{k}", "<missing>", summarize(b[k])))
            elif k not in b:
                out.append((f"{prefix}.{k}", summarize(a[k]), "<missing>"))
            else:
                flatten_diff(a[k], b[k], f"{prefix}.{k}", out, limit)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((prefix, f"len {len(a)}", f"len {len(b)}"))
        n = min(len(a), len(b), 80)
        for i in range(n):
            flatten_diff(a[i], b[i], f"{prefix}[{i}]", out, limit)
        return
    if a != b:
        out.append((prefix, a, b))


s1, s2, s3 = find("1"), find("2"), find("3")
d1, d2, d3 = s1["_Data"], s2["_Data"], s3["_Data"]

print("=== player status 1/2/3 ===")
p1, p2, p3 = d1["_PlayerStatus"], d2["_PlayerStatus"], d3["_PlayerStatus"]
keys = sorted(k for k in set(p1) | set(p2) | set(p3) if k not in SKIP)
for k in keys:
    vals = [p1.get(k), p2.get(k), p3.get(k)]
    if vals[0] != vals[1] or vals[1] != vals[2]:
        print(f"  {k}: {vals}")

print("\n=== hammer hash locations slot1 vs slot3 ===")
for label, data in [("s1", d1), ("s2", d2), ("s3", d3)]:
    hits = []
    walk_hits(data, label, hits, set(WEAPON) | set(WEAPON_U) | {HAMMER})
    interesting = [h for h in hits if h[2] in ("地鸣", "二天", "风卷") or "Skill" in h[0] or "Equip" in h[0] or "Item" in h[0]]
    print(label, "weapon-like hits", len(hits))
    for h in hits:
        if h[2] == "地鸣" or "Skill" in h[0] or "Unlock" in h[0]:
            print(" ", h)

print("\n=== items containing weapon hashes or new in s3 ===")


def item_ids(data):
    out = []
    for i, it in enumerate(data.get("_Items") or []):
        if not isinstance(it, dict):
            continue
        iid = it.get("ItemID")
        if iid not in (0, 46, None) and (it.get("EquipNum") or it.get("BoxNum") or it.get("ObtainUid") or it.get("HasObtainNum")):
            out.append((i, iid, it.get("EquipNum"), it.get("BoxNum"), it.get("ObtainUid"), it.get("HasObtainNum")))
    return out


i1, i2, i3 = item_ids(d1), item_ids(d2), item_ids(d3)
set1 = {x[1] for x in i1}
set2 = {x[1] for x in i2}
set3 = {x[1] for x in i3}
print("new in 2 not 1", sorted(set2 - set1))
print("new in 3 not 2", sorted(set3 - set2))
print("gone 2->3", sorted(set2 - set3))
for row in i3:
    if row[1] in WEAPON or (row[1] & 0xFFFFFFFF) in WEAPON_U or row[1] in (set3 - set2):
        name = WEAPON.get(row[1]) or WEAPON_U.get(row[1] & 0xFFFFFFFF)
        print(" s3 item", row, name)

print("\n=== equipments 1/2/3 ===")


def equips(data):
    out = []
    for it in data.get("_Equipments") or []:
        eid = it.get("EquipmentID")
        val = eid.get("value") if isinstance(eid, dict) else eid
        if val or it.get("Exp") or it.get("TotalExp"):
            out.append((val, it.get("Exp"), it.get("TotalExp"), {k: it[k] for k in it if k not in SKIP and k not in ("EquipmentID", "Exp", "TotalExp")}))
    return out


for label, data in [("1", d1), ("2", d2), ("3", d3)]:
    print(label, equips(data))

print("\n=== bitsets that grow 2->3 (popcount) ===")
bit_diffs = []


def walk_bitsets(obj, path, acc):
    if isinstance(obj, dict):
        if "_Value" in obj and obj.get("$type") == "ace.Bitset":
            acc[path] = bitset_pop(obj)
            return
        for k, v in obj.items():
            if k in SKIP:
                continue
            walk_bitsets(v, f"{path}.{k}", acc)
    elif isinstance(obj, list) and len(obj) < 40:
        for i, v in enumerate(obj):
            walk_bitsets(v, f"{path}[{i}]", acc)


b2, b3 = {}, {}
walk_bitsets(d2, "s2", b2)
walk_bitsets(d3, "s3", b3)
for path in sorted(set(b2) | set(b3)):
    a = b2.get(path)
    b = b3.get(path)
    if a != b:
        ap = a[0] if a else None
        bp = b[0] if b else None
        if ap is not None and bp is not None and bp - ap <= 8:
            bits_a = set(a[1])
            bits_b = set(b[1])
            added = sorted(bits_b - bits_a)
            removed = sorted(bits_a - bits_b)
            short = path.replace("s3.", "").replace("s2.", "")
            bit_diffs.append((short, ap, bp, added, removed, a[2] if a else None))

for row in bit_diffs:
    print(f"  {row[0]}: {row[1]}->{row[2]} +{row[3]} -{row[4]} max={row[5]}")

print("\n=== shallow data key diffs 2->3 ===")
out = []
flatten_diff(d2, d3, "data", out, limit=80)
# filter noisy huge arrays
keep = []
for p, a, b in out:
    if any(x in p for x in ("_ObjectFlags", "_MapCache", "_EventParam", "_StageStatus", "_Npc", "_Dialogue", "_Mission", "PlayTime")):
        continue
    keep.append((p, a, b))
print("kept", len(keep), "of", len(out))
for row in keep[:60]:
    print(" ", row[0], ":", row[1], "->", row[2])
