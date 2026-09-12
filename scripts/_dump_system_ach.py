"""Dump system-wide Steam achievements and parse AchievementCount / Training userdata."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_save import TypeDb, parse_save  # noqa: E402
from _scan_collect_flags import Reader, read_class  # noqa: E402

ROOT = Path(r"d:\开学！\react\onimusha")

TROPHY = [
    (1, "Peerless", "解锁全部成就", "Unlock all achievements"),
    (2, "Onimusha Showdown", "击退佐佐木岩流", "Drive off Sasaki Ganryu"),
    (3, "Get Stuffed", "击败大唾拉", "Defeat Daidara"),
    (4, "Twisted Fates", "击败罗掌愿", "Defeat Rasho-gan"),
    (5, "Howling Wind", "击败畏风", "Defeat Ifuu"),
    (6, "Dokyo's Fixation", "击败大鵺", "Defeat the Greater Nue"),
    (7, "Benkei: Out, but Not Down", "击败弁庆", "Defeat Benkei"),
    (8, "Crashing Lightning", "击败抚雷", "Defeat Burai"),
    (9, "Wide Awake", "击败酒吞童子", "Defeat Shuten Doji"),
    (10, "The Perfect Storm", "击败畏风与抚雷", "Defeat Ifuu and Burai"),
    (11, "We Done Here?", "在岚山击败佐佐木岩流", "Defeat Sasaki Ganryu at Arashiyama"),
    (12, "End This Madness", "击败道狂", "Defeat Dokyo"),
    (13, "Baited by Benkei", "在莲台野击败弁庆", "Defeat Benkei at Rendaino"),
    (14, "Truly, Thank You", "击败源义经", "Defeat Minamoto no Yoshitsune"),
    (15, "Mystery Solved", "完成第一个京都奇谭", "Complete your first Mystery of Kyoto"),
    (16, "Demystified", "完成全部京都奇谭", "Complete all Mysteries of Kyoto"),
    (17, "Life-Saver", "完成第一次奇遇", "Complete your first Chance Encounter"),
    (18, "No Job Too Small", "完成全部奇遇", "Complete all Chance Encounters"),
    (19, "Serves You Right", "在清水寺击败白衣", "Defeat the Byakue at Kiyomizu-dera Temple"),
    (20, "Citizen Savior", "从幻魔手中救出30名町人", "Rescue 30 townspeople from marauding Genma"),
    (21, "Selfish Selflessness", "救出遇袭的商人", "Rescue an attacked merchant"),
    (22, "No Dog Left Behind", "救助第一只狛犬", "Rescue your first Lion Dog"),
    (23, "For the Love of Dog", "救助全部狛犬", "Rescue all the Lion Dogs"),
    (24, "Genma-ologist", "收集全部幻魔杂记", "Collect all the Genma notes"),
    (25, "True Onimusha", "在修罗难度通关", "Complete the game on Carnage"),
    (26, "Second Helping", "在Boss再战中获胜", "Beat an opponent in Boss Rematch"),
    (27, "Glutton for Punishment", "在所有难度击败全部再战Boss", "Beat all Boss Rematch opponents on every difficulty"),
    (28, "The Winding Way of the Sword", "学习并升级基础或特殊技能", "Learn and upgrade all basic or special skills"),
    (29, "Well-Rounded", "学习并升级全部技能", "Learn and upgrade all skills"),
    (30, "Looking Sharp", "首次强化装备", "Enhance equipment for the first time"),
    (31, "Dressed to Kill", "将全部装备强化至满级", "Max out all equipment"),
    (32, "Oni Armory", "获得全部鬼之武具", "Acquire all Oni Armaments"),
    (33, "Health Is Wealth", "将一个鬼灯袋强化至满级", "Fully upgrade a Hozuki Pouch"),
    (34, "Medical Marvel", "将全部鬼灯袋强化至满级", "Fully upgrade all Hozuki Pouches"),
    (35, "A Real Charmer", "将一个御守强化至满级", "Max out a charm"),
    (36, "Charmed Life", "将全部御守强化至满级", "Max out all charms"),
    (37, "Burning Blade", "在焰状态击败50名敌人", "Defeat 50 foes while in the Blazing State"),
    (38, "Stop Motion", "完成50次反射连携", "Perform 50 Reflex Combos"),
    (39, "Wielder of Oni Armaments", "用鬼之武具击败100名敌人", "Defeat 100 enemies using Oni Armaments"),
    (40, "Oni's Oni", "在鬼觉醒状态击败50名敌人", "Defeat 50 enemies in Oni Awakened state"),
    (41, "Brutalist", "打出50次一闪", "Land 50 Issen attacks"),
    (42, "Flow State", "用连锁一闪击败50名敌人", "Defeat 50 enemies with Chain Issen"),
    (43, "Silent Violence", "暗杀20名敌人", "Assassinate 20 enemies"),
    (44, "Pinch Hitter", "弹反50发投射物", "Deflect 50 projectiles"),
    (45, "Deadeye", "弓箭爆头100次", "Score 100 headshots with your bow"),
    (46, "Winning Is What Matters", "用环境物攻击50次", "Perform 50 attacks using environmental objects"),
    (47, "Untouchable", "完成50次擒拿反击", "Perform 50 Grab Reversals"),
    (48, "Coming Through!", "破防50次", "Break enemy guards 50 times"),
    (49, "Helm Splitter", "破坏100件盾或铠", "Break 100 shields or armor pieces"),
    (50, "Get This Thing Off Me", "一次吸收30魂以上", "Absorb 30+ souls at once"),
    (51, "Berserker", "用连续破防一闪击败3名敌人", "Defeat 3 enemies using continuous Break Issen"),
    (52, "Genma Griller", "同时点燃3名敌人", "Set three enemies on fire at once"),
]
TROPHY_MAP = {e: rec for e, *rec in TROPHY}


def dump_system_ach(parsed):
    ach = parsed["roots"][0]["data"]["_SystemSaveData"]["_Data"]["_Achievement"]
    unlocked = []
    counted = []
    print("system ach", len(ach))
    for i, it in enumerate(ach):
        enum = it.get("EnumId")
        if isinstance(enum, dict):
            enum = enum.get("value")
        name = TROPHY_MAP.get(enum, ("?", "未命名", ""))
        row = (enum, it.get("IsUnlocked"), it.get("Count"), name[0], name[1] if len(name) > 1 else name)
        print(f"  {i:02d} enum={enum} unlock={it.get('IsUnlocked')} count={it.get('Count')} {name[1] if isinstance(name, tuple) else name}")
        if it.get("IsUnlocked"):
            unlocked.append(enum)
        if it.get("Count"):
            counted.append((enum, it.get("Count")))
    print("unlocked enums", unlocked)
    print("counts", counted)


def dump_user3(path: Path):
    print("\n====", path, path.stat().st_size)
    data = path.read_bytes()
    r = Reader(data)
    try:
        obj = read_class(r)
        print("parsed fields", obj.get("$fieldCount"), "pos", r.pos)
        def walk(o, indent=0):
            if not isinstance(o, dict) or "fields" not in o:
                print("  " * indent, o)
                return
            print("  " * indent, f"type={o.get('$typeHash'):08x} fc={o.get('$fieldCount')}")
            for fh, ft, val in o["fields"]:
                if isinstance(val, dict) and "fields" in val:
                    print("  " * indent, f"  {fh:08x}")
                    walk(val, indent + 2)
                elif isinstance(val, list) and val and isinstance(val[0], dict):
                    print("  " * indent, f"  {fh:08x} objs[{len(val)}]")
                    for i, item in enumerate(val[:20]):
                        print("  " * indent, f"    [{i}]")
                        walk(item, indent + 3)
                elif isinstance(val, list) and val and all(isinstance(x, int) for x in val[:8]):
                    print("  " * indent, f"  {fh:08x} ints", val[:16])
                else:
                    print("  " * indent, f"  {fh:08x} t{ft}", val)
        walk(obj)
    except Exception as exc:
        print("parse fail", exc)
        print(data[:64].hex())


def exe_strings():
    data = Path(r"D:\SteamLibrary\steamapps\common\OnimushaWotS\OnimushaWotS.exe").read_bytes()
    for needle in (b"AchievementCount", b"RecordBook", b"BossRematch", b"GUITraining", b"GameOverCount"):
        print("\n--", needle)
        start = 0
        n = 0
        while n < 6:
            i = data.find(needle, start)
            if i < 0:
                break
            lo = max(0, i - 80)
            hi = min(len(data), i + 120)
            chunk = data[lo:hi]
            text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            print(hex(i), text)
            start = i + 1
            n += 1


def main():
    src = Path(sys.argv[1])
    if src.suffix == ".json":
        parsed = json.loads(src.read_text(encoding="utf-8"))
    else:
        db = TypeDb(
            json.loads((ROOT / "dumps/REasy/resources/data/dumps/rszoniwots.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "dumps/oniwots_enums.json").read_text(encoding="utf-8")),
        )
        parsed = parse_save(src.read_bytes(), db)
    dump_system_ach(parsed)
    dump_user3(ROOT / r"dumps/pak_sample/natives/stm/GameDesign/System/Achievement/AchievementCountData.user.3")
    dump_user3(ROOT / r"dumps/pak_sample/natives/stm/GameDesign/GUI/TrainingMode/GUITrainingData.user.3")
    if "--exe" in sys.argv:
        exe_strings()


if __name__ == "__main__":
    main()
