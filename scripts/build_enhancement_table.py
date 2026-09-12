"""Build GUID → (category, smallLevel) from PlayerGrowthParameter.user.3."""
from __future__ import annotations

import json
import struct
import uuid
from collections import defaultdict
from pathlib import Path

GROWTH_USER = Path(
    r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm\GameDesign\Action\Player\Data\Common\PlayerGrowthParameter.user.3"
)
SAVE_PARSED = Path(r"d:\开学！\react\onimusha\test_data\data001Slot_834.parsed.json")
OUT = Path(r"d:\开学！\react\onimusha\web\src\data\enhancement_stages.json")
EMPTY = "00000000-0000-0000-0000-000000000000"
# PlayerGrowthParameter 里三份 EnhancementStage 列表的顺序 =
# SaveDataHelper_EnhancementParam.CATEGORY：刀、装束、笼手。
CATEGORIES = ("sword", "armor", "gauntlet")


def activated_from_save(path: Path) -> set[str]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    users = parsed["roots"][0]["data"]["_UserSaveData"]
    out = set()
    for user in users:
        arr = ((user.get("_Data") or {}).get("_PlayerStatus") or {}).get("ActivatedEnhancementStage") or []
        for g in arr:
            if g and g != EMPTY:
                out.add(g)
    return out


def main():
    data = GROWTH_USER.read_bytes()
    known = activated_from_save(SAVE_PARSED)
    rows = []
    for g in known:
        i = data.find(uuid.UUID(g).bytes_le)
        if i < 0:
            raise SystemExit(f"missing {g}")
        level = struct.unpack_from("<i", data, i + 16)[0]
        if not 0 <= level <= 3:
            raise SystemExit(f"bad level {level} for {g}")
        rows.append({"guid": g, "offset": i, "smallLevel": level})
    rows.sort(key=lambda r: r["offset"])

    groups: list[list[dict]] = []
    cur = [rows[0]]
    for prev, item in zip(rows, rows[1:]):
        if item["offset"] - prev["offset"] > 200:
            groups.append(cur)
            cur = [item]
        else:
            cur.append(item)
    groups.append(cur)
    if len(groups) != 3:
        raise SystemExit(f"expected 3 category groups, got {len(groups)} sizes={[len(g) for g in groups]}")

    stages = {}
    catalog = {cat: {str(lv): [] for lv in range(4)} for cat in CATEGORIES}
    for cat, grp in zip(CATEGORIES, groups):
        for row in grp:
            stages[row["guid"]] = {"category": cat, "smallLevel": row["smallLevel"]}
            catalog[cat][str(row["smallLevel"])].append(row["guid"])

    payload = {
        "source": "natives/stm/GameDesign/Action/Player/Data/Common/PlayerGrowthParameter.user.3",
        "note": "大等级 1–4 对应 smallLevel 0–3 的小强化；该档小强化全部点完才进入下一档。大等级 4 的小强化全部点完即为大等级 5（满级，没有小强化）。",
        "maxLevel": 5,
        "smallLevels": 4,
        "categories": list(CATEGORIES),
        "stages": stages,
        "catalog": catalog,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", OUT, "stages", len(stages), "sizes", [len(g) for g in groups])


if __name__ == "__main__":
    main()
