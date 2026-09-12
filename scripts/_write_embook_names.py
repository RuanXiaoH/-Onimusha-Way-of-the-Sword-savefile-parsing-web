from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _parse_gmsg import parse_gmsg

p = Path(r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm\GameDesign\Text\Export\GUI\EmBookDataText.msg.23")
entries = parse_gmsg(p)
out = Path(r"d:\开学！\react\onimusha\scripts\_embook_names.txt")
lines = []
for e in entries:
    if "_EmName_" in e["name"]:
        lines.append(f"{e['name']}\t{e['zh']}\t{e['ja']}\t{e['en']}")
out.write_text("\n".join(lines), encoding="utf-8")
print("wrote", out, len(lines))
