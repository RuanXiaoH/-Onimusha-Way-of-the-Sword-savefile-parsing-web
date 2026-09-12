import json
from pathlib import Path

parsed = json.loads(
    Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8")
)
users = parsed["roots"][0]["data"]["_UserSaveData"]
SKIP = {"$type", "$typeHash", "$fieldCount"}


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


def brief(obj, depth=0):
    if isinstance(obj, dict):
        if obj.get("$type") == "ace.Bitset":
            return {"bits": bits_of(obj), "max": obj.get("_MaxElement"), "raw": obj.get("_Value")}
        return {k: brief(v, depth + 1) for k, v in obj.items() if k not in SKIP and depth < 4}
    if isinstance(obj, list):
        if len(obj) > 12:
            return f"list[{len(obj)}]"
        return [brief(x, depth + 1) for x in obj]
    return obj


for user in users:
    n = slot_no(user)
    if n not in {"1", "2", "3", "4", "5", "6", "7", "9"}:
        continue
    d = user["_Data"]
    train = d.get("_TrainingGUI") or {}
    mystery = d.get("field_299a4b78")
    print(f"\n===== slot {n} TrainingGUI =====")
    print(json.dumps(brief(train), ensure_ascii=False, indent=2)[:2000])
    if n in {"1", "3", "6"}:
        print(f"----- field_299a4b78 slot {n} -----")
        print(json.dumps(brief(mystery, 0) if mystery else None, ensure_ascii=False, indent=2)[:3000])
