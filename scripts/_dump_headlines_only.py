"""Dump SubMystery headlines + attributes only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _parse_gmsg import parse_gmsg

MSG = Path(
    r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm\GameDesign\Text\Export\GUI\SubMysteryText.msg.23"
)
OUT = Path(r"d:\开学！\react\onimusha\scripts\_submystery_headlines.json")

print("parsing", MSG, flush=True)
entries = parse_gmsg(MSG, verbose=False)
print("entries", len(entries), flush=True)
headlines = []
for e in entries:
    name = e["name"]
    if "_Headline_" not in name:
        continue
    headlines.append(
        {
            "index": len(headlines),
            "id": int(name.rsplit("_", 1)[-1]),
            "key": name,
            "name": e["zh"].replace("\r\n", " ").strip(),
            "guid": e["guid"],
            "attrs": e.get("attrs") or {},
        }
    )
OUT.write_text(json.dumps(headlines, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", OUT, "count", len(headlines), flush=True)
for h in headlines:
    print(f"{h['index']:02d} id={h['id']} attr={h['attrs']} {h['name']}", flush=True)
