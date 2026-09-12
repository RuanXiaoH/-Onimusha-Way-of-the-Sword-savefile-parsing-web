import json
import re
import struct
import uuid
from pathlib import Path

PLAYER_KEYS = (
    "Health",
    "OniEnergy",
    "ActiveSkill",
)
EMPTY_GUID = "00000000-0000-0000-0000-000000000000"
EQUIP_MAX_RANK = 5

TAG_RE = re.compile(r"<[^>]+>")
DATA_DIR = Path(r"d:\开学！\react\onimusha\web\src\data")
COLLECTIBLES_PATH = DATA_DIR / "collectibles.json"
COLLECTIBLES = json.loads(COLLECTIBLES_PATH.read_text(encoding="utf-8")) if COLLECTIBLES_PATH.exists() else {}
ACHIEVEMENTS_PATH = DATA_DIR / "achievements.json"
ACHIEVEMENTS = json.loads(ACHIEVEMENTS_PATH.read_text(encoding="utf-8")) if ACHIEVEMENTS_PATH.exists() else {}
ENHANCEMENT_PATH = DATA_DIR / "enhancement_stages.json"
ENHANCEMENT = json.loads(ENHANCEMENT_PATH.read_text(encoding="utf-8")) if ENHANCEMENT_PATH.exists() else {}
def lantern_id_groups(ids):
    groups = []
    for item in ids or []:
        if isinstance(item, list):
            groups.append([int(x) & 0xFFFFFFFF for x in item])
        else:
            groups.append([int(item) & 0xFFFFFFFF])
    return groups


LANTERN_CHAINS = [lantern_id_groups(row.get("ids")) for row in (COLLECTIBLES.get("lanterns") or [])]


def decode_mandrake_guid(value):
    if isinstance(value, int):
        return value
    if not isinstance(value, str) or "-" not in value:
        return None
    v, m = struct.unpack("<2q", uuid.UUID(value).bytes_le)
    if v == 0:
        return 0
    if m == 0 or v % m != 0:
        return None
    return v // m


def clean_text(value):
    if not value:
        return ""
    return TAG_RE.sub("", str(value)).strip()


def amulet_used(it):
    return bool(it.get("IsActive")) or it.get("EquipSlot", -1) not in (-1, None) or it.get("ObtainUid") not in (0, None)


def bag_used(it):
    return it.get("MedicineBagID") not in (0, 46, None)


def amulet_level(it):
    lv = it.get("Level")
    parsed = 0
    if isinstance(lv, dict):
        name = str(lv.get("enum") or "")
        if name.startswith("Level"):
            digits = "".join(ch for ch in name if ch.isdigit())
            if digits:
                parsed = int(digits)
        elif isinstance(lv.get("value"), int):
            parsed = lv.get("value")
    elif isinstance(lv, int):
        parsed = lv
    return parsed if parsed > 0 else 1


def lantern_match(bag_id):
    uid = u32(bag_id)
    if uid is None:
        return None, 1
    for type_index, chain in enumerate(LANTERN_CHAINS):
        for level, ids in enumerate(chain, 1):
            if uid in ids:
                return type_index, min(level, 3)
    return None, 1


