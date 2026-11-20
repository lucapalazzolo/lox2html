import json
import re
import tempfile
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lox_io import write_lox,read_lox
from convert_lox_html import create_data,render_html


def miniature(with_surface=True,with_mesh=True,bad_surface=False):
    model={
        'surveys':[
            {'id':0,'parent':0,'name':'root','title':'Project'},
            {'id':1,'parent':0,'name':'project','title':'Survey project'},
            {'id':2,'parent':1,'name':'cave_one','title':'Cave One'},
            {'id':3,'parent':1,'name':'mine_two','title':'Mine Two'},
            {'id':4,'parent':0,'name':'catasto','title':'External catalog'}],
        'stations':[
            {'id':0,'survey':2,'name':'A','comment':'','flags':2,'xyz':(1000.,2000.,25.)},
            {'id':1,'survey':2,'name':'B','comment':'','flags':0,'xyz':(1020.,2000.,20.)},
            {'id':2,'survey':3,'name':'C','comment':'','flags':0,'xyz':(1000.,2010.,20.)},
            {'id':3,'survey':3,'name':'D','comment':'','flags':0,'xyz':(1030.,2010.,12.)},
            {'id':4,'survey':4,'name':'CAT','comment':'catalog marker','flags':2,'xyz':(1001.,2001.,23.)}],
        'shots':[
            {'from':0,'to':1,'survey':2},
            {'from':2,'to':3,'survey':3}],
        'scraps':[
            {'id':0,'survey':2,'points':[(1000.,2000.,25.),(1010.,2000.,24.),(1010.,2002.,24.)],
             'triangles':[(0,1,2)]}] if with_mesh else [],
        'surfaces':[], 'bitmaps':[]
    }
    if with_surface:
        values=[-9999.]*9 if bad_surface else [12.,16.,20.,15.,19.,23.,18.,22.,26.]
        model['surfaces']=[{'id':0,'width':3,'height':3,
                            'calibration':[998.,1998.,5.,0.,0.,5.],'elevations':values}]
    return model

class ConverterTests(unittest.TestCase):
    def build(self,**kwargs):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'generic.lox';write_lox(p,miniature(**kwargs))
            return create_data(p,min_contour_length=0)

    def test_nested_non_dossena_surveys_auto_split(self):
        d=self.build()
        self.assertEqual(len(d['groups']),2)
        self.assertEqual((d['meta']['stats']['caves'],d['meta']['stats']['mines']),(1,1))
        self.assertEqual(d['meta']['stats']['shots'],2)
        self.assertEqual(d['meta']['stats']['mesh_faces'],1)
        self.assertEqual(d['meta']['stats']['entrances'],2)
        self.assertEqual(len([g for g in d['geometry'] if g['type']=='mesh']),1)
        self.assertTrue(d['meta']['terrain']['present'])
        self.assertTrue(d['contours'])

    def test_no_surface_and_no_mesh_is_supported(self):
        d=self.build(with_surface=False,with_mesh=False)
        self.assertEqual(d['meta']['stats']['shots'],2)
        self.assertEqual(d['meta']['stats']['mesh_faces'],0)
        self.assertFalse(d['meta']['terrain']['present'])
        self.assertFalse(d['contours'])
        self.assertEqual(len(d['geometry']),2)

    def test_nodata_surface_does_not_invent_zero_height(self):
        d=self.build(bad_surface=True)
        self.assertFalse(d['meta']['terrain']['present'])
        self.assertEqual(d['meta']['stats']['mesh_faces'],1)

    def test_html_one_file_and_untrusted_html_escaped(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'source.lox';out=Path(td)/'single.html'
            write_lox(p,miniature(with_surface=False))
            d=create_data(p,site_name='<Danger & Name>')
            result=render_html(d,out)
            html=out.read_text()
            self.assertIn('&lt;Danger &amp; Name&gt;',html)
            self.assertNotIn('<script src=',html)
            self.assertIn('Plotly',html)
            self.assertEqual(result['shots'],2)
            self.assertIn('model-json',html)
            raw=re.search(r'<script id="model-json" type="application/json">(.*?)</script>',html,re.S).group(1)
            self.assertEqual(json.loads(raw)['meta']['stats']['shots'],2)

    def test_root_only_with_own_shots(self):
        with tempfile.TemporaryDirectory() as td:
            m=miniature(with_surface=False,with_mesh=False)
            m['surveys']=[m['surveys'][0]]
            m['stations']=m['stations'][:2]
            for x in m['stations']:x['survey']=0
            m['shots']=m['shots'][:1];m['shots'][0]['survey']=0
            p=Path(td)/'root.lox';write_lox(p,m)
            d=create_data(p)
            self.assertEqual(len(d['groups']),1)
            self.assertEqual(d['meta']['stats']['shots'],1)

    def test_surface_only_lox(self):
        with tempfile.TemporaryDirectory() as td:
            m={'surveys':[],'stations':[],'shots':[],'scraps':[],
               'surfaces':[{'id':0,'width':3,'height':3,
                            'calibration':[0.,0.,5.,0.,0.,5.],
                            'elevations':[11.,15.,19.,14.,18.,22.,17.,21.,25.]}],
               'bitmaps':[]}
            path=Path(td)/'surface_only.lox'
            write_lox(path,m)
            d=create_data(path,min_contour_length=0)
            self.assertEqual(len(d['groups']),0)
            self.assertEqual(d['meta']['stats']['shots'],0)
            self.assertTrue(d['meta']['terrain']['present'])

    def test_group_mode_survey_retains_mesh_and_shots(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'survey_group.lox'
            write_lox(path,miniature(with_surface=False))
            d=create_data(path,group_mode='survey')
            self.assertEqual(d['meta']['stats']['shots'],2)
            self.assertEqual(d['meta']['stats']['mesh_faces'],1)
            self.assertEqual(len(d['groups']),2)

    def test_dossena_reference_full_geometry_and_contours(self):
        p=ROOT/'esempi/DOSSENA_sorgente.lox'
        if not p.exists():self.skipTest('Optional Dossena reference not bundled')
        d=create_data(p,site_name='Dossena',crs='EPSG:32632')
        self.assertEqual(d['meta']['stats']['shots'],2320)
        self.assertEqual(d['meta']['stats']['mesh_faces'],50416)
        self.assertEqual(d['meta']['stats']['entrances'],47)
        self.assertEqual(len(d['groups']),39)
        self.assertEqual(d['meta']['terrain']['contour_fragments'],210)
        self.assertEqual(len([x for x in d['geometry'] if x['type']=='mesh']),40)

if __name__=='__main__':unittest.main()
