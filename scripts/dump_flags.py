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


slots = {}
for user in users:
    n = slot_no(user)
    if n and user.get("Subtitle"):
        slots[n] = user["_Data"]

print("root keys slot1", [k for k in slots["1"] if k not in SKIP])

print("\n=== SetSwitch bits per slot ===")
prev = set()
for s in ["1", "2", "3", "4", "5", "6", "7", "9"]:
    bs = (slots[s].get("_SetSwitchParam") or {}).get("_ActiveSwitchFlag")
    cur = set(bits_of(bs))
    print(f"slot {s} n={len(cur)} +{sorted(cur-prev)} -{sorted(prev-cur)}")
    prev = cur

print("\n=== Tutorial bits ===")
prev = set()
for s in ["1", "2", "3", "4", "5", "6"]:
    bs = (slots[s].get("_Tutorial") or {}).get("_ReadFlag")
    cur = set(bits_of(bs))
    print(f"slot {s} n={len(cur)} +{sorted(cur-prev)} -{sorted(prev-cur)}")
    prev = cur

print("\n=== ItemGUI ===")
for s in ["1", "2", "3", "6"]:
    print(s, json.dumps({k: v for k, v in (slots[s].get("_ItemGUI") or {}).items() if k not in SKIP}, ensure_ascii=False)[:500])

print("\n=== unknown field_* at root ===")
for s in ["1", "2", "3", "5", "6"]:
    unk = {k: slots[s][k] for k in slots[s] if str(k).startswith("field_")}
    print(s, list(unk))
    for k, v in unk.items():
        if isinstance(v, dict) and v.get("$type") == "ace.Bitset":
            print(" ", k, bits_of(v))
        elif isinstance(v, dict):
            print(" ", k, v.get("$type"), [x for x in v if x not in SKIP][:12])
        else:
            print(" ", k, v)

print("\n=== MissionGUI / Tips bits ===")
for s in ["1", "2", "3", "4", "5", "6"]:
    m = bits_of((slots[s].get("_MissionGUI") or {}).get("_ReadFlag"))
    t = slots[s].get("_Tips") or {}
    print(s, "mission", m, "tips keys", [k for k in t if k not in SKIP])
