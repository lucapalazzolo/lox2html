"""Universal (any-device) converter: grouping, mesh packing and single-file HTML."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from convert_lox_html import create_data  # noqa: E402
from convert_lox_universal import TEMPLATE, build_universal_data, convert, pack_meshes  # noqa: E402
from lox_io import write_lox  # noqa: E402
from test_converter import miniature  # noqa: E402


def therion_project():
    """root -> project -> {empty placeholder, system -> 2 caves -> branches}; titles inherited."""
    title = 'Sistema di Prova'
    surveys = [{'id': 0, 'parent': 0, 'name': '', 'title': ''},
               {'id': 1, 'parent': 0, 'name': 'Progetto_x1', 'title': title},
               {'id': 2, 'parent': 1, 'name': 'unnamed', 'title': title},
               {'id': 3, 'parent': 1, 'name': 'sistema', 'title': title},
               {'id': 4, 'parent': 3, 'name': 'Bueno', 'title': title},
               {'id': 5, 'parent': 3, 'name': 'Nueva', 'title': title},
               {'id': 6, 'parent': 4, 'name': 'ramo_a', 'title': title},
               {'id': 7, 'parent': 5, 'name': 'ramo_b', 'title': title}]
    stations, shots, scraps = [], [], []
    for survey, x in ((3, 0.0), (6, 100.0), (7, 200.0)):
        a, b = len(stations), len(stations) + 1
        stations.append({'id': a, 'survey': survey, 'name': f'{a}', 'comment': '', 'flags': 2 if survey == 3 else 0,
                         'xyz': (5000.0 + x, 9000.0, 300.0)})
        stations.append({'id': b, 'survey': survey, 'name': f'{b}', 'comment': '', 'flags': 0,
                         'xyz': (5010.0 + x, 9004.0, 296.0)})
        shots.append({'from': a, 'to': b, 'survey': survey})
    # Many small scraps in one branch, as produced by Therion for large systems.
    for n in range(25):
        x = 5100.0 + n
        scraps.append({'id': n, 'survey': 6, 'points': [(x, 9000., 300.), (x + .5, 9000., 300.), (x, 9000.5, 299.)],
                       'triangles': [(0, 1, 2)]})
    scraps.append({'id': 25, 'survey': 7, 'points': [(5200., 9000., 300.), (5201., 9000., 300.), (5200., 9001., 300.),
                                                     (5201., 9001., 301.)], 'triangles': [(0, 1, 2), (1, 3, 2)]})
    return {'surveys': surveys, 'stations': stations, 'shots': shots, 'scraps': scraps, 'surfaces': [], 'bitmaps': []}


def embedded_model(page: str) -> dict:
    raw = re.search(r'<script id="model-json" type="application/json">(.*?)</script>', page, re.S).group(1)
    return json.loads(raw)


class UniversalConverterTests(unittest.TestCase):
    def write(self, folder, model, name='model.lox'):
        path = Path(folder) / name
        write_lox(path, model)
        return path

    def test_auto_grouping_skips_empty_branches_and_uses_readable_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = create_data(self.write(tmp, therion_project()))
        names = sorted(g['name'] for g in data['groups'])
        # Empty 'unnamed' placeholder is gone; caves are separate; the junction keeps its own shot.
        self.assertEqual(names, ['Bueno', 'Nueva', 'sistema'])
        self.assertEqual(sum(g['shots'] for g in data['groups']), 3)
        self.assertEqual(data['meta']['stats']['mesh_faces'], 27)

    def test_pack_meshes_keeps_every_vertex_and_face(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = self.write(tmp, therion_project())
            base = create_data(src)
            packed = pack_meshes(json.loads(json.dumps(base)))
        before = [a for a in base['geometry'] if a['type'] == 'mesh']
        after = [a for a in packed['geometry'] if a['type'] == 'mesh']
        self.assertEqual(len(before), 26)
        self.assertEqual(len(after), 2)  # one trace per survey group
        self.assertEqual(packed['meta']['stats']['mesh_pieces'], 26)
        self.assertEqual(packed['meta']['stats']['mesh_traces'], 2)
        for gid in {a['gid'] for a in before}:
            parts = [a for a in before if a['gid'] == gid]
            merged = next(a for a in after if a['gid'] == gid)
            vertices = [(x, y, z) for a in parts for x, y, z in zip(a['x'], a['y'], a['z'])]
            self.assertEqual(list(zip(merged['x'], merged['y'], merged['z'])), vertices)
            faces, offset = [], 0
            for a in parts:
                faces += [(i + offset, j + offset, k + offset) for i, j, k in zip(a['i'], a['j'], a['k'])]
                offset += len(a['x'])
            self.assertEqual(list(zip(merged['i'], merged['j'], merged['k'])), faces)

    def test_single_self_contained_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = self.write(tmp, miniature())
            out = Path(tmp) / 'out' / 'viewer.html'
            result = convert(src, out, site_name='Rilievo <prova> & co')
            page = out.read_text(encoding='utf-8')
        self.assertNotIn('<script src=', page)
        self.assertNotIn('<link rel="stylesheet"', page)
        self.assertNotIn('/*__PLOTLY_JS__*/', page)
        self.assertNotIn('/*__MODEL_JSON__*/', page)
        self.assertNotIn('__HTML_TITLE__', page)
        self.assertIn('Rilievo &lt;prova&gt; &amp; co', page)
        self.assertIn('viewport-fit=cover', page)
        self.assertIn('plotly.js v', page)
        data = embedded_model(page)
        self.assertEqual(data['meta']['viewer'], {'start_mode': 'auto', 'version': '3.0', 'layout': 'universal'})
        self.assertEqual(data['meta']['categories'], {'all': 2, 'cave': 0, 'mine': 0})
        self.assertEqual(result['shots'], 2)
        self.assertEqual(result['mesh_faces'], 1)

    def test_template_has_each_placeholder_once(self):
        text = TEMPLATE.read_text(encoding='utf-8')
        self.assertEqual(text.count('/*__PLOTLY_JS__*/'), 1)
        self.assertEqual(text.count('/*__MODEL_JSON__*/'), 1)
        self.assertGreaterEqual(text.count('__HTML_TITLE__'), 2)

    def test_options_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = self.write(tmp, miniature())
            with self.assertRaisesRegex(ValueError, 'start_mode'):
                build_universal_data(src, start_mode='fast')
            with self.assertRaisesRegex(ValueError, 'Surface index 3'):
                build_universal_data(src, surface_index=3)
            data = build_universal_data(src, mine=['*mine*'], start_mode='light')
        self.assertEqual({g['kind'] for g in data['groups']}, {'all', 'mine'})
        self.assertEqual(data['meta']['viewer']['start_mode'], 'light')

    def test_dossena_reference(self):
        source = ROOT / 'esempi' / 'DOSSENA_sorgente.lox'
        if not source.exists():
            self.skipTest('Dossena reference not distributed')
        data = build_universal_data(source, site_name='Dossena')
        self.assertEqual(len(data['groups']), 39)
        self.assertEqual(data['meta']['stats']['shots'], 2320)
        self.assertEqual(data['meta']['stats']['mesh_faces'], 50416)
        self.assertEqual(data['meta']['stats']['mesh_pieces'], 40)
        self.assertEqual(data['meta']['terrain']['contour_fragments'], 210)


if __name__ == '__main__':
    unittest.main()
