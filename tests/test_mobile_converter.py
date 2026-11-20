"""Portable mobile viewer regression tests (no browser dependency)."""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from convert_lox_mobile import build_mobile_data,convert,assign_categories,_matches
from lox_io import write_lox
from test_converter import miniature

class MobileConverterTests(unittest.TestCase):
    def source(self, folder, **kw):
        p=Path(folder)/'small.lox'
        write_lox(p,miniature(**kw))
        return p

    def test_default_is_neutral_no_inferred_mining(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=build_mobile_data(self.source(tmp),min_contour_length=0)
            self.assertEqual({g['kind'] for g in data['groups']},{'all'})
            self.assertEqual(data['meta']['categories'],{'all':2,'cave':0,'mine':0})
            self.assertEqual(data['meta']['stats']['mines'],0)
            self.assertEqual(data['meta']['stats']['shots'],2)

    def test_global_cave_or_mine(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=self.source(tmp)
            self.assertEqual({x['kind'] for x in build_mobile_data(src,category='cave')['groups']},{'cave'})
            self.assertEqual({x['kind'] for x in build_mobile_data(src,category='mine')['groups']},{'mine'})

    def test_explicit_mixed_classification_without_geometry_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=self.source(tmp)
            base=build_mobile_data(src)
            typed=build_mobile_data(src,mine=['*mine*'],cave=['cave_one'])
            self.assertEqual(set(x['kind'] for x in typed['groups']),{'cave','mine'})
            self.assertEqual([a['x'] for a in typed['geometry']],[a['x'] for a in base['geometry']])
            self.assertEqual([a['z'] for a in typed['geometry']],[a['z'] for a in base['geometry']])
            self.assertEqual([a.get('i') for a in typed['geometry']],[a.get('i') for a in base['geometry']])

    def test_unmatched_pattern_and_conflicts_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=self.source(tmp)
            with self.assertRaisesRegex(ValueError,'does not match'):
                build_mobile_data(src,mine=['no_such_survey'])
            with self.assertRaisesRegex(ValueError,'both cave and mine'):
                build_mobile_data(src,mine=['*one*'],cave=['*one*'])

    def test_mobile_html_single_file_no_external_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=self.source(tmp,with_surface=False,with_mesh=False)
            output=Path(tmp)/'mobile.html'
            result=convert(src,output,site_name='Generic <name>')
            page=output.read_text(encoding='utf-8')
            self.assertIn('Esplora',page)
            self.assertIn('Un dito: ruota',page)
            self.assertIn('id="joyPad"',page)
            self.assertNotIn('<script src=',page)
            self.assertNotIn('Geometria LOX non alterata',page)
            self.assertNotIn('Standalone/nessuna rete',page)
            self.assertIn('Generic &lt;name&gt;',page)
            raw=re.search(r'<script id="model-json" type="application/json">(.*?)</script>',page,re.S).group(1)
            D=json.loads(raw)
            self.assertEqual(D['meta']['categories']['all'],2)
            self.assertFalse(D['meta']['terrain']['present'])
            self.assertEqual(result['shots'],2)

    def test_dossena_mobile_reference(self):
        source=ROOT/'esempi'/'DOSSENA_sorgente.lox'
        if not source.exists():self.skipTest('Dossena reference not distributed')
        d=build_mobile_data(source,site_name='Dossena',crs='EPSG:32632')
        self.assertEqual(len(d['groups']),39)
        self.assertEqual(d['meta']['stats']['shots'],2320)
        self.assertEqual(d['meta']['stats']['mesh_faces'],50416)
        self.assertEqual(d['meta']['terrain']['contour_fragments'],210)
        self.assertEqual(d['meta']['categories']['all'],39)
        self.assertEqual(set(x['kind'] for x in d['geometry']),{'all'})

if __name__=='__main__':unittest.main()
