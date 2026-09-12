import json
from pathlib import Path

parsed = json.loads(Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json").read_text(encoding="utf-8"))
users = parsed["roots"][0]["data"]["_UserSaveData"]
SKIP = {"$type", "$typeHash", "$fieldCount"}


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def find(n):
    for u in users:
        if slot_no(u) == n:
            return u
    raise SystemExit(n)


def walk(a, b, prefix, out):
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(k for k in set(a) | set(b) if k not in SKIP)
        for k in keys:
            if k not in a:
                out.append((f"{prefix}.{k}", "<missing>", summarize(b[k])))
            elif k not in b:
                out.append((f"{prefix}.{k}", summarize(a[k]), "<missing>"))
            else:
                walk(a[k], b[k], f"{prefix}.{k}" if prefix else k, out)
        return
    if isinstance(a, list) and isinstance(b, list):
        if a == b:
            return
        if a and b and isinstance(a[0], dict) and isinstance(b[0], dict):
            n = max(len(a), len(b))
            changed = 0
            for i in range(n):
                if i >= len(a) or i >= len(b) or a[i] != b[i]:
                    changed += 1
                    if changed <= 8:
                        aa = a[i] if i < len(a) else "<missing>"
                        bb = b[i] if i < len(b) else "<missing>"
                        walk(aa if isinstance(aa, (dict, list)) else {"_": aa}, bb if isinstance(bb, (dict, list)) else {"_": bb}, f"{prefix}[{i}]", out)
            if changed:
                out.append((prefix, f"list[{len(a)}] changed={changed}", f"list[{len(b)}]"))
            return
        if a != b:
            out.append((prefix, summarize(a), summarize(b)))
        return
    if a != b:
        out.append((prefix, a, b))


def summarize(v):
    if isinstance(v, list):
        return f"list[{len(v)}]"
    if isinstance(v, dict):
        return f"dict({v.get('$type', 'keys=' + str(len(v)))})"
    s = repr(v)
    return s if len(s) < 120 else s[:117] + "..."


u7, u9 = find("7"), find("9")
out = []
walk(u7.get("_Data") or {}, u9.get("_Data") or {}, "", out)
print("diff count", len(out))
for p, a, b in out:
    print(f"{p}: {a!r} -> {b!r}")

print("\n=== slot7/9 SkillOrder vs ActiveSkill ===")
for name, u in (("7", u7), ("9", u9)):
    d = u["_Data"]
    print(name, "ActiveSkill", d["_PlayerStatus"].get("ActiveSkill"))
    print(name, "SkillOrder", (d.get("_EquipGUI") or {}).get("SkillOrder"))
    print(name, "SubWeaponID", d["_PlayerStatus"].get("SubWeaponID"))
    print(name, "EquipWeaponsID", d["_PlayerStatus"].get("EquipWeaponsID"))
    print(name, "EquipBowID", d["_PlayerStatus"].get("EquipBowID"))
    print(name, "EquipEquipments", json.dumps(d.get("_EquipEquipments"), ensure_ascii=False))
