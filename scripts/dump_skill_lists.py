import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]
WEAPON = {
    -1122577408: "二天",
    1100475904: "风卷",
    -1061520576: "地鸣",
    -1617688704: "火鸟",
    559907904: "闪空",
    -2048213632: "止水",
}


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def brief_list(v):
    if not isinstance(v, list):
        return v
    named = []
    for x in v:
        if isinstance(x, int) and (x in WEAPON or (x & 0xFFFFFFFF) in {k & 0xFFFFFFFF for k in WEAPON}):
            named.append(f"{x}:{WEAPON.get(x) or WEAPON.get(x if x in WEAPON else None)}")
        elif isinstance(x, dict):
            named.append({k: x[k] for k in x if not str(k).startswith("$")})
        else:
            named.append(x)
    return named


for user in users:
    n = slot_no(user)
    if n not in {"1", "2", "3", "4", "5", "6", "7", "9"}:
        continue
    d = user["_Data"]
    p = d.get("_PlayerStatus") or {}
    extra = d.get("field_198c974a") or {}
    print(f"\n======== slot {n} ========")
    print("player extra", {k: p.get(k) for k in ("field_ff5d7ff0", "field_7b90259a", "field_617c7d68")})
    for k in ("field_98540712", "field_038be53e", "field_27a783d0", "field_801a6578"):
        v = extra.get(k)
        print(f" 198c.{k} len={len(v) if isinstance(v, list) else None}")
        print("   ", brief_list(v)[:20], ("..." if isinstance(v, list) and len(v) > 20 else ""))
    # also cad768a6
    cad = d.get("field_cad768a6") or {}
    print(" cad", {k: cad[k] for k in cad if not str(k).startswith("$") and not isinstance(cad[k], dict)})
    for k, v in cad.items():
        if str(k).startswith("$"):
            continue
        if isinstance(v, list):
            print(f" cad.{k}", brief_list(v)[:15])
        elif isinstance(v, dict) and "_Value" not in v:
            print(f" cad.{k} dict", [x for x in v if not str(x).startswith("$")])
