"""Decrypt (if needed) and pack a data001Slot.bin into display JSON."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from make_display_data import build_display  # noqa: E402
from parse_save import TypeDb, parse_save  # noqa: E402

DUMP = ROOT / "dumps" / "rszoniwots.json"
if not DUMP.exists():
    DUMP = ROOT / "dumps" / "REasy" / "resources" / "data" / "dumps" / "rszoniwots.json"
ENUMS = ROOT / "dumps" / "oniwots_enums.json"
CLI = ROOT / "tools" / "mandarin_cli" / "MandarinJuice" / "mandarin-juice-cli.exe"
PROFILE = ROOT / "tools" / "profiles_extract" / "_profiles" / "Onimusha Way of the Sword v1.bin"
STEAMID_FILE = SCRIPTS / "steamid.txt"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def steam_id() -> str:
    env = (os.environ.get("ONIMUSHA_STEAM_ID") or "").strip()
    if env:
        return env
    if STEAMID_FILE.exists():
        return STEAMID_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    raise RuntimeError("未配置 SteamID，无法解密存档")


def looks_encrypted(data: bytes) -> bool:
    return data[:4] in (b"DSSS", b"dsss")


def decrypt_bin(src: Path, dest: Path) -> Path:
    if not CLI.exists():
        raise RuntimeError(f"找不到解密工具：{CLI}")
    if not PROFILE.exists():
        raise RuntimeError(f"找不到游戏 profile：{PROFILE}")
    work = Path(tempfile.mkdtemp(prefix="oni-decrypt-"))
    try:
        inbox = work / "in"
        inbox.mkdir()
        copied = inbox / "data001Slot.bin"
        copied.write_bytes(src.read_bytes())
        out_root = CLI.parent / "_OUTPUT"
        before = {p.resolve() for p in out_root.glob("**/*.bin")} if out_root.exists() else set()
        cmd = [
            str(CLI),
            "-m",
            "d",
            "-g",
            str(PROFILE),
            "-p",
            str(inbox),
            "-u",
            steam_id(),
            "-q",
        ]
        log("decrypt " + " ".join(cmd[1:5]) + " ...")
        proc = subprocess.run(cmd, cwd=str(CLI.parent), capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            sid = steam_id()
            if sid:
                detail = detail.replace(sid, "")
            raise RuntimeError(detail or f"解密失败，退出码 {proc.returncode}")
        after = {p.resolve() for p in out_root.glob("**/*.bin")} if out_root.exists() else set()
        new_files = [p for p in after - before if p.name.lower().endswith(".bin")]
        if not new_files:
            cands = sorted(out_root.glob("*_decrypted/*.bin"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not cands:
                raise RuntimeError("解密完成但没有找到明文存档")
            newest = cands[0]
        else:
            newest = max(new_files, key=lambda p: p.stat().st_mtime)
        dest.write_bytes(newest.read_bytes())
        parent = newest.parent
        if parent.name.endswith("_decrypted"):
            shutil.rmtree(parent, ignore_errors=True)
        return dest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def analyze_bytes(raw: bytes) -> dict:
    if not DUMP.exists() or not ENUMS.exists():
        raise RuntimeError("缺少解析用的类型表，无法分析存档")
    with tempfile.TemporaryDirectory(prefix="oni-analyze-") as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "upload.bin"
        src.write_bytes(raw)
        plain = tmp_path / "plain.bin"
        if looks_encrypted(raw):
            decrypt_bin(src, plain)
            data = plain.read_bytes()
        else:
            data = raw
        dump = json.loads(DUMP.read_text(encoding="utf-8"))
        enums = json.loads(ENUMS.read_text(encoding="utf-8"))
        db = TypeDb(dump, enums)
        try:
            parsed = parse_save(data, db)
        except Exception:
            if looks_encrypted(raw):
                raise
            log("明文解析失败，尝试按加密存档解密")
            decrypt_bin(src, plain)
            parsed = parse_save(plain.read_bytes(), db)
        if not parsed.get("roots"):
            raise RuntimeError("存档里没有读到数据根")
        display = build_display(parsed)
        if not display.get("slots"):
            raise RuntimeError("没有占用中的存档栏位")
        return display


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    args = ap.parse_args()
    path = Path(args.bin)
    if not path.exists():
        raise SystemExit(f"找不到文件 {path}")
    display = analyze_bytes(path.read_bytes())
    display["_source"] = {
        "filename": path.name,
        "analyzedAt": datetime.now().isoformat(timespec="seconds"),
    }
    sys.stdout.write(json.dumps(display, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
