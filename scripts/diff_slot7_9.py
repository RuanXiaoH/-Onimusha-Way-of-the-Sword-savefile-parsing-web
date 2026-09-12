import json
from pathlib import Path

PLAYER_KEYS = (
    "Health",
    "OniEnergy",
    "SoulAmountReserve",
    "SoulBoostValue",
    "JustDodgeAttackValue",
    "ActiveSkill",
    "SubWeaponID",
    "EquipBodyID",
    "EquipHeadID",
    "EquipHairID",
    "EquipGauntletID",
    "EquipCloakID",
    "EquipWeaponsID",
    "EquipBowID",
)

parsed = json.loads(Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8"))
users = parsed["roots"][0]["data"]["_UserSaveData"]


def slot_no(user):
    sub = (user.get("Subtitle") or "").split("\t")
    return sub[0] if sub and sub[0] else ""


def find(number):
    for i, user in enumerate(users):
        if slot_no(user) == number:
            return i, user
    raise SystemExit(f"missing slot {number}")


def used_equips(items):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        eid = it.get("EquipmentID")
        val = eid.get("value") if isinstance(eid, dict) else eid
        if val or it.get("Exp") or it.get("TotalExp"):
            out.append(it)
    return out


print("=== headers ===")
for i, u in enumerate(users):
    res = (u.get("_Data") or {}).get("_ResourceData") or {}
    if u.get("Subtitle") or res.get("SoulAmount"):
        print(f"{i:02d} {u.get('Subtitle')!r} | {u.get('Detail')!r} soul={res.get('SoulAmount')}")

i7, u7 = find("7")
i9, u9 = find("9")
d7 = u7["_Data"]
d9 = u9["_Data"]
p7 = d7.get("_PlayerStatus") or {}
p9 = d9.get("_PlayerStatus") or {}

print("\n=== player equip fields slot7 -> slot9 ===")
for k in PLAYER_KEYS:
    a, b = p7.get(k), p9.get(k)
    mark = "  " if a == b else "* "
    print(f"{mark}{k}: {a!r} -> {b!r}")

print("\n=== cEquipEquipments ===")
e7 = d7.get("_EquipEquipments") or d7.get("_EquipmentsParam") or {}
# search keys containing Equip
print("data7 keys with equip/weapon/sub", [k for k in d7 if "quip" in k or "eapon" in k or "Sub" in k or "Bow" in k])
print("data9 keys with equip/weapon/sub", [k for k in d9 if "quip" in k or "eapon" in k or "Sub" in k or "Bow" in k])

for key in sorted(set(d7) | set(d9)):
    if str(key).startswith("$"):
        continue
    if not any(s in key.lower() for s in ("equip", "weapon", "bow", "sub")):
        continue
    a, b = d7.get(key), d9.get(key)
    print(f"\n-- {key} --")
    print("7", json.dumps(a, ensure_ascii=False)[:800] if not isinstance(a, list) else f"list[{len(a)}]")
    print("9", json.dumps(b, ensure_ascii=False)[:800] if not isinstance(b, list) else f"list[{len(b)}]")

print("\n=== used _Equipments ===")
print("7", json.dumps(used_equips(d7.get("_Equipments")), ensure_ascii=False)[:2000])
print("9", json.dumps(used_equips(d9.get("_Equipments")), ensure_ascii=False)[:2000])
