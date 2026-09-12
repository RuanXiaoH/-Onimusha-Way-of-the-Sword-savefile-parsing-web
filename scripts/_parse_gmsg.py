"""Parse RE Engine GMSG (.msg.23) and dump SubMystery names."""
from __future__ import annotations

import io
import struct
import uuid
from pathlib import Path

KEY = bytes(
    [
        0xCF,
        0xCE,
        0xFB,
        0xF8,
        0xEC,
        0x0A,
        0x33,
        0x66,
        0x93,
        0xA9,
        0x1D,
        0x93,
        0x50,
        0x39,
        0x5F,
        0x09,
    ]
)

LANG_LIST = {
    0: "Japanese",
    1: "English",
    2: "French",
    3: "Italian",
    4: "German",
    5: "Spanish",
    6: "Russian",
    7: "Polish",
    8: "Dutch",
    9: "Portuguese",
    10: "PortugueseBr",
    11: "Korean",
    12: "TraditionalChinese",
    13: "SimplifiedChinese",
    14: "Finnish",
    15: "Swedish",
    16: "Danish",
    17: "Norwegian",
    18: "Czech",
    19: "Hungarian",
    20: "Slovak",
    21: "Arabic",
    22: "Turkish",
    23: "Bulgarian",
    24: "Greek",
    25: "Romanian",
    26: "Thai",
    27: "Ukrainian",
    28: "Vietnamese",
    29: "Indonesian",
    30: "Fiction",
    31: "Hindi",
    32: "LatinAmericanSpanish",
    -1: "Unused",
}


def pad_align_up(buf: io.BytesIO, align: int) -> None:
    pos = buf.tell()
    pad = (align - pos % align) % align
    if pad:
        buf.read(pad)


def decrypt_pool(data: bytes) -> bytes:
    out = bytearray(data)
    prev = 0
    for i, cur in enumerate(data):
        out[i] = cur ^ prev ^ KEY[i & 0xF]
        prev = cur
    return bytes(out)


def wchar_pool_to_dict(wchar_pool: bytes) -> dict[int, str]:
    string_pool = wchar_pool.decode("utf-16-le")
    out: dict[int, str] = {}
    start = 0
    for i, ch in enumerate(string_pool):
        if ch == "\x00":
            out[start * 2] = string_pool[start:i]
            start = i + 1
    return out


def seek_str(offset: int, pool: dict[int, str]) -> str:
    if offset not in pool:
        return f"<missing {offset}>"
    return pool[offset]


def parse_gmsg(path: Path, verbose: bool = False) -> list[dict]:
    data = path.read_bytes()
    buf = io.BytesIO(data)
    version = struct.unpack("<I", buf.read(4))[0]
    magic = buf.read(4)
    assert magic == b"GMSG", magic
    header_off, entry_count, attr_count, lang_count = struct.unpack("<QIII", buf.read(20))
    pad_align_up(buf, 8)
    encrypt = version > 12 and version not in (0x2022033D, 0x0100010C)
    data_off = 0
    if encrypt:
        data_off = struct.unpack("<Q", buf.read(8))[0]
    unkn_off, lang_off, attr_off, attr_name_off = struct.unpack("<QQQQ", buf.read(32))
    entry_offs = [struct.unpack("<Q", buf.read(8))[0] for _ in range(entry_count)]
    if verbose:
        print(
            f"{path.name}: ver={version} entries={entry_count} attrs={attr_count} langs={lang_count} data_off={data_off}"
        )

    if unkn_off:
        buf.seek(unkn_off)
        buf.read(8)

    buf.seek(lang_off)
    langs = [struct.unpack("<i", buf.read(4))[0] for _ in range(lang_count)]
    if verbose:
        print("langs", langs)
    pad_align_up(buf, 8)

    buf.seek(attr_off)
    attr_types = [struct.unpack("<i", buf.read(4))[0] for _ in range(attr_count)]
    pad_align_up(buf, 8)

    buf.seek(attr_name_off)
    attr_name_offs = [struct.unpack("<Q", buf.read(8))[0] for _ in range(attr_count)]

    entries = []
    for eoff in entry_offs:
        buf.seek(eoff)
        guid = uuid.UUID(bytes_le=buf.read(16))
        sound_id = struct.unpack("<I", buf.read(4))[0]
        hash_or_index = struct.unpack("<I", buf.read(4))[0]
        name_off = struct.unpack("<Q", buf.read(8))[0]
        attr_val_off = struct.unpack("<Q", buf.read(8))[0]
        content_offs = [struct.unpack("<Q", buf.read(8))[0] for _ in range(lang_count)]
        entries.append(
            {
                "guid": guid,
                "sound": sound_id,
                "hash": hash_or_index,
                "name_off": name_off,
                "attr_off": attr_val_off,
                "content_offs": content_offs,
            }
        )

    raw_attrs = []
    for e in entries:
        buf.seek(e["attr_off"])
        vals = []
        for t in attr_types:
            if t in (-1, 0, 2):
                vals.append(struct.unpack("<Q", buf.read(8))[0])
            elif t == 1:
                vals.append(struct.unpack("<d", buf.read(8))[0])
            else:
                vals.append(struct.unpack("<Q", buf.read(8))[0])
        raw_attrs.append(vals)

    if encrypt:
        pool_bytes = decrypt_pool(data[data_off:])
    else:
        pool_bytes = data[data_off:]
    pool = wchar_pool_to_dict(pool_bytes)

    attr_names = [seek_str(o - data_off, pool) for o in attr_name_offs]
    if verbose:
        print("attr names", list(zip(attr_types, attr_names)))

    out = []
    zh_idx = langs.index(13) if 13 in langs else None
    ja_idx = langs.index(0) if 0 in langs else 0
    en_idx = langs.index(1) if 1 in langs else 1
    for i, e in enumerate(entries):
        name = seek_str(e["name_off"] - data_off, pool)
        texts = [seek_str(o - data_off, pool) if o else "" for o in e["content_offs"]]
        attrs = {}
        for t, an, val in zip(attr_types, attr_names, raw_attrs[i]):
            if t in (-1, 2) and isinstance(val, int):
                attrs[an or f"attr_{t}"] = seek_str(val - data_off, pool)
            else:
                attrs[an or f"attr_{t}"] = val
        rec = {
            "i": i,
            "guid": str(e["guid"]),
            "hash": e["hash"],
            "name": name,
            "zh": texts[zh_idx] if zh_idx is not None else "",
            "ja": texts[ja_idx] if ja_idx is not None else "",
            "en": texts[en_idx] if en_idx is not None else "",
            "attrs": attrs,
        }
        out.append(rec)
        if verbose:
            zh_short = rec["zh"].replace("\r\n", " / ").replace("\n", " / ")
            if len(zh_short) > 80:
                zh_short = zh_short[:80] + "…"
            print(f"{i:03d} {name:40s} {rec['guid']}  {zh_short}")
    return out


if __name__ == "__main__":
    parse_gmsg(
        Path(
            r"d:\开学！\react\onimusha\dumps\pak_sample\natives\stm\GameDesign\Text\Export\GUI\SubMysteryText.msg.23"
        ),
        verbose=True,
    )
