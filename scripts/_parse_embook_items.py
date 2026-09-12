"""Parse EmBookData.user.3 records and count matching items in a decrypted save."""
from __future__ import annotations

import struct
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

USER = Path(
    r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm\GameDesign\DataExcel\GUI\EmBookData.user.3"
)
NAMES = {
    19292: "一目笠",
    24988: "首灯",
    13820: "棘丸",
    15548: "蛊饲",
    29399: "蛊头",
    2966: "胧乌",
    777: "亡邪",
    5586: "血儿固",
    22208: "鳍姬",
    27783: "一目将",
    3946: "百秽",
    5597: "怒伐天",
    21297: "鵺兽",
    19741: "大唾拉",
    29586: "大鵺",
    32620: "罗掌愿",
    31431: "佐佐木岩流",
    16834: "弁庆",
    28649: "酒吞童子",
    8553: "道狂",
    15401: "畏风",
    24526: "抚雷",
    1590: "源义经",
}
ORDER = ["1", "2", "3", "4", "5", "6", "7"]
EXPECT = {"1": 3, "2": 4, "3": 5, "4": 8, "5": 14, "6": 15, "7": 23}


def parse_embook(path: Path) -> list[dict]:
    data = path.read_bytes()
    recs = []
    for off in range(0, len(data) - 3, 4):
        book_id = struct.unpack_from("<i", data, off)[0]
        if book_id not in NAMES:
            continue
        enemy = struct.unpack_from("<i", data, off + 4)[0]
        item = struct.unpack_from("<i", data, off + 8)[0]
        # index is usually at off+28 (after 4x 1182817408)
        idx = None
        for rel in (28, 24, 32, 20):
            if off + rel + 4 <= len(data):
                cand = struct.unpack_from("<i", data, off + rel)[0]
                if 0 <= cand <= 22:
                    idx = cand
                    break
        recs.append(
            {
                "off": off,
                "bookId": book_id,
                "name": NAMES[book_id],
                "enemyId": enemy,
                "itemId": item,
                "index": idx,
            }
        )
    # keep first hit per bookId
    uniq = {}
    for r in recs:
        uniq.setdefault(r["bookId"], r)
    out = sorted(uniq.values(), key=lambda r: (r["index"] is None, r["index"] or 99, r["off"]))
    return out


def collect_item_ids(data_obj) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    items_h = murmur3_32("_Items")
    item_id_h = murmur3_32("ItemID")
    obtain_h = murmur3_32("HasObtainNum")
    box_h = murmur3_32("BoxNum")
    items = []
    for fh, ft, val in data_obj["fields"]:
        if fh == items_h and isinstance(val, list):
            items = val
            break
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        fields = {fh: val for fh, ft, val in it["fields"]}
        item_id = fields.get(item_id_h)
        obtain = fields.get(obtain_h)
        box = fields.get(box_h)
        if isinstance(item_id, int) and item_id not in (0, 46):
            found.setdefault(item_id, []).append(f"items[{i}] obtain={obtain} box={box}")
    return found


def main():
    recs = parse_embook(USER)
    print("EmBook records", len(recs), flush=True)
    for r in recs:
        print(
            f"  idx={r['index']} book={r['bookId']} item={r['itemId']} enemy={r['enemyId']} {r['name']}",
            flush=True,
        )
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"d:\开学！\react\onimusha\test_data\data001Slot_1045.decrypted.bin"
    )
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
            slots[n] = collect_item_ids(data_of(user))

    item_ids = [r["itemId"] for r in recs]
    print("\n=== owned by itemId ===", flush=True)
    prev = set()
    for s in ORDER:
        owned = []
        for r in recs:
            if r["itemId"] in slots[s]:
                owned.append(r)
        names = [r["name"] for r in owned]
        added = [r["name"] for r in owned if r["name"] not in prev]
        print(
            f"slot {s}: {len(owned)} expect {EXPECT[s]} +{added} {names}",
            flush=True,
        )
        prev = {r["name"] for r in owned}


if __name__ == "__main__":
    main()
