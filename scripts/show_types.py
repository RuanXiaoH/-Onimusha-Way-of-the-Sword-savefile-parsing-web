import json

p = r"d:\开学！\react\onimusha\dumps\REasy\resources\data\dumps\rszoniwots.json"
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)

names = [
    "app.savedata.cSaveDataRoot",
    "ace.cSaveDataMain",
    "app.savedata.cSystemSaveData",
    "app.savedata.cUserSaveData",
    "app.savedata.cPlayerStatus",
    "app.savedata.cSaveItem",
    "app.savedata.cUserSaveParamList",
    "app.savedata.cEquipItems",
    "app.savedata.cSaveEquipment",
    "app.savedata.cSystemSaveParamList",
    "app.savedata.cStoryParam",
    "app.savedata.cObjectFlags",
    "app.savedata.cAmuletData",
    "app.savedata.cMedicineBagParam",
    "app.savedata.cEnhancementParam",
]

by_name = {v.get("name"): (k, v) for k, v in d.items()}
for n in names:
    item = by_name.get(n)
    if not item:
        print("missing", n)
        continue
    k, v = item
    print("====", n, "key", k, "parent", v.get("parent"), "n", len(v.get("fields", [])))
    for f in v.get("fields", []):
        print(
            f"  {f.get('name'):40} {f.get('type'):12} arr={str(f.get('array')):5} {f.get('original_type', '')}"
        )
    print()
