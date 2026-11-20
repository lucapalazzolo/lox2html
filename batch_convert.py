#!/usr/bin/env python3
"""Convert LOX folders to standalone HTML; preserve relative input structure."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from convert_lox_html import create_data, render_html


def main(argv=None):
    ap=argparse.ArgumentParser(description='Convert all *.lox files from a directory to offline HTML')
    ap.add_argument('directory',type=Path)
    ap.add_argument('-o','--output-dir',type=Path,default=Path(__file__).resolve().parent/'output')
    ap.add_argument('--recursive',action='store_true')
    ap.add_argument('--crs',default='non dichiarato')
    ap.add_argument('--z-label',default='Z (m)')
    ap.add_argument('--group-mode',choices=['auto','survey','top'],default='auto')
    ap.add_argument('--surface-index',type=int,default=0)
    ap.add_argument('--no-contours',action='store_true')
    args=ap.parse_args(argv)
    if not args.directory.is_dir():ap.error('Directory not found: '+str(args.directory))
    paths=sorted((args.directory.rglob('*') if args.recursive else args.directory.iterdir()),key=lambda p:str(p).casefold())
    files=[p for p in paths if p.is_file() and p.suffix.lower()=='.lox']
    if not files:ap.error('No *.lox in directory (use --recursive to include subdirectories)')
    report=[]
    for path in files:
        target=args.output_dir/path.relative_to(args.directory).with_suffix('.html')
        try:
            data=create_data(path,site_name=path.stem,group_mode=args.group_mode,crs=args.crs,
                             z_label=args.z_label,surface_index=args.surface_index,
                             without_contours=args.no_contours)
            result=render_html(data,target,qa_json=target.with_suffix('.qa.json'))
            entry={'input':str(path),'ok':True,**result}
            print('OK',path,'->',target,flush=True)
        except Exception as exc:
            entry={'input':str(path),'ok':False,'error':str(exc)}
            print('FAILED',path,':',exc,file=sys.stderr,flush=True)
        report.append(entry)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'LOX2HTML_BATCH_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    ok=sum(r['ok'] for r in report)
    print(f'Completed {ok}/{len(report)}; report: {args.output_dir/"LOX2HTML_BATCH_REPORT.json"}')
    return 0 if ok==len(report) else 1

if __name__=='__main__':raise SystemExit(main())
