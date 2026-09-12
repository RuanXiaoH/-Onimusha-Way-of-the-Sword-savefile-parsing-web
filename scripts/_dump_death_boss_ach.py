"""Dump GameOverCount, achievements, story/training flags from a parsed or decrypted save."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from parse_save import TypeDb, parse_save  # noqa: E402


def bits_of(bs):
    out = []
    if not isinstance(bs, dict):
        return out
    for i, word in enumerate(bs.get("_Value") or []):
        if not isinstance(word, int):
            continue
        for b in range(32):
            if word & (1 << b):
                out.append(i * 32 + b)
    return out


def slot_no(user):
    return ((user.get("Subtitle") or "").split("\t") or [""])[0]


def load_users(path: Path):
    if path.suffix.lower() == ".json":
        parsed = json.loads(path.read_text(encoding="utf-8"))
    else:
        dump = json.loads((ROOT / "dumps/REasy/resources/data/dumps/rszoniwots.json").read_text(encoding="utf-8"))
        enums = json.loads((ROOT / "dumps/oniwots_enums.json").read_text(encoding="utf-8"))
        parsed = parse_save(path.read_bytes(), TypeDb(dump, enums))
    return parsed["roots"][0]["data"]["_UserSaveData"]


def ach_row(it, idx):
    enum = it.get("EnumId")
    if isinstance(enum, dict):
        enum = enum.get("value", enum)
    return {
        "i": idx,
        "FixedId": it.get("FixedId"),
        "EnumId": enum,
        "Count": it.get("Count"),
        "IsUnlocked": it.get("IsUnlocked"),
    }


def main():
    src = Path(sys.argv[1])
    users = load_users(src)
    print("file", src.name, "users", len(users), flush=True)
    for user in users:
        n = slot_no(user)
        if not n:
            continue
        d = user.get("_Data") or {}
        us = d.get("_UserSystemParam") or {}
        story = d.get("_StoryParam") or {}
        train = d.get("_TrainingGUI") or {}
        tut = d.get("_Tutorial") or {}
        rec = None
        for k, v in d.items():
            if isinstance(v, dict) and v.get("$type") == "app.savedata.cRecordBook":
                rec = v
                break
        ach = d.get("_Achievement") or []
        unlocked = [ach_row(it, i) for i, it in enumerate(ach) if isinstance(it, dict) and it.get("IsUnlocked")]
        counted = [
            ach_row(it, i)
            for i, it in enumerate(ach)
            if isinstance(it, dict) and (it.get("Count") or 0) not in (0, None)
        ]
        print(
            f"\n=== slot {n} {user.get('Subtitle','').split(chr(9))[1] if chr(9) in (user.get('Subtitle') or '') else ''} ===",
            flush=True,
        )
        print(
            "GameOverCount",
            us.get("GameOverCount"),
            "Packed",
            us.get("Packed"),
            "UniqueID",
            us.get("UniqueID"),
            flush=True,
        )
        print("ach total", len(ach), "unlocked", len(unlocked), "withCount", len(counted), flush=True)
        print("unlocked", [(x["i"], x["EnumId"], x["Count"]) for x in unlocked], flush=True)
        print("counts", [(x["i"], x["EnumId"], x["Count"], x["IsUnlocked"]) for x in counted], flush=True)
        print("story mission", bits_of(story.get("_MissionClearFlag")), "selected", story.get("SelectedMissionID"), flush=True)
        print("train cleared", bits_of(train.get("_Cleared")), "selected", bits_of(train.get("_Selected")), flush=True)
        print("tutorial", bits_of(tut.get("_ReadFlag")), flush=True)
        if rec:
            print("recordBook", {k: bits_of(v) if isinstance(v, dict) and "_Value" in v else v for k, v in rec.items() if not str(k).startswith("$")}, flush=True)


if __name__ == "__main__":
    main()
