#!/usr/bin/env python3
"""Convert a tree of LOX files to self-contained mobile HTML files."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from convert_lox_mobile import convert


def main(argv=None):
    p=argparse.ArgumentParser(description='Batch convert LOX to touch-friendly HTML')
    p.add_argument('directory',type=Path)
    p.add_argument('-o','--output-dir',type=Path,default=Path(__file__).resolve().parent/'output')
    p.add_argument('--recursive',action='store_true')
    p.add_argument('--crs',default='non dichiarato')
    p.add_argument('--group-mode',choices=['auto','survey','top'],default='auto')
    p.add_argument('--type','--category',dest='category',choices=['all','cave','mine'],default='all')
    p.add_argument('--mine',action='append',default=[])
    p.add_argument('--cave',action='append',default=[])
    p.add_argument('--start-mode',choices=['balanced','light','detailed'],default='balanced')
    p.add_argument('--surface-index',type=int,default=0)
    p.add_argument('--no-contours',action='store_true')
    a=p.parse_args(argv)
    if not a.directory.is_dir():p.error(f'Directory not found: {a.directory}')
    paths=a.directory.rglob('*') if a.recursive else a.directory.iterdir()
    files=sorted([f for f in paths if f.is_file() and f.suffix.lower()=='.lox'])
    if not files:p.error('No .lox files found')
    report=[]
    for f in files:
        target=(a.output_dir/f.relative_to(a.directory)).with_suffix('.html')
        try:
            result=convert(f,target,qa_json=target.with_suffix('.qa.json'),site_name=f.stem,
                         category=a.category,mine=a.mine,cave=a.cave,
                         start_mode=a.start_mode,crs=a.crs,group_mode=a.group_mode,
                         surface_index=a.surface_index,without_contours=a.no_contours)
            report.append({'source':str(f),'ok':True,**result})
            print('OK',f,'->',target,flush=True)
        except Exception as exc:
            report.append({'source':str(f),'ok':False,'error':str(exc)})
            print('FAILED:',f,exc,file=sys.stderr,flush=True)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/'BATCH_MOBILE_REPORT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"Converted {sum(x['ok'] for x in report)}/{len(report)}")
    return 0 if all(x['ok'] for x in report) else 1


if __name__=='__main__':
    raise SystemExit(main())