def pack_lanterns(used_bags):
    by_type = {}
    unknown = []
    for it in used_bags:
        bag_id = it.get("MedicineBagID")
        type_index, level = lantern_match(bag_id)
        rec = {
            "MedicineBagID": bag_id,
            "Count": it.get("Count") or 0,
            "IsEquiped": bool(it.get("IsEquiped")),
            "level": level,
            "typeIndex": None if type_index is None else type_index + 1,
        }
        if type_index is None:
            unknown.append(rec)
            continue
        prev = by_type.get(type_index)
        if not prev or level > prev["level"]:
            rec["IsEquiped"] = rec["IsEquiped"] or bool(prev and prev.get("IsEquiped"))
            rec["Count"] = rec["Count"] or (prev.get("Count") if prev else 0)
            by_type[type_index] = rec
        elif rec["IsEquiped"]:
            prev["IsEquiped"] = True
        elif rec["Count"] and not prev.get("Count"):
            prev["Count"] = rec["Count"]
    missing = [i for i in range(len(LANTERN_CHAINS) or 5) if i not in by_type]
    for rec in unknown:
        if not missing:
            rec["typeIndex"] = len(by_type) + 1
            by_type[len(by_type)] = rec
            continue
        type_index = missing.pop(0)
        rec["typeIndex"] = type_index + 1
        rec["level"] = 1
        by_type[type_index] = rec
    total = max(len(LANTERN_CHAINS), 5)
    packed = []
    for i in range(total):
        rec = by_type.get(i)
        if rec:
            packed.append(rec)
    return packed


def bitset_bits(bs):
    if not isinstance(bs, dict):
        return []
    out = []
    for i, word in enumerate(bs.get("_Value") or []):
        if not isinstance(word, int):
            continue
        for b in range(32):
            if word & (1 << b):
                out.append(i * 32 + b)
    return out


def u32(value):
    if value is None:
        return None
    return int(value) & 0xFFFFFFFF


def u64_value(value):
    if isinstance(value, dict):
        value = value.get("value", 0)
    try:
        return int(value) & ((1 << 64) - 1)
    except (TypeError, ValueError):
        return 0


def u64_bits(value, total=64):
    flags = u64_value(value)
    return [i for i in range(total) if flags & (1 << i)]


def mystery_catalog():
    return list(COLLECTIBLES.get("mysteries") or [])


def inventory_item_ids(items):
    out = set()
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        item_id = u32(it.get("ItemID"))
        if item_id in (None, 0, 46):
            continue
        out.add(item_id)
    return out


def mystery_owned(items):
    # 23 notes are inventory pickups (EmBook item IDs), not bit prefixes.
    owned_ids = inventory_item_ids(items)
    bits = []
    item_ids = []
    for row in mystery_catalog():
        item_id = u32(row.get("itemId"))
        if item_id is None or item_id not in owned_ids:
            continue
        bits.append(int(row.get("index") or 0))
        item_ids.append(int(row.get("itemId")))
    return bits, item_ids


def komainu_bits(data, total=36):
    # Persistent rescue flags sit after ReleasedMainMysteryFlags.
    # Bit 0-35 are the 36 statues; a filled NG+ value also sets bit 36.
    mystery = data.get("_MysteryParam") or {}
    flags = u64_bits(mystery.get("field_6858d6b7"), 64)
    return [b for b in flags if 0 <= b < total]


def unlocked_oni_ids(data, status):
    # SkillOrder is the wheel list (always 6). Unlock is sequential:
    # training-notified popcount covers the first 1-4; the 5th/6th do not
    # get extra notified bits, but their training-clear bits stay even after
    # you switch back to an earlier weapon.
    order = [s for s in ((data.get("_EquipGUI") or {}).get("SkillOrder") or []) if s not in (0, None)]
    train = data.get("_TrainingGUI") or {}
    notified = bitset_bits(train.get("_SkillTrainingNotified"))
    cleared = bitset_bits(train.get("_Cleared"))
    active = status.get("ActiveSkill")
    active_index = next((i for i, wid in enumerate(order) if u32(wid) == u32(active)), -1)
    count = len(notified)
    if active_index >= 0:
        count = max(count, active_index + 1)
    max_clear = max(cleared) if cleared else -1
    if max_clear >= 18:
        count = max(count, 6)
    elif max_clear >= 16:
        count = max(count, 5)
    count = min(max(count, 0), len(order) or 6)
    return order, order[:count], notified


