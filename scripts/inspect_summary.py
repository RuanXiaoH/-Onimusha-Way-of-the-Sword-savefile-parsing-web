import json
from pathlib import Path

summary = json.loads(Path(r"d:\开学！\react\onimusha\data001Slot.summary.json").read_text(encoding="utf-8"))
parsed = json.loads(Path(r"d:\开学！\react\onimusha\data001Slot.parsed.json").read_text(encoding="utf-8"))

print("=== roots ===")
for i, r in enumerate(parsed["roots"]):
    data = r["data"]
    print(i, r.get("slotHash"), data.get("$type"), "fields", [k for k in data if not k.startswith("$")])

print("\n=== header ===")
for k in ("type", "subtitle", "detail", "selectedMissionID"):
    print(k, ":", summary.get(k))

print("\n=== player ===")
for k, v in (summary.get("player") or {}).items():
    print(f"  {k}: {v}")

print("\n=== resource ===")
res = summary.get("resource") or {}
for k, v in res.items():
    if isinstance(v, (int, float, str, bool)) or v is None:
        print(f"  {k}: {v}")
    elif isinstance(v, list):
        print(f"  {k}: list[{len(v)}]")
    elif isinstance(v, dict):
        print(f"  {k}: dict type={v.get('$type')} keys={[x for x in v if not str(x).startswith('$')][:12]}")

print("\n=== counts ===")
print("items", summary.get("itemCount"))
print("equipments", summary.get("equipmentCount"))
print("amulets", summary.get("amuletCount"))
print("medicineBags", len(summary.get("medicineBags") or []))

print("\n=== first 15 items ===")
for it in (summary.get("items") or [])[:15]:
    if isinstance(it, dict):
        print({k: it.get(k) for k in ("ItemID", "EquipNum", "BoxNum", "HasObtainNum", "ObtainUid", "$type")})

print("\n=== equipments ===")
for it in (summary.get("equipments") or [])[:20]:
    if isinstance(it, dict):
        print({k: it.get(k) for k in ("EquipmentID", "Exp", "TotalExp", "$type")})

print("\n=== amulets ===")
for it in (summary.get("amulets") or [])[:15]:
    if isinstance(it, dict):
        print({k: it.get(k) for k in ("SeriesId", "Flags", "EquipSlot", "IsActive", "ObtainUid", "$type")})

print("\n=== medicine bags ===")
for it in (summary.get("medicineBags") or [])[:15]:
    if isinstance(it, dict):
        print({k: it.get(k) for k in ("MedicineBagID", "Count", "IsEquiped", "$type")})
