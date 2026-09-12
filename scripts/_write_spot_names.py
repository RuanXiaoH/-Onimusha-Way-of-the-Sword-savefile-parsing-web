from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _parse_gmsg import parse_gmsg

p = Path(r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm\GameDesign\Text\Manual\GUI\MysteryBook.msg.23")
entries = parse_gmsg(p)
out = Path(r"d:\开学！\react\onimusha\scripts\_mysterybook_names.txt")
lines = [f"{e['name']}\t{e['zh']}\t{e['ja']}\t{e['en']}" for e in entries]
out.write_text("\n".join(lines), encoding="utf-8")
print(len(lines))
