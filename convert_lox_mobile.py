#!/usr/bin/env python3
"""Convert LOX -> a single-file touch-oriented HTML viewer.

Shares the unchanged geometry reader and contour extractor with the desktop
converter. Categorization is opt-in; by default every survey has type 'all'.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
import sys

from convert_lox_html import ROOT, create_data, render_html


def _matches(group: dict, pattern: str) -> bool:
    """Case-insensitive glob on survey code/title; bare text matches a substring."""
    values = (str(group.get('code', '')).casefold(), str(group.get('name', '')).casefold())
    pat = pattern.strip().casefold()
    if not pat:
        raise ValueError('Category patterns cannot be empty')
    if any(c in pat for c in '*?['):
        return any(fnmatch.fnmatchcase(v, pat) for v in values)
    return any(pat in v for v in values)


def assign_categories(data: dict, category: str = 'all', mine: list[str] | None = None,
                      cave: list[str] | None = None) -> dict:
    """Apply optional labels only; geometry coordinates and faces never change."""
    if category not in {'all', 'cave', 'mine'}:
        raise ValueError('category must be all, cave or mine')
    mine, cave = list(mine or []), list(cave or [])
    assignments = {}
    for g in data['groups']:
        hit_mine = [p for p in mine if _matches(g, p)]
        hit_cave = [p for p in cave if _matches(g, p)]
        if hit_mine and hit_cave:
            raise ValueError(f'Survey matched both cave and mine patterns: {g["name"]}')
        assignments[g['id']] = 'mine' if hit_mine else 'cave' if hit_cave else category
    for pat, kind in [(p, 'mine') for p in mine] + [(p, 'cave') for p in cave]:
        if not any(_matches(g, pat) for g in data['groups']):
            raise ValueError(f'{kind} pattern does not match any survey: {pat!r}')
    for g in data['groups']:
        g['kind'] = assignments[g['id']]
    for geom in data['geometry']:
        if geom.get('gid') in assignments:
            geom['kind'] = assignments[geom['gid']]
    by_kind = {key: sum(g['kind'] == key for g in data['groups'])
               for key in ('all', 'cave', 'mine')}
    data['meta']['categories'] = by_kind
    data['meta']['stats']['caves'] = by_kind['cave']
    data['meta']['stats']['mines'] = by_kind['mine']
    return data


def build_mobile_data(lox: Path, *, category='all', mine=None, cave=None,
                      start_mode='balanced', **kwargs) -> dict:
    if start_mode not in {'balanced', 'light', 'detailed'}:
        raise ValueError('start_mode must be balanced, light or detailed')
    data = create_data(lox, **kwargs)
    assign_categories(data, category, mine, cave)
    data['meta']['mobile'] = {'start_mode': start_mode, 'version': '2.2'}
    return data


def convert(lox: Path, output: Path, *, qa_json=None, **kwargs) -> dict:
    data = build_mobile_data(lox, **kwargs)
    return render_html(data, output, template_file=ROOT / 'mobile_viewer_template.html',
                       qa_json=qa_json)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Convert LOX to a mobile-friendly single-file HTML (offline).')
    parser.add_argument('lox', type=Path, help='Therion .lox source')
    parser.add_argument('-o', '--output', type=Path, help='destination HTML')
    parser.add_argument('--site-name', default=None, help='title on the page')
    parser.add_argument('--crs', default='non dichiarato', help='coordinate label, no transformation')
    parser.add_argument('--z-label', default='Z (m)', help='vertical axis label')
    parser.add_argument('--group-mode', choices=['auto', 'survey', 'top'], default='auto')
    parser.add_argument('--type', '--category', dest='category',
                        choices=['all', 'cave', 'mine'], default='all',
                        help='default survey category; all is neutral (default)')
    parser.add_argument('--mine', action='append', default=[], metavar='PATTERN',
                        help='mark matching surveys as mines; repeatable; glob or substring')
    parser.add_argument('--cave', action='append', default=[], metavar='PATTERN',
                        help='mark matching surveys as caves; repeatable; glob or substring')
    parser.add_argument('--start-mode', choices=['balanced', 'light', 'detailed'],
                        default='balanced', help='mobile start: volume+lines, lines only, or detailed')
    parser.add_argument('--surface-index', type=int, default=0)
    parser.add_argument('--no-contours', action='store_true')
    parser.add_argument('--min-contour-length', type=float, default=12)
    parser.add_argument('--coordinate-decimals', type=int, default=3)
    parser.add_argument('--qa-json', type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.lox.is_file(): parser.error(f'LOX not found: {args.lox}')
    if args.surface_index < 0: parser.error('--surface-index must be >= 0')
    if args.min_contour_length < 0: parser.error('--min-contour-length must be >= 0')
    if not 0 <= args.coordinate_decimals <= 9: parser.error('--coordinate-decimals must be 0..9')
    destination = args.output or ROOT / 'output' / (args.lox.stem + '_mobile.html')
    try:
        result = convert(args.lox, destination, qa_json=args.qa_json,
            category=args.category, mine=args.mine, cave=args.cave,
            start_mode=args.start_mode, site_name=args.site_name,
            crs=args.crs, z_label=args.z_label,
            group_mode=args.group_mode, surface_index=args.surface_index,
            without_contours=args.no_contours,
            min_contour_length=args.min_contour_length,
            decimals=args.coordinate_decimals)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
