#!/usr/bin/env python3
"""Convert a folder (optionally recursive) of LOX files to universal HTML viewers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from convert_lox_universal import add_common_arguments, check_common_arguments, common_options, convert


def main(argv=None):
    parser = argparse.ArgumentParser(description='Batch convert LOX to HTML viewers for any device')
    parser.add_argument('directory', type=Path)
    parser.add_argument('-o', '--output-dir', type=Path, default=Path(__file__).resolve().parent / 'output')
    parser.add_argument('--recursive', action='store_true')
    add_common_arguments(parser)
    args = parser.parse_args(argv)
    if not args.directory.is_dir(): parser.error(f'Directory not found: {args.directory}')
    check_common_arguments(parser, args)
    paths = args.directory.rglob('*') if args.recursive else args.directory.iterdir()
    files = sorted((p for p in paths if p.is_file() and p.suffix.lower() == '.lox'),
                   key=lambda p: str(p).casefold())
    if not files: parser.error('No .lox files found (use --recursive to include subfolders)')
    report = []
    for source in files:
        target = (args.output_dir / source.relative_to(args.directory)).with_suffix('.html')
        try:
            result = convert(source, target, qa_json=target.with_suffix('.qa.json'),
                             site_name=source.stem, **common_options(args))
            report.append({'source': str(source), 'ok': True, **result})
            print('OK', source, '->', target, flush=True)
        except Exception as exc:  # one broken file must not stop the batch
            report.append({'source': str(source), 'ok': False, 'error': str(exc)})
            print('FAILED:', source, exc, file=sys.stderr, flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / 'BATCH_UNIVERSAL_REPORT.json'
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    ok = sum(r['ok'] for r in report)
    print(f'Converted {ok}/{len(report)}; report: {report_path}')
    return 0 if ok == len(report) else 1


if __name__ == '__main__':
    raise SystemExit(main())
