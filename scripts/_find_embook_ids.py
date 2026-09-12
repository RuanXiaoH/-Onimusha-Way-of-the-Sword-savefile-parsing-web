"""Find EmBook IDs (幻魔杂记) inside each save slot."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _scan_collect_flags import (  # noqa: E402
    Reader,
    data_of,
    murmur3_32,
    read_class,
    subtitle_of,
)

# EmBookDataText_EmName_* order (23)
BOOKS = [
    (19292, "一目笠"),
    (24988, "首灯"),
    (13820, "棘丸"),
    (15548, "蛊饲"),
    (29399, "蛊头"),
    (2966, "胧乌"),
    (777, "亡邪"),
    (5586, "血儿固"),
    (22208, "鳍姬"),
    (27783, "一目将"),
    (3946, "百秽"),
    (5597, "怒伐天"),
    (21297, "鵺兽"),
    (19741, "大唾拉"),
    (29586, "大鵺"),
    (32620, "罗掌愿"),
    (31431, "佐佐木岩流"),
    (16834, "弁庆"),
    (28649, "酒吞童子"),
    (8553, "道狂"),
    (15401, "畏风"),
    (24526, "抚雷"),
    (1590, "源义经"),
]
IDS = {i for i, _ in BOOKS}
ORDER = ["1", "2", "3", "4", "5", "6", "7"]
EXPECT = {"1": 3, "2": 4, "3": 5, "4": 8, "5": 14, "6": 15, "7": 23}


def walk_ints(obj, path, acc):
    if isinstance(obj, dict) and "fields" in obj:
        for fh, ft, val in obj["fields"]:
            walk_ints(val, f"{path}.{fh:08x}", acc)
    elif isinstance(obj, list):
        if obj and all(isinstance(x, int) for x in obj):
            for i, x in enumerate(obj):
                if x in IDS:
                    acc.append((f"{path}[{i}]", x))
        else:
            for i, item in enumerate(obj):
                walk_ints(item, f"{path}[{i}]", acc)
    elif isinstance(obj, int) and obj in IDS:
        acc.append((path, obj))


def main():
    src = Path(sys.argv[1])
    data = src.read_bytes()
    r = Reader(data)
    end = max(0, len(data) - 7)
    roots = []
    while r.pos < end and r.remaining() >= 8:
        r.u32()
        roots.append(read_class(r))
    users = []
    uh = murmur3_32("_UserSaveData")
    for root in roots:
        for fh, ft, val in root["fields"]:
            if fh == uh and isinstance(val, list):
                users = val
    slots = {}
    for user in users:
        sub = subtitle_of(user)
        n = (sub.split("\t") or [""])[0]
        if n in ORDER:
            slots[n] = data_of(user)

    for s in ORDER:
        hits = []
        walk_ints(slots[s], "d", hits)
        by_id = {}
        for path, vid in hits:
            by_id.setdefault(vid, []).append(path)
        owned = [name for i, name in BOOKS if i in by_id]
        print(f"\n===== slot {s} expect {EXPECT[s]} uniqueHits={len(by_id)} names={owned} =====", flush=True)
        for i, name in BOOKS:
            if i in by_id:
                paths = by_id[i]
                print(f"  {name} {i} x{len(paths)} {paths[:6]}", flush=True)


if __name__ == "__main__":
    main()
