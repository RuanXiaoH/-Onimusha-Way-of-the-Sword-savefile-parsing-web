import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def used_items(data):
    out = []
    for it in data.get("_Items") or []:
        if not isinstance(it, dict):
            continue
        iid = it.get("ItemID")
        if iid in (0, 46, None):
            continue
        if not (it.get("EquipNum") or it.get("BoxNum") or it.get("ObtainUid") or it.get("HasObtainNum")):
            continue
        out.append(it)
    return out


def nodes(data):
    arr = (data.get("_PlayerStatus") or {}).get("ActivatedNodes") or []
    return [x for x in arr if x and x != "00000000-0000-0000-0000-000000000000"]


def enhance(data):
    arr = (data.get("_PlayerStatus") or {}).get("ActivatedEnhancementStage") or []
    return [x for x in arr if x and x != "00000000-0000-0000-0000-000000000000"]


slots = {}
for user in users:
    n = slot_no(user)
    if not n or not user.get("Subtitle"):
        continue
    data = user["_Data"]
    items = used_items(data)
    slots[n] = {
        "items": {it["ItemID"]: it for it in items},
        "nodes": nodes(data),
        "enhance": enhance(data),
        "active": (data.get("_PlayerStatus") or {}).get("ActiveSkill"),
    }

order = [s for s in ["1", "2", "3", "4", "5", "6", "7", "8", "9"] if s in slots]

print("slot | items | nodes | enhance | active")
for s in order:
    d = slots[s]
    print(f"{s:>3} items={len(d['items'])} nodes={len(d['nodes'])} enhance={len(d['enhance'])} active={d['active']}")

print("\n=== item IDs first appearing per slot ===")
seen = set()
first_at = {}
for s in order:
    ids = set(slots[s]["items"])
    new = sorted(ids - seen)
    first_at[s] = new
    print(f"slot {s} new {len(new)}: {new}")
    seen |= ids

print("\n=== items present in 3+ but not 1/2 ===")
s1, s2, s3 = set(slots["1"]["items"]), set(slots["2"]["items"]), set(slots["3"]["items"])
print("in3 not 1/2", sorted(s3 - s1 - s2))
print("in2 not 1", sorted(s2 - s1))

print("\n=== HasObtainNum items by slot ===")
for s in order:
    rows = []
    for iid, it in slots[s]["items"].items():
        if it.get("HasObtainNum"):
            rows.append((iid, it.get("EquipNum"), it.get("BoxNum"), it.get("HasObtainNum"), it.get("ObtainUid")))
    print(s, rows)

print("\n=== hash-like item IDs (abs>100000) presence ===")
all_hash = set()
for s in order:
    for iid in slots[s]["items"]:
        if abs(iid) > 100000:
            all_hash.add(iid)
print("all hash items", sorted(all_hash))
for iid in sorted(all_hash):
    pres = "".join("1" if iid in slots[s]["items"] else "0" for s in order)
    it = None
    for s in order:
        if iid in slots[s]["items"]:
            it = slots[s]["items"][iid]
            break
    print(f"  {iid:12} {hex(iid & 0xFFFFFFFF)} slots={pres} obtain={it.get('HasObtainNum')} eq={it.get('EquipNum')} box={it.get('BoxNum')}")

print("\n=== ActivatedNodes first appearing ===")
seen_n = set()
for s in order:
    cur = set(slots[s]["nodes"])
    new = [x for x in slots[s]["nodes"] if x not in seen_n]
    print(f"slot {s} +{len(new)} {new}")
    seen_n |= cur

print("\n=== which new node in 3 not in 2 ===")
print(sorted(set(slots["3"]["nodes"]) - set(slots["2"]["nodes"])))
print("nodes in 2 not 3", sorted(set(slots["2"]["nodes"]) - set(slots["3"]["nodes"])))
