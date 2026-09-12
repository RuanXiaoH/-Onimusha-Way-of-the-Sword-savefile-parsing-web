"""Clear all 幻魔杂记 unlock flags in data001Slot_1814.bin."""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

print("start", flush=True)

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from parse_save import Reader, murmur3_32  # noqa: E402

CLI = ROOT / "tools" / "mandarin_cli" / "MandarinJuice" / "mandarin-juice-cli.exe"
PROFILE = ROOT / "tools" / "profiles_extract" / "_profiles" / "Onimusha Way of the Sword v1.bin"
STEAMID_FILE = SCRIPTS / "steamid.txt"

HASH_MYSTERY_GUI = 0x299A4B78
HASH_MAIN_FLAGS = murmur3_32("ReleasedMainMysteryFlags")  # cfb8ea4a
HASH_VALUE = murmur3_32("_Value")  # 861ab707
HASH_SUB_FLAGS = 0x6858D6B7  # ReleasedSubMysteryFlags
TYPE_MYSTERY_PARAM = 0x540CC7AB
TYPE_MYSTERY_GUI = 0x2E1CB3DF
TYPE_BITSET = 0x1CA59446


def steam_id() -> str:
    return STEAMID_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()


def looks_encrypted(data: bytes) -> bool:
    return data[:4] in (b"DSSS", b"dsss")


