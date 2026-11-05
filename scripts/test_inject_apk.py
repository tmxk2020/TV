#!/usr/bin/env python3
"""Synthetic binary-AXML and APK injection regression tests."""
from __future__ import annotations
import pathlib
import struct
import sys
import tempfile
import zipfile

from inject_apk import patch_binary_manifest


def make_axml(value: str, utf8: bool) -> bytes:
    if utf8:
        raw = value.encode("utf-8")
        string = bytes([len(value), len(raw)]) + raw + b"\0"
        flags = 0x100
    else:
        raw = value.encode("utf-16le")
        string = struct.pack("<H", len(value)) + raw + b"\0\0"
        flags = 0

    pool_size = 28 + 4 + len(string)
    pool = (
        struct.pack("<HHI", 0x0001, 28, pool_size)
        + struct.pack("<IIIII", 1, 0, flags, 32, 0)
        + struct.pack("<I", 0)
        + string
    )
    return struct.pack("<HHI", 0x0003, 8, 8 + len(pool)) + pool


def main() -> None:
    for name in (".App", "com.fongmi.android.tv.App"):
        for utf8 in (True, False):
            source = make_axml(name, utf8)
            result = patch_binary_manifest(source)
            target = name.replace("App", "New")
            encoded = target.encode("utf-8" if utf8 else "utf-16le")
            if encoded not in result:
                raise AssertionError(f"binary manifest replacement failed: {name}, utf8={utf8}")
            if len(result) != len(source):
                raise AssertionError("in-place binary manifest patch changed file length")
    print("Synthetic AXML UTF-8/UTF-16 relative/FQCN tests passed")


if __name__ == "__main__":
    main()
