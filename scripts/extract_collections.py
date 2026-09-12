import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]


def popcount_list(values):
    n = 0
    for v in values or []:
        if isinstance(v, int):
            n += bin(v & 0xFFFFFFFF).count("1")
    return n


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def used_amulets(items):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if it.get("ObtainUid") not in (0, None) or it.get("IsActive") or it.get("EquipSlot", -1) not in (-1, None):
            lv = it.get("Level")
            lv_name = lv.get("enum") if isinstance(lv, dict) else lv
            out.append(
                {
                    "SeriesId": it.get("SeriesId"),
                    "Level": lv_name,
                    "EquipSlot": it.get("EquipSlot"),
                    "IsActive": it.get("IsActive"),
                    "ObtainUid": it.get("ObtainUid"),
                }
            )
    return out


def used_bags(items):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if it.get("Count") or it.get("IsEquiped"):
            out.append(
                {
                    "MedicineBagID": it.get("MedicineBagID"),
                    "Count": it.get("Count"),
                    "IsEquiped": it.get("IsEquiped"),
                }
            )
    return out


print("slot | skills | amulets | bags | mystery | record_bits | play")
for user in users:
    n = slot_no(user)
    data = user.get("_Data") or {}
    if not (user.get("Subtitle") or (data.get("_ResourceData") or {}).get("SoulAmount")):
        continue
    skills = (data.get("_EquipGUI") or {}).get("SkillOrder") or []
    amulets = used_amulets(data.get("_Amulets"))
    bags = used_bags(data.get("_MedicineBags"))
    mystery = (data.get("_MysteryParam") or {}).get("ReleasedMainMysteryFlags")
    mv = mystery.get("value") if isinstance(mystery, dict) else mystery
    rec = data.get("field_c761ca52") or {}
    read = (rec.get("_Read") or {}).get("_Value")
    detail = user.get("Detail") or ""
    print(
        f"{n:>3} skills={len(skills)} amulets={len(amulets)} bags={len(bags)} mystery={mv} rec={read} | {detail[:40]}"
    )
    print("    skills", [hex(s & 0xFFFFFFFF) for s in skills])
    print("    amulets", amulets)
    print("    bags", bags)
    extra = data.get("_MysteryParam") or {}
    print("    mystery_fields", {k: extra[k] for k in extra if not str(k).startswith("$")})