def enum_int(value):
    if isinstance(value, dict):
        value = value.get("value", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def pack_achievements(parsed):
    catalog = list(ACHIEVEMENTS.get("items") or [])
    by_enum = {int(row["enumId"]): row for row in catalog if row.get("enumId") is not None}
    raw = (((parsed.get("roots") or [{}])[0].get("data") or {}).get("_SystemSaveData") or {}).get("_Data") or {}
    items = raw.get("_Achievement") or []
    packed = []
    for it in items:
        if not isinstance(it, dict):
            continue
        enum_id = enum_int(it.get("EnumId"))
        if enum_id <= 0:
            continue
        row = by_enum.get(enum_id) or {"enumId": enum_id, "name": f"成就 {enum_id}", "group": "other"}
        count = enum_int(it.get("Count"))
        target = row.get("target")
        packed.append(
            {
                "enumId": enum_id,
                "name": row.get("name"),
                "title": row.get("title"),
                "desc": row.get("desc"),
                "group": row.get("group") or "other",
                "boss": row.get("boss"),
                "place": row.get("place"),
                "unlocked": bool(it.get("IsUnlocked")),
                "count": count,
                "target": target,
            }
        )
    bosses = [row for row in packed if row.get("boss")]
    unlocked = sum(1 for row in packed if row.get("unlocked"))
    return {
        "owned": unlocked,
        "total": ACHIEVEMENTS.get("total") or max(len(packed), 52),
        "items": packed,
        "bosses": {
            "owned": sum(1 for row in bosses if row.get("unlocked")),
            "total": len(bosses) or 15,
            "items": bosses,
        },
    }


def pack_collections(data, status, amulets, bags, items=None):
    order, unlocked, notified = unlocked_oni_ids(data, status)
    displayed = bitset_bits((data.get("_MedicineBagGUI") or {}).get("_MedicineBagDisplayed"))
    mystery_bits_owned, mystery_item_ids = mystery_owned(items if items is not None else data.get("_Items"))
    komainu = komainu_bits(data)
    maps = COLLECTIBLES.get("komainuMaps") or []
    return {
        "oniWeapons": {
            "owned": len(unlocked),
            "total": 6,
            "equipped": status.get("ActiveSkill"),
            "ids": order,
            "unlockedIds": unlocked,
            "notifiedBits": notified,
        },
        "lanterns": {
            "owned": min(5, max(len([b for b in displayed if 1 <= b <= 5]), len(bags))),
            "total": 5,
            "maxLevel": 3,
            "level3": sum(1 for it in bags if (it.get("level") or 1) >= 3),
            "displayedBits": displayed,
        },
        "amulets": {
            "owned": len(amulets),
            "total": 15,
            "maxLevel": 3,
            "level3": sum(1 for it in amulets if (it.get("level") or 1) >= 3),
        },
        "mysteries": {
            "owned": len(mystery_bits_owned),
            "total": 23,
            "bits": mystery_bits_owned,
            "itemIds": mystery_item_ids,
        },
        "komainu": {
            "owned": len(komainu),
            "total": 36,
            "bits": komainu,
            "maps": maps,
        },
    }


def pack_equip_piece(level, value, kind, small_owned=0, small_total=0):
    level = max(1, min(int(level or 1), EQUIP_MAX_RANK))
    maxed = level >= EQUIP_MAX_RANK
    return {
        "level": level,
        "maxLevel": EQUIP_MAX_RANK,
        "maxed": maxed,
        "value": value,
        "kind": kind,
        "smallOwned": 0 if maxed else int(small_owned or 0),
        "smallTotal": 0 if maxed else int(small_total or 0),
    }


def split_stage_guids(ids, small_level):
    """Ordered stage list: leading GUID is the rank-up into this major rank.

    Rank 1 (small_level 0) has only small nodes.
    Rank 2–3 have 1 rank-up + N smalls.
    Rank 4 has 1 rank-up in + N smalls + 1 final rank-up to major 5.
    Filling all smalls does not raise the major rank; the extra rank-up does,
    resetting small progress to 0 of the next rank.
    """
    ids = list(ids or [])
    if not ids:
        return None, [], None
    if small_level <= 0:
        return None, ids, None
    if small_level >= 3:
        if len(ids) == 1:
            return ids[0], [], None
        return ids[0], ids[1:-1], ids[-1]
    return ids[0], ids[1:], None


def equipment_progress(activated, category):
    catalog = ((ENHANCEMENT.get("catalog") or {}).get(category) or {})
    activated = set(activated)
    parts = []
    for small in range(ENHANCEMENT.get("smallLevels") or 4):
        ids = list(catalog.get(str(small)) or [])
        rank_in, smalls, rank_out = split_stage_guids(ids, small)
        parts.append((rank_in, smalls, rank_out))

    major = 1
    current_smalls = parts[0][1] if parts else []
    for small, (rank_in, smalls, rank_out) in enumerate(parts):
        if small == 0:
            continue
        if rank_in and rank_in in activated:
            major = small + 1
            current_smalls = smalls
        else:
            break
    if parts:
        rank_out = parts[-1][2]
        if rank_out and rank_out in activated:
            return EQUIP_MAX_RANK, 0, 0
    if major >= EQUIP_MAX_RANK:
        return EQUIP_MAX_RANK, 0, 0
    owned = sum(1 for g in current_smalls if g in activated)
    return major, owned, len(current_smalls)


def equipment_ranks(data, status):
    # UI030600 显示的是大等级，不是 cad768a6 那 18 个小强化/界面位。
    activated = [
        g
        for g in (status.get("ActivatedEnhancementStage") or [])
        if g and g != EMPTY_GUID
    ]
    armor_lv, armor_small, armor_need = equipment_progress(activated, "armor")
    sword_lv, sword_small, sword_need = equipment_progress(activated, "sword")
    gaunt_lv, gaunt_small, gaunt_need = equipment_progress(activated, "gauntlet")
    return {
        "armor": pack_equip_piece(armor_lv, status.get("Health"), "health", armor_small, armor_need),
        "sword": pack_equip_piece(sword_lv, None, "attack", sword_small, sword_need),
        "gauntlet": pack_equip_piece(gaunt_lv, status.get("OniEnergy"), "oni", gaunt_small, gaunt_need),
    }


def pack_slot(user, array_index):
    data = user.get("_Data") or {}
    status = data.get("_PlayerStatus") or {}
    resource = data.get("_ResourceData") or {}
    amulets = data.get("_Amulets") or []
    bags = data.get("_MedicineBags") or []
    sub = (user.get("Subtitle") or "").split("\t")
    detail = (user.get("Detail") or "").split("\t")
    soul = resource.get("SoulAmount")
    if not isinstance(soul, int):
        soul = decode_mandrake_guid(resource.get("field_d9e97c41") or soul)
    slot_no = sub[0] if sub and sub[0] else str(array_index + 1)
    location = sub[1] if len(sub) > 1 else ""
    used_amulets = [it for it in amulets if amulet_used(it)] if isinstance(amulets, list) else []
    used_bags = [it for it in bags if bag_used(it)] if isinstance(bags, list) else []
    packed_amulets = [
        {
            "SeriesId": it.get("SeriesId"),
            "level": amulet_level(it),
            "EquipSlot": it.get("EquipSlot"),
            "IsActive": it.get("IsActive"),
            "ObtainUid": it.get("ObtainUid"),
        }
        for it in used_amulets
    ]
    packed_amulets.sort(key=lambda it: it.get("ObtainUid") or 0)
    packed_bags = pack_lanterns(used_bags)
    packed_bags.sort(key=lambda it: it.get("typeIndex") or 99)
    user_sys = data.get("_UserSystemParam") or {}
    return {
        "arrayIndex": array_index,
        "slotIndex": slot_no,
        "isAutosave": slot_no == "101",
        "location": location,
        "savedAt": detail[0] if detail else "",
        "playTime": detail[1] if len(detail) > 1 else "",
        "difficulty": clean_text(detail[2] if len(detail) > 2 else ""),
        "objective": detail[3] if len(detail) > 3 else "",
        "soulAmount": soul,
        "gameOverCount": enum_int(user_sys.get("GameOverCount")),
        "clearCount": decode_mandrake_guid(user_sys.get("field_660f397b")) or 0,
        "packFlags": enum_int(user_sys.get("Packed")),
        "player": {k: status.get(k) for k in PLAYER_KEYS},
        "equipment": equipment_ranks(data, status),
        "skillOrder": (data.get("_EquipGUI") or {}).get("SkillOrder") or [],
        "amulets": packed_amulets,
        "medicineBags": packed_bags,
        "collections": pack_collections(data, status, packed_amulets, packed_bags, data.get("_Items")),
    }


def slot_used(packed):
    return bool(packed.get("savedAt") or packed.get("objective") or packed.get("soulAmount"))


def build_display(parsed):
    users = parsed["roots"][0]["data"].get("_UserSaveData") or []
    all_slots = [pack_slot(user, i) for i, user in enumerate(users) if isinstance(user, dict)]
    slots = [s for s in all_slots if slot_used(s)]
    current = slots[0] if slots else {}
    achievements = pack_achievements(parsed)
    return {
        **current,
        "slots": slots,
        "totalSlotCapacity": len(all_slots),
        "achievements": achievements,
        "bosses": achievements.get("bosses") or {"owned": 0, "total": 15, "items": []},
    }


def main():
    parsed = json.loads(
        Path(r"d:\开学！\react\onimusha\test_data\data001Slot_1549.parsed.json").read_text(encoding="utf-8")
    )
    out = build_display(parsed)
    print(
        json.dumps(
            {
                "capacity": out.get("totalSlotCapacity"),
                "used": [
                    {
                        "slot": s["slotIndex"],
                        "location": s["location"],
                        "soul": s["soulAmount"],
                        "weapons": s["collections"]["oniWeapons"]["owned"],
                        "amulets": s["collections"]["amulets"]["owned"],
                        "lanterns": s["collections"]["lanterns"]["owned"],
                        "lanternLv": [it.get("level") for it in s.get("medicineBags") or []],
                        "amuletLv3": s["collections"]["amulets"]["level3"],
                        "gear": [
                            (s.get("equipment") or {}).get("armor", {}).get("level"),
                            (s.get("equipment") or {}).get("sword", {}).get("level"),
                            (s.get("equipment") or {}).get("gauntlet", {}).get("level"),
                        ],
                        "small": [
                            [
                                (s.get("equipment") or {}).get("armor", {}).get("smallOwned"),
                                (s.get("equipment") or {}).get("armor", {}).get("smallTotal"),
                            ],
                            [
                                (s.get("equipment") or {}).get("sword", {}).get("smallOwned"),
                                (s.get("equipment") or {}).get("sword", {}).get("smallTotal"),
                            ],
                            [
                                (s.get("equipment") or {}).get("gauntlet", {}).get("smallOwned"),
                                (s.get("equipment") or {}).get("gauntlet", {}).get("smallTotal"),
                            ],
                        ],
                        "hp": (s.get("equipment") or {}).get("armor", {}).get("value"),
                        "oni": (s.get("equipment") or {}).get("gauntlet", {}).get("value"),
                        "mysteries": s["collections"]["mysteries"]["owned"],
                    }
                    for s in out.get("slots") or []
                ],
            },
            ensure_ascii=False,
        )
    )
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    Path(r"d:\开学！\react\onimusha\scripts\_display_preview.json").write_text(payload, encoding="utf-8")
    web_json = Path(r"d:\开学！\react\onimusha\web\src\data\save.json")
    if web_json.parent.exists():
        web_json.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
