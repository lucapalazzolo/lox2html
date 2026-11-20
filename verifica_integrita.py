#!/usr/bin/env python3
"""Verify the immutable files shipped with the complete distribution."""
from pathlib import Path
import hashlib
import sys

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'MANIFEST_SHA256.txt'


def check():
    if not MANIFEST.is_file():
        print('Missing MANIFEST_SHA256.txt',file=sys.stderr)
        return 1
    errors=[]
    rows=0
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        digest,relative=line.split('  ',1)
        p=ROOT/relative
        rows+=1
        if not p.is_file():
            errors.append(f'MISSING: {relative}')
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            errors.append(f'MISMATCH: {relative}')
    for err in errors:print(err,file=sys.stderr)
    print(f'Integrity: {rows-len(errors)}/{rows} files match SHA256')
    return 1 if errors else 0

if __name__=='__main__':raise SystemExit(check())
