#!/usr/bin/env python3
"""Convert LOX -> one self-contained HTML that adapts to any device (v3).

The same page works on desktop computers (mouse, wheel, keyboard), laptops
(trackpad), tablets and phones (touch, pinch, joystick): the layout and the
controls adapt at runtime to screen size and input type.

Reader, grouping, contour extraction and optional categories are shared with
the desktop and mobile converters. Mesh pieces of the same survey group are
packed into a single WebGL trace (vertices appended, triangle indices offset):
no coordinate, vertex or face is changed, added or removed. This keeps large
LOX files with tens of thousands of scraps usable on phones.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from convert_lox_html import ROOT, create_data, render_html
from convert_lox_mobile import assign_categories

VERSION = '3.0'
TEMPLATE = ROOT / 'universal_viewer_template.html'
START_MODES = ('auto', 'balanced', 'light', 'detailed')


def pack_meshes(data: dict) -> dict:
    """Merge mesh assets sharing group, category and confidence, in source order."""
    packed, index = [], {}
    pieces = 0
    for asset in data['geometry']:
        if asset['type'] != 'mesh':
            packed.append(asset)
            continue
        pieces += 1
        key = (asset['gid'], asset['kind'], asset.get('confidence', 'measured'))
        target = index.get(key)
        if target is None:
            target = {**asset, 'x': list(asset['x']), 'y': list(asset['y']), 'z': list(asset['z']),
                      'i': list(asset['i']), 'j': list(asset['j']), 'k': list(asset['k']), 'parts': 1}
            index[key] = target
            packed.append(target)
            continue
        offset = len(target['x'])
        for axis in 'xyz':
            target[axis].extend(asset[axis])
        for axis in 'ijk':
            target[axis].extend(v + offset for v in asset[axis])
        target['parts'] += 1
    data['geometry'] = packed
    stats = data['meta']['stats']
    meshes = [a for a in packed if a['type'] == 'mesh']
    if sum(len(a['i']) for a in meshes) != stats['mesh_faces']:
        raise ValueError('Mesh packing lost some faces')
    if sum(len(a['x']) for a in meshes) != stats['mesh_vertices']:
        raise ValueError('Mesh packing lost some vertices')
    stats['mesh_pieces'] = pieces
    stats['mesh_traces'] = len(meshes)
    return data


def build_universal_data(lox: Path, *, category='all', mine=None, cave=None,
                         start_mode='auto', **kwargs) -> dict:
    if start_mode not in START_MODES:
        raise ValueError('start_mode must be one of ' + ', '.join(START_MODES))
    data = create_data(lox, **kwargs)
    assign_categories(data, category, mine, cave)
    pack_meshes(data)
    data['meta']['viewer'] = {'start_mode': start_mode, 'version': VERSION, 'layout': 'universal'}
    data['meta']['generator'] = f'LOX2HTML {VERSION} (Python)'
    return data


def convert(lox: Path, output: Path, *, qa_json=None, assets=None, **kwargs) -> dict:
    data = build_universal_data(lox, **kwargs)
    return render_html(data, output, assets=assets, template_file=TEMPLATE, qa_json=qa_json)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--crs', default='non dichiarato', help='coordinate label only, no transformation')
    parser.add_argument('--z-label', default='Z (m)', help='vertical axis label, no datum is assumed')
    parser.add_argument('--group-mode', choices=['auto', 'survey', 'top'], default='auto')
    parser.add_argument('--type', '--category', dest='category', choices=['all', 'cave', 'mine'],
                        default='all', help='default survey category; all is neutral (default)')
    parser.add_argument('--mine', action='append', default=[], metavar='PATTERN',
                        help='mark matching surveys as mines; repeatable; glob or substring')
    parser.add_argument('--cave', action='append', default=[], metavar='PATTERN',
                        help='mark matching surveys as caves; repeatable; glob or substring')
    parser.add_argument('--start-mode', choices=START_MODES, default='auto',
                        help='initial layers: auto adapts to the device (default)')
    parser.add_argument('--surface-index', type=int, default=0)
    parser.add_argument('--no-contours', action='store_true')
    parser.add_argument('--min-contour-length', type=float, default=12)
    parser.add_argument('--coordinate-decimals', type=int, default=3)


def check_common_arguments(parser, args) -> None:
    if args.surface_index < 0: parser.error('--surface-index must be >= 0')
    if args.min_contour_length < 0: parser.error('--min-contour-length must be >= 0')
    if not 0 <= args.coordinate_decimals <= 9: parser.error('--coordinate-decimals must be 0..9')


def common_options(args) -> dict:
    return dict(category=args.category, mine=args.mine, cave=args.cave,
                start_mode=args.start_mode, crs=args.crs, z_label=args.z_label,
                group_mode=args.group_mode, surface_index=args.surface_index,
                without_contours=args.no_contours,
                min_contour_length=args.min_contour_length,
                decimals=args.coordinate_decimals)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Convert LOX to one offline HTML viewer for any device (computer, tablet, phone).')
    parser.add_argument('lox', type=Path, help='Therion .lox source')
    parser.add_argument('-o', '--output', type=Path, help='destination HTML (default: output/<name>_3D.html)')
    parser.add_argument('--site-name', default=None, help='title on the page')
    parser.add_argument('--origin', nargs=2, type=float, metavar=('X0', 'Y0'), default=[None, None],
                        help='display origin subtracted from X/Y; automatic if omitted')
    parser.add_argument('--qa-json', type=Path, default=None, help='write provenance and counts to JSON')
    add_common_arguments(parser)
    args = parser.parse_args(argv)
    if not args.lox.is_file(): parser.error(f'LOX not found: {args.lox}')
    check_common_arguments(parser, args)
    destination = args.output or ROOT / 'output' / (args.lox.stem + '_3D.html')
    try:
        result = convert(args.lox, destination, qa_json=args.qa_json, site_name=args.site_name,
                         x0=args.origin[0], y0=args.origin[1], **common_options(args))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
