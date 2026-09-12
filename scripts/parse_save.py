"""Parse a Mandarin-decrypted Onimusha: Way of the Sword slot using REasy RSZ dump."""

from __future__ import annotations

import argparse
import json
import struct
import uuid
from pathlib import Path

TYPE_NAMES = {
    -1: "Array",
    0: "Unknown",
    1: "Enum",
    2: "Boolean",
    3: "S8",
    4: "U8",
    5: "S16",
    6: "U16",
    7: "S32",
    8: "U32",
    9: "S64",
    10: "U64",
    11: "F32",
    12: "F64",
    13: "C8",
    14: "C16",
    15: "String",
    16: "Struct",
    17: "Class",
}


def murmur3_32(data, seed=0xFFFFFFFF) -> int:
    if isinstance(data, str):
        data = data.encode("utf-8")
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h = seed & 0xFFFFFFFF
    length = len(data)
    nblocks = length // 4
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
    h ^= length
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def align(self, n: int) -> None:
        self.pos = (self.pos + n - 1) & ~(n - 1)

    def check(self, n: int) -> None:
        if self.pos + n > len(self.data):
            raise EOFError(f"need {n} bytes at 0x{self.pos:X}, remaining {self.remaining()}")

    def raw(self, n: int) -> bytes:
        self.check(n)
        b = self.data[self.pos : self.pos + n]
        self.pos += n
        return b

    def u8(self) -> int:
        return self.raw(1)[0]

    def i8(self) -> int:
        return struct.unpack("<b", self.raw(1))[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.raw(2))[0]

    def i16(self) -> int:
        return struct.unpack("<h", self.raw(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.raw(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.raw(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.raw(8))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self.raw(8))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.raw(4))[0]

    def f64(self) -> float:
        return struct.unpack("<d", self.raw(8))[0]


class TypeDb:
    def __init__(self, dump: dict, enums: dict):
        self.by_hash: dict[int, dict] = {}
        self.by_name: dict[str, dict] = {}
        for key, info in dump.items():
            try:
                h = int(key, 16)
            except ValueError:
                continue
            rec = {
                "hash": h,
                "key": key,
                "name": info.get("name") or f"type_{key}",
                "parent": info.get("parent"),
                "fields": info.get("fields") or [],
            }
            self.by_hash[h] = rec
            if rec["name"]:
                self.by_name[rec["name"]] = rec
        self.enums = enums
        self._field_maps: dict[int, dict[int, dict]] = {}
        self._global_fields: dict[int, dict] = {}
        for rec in self.by_hash.values():
            for field in rec["fields"]:
                name = field.get("name") or ""
                if name:
                    self._global_fields[murmur3_32(name)] = field

    def type_name(self, h: int) -> str:
        rec = self.by_hash.get(h)
        return rec["name"] if rec else f"unk_{h:08x}"

    def field_map(self, type_hash: int) -> dict[int, dict]:
        if type_hash in self._field_maps:
            return self._field_maps[type_hash]
        mapping: dict[int, dict] = {}
        chain = []
        rec = self.by_hash.get(type_hash)
        seen = set()
        while rec and rec["name"] not in seen:
            seen.add(rec["name"])
            chain.append(rec)
            parent = rec.get("parent")
            rec = self.by_name.get(parent) if parent else None
        # parent fields first, then child (typical RSZ)
        for rec in reversed(chain):
            fields = rec["fields"]
            for i, field in enumerate(fields):
                name = field.get("name") or ""
                mapping[murmur3_32(name)] = field
                if name.startswith("STRUCT_") and name.endswith("_v") and i + 1 < len(fields):
                    base = name[len("STRUCT_") : -2]
                    nxt = fields[i + 1].get("name") or ""
                    if nxt == f"STRUCT_{base}_m" and base:
                        mapping[murmur3_32(base)] = {
                            "name": base,
                            "packed_mandrake": True,
                            "original_type": "via.rds.Mandrake",
                            "type": "Struct",
                        }
        self._field_maps[type_hash] = mapping
        return mapping

    def field_info(self, type_hash: int, field_hash: int) -> dict:
        return self.field_map(type_hash).get(field_hash) or self._global_fields.get(field_hash) or {}

    def field_name(self, type_hash: int, field_hash: int) -> str:
        field = self.field_info(type_hash, field_hash)
        return field.get("name") or f"field_{field_hash:08x}"

    def enum_name(self, orig_type: str | None, value: int) -> str | int:
        if not orig_type:
            return value
        table = self.enums.get(orig_type)
        if not table:
            return value
        for item in table:
            if item.get("value") == value:
                return item.get("name", value)
        return value


def decode_mandrake(data: bytes) -> int | None:
    """Capcom packed int: 16 bytes {v, m} as int64le, plaintext = v / m."""
    if len(data) != 16:
        return None
    v, m = struct.unpack("<2q", data)
    if v == 0:
        return 0
    if m == 0 or v % m != 0:
        return None
    return v // m


def read_sized(r: Reader, field_type: int, size: int, packed_mandrake: bool = False):
    if size != 1:
        aligned = (r.pos + size - 1) & ~(size - 1)
        r.pos = aligned
    if field_type == 1:  # Enum
        if size == 1:
            return r.i8()
        if size == 2:
            return r.i16()
        if size == 4:
            return r.i32()
        if size == 8:
            return r.i64()
        raise ValueError(f"bad enum size {size} at 0x{r.pos:X}")
    if field_type == 2:
        return bool(r.u8())
    if field_type == 3:
        return r.i8()
    if field_type == 4:
        return r.u8()
    if field_type == 5:
        return r.i16()
    if field_type == 6:
        return r.u16()
    if field_type == 7:
        return r.i32()
    if field_type == 8:
        return r.u32()
    if field_type == 9:
        return r.i64()
    if field_type == 10:
        return r.u64()
    if field_type == 11:
        return r.f32()
    if field_type == 12:
        return r.f64()
    if field_type == 13:
        return r.u8()
    if field_type == 14:
        return r.u16()
    if field_type == 16:
        data = r.raw(size)
        if size == 16:
            if packed_mandrake:
                decoded = decode_mandrake(data)
                if decoded is not None:
                    return decoded
            return str(uuid.UUID(bytes_le=data))
        return data.hex()
    raise ValueError(f"unexpected sized type {field_type} size {size} at 0x{r.pos:X}")


def read_string(r: Reader) -> str:
    r.align(4)
    count = r.u32()
    chars = [r.u16() for _ in range(count)]
    # trim trailing utf16 null if present
    while chars and chars[-1] == 0:
        chars.pop()
    return bytes(b for c in chars for b in struct.pack("<H", c)).decode("utf-16-le", errors="replace")


def read_array(r: Reader, db: TypeDb):
    r.align(4)
    member_type = r.i32()
    member_size = r.u32()
    length = r.u32()
    array_type = r.i32()  # 0 value, 1 class
    hashes = None
    if array_type == 1:
        marker = r.u32()
        if marker == 0xFFEEFFEE:
            hashes = [r.u32() for _ in range(length)]
        else:
            r.pos -= 4
    values = []
    for i in range(length):
        if array_type == 0:
            if member_type == 15:
                values.append(read_string(r))
            else:
                values.append(read_sized(r, member_type, member_size))
        elif array_type == 1:
            values.append(read_class(r, db, hashes[i] if hashes else None))
        else:
            raise ValueError(f"bad array_type {array_type} at 0x{r.pos:X}")
    r.align(4)
    return values


def read_value(r: Reader, field_type: int, db: TypeDb, packed_mandrake: bool = False):
    if field_type == 17:
        return read_class(r, db)
    if field_type == 15:
        return read_string(r)
    if field_type == -1:
        return read_array(r, db)
    r.align(4)
    size = r.u32()
    return read_sized(r, field_type, size, packed_mandrake=packed_mandrake)


def read_field(r: Reader, db: TypeDb, owner_hash: int) -> dict:
    field_hash = r.u32()
    field_type = r.i32()
    field_info = db.field_info(owner_hash, field_hash)
    value = read_value(r, field_type, db, packed_mandrake=bool(field_info.get("packed_mandrake")))
    r.align(4)
    orig = field_info.get("original_type") or ""
    name = field_info.get("name") or f"field_{field_hash:08x}"
    if field_type in (1, 3, 5, 7, 9) and orig and orig not in ("System.Int32", "System.Int64", "System.SByte", "System.Int16"):
        if orig.startswith("app.") or orig.startswith("via.") or orig.startswith("ace.") or orig.endswith("ID"):
            value = {"value": value, "enum": db.enum_name(orig, value) if not isinstance(value, dict) else value}
    return {
        "name": name,
        "hash": f"{field_hash:08x}",
        "type": TYPE_NAMES.get(field_type, str(field_type)),
        "orig_type": orig,
        "value": value,
    }


def read_class(r: Reader, db: TypeDb, forced_hash: int | None = None) -> dict:
    num_fields = r.u32()
    type_hash = r.u32()
    if forced_hash:
        type_hash = forced_hash
    fields = [read_field(r, db, type_hash) for _ in range(num_fields)]
    obj = {f["name"]: f["value"] for f in fields}
    obj["$type"] = db.type_name(type_hash)
    obj["$typeHash"] = f"{type_hash:08x}"
    obj["$fieldCount"] = num_fields
    return obj


def parse_save(data: bytes, db: TypeDb) -> dict:
    r = Reader(data)
    roots = []
    # rust stops at len-7 to skip trailing hash-ish bytes
    end = max(0, len(data) - 7)
    while r.pos < end and r.remaining() >= 8:
        start = r.pos
        native_hash = r.u32()
        try:
            klass = read_class(r, db)
        except Exception as exc:
            raise RuntimeError(
                f"parse failed at native_hash={native_hash:08x} start=0x{start:X} pos=0x{r.pos:X}: {exc}"
            ) from exc
        roots.append(
            {
                "slotHash": f"{native_hash:08x}",
                "slotName": db.field_name(int(klass["$typeHash"], 16), native_hash),
                "data": klass,
            }
        )
        if r.pos >= end:
            break
    return {
        "rootCount": len(roots),
        "parsedBytes": r.pos,
        "fileSize": len(data),
        "unparsedTail": data[r.pos :].hex() if r.pos < len(data) else "",
        "roots": roots,
    }


def pick(obj, *path):
    cur = obj
    for key in path:
        if cur is None:
            return None
        if isinstance(cur, list):
            return None
        if isinstance(cur, dict) and "$type" in cur and key not in cur:
            return None
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return None
    return cur


def summarize(parsed: dict) -> dict:
    if not parsed["roots"]:
        return {"error": "no roots"}
    root = parsed["roots"][0]["data"]
    users = pick(root, "_UserSaveData") or []
    user = users[0] if users else {}
    data = pick(user, "_Data") or {}
    status = pick(data, "_PlayerStatus") or {}
    items = pick(data, "_Items") or []
    equips = pick(data, "_Equipments") or []
    amulets = pick(data, "_Amulets") or []
    bags = pick(data, "_MedicineBags") or []
    story = pick(data, "_StoryParam") or {}
    resource = pick(data, "_ResourceData") or {}
    return {
        "type": root.get("$type"),
        "subtitle": user.get("Subtitle"),
        "detail": user.get("Detail"),
        "selectedMissionID": story.get("SelectedMissionID"),
        "player": {
            k: status.get(k)
            for k in (
                "Health",
                "OniEnergy",
                "SoulAmountReserve",
                "SoulBoostValue",
                "JustDodgeAttackValue",
                "ActiveSkill",
                "SubWeaponID",
                "EquipBodyID",
                "EquipHeadID",
                "EquipHairID",
                "EquipGauntletID",
                "EquipCloakID",
                "EquipWeaponsID",
                "EquipBowID",
            )
        },
        "resource": {k: v for k, v in resource.items() if not str(k).startswith("$")},
        "itemCount": len(items) if isinstance(items, list) else None,
        "items": items if isinstance(items, list) else [],
        "equipmentCount": len(equips) if isinstance(equips, list) else None,
        "equipments": equips if isinstance(equips, list) else [],
        "amuletCount": len(amulets) if isinstance(amulets, list) else None,
        "amulets": amulets if isinstance(amulets, list) else [],
        "medicineBags": bags if isinstance(bags, list) else [],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--enums", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    dump = json.loads(Path(args.dump).read_text(encoding="utf-8"))
    enums = json.loads(Path(args.enums).read_text(encoding="utf-8"))
    db = TypeDb(dump, enums)
    data = Path(args.save).read_bytes()
    parsed = parse_save(data, db)
    Path(args.out).write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = summarize(parsed)
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "roots": parsed["rootCount"],
                "parsedBytes": parsed["parsedBytes"],
                "fileSize": parsed["fileSize"],
                "tailBytes": len(parsed["unparsedTail"]) // 2,
                "rootType": parsed["roots"][0]["data"].get("$type") if parsed["roots"] else None,
                "summaryFile": args.summary,
                "outFile": args.out,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
