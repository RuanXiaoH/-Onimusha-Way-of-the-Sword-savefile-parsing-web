"""Walk a decrypted native save without the RSZ dump and print collection-sized flags."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

TYPE_BITSET = 0x1CA59446
TYPE_MYSTERY = 0x540CC7AB
HASH_SUBTITLE = 0  # filled in main via murmur if needed

EXPECT = [3, 4, 5, 8, 14, 15, 23]


def murmur3_32(data, seed=0xFFFFFFFF) -> int:
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


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self):
        return len(self.data) - self.pos

    def align(self, n):
        self.pos = (self.pos + n - 1) & ~(n - 1)

    def raw(self, n):
        b = self.data[self.pos : self.pos + n]
        if len(b) < n:
            raise EOFError(f"need {n} at {self.pos:#x}")
        self.pos += n
        return b

    def u32(self):
        return struct.unpack("<I", self.raw(4))[0]

    def i32(self):
        return struct.unpack("<i", self.raw(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.raw(8))[0]


def bits_of_u64(v, total=64):
    return [i for i in range(total) if v & (1 << i)]


def bits_of_words(words):
    out = []
    for i, word in enumerate(words):
        for b in range(32):
            if word & (1 << b):
                out.append(i * 32 + b)
    return out


def read_string(r: Reader) -> str:
    r.align(4)
    count = r.u32()
    chars = [struct.unpack("<H", r.raw(2))[0] for _ in range(count)]
    while chars and chars[-1] == 0:
        chars.pop()
    return bytes(b for c in chars for b in struct.pack("<H", c)).decode("utf-16-le", errors="replace")


def read_array(r: Reader):
    r.align(4)
    member_type = r.i32()
    member_size = r.u32()
    length = r.u32()
    array_type = r.i32()
    hashes = None
    if array_type == 1:
        marker = r.u32()
        if marker == 0xFFEEFFEE:
            hashes = [r.u32() for _ in range(length)]
        else:
            r.pos -= 4
    values = []
    for _ in range(length):
        if array_type == 0:
            if member_type == 15:
                values.append(read_string(r))
            else:
                values.append(read_sized(r, member_type, member_size))
        else:
            values.append(read_class(r))
    r.align(4)
    return values


def read_sized(r: Reader, field_type: int, size: int):
    if size != 1:
        r.align(size)
    if field_type in (1, 3, 7) and size == 4:
        return struct.unpack("<i", r.raw(4))[0]
    if field_type in (1, 8) and size == 4:
        return struct.unpack("<I", r.raw(4))[0]
    if field_type in (1, 9) and size == 8:
        return struct.unpack("<q", r.raw(8))[0]
    if field_type in (1, 10) and size == 8:
        return struct.unpack("<Q", r.raw(8))[0]
    if field_type == 2 and size == 1:
        return r.raw(1)[0]
    if field_type == 11 and size == 4:
        return struct.unpack("<f", r.raw(4))[0]
    if field_type == 12 and size == 8:
        return struct.unpack("<d", r.raw(8))[0]
    if size == 4:
        return struct.unpack("<I", r.raw(4))[0]
    if size == 8:
        return struct.unpack("<Q", r.raw(8))[0]
    return r.raw(size)


def read_value(r: Reader, field_type: int):
    if field_type == 17:
        return read_class(r)
    if field_type == 15:
        return read_string(r)
    if field_type == -1:
        return read_array(r)
    r.align(4)
    size = r.u32()
    return read_sized(r, field_type, size)


def read_class(r: Reader) -> dict:
    num_fields = r.u32()
    type_hash = r.u32()
    fields = []
    for _ in range(num_fields):
        field_hash = r.u32()
        field_type = r.i32()
        value = read_value(r, field_type)
        r.align(4)
        fields.append((field_hash, field_type, value))
    return {"$typeHash": type_hash, "$fieldCount": num_fields, "fields": fields}


def walk_collect(obj, path, acc, slot_ctx):
    if not isinstance(obj, dict) or "fields" not in obj:
        return
    th = obj["$typeHash"]
    if th == TYPE_BITSET:
        words = []
        mx = None
        for fh, ft, val in obj["fields"]:
            if isinstance(val, list) and val and isinstance(val[0], int):
                words = val
            elif isinstance(val, int) and ft in (7, 8):
                mx = val
        bits = bits_of_words(words)
        acc.append((slot_ctx, f"{path}.bitset", "bitset", bits, mx))
        return
    for i, (fh, ft, val) in enumerate(obj["fields"]):
        name = f"field_{fh:08x}"
        here = f"{path}.{name}"
        if isinstance(val, dict) and "fields" in val:
            walk_collect(val, here, acc, slot_ctx)
        elif isinstance(val, list):
            for j, item in enumerate(val):
                if isinstance(item, dict) and "fields" in item:
                    walk_collect(item, f"{here}[{j}]", acc, slot_ctx)
        elif isinstance(val, int) and ft in (1, 9, 10):
            bits = bits_of_u64(val & ((1 << 64) - 1))
            if 1 <= len(bits) <= 40:
                acc.append((slot_ctx, here, f"t{ft}", bits, 64))


def mystery_dump(obj):
    if obj.get("$typeHash") != TYPE_MYSTERY:
        return None
    out = {}
    for fh, ft, val in obj["fields"]:
        if isinstance(val, int):
            bits = bits_of_u64(val & ((1 << 64) - 1))
            out[f"{fh:08x}"] = {"type": ft, "value": val, "n": len(bits), "bits": bits}
        else:
            out[f"{fh:08x}"] = {"type": ft, "kind": type(val).__name__}
    return out


def find_objs(obj, pred, out):
    if not isinstance(obj, dict) or "fields" not in obj:
        return
    if pred(obj):
        out.append(obj)
    for _fh, _ft, val in obj["fields"]:
        if isinstance(val, dict) and "fields" in val:
            find_objs(val, pred, out)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and "fields" in item:
                    find_objs(item, pred, out)


def subtitle_of(user_obj):
    h = murmur3_32("Subtitle")
    for fh, ft, val in user_obj["fields"]:
        if fh == h and isinstance(val, str):
            return val
    return ""


def data_of(user_obj):
    h = murmur3_32("_Data")
    for fh, ft, val in user_obj["fields"]:
        if fh == h:
            return val
    return None


def main():
    src = Path(sys.argv[1])
    data = src.read_bytes()
    r = Reader(data)
    end = max(0, len(data) - 7)
    roots = []
    while r.pos < end and r.remaining() >= 8:
        _native = r.u32()
        roots.append(read_class(r))
        if r.pos >= end:
            break
    print(f"parsed roots={len(roots)} pos={r.pos} size={len(data)}", flush=True)
    users_hash = murmur3_32("_UserSaveData")
    users = []
    for root in roots:
        for fh, ft, val in root["fields"]:
            if fh == users_hash and isinstance(val, list):
                users = val
    print(f"users={len(users)}", flush=True)
    acc = []
    mystery_rows = []
    gui_hash = 0x299A4B78
    for user in users:
        sub = subtitle_of(user)
        n = (sub.split("\t") or [""])[0]
        if not n or not sub:
            continue
        data_obj = data_of(user)
        if not data_obj:
            continue
        print(f"\n===== slot {n} {sub!r} =====", flush=True)
        mysts = []
        find_objs(data_obj, lambda o: o.get("$typeHash") == TYPE_MYSTERY, mysts)
        for m in mysts:
            row = mystery_dump(m)
            mystery_rows.append((n, row))
            print("MysteryParam", row, flush=True)
        # field_299a4b78 and the next few root fields
        fields = data_obj["fields"]
        names = [f"{fh:08x}" for fh, _ft, _val in fields]
        if f"{gui_hash:08x}" in names:
            i = names.index(f"{gui_hash:08x}")
            print("around 299a", names[max(0, i - 2) : i + 6], flush=True)
            gui = fields[i][2]
            if isinstance(gui, dict):
                print("GUI299a fieldCount", gui.get("$fieldCount"), "type", f"{gui.get('$typeHash'):08x}", flush=True)
                for fh, ft, val in gui["fields"]:
                    if isinstance(val, dict) and val.get("$typeHash") == TYPE_BITSET:
                        words = []
                        mx = None
                        for sfh, sft, sval in val["fields"]:
                            if isinstance(sval, list) and sval and isinstance(sval[0], int):
                                words = sval
                            elif isinstance(sval, int):
                                mx = sval
                        bits = bits_of_words(words)
                        print(f"  {fh:08x} n={len(bits)} max={mx} {bits}", flush=True)
                    elif isinstance(val, int):
                        print(f"  {fh:08x} int {val}", flush=True)
            if i + 1 < len(fields):
                nh, nt, nv = fields[i + 1]
                print(f"NEXT field {nh:08x} type={nt} kind={type(nv).__name__}", flush=True)
                if isinstance(nv, dict):
                    print("  next type", f"{nv.get('$typeHash'):08x}", "fieldCount", nv.get("$fieldCount"), flush=True)
                    for fh, ft, val in nv["fields"][:20]:
                        extra = ""
                        if isinstance(val, dict) and val.get("$typeHash") == TYPE_BITSET:
                            words = []
                            mx = None
                            for sfh, sft, sval in val["fields"]:
                                if isinstance(sval, list) and sval and isinstance(sval[0], int):
                                    words = sval
                                elif isinstance(sval, int):
                                    mx = sval
                            bits = bits_of_words(words)
                            extra = f" bitset n={len(bits)} max={mx} {bits}"
                        elif isinstance(val, int):
                            bits = bits_of_u64(val & ((1 << 64) - 1))
                            extra = f" int n={len(bits)} {bits[:24]}"
                        print(f"    {fh:08x} t{ft}{extra}", flush=True)
        walk_collect(data_obj, "d", acc, n)

    by_path = {}
    for slot, path, kind, bits, mx in acc:
        by_path.setdefault(path, {})[slot] = (kind, bits, mx)
    order = [str(i) for i in range(1, 13)]
    print("\n=== popcount match 3,4,5,8,14,15,23 ===", flush=True)
    for path, per in sorted(by_path.items()):
        got = [len(per[s][1]) if s in per else None for s in ["1", "2", "3", "4", "5", "6", "7"]]
        if got == EXPECT:
            print("MATCH", path, flush=True)
            for s in ["1", "2", "3", "4", "5", "6", "7"]:
                if s in per:
                    print(f"  {s}: n={len(per[s][1])} {per[s][1]}", flush=True)
        elif sum(1 for g, t in zip(got, EXPECT) if g == t) >= 5:
            print("NEAR", path, "pops", got, flush=True)
            for s in ["1", "2", "3", "4", "5", "6", "7"]:
                if s in per:
                    print(f"  {s}: n={len(per[s][1])} {per[s][1]}", flush=True)

    print("\n=== MysteryParam extras across slots ===", flush=True)
    keys = set()
    for _n, row in mystery_rows:
        keys |= set(row)
    for key in sorted(keys):
        print(f"-- {key} --", flush=True)
        for n, row in mystery_rows:
            cell = row.get(key)
            if not cell:
                continue
            print(f"  {n}: n={cell.get('n')} bits={cell.get('bits')}", flush=True)


if __name__ == "__main__":
    main()