def run_cli(mode: str, src: Path, dest: Path, suffix: str) -> None:
    work = Path(tempfile.mkdtemp(prefix=f"oni-{mode}-"))
    try:
        inbox = work / "in"
        inbox.mkdir()
        (inbox / "data001Slot.bin").write_bytes(src.read_bytes())
        out_root = CLI.parent / "_OUTPUT"
        before = {p.resolve() for p in out_root.glob("**/*.bin")} if out_root.exists() else set()
        cmd = [str(CLI), "-m", mode, "-g", str(PROFILE), "-p", str(inbox), "-u", steam_id(), "-q"]
        print("cli", mode, flush=True)
        proc = subprocess.run(cmd, cwd=str(CLI.parent), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or f"exit {proc.returncode}").strip())
        after = {p.resolve() for p in out_root.glob("**/*.bin")} if out_root.exists() else set()
        new_files = [p for p in after - before if p.name.lower().endswith(".bin")]
        if not new_files:
            cands = sorted(out_root.glob(f"*{suffix}/*.bin"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not cands:
                raise RuntimeError(f"{mode} 完成但没有输出")
            newest = cands[0]
        else:
            newest = max(new_files, key=lambda p: p.stat().st_mtime)
        dest.write_bytes(newest.read_bytes())
        parent = newest.parent
        if parent.name.endswith(suffix):
            shutil.rmtree(parent, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


class Patcher:
    def __init__(self, buf: bytearray):
        self.buf = buf
        self.r = Reader(bytes(buf))
        self.in_mystery_gui = 0
        self.in_mystery_param = 0
        self.in_bitset_value = 0
        self.seen_mystery_param = 0
        self.seen_mystery_gui = 0
        self.patches: list[tuple[str, int, int]] = []

    def poke(self, off: int, size: int, old: int, label: str) -> None:
        if old == 0:
            return
        if size == 4:
            struct.pack_into("<I", self.buf, off, 0)
        elif size == 8:
            struct.pack_into("<Q", self.buf, off, 0)
        else:
            return
        self.patches.append((label, off, old))

    def read_sized(self, field_type: int, size: int):
        r = self.r
        if size != 1:
            r.pos = (r.pos + size - 1) & ~(size - 1)
        off = r.pos
        if field_type in (1, 7) and size == 4:
            return r.i32(), off, 4
        if field_type in (1, 9) and size == 8:
            return r.i64(), off, 8
        if field_type == 2:
            return r.u8(), off, 1
        if field_type in (3, 13):
            return r.i8() if field_type == 3 else r.u8(), off, 1
        if field_type in (4,):
            return r.u8(), off, 1
        if field_type in (5,):
            return r.i16(), off, 2
        if field_type in (6, 14):
            return r.u16(), off, 2
        if field_type == 8:
            return r.u32(), off, 4
        if field_type == 10:
            return r.u64(), off, 8
        if field_type == 11:
            return r.f32(), off, 4
        if field_type == 12:
            return r.f64(), off, 8
        if field_type == 1 and size == 1:
            return r.i8(), off, 1
        if field_type == 1 and size == 2:
            return r.i16(), off, 2
        if field_type == 16:
            return r.raw(size), off, size
        raise ValueError(f"type {field_type} size {size} at 0x{r.pos:X}")

    def read_string(self) -> None:
        r = self.r
        r.align(4)
        count = r.u32()
        r.raw(count * 2)

    def read_array(self) -> None:
        r = self.r
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
        zero_words = self.in_bitset_value and self.in_mystery_gui
        for i in range(length):
            if array_type == 0:
                if member_type == 15:
                    self.read_string()
                else:
                    value, off, size = self.read_sized(member_type, member_size)
                    if zero_words and size in (4, 8) and isinstance(value, int) and value:
                        self.poke(off, size, value & ((1 << (size * 8)) - 1), f"gui_bit[{i}]")
            elif array_type == 1:
                self.read_class(hashes[i] if hashes else None)
            else:
                raise ValueError(f"array_type {array_type}")
        r.align(4)

    def read_value(self, field_type: int):
        r = self.r
        if field_type == 17:
            self.read_class()
            return None
        if field_type == 15:
            self.read_string()
            return None
        if field_type == -1:
            self.read_array()
            return None
        r.align(4)
        size = r.u32()
        return self.read_sized(field_type, size)

    def read_field(self, owner_hash: int) -> None:
        r = self.r
        field_hash = r.u32()
        field_type = r.i32()
        if field_hash == HASH_MYSTERY_GUI:
            self.in_mystery_gui += 1
            self.seen_mystery_gui += 1
        if field_hash == HASH_VALUE and self.in_mystery_gui:
            self.in_bitset_value += 1
        try:
            got = self.read_value(field_type)
            if got is not None and self.in_mystery_param and field_hash != HASH_MAIN_FLAGS:
                value, off, size = got
                if size in (4, 8) and isinstance(value, int) and value:
                    self.poke(off, size, value & ((1 << (size * 8)) - 1), f"myst_{field_hash:08x}")
        finally:
            if field_hash == HASH_VALUE and self.in_mystery_gui:
                self.in_bitset_value -= 1
            if field_hash == HASH_MYSTERY_GUI:
                self.in_mystery_gui -= 1
        r.align(4)

    def read_class(self, forced_hash: int | None = None) -> None:
        r = self.r
        num_fields = r.u32()
        type_hash = r.u32()
        if forced_hash:
            type_hash = forced_hash
        entered_param = type_hash == TYPE_MYSTERY_PARAM
        entered_gui = type_hash == TYPE_MYSTERY_GUI
        entered_bitset = type_hash == TYPE_BITSET and self.in_mystery_gui
        if entered_param:
            self.in_mystery_param += 1
            self.seen_mystery_param += 1
        if entered_gui:
            self.in_mystery_gui += 1
            self.seen_mystery_gui += 1
        if entered_bitset:
            self.in_bitset_value += 1
        try:
            for _ in range(num_fields):
                self.read_field(type_hash)
        finally:
            if entered_bitset:
                self.in_bitset_value -= 1
            if entered_gui:
                self.in_mystery_gui -= 1
            if entered_param:
                self.in_mystery_param -= 1

    def run(self) -> None:
        r = self.r
        end = max(0, len(r.data) - 7)
        while r.pos < end and r.remaining() >= 8:
            r.u32()
            self.read_class()
            if r.pos >= end:
                break


def main() -> None:
    src = Path(r"d:\开学！\react\onimusha\test_data\data001Slot_1814.bin")
    bak = src.with_suffix(src.suffix + ".bak")
    print("src exists", src.exists(), "bak exists", bak.exists(), flush=True)
    source = bak if bak.exists() else src
    raw = source.read_bytes()
    print("source", source, "size", len(raw), "magic", raw[:4], flush=True)
    if not bak.exists():
        bak.write_bytes(raw)
        print("backup", bak, flush=True)
    work = Path(tempfile.mkdtemp(prefix="oni-lock-mystery-"))
    try:
        plain = work / "plain.bin"
        encrypted = looks_encrypted(raw)
        print("encrypted", encrypted, flush=True)
        if encrypted:
            run_cli("d", source, plain, "_decrypted")
        else:
            plain.write_bytes(raw)
        data = bytearray(plain.read_bytes())
        print("plain", len(data), "plain_magic", bytes(data[:4]), flush=True)
        n_type = sum(
            1
            for off in range(0, len(data) - 3, 4)
            if int.from_bytes(data[off : off + 4], "little") == TYPE_MYSTERY_PARAM
        )
        n_gui = sum(
            1
            for off in range(0, len(data) - 3, 4)
            if int.from_bytes(data[off : off + 4], "little") == HASH_MYSTERY_GUI
        )
        print("hits type_540cc7ab", n_type, "field_299a4b78", n_gui, flush=True)
        patcher = Patcher(data)
        patcher.run()
        print(
            "visits mystery_param",
            patcher.seen_mystery_param,
            "mystery_gui",
            patcher.seen_mystery_gui,
            flush=True,
        )
        print("patches", len(patcher.patches), flush=True)
        for row in patcher.patches[:50]:
            print(" ", row, flush=True)
        patched = work / "patched.bin"
        patched.write_bytes(data)
        if encrypted:
            run_cli("e", patched, src, "_encrypted")
        else:
            src.write_bytes(data)
        print("done", src, src.stat().st_size, "magic", src.read_bytes()[:4], flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
