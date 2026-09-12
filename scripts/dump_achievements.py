import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def bits_of(bs):
    out = []
    for i, word in enumerate((bs or {}).get("_Value") or []):
        if not isinstance(word, int):
            continue
        for b in range(32):
            if word & (1 << b):
                out.append(i * 32 + b)
    return out


print("=== achievements unlocked ===")
for user in users:
    n = slot_no(user)
    if n not in {"1", "2", "3", "5", "6"}:
        continue
    ach = user["_Data"].get("_Achievement") or []
    unlocked = []
    for it in ach:
        if isinstance(it, dict) and it.get("IsUnlocked"):
            unlocked.append((it.get("FixedId"), it.get("EnumId"), it.get("Count")))
    print(n, "unlocked", len(unlocked), unlocked[:20])

print("\n=== story mission bits per slot ===")
for user in users:
    n = slot_no(user)
    if not n or not user.get("Subtitle"):
        continue
    story = user["_Data"].get("_StoryParam") or {}
    print(
        n,
        "mission",
        bits_of(story.get("_MissionClearFlag")),
        "selected",
        story.get("SelectedMissionID"),
    )

print("\n=== AmuletGUI / MedicineBagGUI / Notice ===")
for user in users:
    n = slot_no(user)
    if n not in {"1", "2", "3", "4", "5", "6"}:
        continue
    d = user["_Data"]
    am = d.get("_AmuletGUI") or {}
    mb = d.get("_MedicineBagGUI") or {}
    nt = d.get("_NoticeStorageGUI") or {}
    print(f"\nslot {n}")
    print(" amulet", {k: am[k] if not isinstance(am[k], (dict, list)) else bits_of(am[k]) if isinstance(am[k], dict) and "_Value" in am[k] else type(am[k]).__name__ for k in am if not str(k).startswith("$")})
    print(" medgui", {k: mb[k] if not isinstance(mb[k], (dict, list)) else bits_of(mb[k]) if isinstance(mb[k], dict) and "_Value" in mb[k] else mb[k][:8] if isinstance(mb[k], list) else type(mb[k]).__name__ for k in mb if not str(k).startswith("$")})
    print(" notice ItemGet", nt.get("ItemGetNotice"))
    print(" notice Count", nt.get("ItemCountNotice"))
    print(" item 338378368 / 19861")
    for it in d.get("_Items") or []:
        if it.get("ItemID") in (338378368, 19861, 1697319168, -1773206400, -2003256576):
            print("  ", it.get("ItemID"), "eq", it.get("EquipNum"), "box", it.get("BoxNum"), "uid", it.get("ObtainUid"), "has", it.get("HasObtainNum"))
