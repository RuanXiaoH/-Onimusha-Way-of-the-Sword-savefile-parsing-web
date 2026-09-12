import json
from pathlib import Path

parsed = json.loads(Path(r"d:\开学！\react\onimusha\data001Slot.parsed.json").read_text(encoding="utf-8"))
root = parsed["roots"][0]["data"]
print("root keys", [k for k in root if not str(k).startswith("$")])

users = root.get("_UserSaveData")
print("UserSaveData len", len(users) if isinstance(users, list) else type(users).__name__)

if isinstance(users, list):
    for i, user in enumerate(users):
        if not isinstance(user, dict):
            print(i, type(user).__name__)
            continue
        data = user.get("_Data") or {}
        res = data.get("_ResourceData") or {} if isinstance(data, dict) else {}
        soul = res.get("SoulAmount") if isinstance(res, dict) else None
        money = res.get("Money") if isinstance(res, dict) else None
        print(f"{i:02d} sub={user.get('Subtitle')!r} detail={user.get('Detail')!r} soul={soul} money={money}")

thumbs = root.get("_ThumbnailData")
print("thumbnails", len(thumbs) if isinstance(thumbs, list) else type(thumbs).__name__)
if isinstance(thumbs, list):
    for i, t in enumerate(thumbs[:25]):
        if isinstance(t, dict):
            keys = [k for k in t if not str(k).startswith("$")]
            print(f"  thumb {i} type={t.get('$type')} keys={keys[:12]}")

sysd = root.get("_SystemSaveData")
print("system", type(sysd).__name__, (sysd or {}).get("$type") if isinstance(sysd, dict) else None)
if isinstance(sysd, dict):
    for k, v in sysd.items():
        if str(k).startswith("$"):
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            print(" sys", k, v)
        elif isinstance(v, list):
            print(" sys", k, "list", len(v))
        elif isinstance(v, dict):
            inner = {x: v[x] for x in v if not str(x).startswith("$") and not isinstance(v[x], (list, dict))}
            print(" sys", k, v.get("$type"), inner)

print("root2", parsed["roots"][1]["data"].get("$type"))
r2 = parsed["roots"][1]["data"]
for k, v in r2.items():
    if str(k).startswith("$"):
        continue
    if isinstance(v, (str, int, float, bool)) or v is None:
        print(" r2", k, v)
    elif isinstance(v, list):
        print(" r2", k, "list", len(v))
