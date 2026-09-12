"""Dump MysteryBook / EmBook / EnemyName GMSG entries."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _parse_gmsg import parse_gmsg  # noqa: E402

ROOT = Path(r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm")
FILES = [
    ROOT / r"GameDesign\Text\Manual\GUI\MysteryBook.msg.23",
    ROOT / r"GameDesign\Text\Export\GUI\EmBookDataText.msg.23",
    ROOT / r"GameDesign\Text\Export\Enemy\EnemyNameText.msg.23",
]


def main():
    for path in FILES:
        print(f"\n======== {path.name} exists={path.exists()} size={path.stat().st_size if path.exists() else 0} ========", flush=True)
        if not path.exists():
            continue
        entries = parse_gmsg(path, verbose=False)
        print("count", len(entries), flush=True)
        for e in entries:
            zh = e["zh"].replace("\r\n", " / ").replace("\n", " / ")
            if len(zh) > 60:
                zh = zh[:60] + "…"
            print(f"{e['i']:03d} hash={e['hash']:10d} {e['name'][:50]:50s} {zh}", flush=True)


if __name__ == "__main__":
    main()
