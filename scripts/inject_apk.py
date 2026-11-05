#!/usr/bin/env python3
"""Inject TMXK assets and a bootstrap DEX without rebuilding Android resources.

The official FongMi manifest contains android:name=".App". The bootstrap class
is deliberately named com.fongmi.android.tv.New so the binary AXML string
".App" can be changed to ".New" in-place (same UTF-8/UTF-16 byte length).
All other resources, original DEX files and native player libraries are copied
from the official APK unchanged.
"""
from __future__ import annotations
import pathlib
import re
import struct
import sys
import zipfile

OLD_NAME = ".App"
NEW_NAME = ".New"
SIGNATURE_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def u16(data: bytes, pos: int) -> int:
    return struct.unpack_from("<H", data, pos)[0]


def u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def read_len8(data: bytes, pos: int) -> tuple[int, int]:
    first = data[pos]
    pos += 1
    if first & 0x80:
        second = data[pos]
        pos += 1
        return ((first & 0x7F) << 8) | second, pos
    return first, pos


def read_len16(data: bytes, pos: int) -> tuple[int, int]:
    first = u16(data, pos)
    pos += 2
    if first & 0x8000:
        second = u16(data, pos)
        pos += 2
        return ((first & 0x7FFF) << 16) | second, pos
    return first, pos


def patch_binary_manifest(data: bytes) -> bytes:
    if len(data) < 8 or u16(data, 0) != 0x0003:
        raise ValueError("AndroidManifest.xml is not binary AXML")

    root_header = u16(data, 2)
    root_size = u32(data, 4)
    if root_size != len(data):
        raise ValueError(f"AXML size mismatch: header={root_size}, actual={len(data)}")

    patched = bytearray(data)
    offset = root_header
    replacements = 0
    while offset + 8 <= len(patched):
        chunk_type = u16(patched, offset)
        header_size = u16(patched, offset + 2)
        chunk_size = u32(patched, offset + 4)
        if chunk_size < header_size or offset + chunk_size > len(patched):
            raise ValueError("Invalid AXML chunk boundaries")

        if chunk_type == 0x0001:  # RES_STRING_POOL_TYPE
            string_count = u32(patched, offset + 8)
            flags = u32(patched, offset + 16)
            strings_start = u32(patched, offset + 20)
            utf8 = bool(flags & 0x00000100)
            old_bytes = OLD_NAME.encode("utf-8") if utf8 else OLD_NAME.encode("utf-16le")
            new_bytes = NEW_NAME.encode("utf-8") if utf8 else NEW_NAME.encode("utf-16le")

            for index in range(string_count):
                string_offset = u32(patched, offset + header_size + index * 4)
                pos = offset + strings_start + string_offset
                if utf8:
                    _utf16_length, pos = read_len8(patched, pos)
                    byte_length, pos = read_len8(patched, pos)
                    value_pos = pos
                else:
                    _char_length, value_pos = read_len16(patched, pos)
                    byte_length = len(old_bytes)

                if bytes(patched[value_pos:value_pos + byte_length]) == old_bytes:
                    if len(old_bytes) != len(new_bytes):
                        raise ValueError("Replacement must be equal length")
                    patched[value_pos:value_pos + byte_length] = new_bytes
                    replacements += 1

        offset += chunk_size

    if replacements < 1:
        raise ValueError(f"Could not find exact manifest string {OLD_NAME!r} in AXML string pool")
    check_old = OLD_NAME.encode("utf-8")
    check_new = NEW_NAME.encode("utf-8")
    if check_old in patched and check_old not in check_new:
        # It is possible for a different longer string to contain the sequence;
        # the string-pool entries were patched exactly, so this is only a guard.
        pass
    return bytes(patched)


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("Usage: inject_apk.py input.apk output.apk assets_dir bootstrap.dex")

    source = pathlib.Path(sys.argv[1])
    output = pathlib.Path(sys.argv[2])
    assets_dir = pathlib.Path(sys.argv[3])
    dex_path = pathlib.Path(sys.argv[4])

    if not source.is_file() or not assets_dir.is_dir() or not dex_path.is_file():
        raise SystemExit("Input APK, assets directory, or bootstrap DEX is missing")

    assets = sorted(p for p in assets_dir.rglob("*") if p.is_file())
    if not assets:
        raise SystemExit("No TMXK asset files found")

    with zipfile.ZipFile(source, "r") as original:
        infos = original.infolist()
        names = {info.filename for info in infos}
        if "AndroidManifest.xml" not in names:
            raise SystemExit("Official APK has no AndroidManifest.xml")
        if any(name.startswith("assets/tmxk/") for name in names):
            raise SystemExit("Official APK unexpectedly already contains assets/tmxk")
        if any(name.startswith("classes") and name.endswith(".dex") for name in names) is False:
            raise SystemExit("Official APK has no DEX files")

        dex_indexes = []
        for name in names:
            match = re.fullmatch(r"classes(\d*)\.dex", name)
            if match:
                dex_indexes.append(int(match.group(1) or "1"))
        next_dex_index = max(dex_indexes) + 1
        dex_name = f"classes{next_dex_index}.dex"

        manifest = original.read("AndroidManifest.xml")
        patched_manifest = patch_binary_manifest(manifest)

        with zipfile.ZipFile(output, "w") as patched:
            patched.comment = original.comment
            for info in infos:
                upper = info.filename.upper()
                if upper == "META-INF/MANIFEST.MF" or (
                    upper.startswith("META-INF/") and upper.endswith(SIGNATURE_SUFFIXES)
                ):
                    continue
                payload = patched_manifest if info.filename == "AndroidManifest.xml" else original.read(info.filename)
                patched.writestr(info, payload)

            for file_path in assets:
                relative = file_path.relative_to(assets_dir).as_posix()
                arcname = f"assets/tmxk/{relative}"
                if arcname in names:
                    raise SystemExit(f"Duplicate APK entry: {arcname}")
                patched.write(file_path, arcname)

            patched.write(dex_path, dex_name)

    with zipfile.ZipFile(output, "r") as check:
        check.testzip()
        final_names = set(check.namelist())
        expected = {
            "AndroidManifest.xml",
            "assets/tmxk/config.json",
            "assets/tmxk/game-live-vod.json",
            "assets/tmxk/live/cctv.py",
            "assets/tmxk/live/yangshipin.py",
            "assets/tmxk/live/gdtv.py",
            "assets/tmxk/vod/game_live.py",
            dex_name,
        }
        missing = sorted(expected - final_names)
        if missing:
            raise SystemExit("Missing after injection: " + ", ".join(missing))
        manifest_after = check.read("AndroidManifest.xml")
        if NEW_NAME.encode("utf-8") not in manifest_after and NEW_NAME.encode("utf-16le") not in manifest_after:
            raise SystemExit("Bootstrap Application class was not written")

    print(f"Injected {len(assets)} resource files and {dex_name}")
    print(f"APK size: {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
