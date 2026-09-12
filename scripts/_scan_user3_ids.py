"""Scan user.3 files for EmBook IDs and dump nearby i32s."""
from __future__ import annotations

import struct
from pathlib import Path

BOOKS = [
    19292, 24988, 13820, 15548, 29399, 2966, 777, 5586, 22208, 27783,
    3946, 5597, 21297, 19741, 29586, 32620, 31431, 16834, 28649, 8553,
    15401, 24526, 1590,
]
IDS = set(BOOKS)
ROOT = Path(r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm")
FILES = [
    ROOT / r"GameDesign\DataExcel\GUI\EmBookData.user.3",
    ROOT / r"GameDesign\DataExcel\GUI\SubMystery.user.3",
    ROOT / r"GameDesign\GUI\MysteryBook\MysteryBookList.user.3",
    ROOT / r"GameDesign\GUI\MysteryBook\MysteryBookAreaList.user.3",
    ROOT / r"GameDesign\DataExcel\Enemy\EnemyName.user.3",
    ROOT / r"GameDesign\DataExcel\GUI\MissionMystery.user.3",
]


def main():
    for path in FILES:
        data = path.read_bytes()
        print(f"\n===== {path.name} size={len(data)} =====", flush=True)
        hits = []
        for off in range(0, len(data) - 3, 4):
            v = struct.unpack_from("<i", data, off)[0]
            if v in IDS:
                hits.append((off, v))
        print("id hits", len(hits), flush=True)
        seen = set()
        for off, v in hits:
            if v in seen:
                continue
            seen.add(v)
            start = max(0, off - 32)
            nums = list(struct.unpack_from("<16i", data, start)) if start + 64 <= len(data) else []
            print(f"  first {v} @{off} around {nums}", flush=True)
        # also unique small positive i32s in data section
        rsz = data.find(b"RSZ\x00")
        uniq = []
        for off in range(rsz + 48 if rsz >= 0 else 0, len(data) - 3, 4):
            v = struct.unpack_from("<i", data, off)[0]
            if 1 <= v <= 40000:
                uniq.append(v)
        # count
        from collections import Counter
        c = Counter(uniq)
        interesting = [(n, k) for k, n in c.items() if k in IDS or (100 <= k <= 40000 and n <= 8)]
        print("interesting small ints", sorted(set(uniq))[:40], "count", len(set(uniq)), flush=True)


if __name__ == "__main__":
    main()
