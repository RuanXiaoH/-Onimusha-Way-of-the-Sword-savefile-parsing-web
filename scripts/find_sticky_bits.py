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
            acc[path] = set(bits_of(obj))
            return
        for k, v in obj.items():
            if k in SKIP or str(k).endswith("_ver"):
                continue
            walk(v, f"{path}.{k}", acc)
    elif isinstance(obj, list):
        # skip huge item arrays but allow objectflags-like dict lists? objectflags is dict of bitsets
        if len(obj) <= 8:
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]", acc)


slots = {}
for user in users:
    n = slot_no(user)
    if n and user.get("Subtitle"):
        acc = {}
        walk(user["_Data"], "d", acc)
        slots[n] = acc

order = ["1", "2", "3", "4", "5", "6", "7", "9"]
s1, s2, s3, s6, s9 = slots["1"], slots["2"], slots["3"], slots["6"], slots["9"]

print("=== bits added 2->3 and still on in 6 and 9, off in 1 ===")
paths = set(s1) | set(s2) | set(s3) | set(s6) | set(s9)
hits = []
for path in sorted(paths):
    a1 = s1.get(path, set())
    a2 = s2.get(path, set())
    a3 = s3.get(path, set())
    a6 = s6.get(path, set())
    a9 = s9.get(path, set())
    added = a3 - a2
    sticky = [b for b in added if b not in a1 and b in a6 and b in a9]
    if sticky:
        hits.append((path, sticky, sorted(a1)[:12], sorted(a2)[:12], sorted(a3)[:12], sorted(a6)[:20]))

print("hit paths", len(hits))
for path, sticky, a1, a2, a3, a6 in hits:
    print(f"\n{path.replace('d.','')}")
    print(f"  sticky +{sticky}")
    print(f"  s1 {a1}")
    print(f"  s2 {a2}")
    print(f"  s3 {a3}")
    print(f"  s6 {a6}")

print("\n=== Story/Mission/Event keys ===")
# print from original
for user in users:
    if slot_no(user) == "1":
        d = user["_Data"]
        for key in ("_StoryParam", "_MissionParam", "_EventParam", "_StageStatus"):
            obj = d.get(key) or {}
            print(key, [k for k in obj if not str(k).startswith("$")])
        break
