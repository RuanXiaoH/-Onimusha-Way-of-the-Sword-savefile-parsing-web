"""Dump SubMystery headline names, table GUID order, and save flag bits."""
from __future__ import annotations

import json
import struct
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _parse_gmsg import parse_gmsg  # noqa: E402

ROOT = Path(r"d:\开学！\react\onimusha")
MSG = ROOT / r"dumps\pak_sample\natives\stm\GameDesign\Text\Export\GUI\SubMysteryText.msg.23"
USER = ROOT / r"dumps\pak_sample\natives\stm\GameDesign\DataExcel\GUI\SubMystery.user.3"
MSG_DIR = MSG.parent
OUT = ROOT / r"scripts\_mystery_dump.json"
PARSED = ROOT / r"test_data\data001Slot_1549.parsed.json"


def murmur3_32(data: bytes | str, seed: int = 0xFFFFFFFF) -> int:
    if isinstance(data, str):
        data = data.encode("utf-8")
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h = seed & 0xFFFFFFFF
    nblocks = len(data) // 4
    for i in range(nblocks):
        k = struct.unpack_from("<I", data, i * 4)[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail = data[nblocks * 4 :]
    k = 0
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if len(tail) >= 1:
        k ^= tail[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def u64_bits(value, total=64):
    v = value.get("value") if isinstance(value, dict) else value
    try:
        v = int(v) & ((1 << 64) - 1)
    except (TypeError, ValueError):
        return []
    return [i for i in range(total) if v & (1 << i)]


def bitset_bits(bs):
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


def dump_user3(path: Path, headlines: list[dict]) -> dict:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    data = path.read_bytes()
    info = {
        "exists": True,
        "path": str(path),
        "size": len(data),
        "head_hex": data[:80].hex(),
        "guid_hits": [],
        "instance_hashes": [],
    }
    rsz = data.find(b"RSZ\x00")
    info["rsz_off"] = rsz
    if rsz >= 0:
        ver, obj_count, inst_count, ud_count, scr_count, reserved = struct.unpack_from(
            "<IIIIII", data, rsz + 4
        )
        info["rsz"] = {
            "ver": ver,
            "obj_count": obj_count,
            "inst_count": inst_count,
            "userdata_count": ud_count,
            "script_count": scr_count,
        }
        # instance infos typically follow some tables; try common layout:
        # after 6 u32s: instanceOffset u64, dataOffset u64, scriptCount already in header
        # REasy RSZ16: after header 24 bytes from magic+4? Let's scan for known hashes.
        want = {
            murmur3_32("app.user_data.SubMystery.cData"): "cData",
            murmur3_32("app.user_data.SubMystery"): "SubMystery",
            murmur3_32("ace.user_data.ExcelUserData"): "ExcelUserData",
            murmur3_32("ace.user_data.ExcelUserData.cData"): "Excel.cData",
        }
        info["expected_hashes"] = {k: f"{v:08x}" for v, k in ((h, n) for h, n in want.items())}
        hashes_found = []
        for off in range(0, min(len(data) - 4, 20000), 4):
            h = struct.unpack_from("<I", data, off)[0]
            if h in want:
                hashes_found.append({"off": off, "hash": f"{h:08x}", "name": want[h]})
        info["hash_hits"] = hashes_found[:80]

    guid_to_head = {h["guid"]: h for h in headlines}
    for h in headlines:
        g = uuid.UUID(h["guid"]).bytes_le
        off = data.find(g)
        rec = {"id": h["id"], "name": h["zh"], "guid": h["guid"], "off": off}
        if off >= 0:
            start = max(0, off - 32)
            rec["before"] = data[start:off].hex()
            rec["after"] = data[off + 16 : off + 48].hex()
            if off >= 8:
                rec["i32_before"] = list(struct.unpack_from("<8i", data, off - 32 if off >= 32 else 0))
        info["guid_hits"].append(rec)
    found = [g for g in info["guid_hits"] if g["off"] >= 0]
    if found:
        found_sorted = sorted(found, key=lambda x: x["off"])
        info["guid_order"] = [x["name"] for x in found_sorted]
        if len(found_sorted) >= 2:
            deltas = [b["off"] - a["off"] for a, b in zip(found_sorted, found_sorted[1:])]
            info["guid_deltas"] = deltas
    return info


def dump_save_bits(path: Path) -> list[dict]:
    if not path.exists():
        return [{"error": f"missing {path}"}]
    parsed = json.loads(path.read_text(encoding="utf-8"))
    users = parsed["roots"][0]["data"]["_UserSaveData"]
    rows = []
    for user in users:
        n = slot_no(user)
        if not n or not user.get("Subtitle"):
            continue
        data = user["_Data"]
        gui = data.get("field_299a4b78") or {}
        myst = data.get("_MysteryParam") or {}
        rows.append(
            {
                "slot": n,
                "subtitle": user.get("Subtitle"),
                "gui_read": bitset_bits(gui.get("_ReadFlag")),
                "gui_keys": [k for k in gui if not str(k).startswith("$")],
                "sub": myst.get("field_6858d6b7"),
                "sub_bits": u64_bits(myst.get("field_6858d6b7"), 64),
                "main_bits": u64_bits(myst.get("ReleasedMainMysteryFlags"), 64),
                "mystery_keys": [k for k in myst if not str(k).startswith("$")],
            }
        )
    return rows


def main():
    entries = parse_gmsg(MSG, verbose=False)
    headlines = []
    for e in entries:
        name = e["name"]
        if "_Headline_" not in name:
            continue
        sid = int(name.rsplit("_", 1)[-1])
        headlines.append(
            {
                "i": e["i"],
                "id": sid,
                "guid": e["guid"],
                "zh": e["zh"].replace("\r\n", " ").strip(),
                "ja": e["ja"].replace("\r\n", " ").strip()[:80],
                "en": e["en"].replace("\r\n", " ").strip()[:80],
                "key": name,
            }
        )

    other_msg = {}
    for p in sorted(MSG_DIR.glob("*.msg.23")):
        other_msg[p.name] = p.stat().st_size

    payload = {
        "headlines": headlines,
        "headline_count": len(headlines),
        "msg_files": other_msg,
        "user3": dump_user3(USER, headlines),
        "type_hashes": {
            "app.user_data.SubMystery.cData": f"{murmur3_32('app.user_data.SubMystery.cData'):08x}",
            "app.user_data.SubMystery": f"{murmur3_32('app.user_data.SubMystery'):08x}",
        },
        "slots": dump_save_bits(PARSED),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "headlines", len(headlines), "slots", len(payload["slots"]))
    print("names:")
    for i, h in enumerate(headlines):
        print(f"  {i:02d} id={h['id']} {h['zh']}")
    u = payload["user3"]
    print("user3 exists", u.get("exists"), "size", u.get("size"), "rsz", u.get("rsz"))
    print("guid found", sum(1 for g in u.get("guid_hits", []) if g.get("off", -1) >= 0))
    if u.get("guid_order"):
        print("user3 guid order:")
        for i, n in enumerate(u["guid_order"]):
            print(f"  {i:02d} {n}")
    for s in payload["slots"]:
        print(
            f"slot {s['slot']}: gui={s['gui_read'][:40]} sub={s['sub']} sub_bits={s['sub_bits'][:40]}"
        )


if __name__ == "__main__":
    main()
