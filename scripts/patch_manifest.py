#!/usr/bin/env python3
"""Patch the decoded FongMi manifest to start the TMXK bootstrap subclass."""
from __future__ import annotations
import pathlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: patch_manifest.py <decoded AndroidManifest.xml>")

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
match = re.search(r"<application\b[^>]*>", text)
if not match:
    raise SystemExit("AndroidManifest.xml has no <application> element")

tag = match.group(0)
target = 'com.tmxk.bootstrap.TMXKApplication'
if re.search(r'\bandroid:name\s*=\s*"' + re.escape(target) + r'"', tag):
    print("TMXK Application already installed")
    raise SystemExit(0)

tag = re.sub(r'\s+android:name\s*=\s*"[^"]*"', "", tag)
if not tag.endswith(">"):
    raise SystemExit("Unexpected application tag shape")
tag = tag[:-1] + f' android:name="{target}">'
patched = text[:match.start()] + tag + text[match.end():]
path.write_text(patched, encoding="utf-8")
print(f"Application class set to {target}")
