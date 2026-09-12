import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def all_nonzero_id_items(data):
    rows = []
    for i, it in enumerate(data.get("_Items") or []):
        if not isinstance(it, dict):
            continue
        iid = it.get("ItemID")
        if iid in (0, 46, None):
            continue
        rows.append(
            {
                "i": i,
                "id": iid,
                "eq": it.get("EquipNum"),
                "box": it.get("BoxNum"),
                "uid": it.get("ObtainUid"),
                "has": it.get("HasObtainNum"),
            }
        )
    return rows


for user in users:
    n = slot_no(user)
    if n not in {"1", "2", "3", "6"}:
        continue
    data = user["_Data"]
    rows = all_nonzero_id_items(data)
    print(f"\nslot {n} nonempty-id items {len(rows)}")
    # items with no obtain/count
    ghosts = [r for r in rows if not (r["eq"] or r["box"] or r["uid"] or r["has"])]
    print(" zero-count", ghosts)
    print(" player tips", {k: (data.get("_PlayerStatus") or {}).get(k) for k in data.get("_PlayerStatus") or {} if "Tip" in k or "Skill" in k or "Unlock" in k})
    tips = data.get("_Tips") or {}
    print(" tips unlock", (tips.get("_UnlockFlag") or {}).get("_Value"), "read", (tips.get("_AlreadyReadFlag") or {}).get("_Value"))
    notice = data.get("_NoticeStorageGUI") or {}
    print(" notice keys", [k for k in notice if not str(k).startswith("$")])
    print(" firstObtain", (notice.get("_ItemFirstObtainNotice") or {}).get("_Value"))
    extra = data.get("field_198c974a") or {}
    print(" 198c keys", [k for k in extra if not str(k).startswith("$")])
    for k, v in extra.items():
        if str(k).startswith("$"):
            continue
        if isinstance(v, dict) and "_Value" in v:
            print(f"  {k} bits value={v.get('_Value')} max={v.get('_MaxElement')}")
        else:
            print(f"  {k}={v if not isinstance(v, (dict, list)) else type(v).__name__}")

print("\n=== player status keys ===")
p = None
for user in users:
    if slot_no(user) == "1":
        p = user["_Data"]["_PlayerStatus"]
        break
print([k for k in p if not str(k).startswith("$")])
print("fieldCount", p.get("$fieldCount"))
