import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_save import murmur3_32

TARGET_BAGS = {
    700669120,
    700669120 & 0xFFFFFFFF,
    (-749388992) & 0xFFFFFFFF,
    (-1014532928) & 0xFFFFFFFF,
    808782848 & 0xFFFFFFFF,
}
TARGET_SKILLS = {
    (-1122577408) & 0xFFFFFFFF,  # 二天
    1100475904 & 0xFFFFFFFF,
    (-1061520576) & 0xFFFFFFFF,
    (-1617688704) & 0xFFFFFFFF,
    559907904 & 0xFFFFFFFF,
    (-2048213632) & 0xFFFFFFFF,
}

candidates = []
for i in range(0, 16):
    candidates += [
        f"MEDICINE_BAG{i:02d}",
        f"MEDICINE_BAG{i}",
        f"MEDICINE_BAG_{i:02d}",
        f"MEDICINE_BAG_{i}",
        f"MEDICINE_BAG0{i}",
        f"SF_MEDICINE_BAG_{i:02d}",
        f"GHOST_LANTERN_{i:02d}",
        f"LANTERN_{i:02d}",
    ]
    for lv in range(0, 5):
        candidates += [
            f"MEDICINE_BAG{i:02d}_LV{lv}",
            f"MEDICINE_BAG{i:02d}_LV_{lv}",
            f"MEDICINE_BAG{i:02d}_{lv}",
            f"MEDICINE_BAG_{i:02d}_{lv}",
            f"MEDICINE_BAG{i:02d}_LEVEL{lv}",
        ]

skill_names = [
    "NITEN", "NITOU", "NITORYU", "NITOU_RYU", "DUAL_SWORD", "DUALBLADE", "FUTEN",
    "KAZEMAKI", "KAZEMARI", "FUUMAKI", "FUTABA", "FUTABA_KAZE", "WIND_SCROLL",
    "JIMEI", "CHIMEI", "DAITSUCHI", "HAMMER", "EARTH_ROAR",
    "HITORI", "KATORI", "HOUOU", "FIREBIRD", "FLUTE", "MAGIC_FLUTE",
    "SENKU", "SENKUU", "SPEAR", "FLASH",
    "SHISUI", "TOMEIZU", "TACHI", "STOP_WATER",
    "SKILL_NITEN", "SKILL1", "SKILL_1", "SKILL2", "SKILL_2",
    "PLSKILL_01", "PLSKILL_02", "PLSKILL_03", "PLSKILL_04", "PLSKILL_05", "PLSKILL_06",
    "ONI_WEAPON_01", "ONIWEAPON_01", "SUBWEAPON_01",
]
for i in range(1, 12):
    skill_names += [
        f"SKILL{i}", f"SKILL_{i:02d}", f"SKILL_{i}", f"PLSKILL_{i:02d}",
        f"PLAYER_SKILL_{i:02d}", f"EQUIP_SKILL_{i:02d}", f"ONI_SKILL_{i:02d}",
        f"WEAPON_SKILL_{i:02d}", f"GHOST_WEAPON_{i:02d}",
    ]
for jp in ["二天", "风卷", "地鸣", "火鸟", "闪空", "止水", "兩刃", "風巻"]:
    skill_names.append(jp)

def variants(name):
    out = [name, name.lower(), name.upper()]
    out += [name.encode("utf-16le"), name.encode("utf-16")]
    return out

hits = []
for name in candidates + skill_names:
    for v in variants(name) if not isinstance(name, bytes) else [name]:
        if isinstance(v, str):
            h = murmur3_32(v)
            h0 = murmur3_32(v, 0)
        else:
            h = murmur3_32(v)
            h0 = murmur3_32(v, 0)
        label = name if isinstance(name, str) else repr(name)
        if h in TARGET_BAGS or h in TARGET_SKILLS:
            hits.append((label, "seedFF", h, "bag" if h in TARGET_BAGS else "skill"))
        if h0 in TARGET_BAGS or h0 in TARGET_SKILLS:
            hits.append((label, "seed0", h0, "bag" if h0 in TARGET_BAGS else "skill"))

print("known MEDICINE_BAG00 hash", murmur3_32("MEDICINE_BAG00"), 700669120)
print("hits", len(hits))
for row in hits[:50]:
    print(row)

# dump bags/skills from save
parsed = json.loads(Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8"))
users = parsed["roots"][0]["data"]["_UserSaveData"]

def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]

for user in users:
    n = slot_no(user)
    data = user.get("_Data") or {}
    if not user.get("Subtitle"):
        continue
    bags = []
    for it in data.get("_MedicineBags") or []:
        bid = it.get("MedicineBagID")
        if bid not in (0, 46, None):
            bags.append((bid, it.get("Count"), it.get("IsEquiped"), hex(bid & 0xFFFFFFFF)))
    items = []
    for it in data.get("_Items") or []:
        iid = it.get("ItemID")
        if iid not in (0, 46, None) and (it.get("EquipNum") or it.get("BoxNum") or it.get("ObtainUid")):
            items.append(iid)
    status = data.get("_PlayerStatus") or {}
    print(f"slot {n} active={status.get('ActiveSkill')} bags={bags} item_count={len(items)}")
