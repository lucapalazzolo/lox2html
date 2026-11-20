#!/usr/bin/env python3
"""Universal LOX -> portable single-file interactive HTML 3D with contour lines.

Input: Therion LOX with surveys, stations, shots, optional scraps/terrain.
Output: a single offline HTML, embedding Plotly.js and derived vector contours.
The source LOX is never modified. Ortho bitmaps and DEM raster pixels are never
embedded in the HTML; only vector contour isolines are exported.

Usage: python convert_lox_html.py input.lox -o output.html
Requires numpy, scikit-image, matplotlib (optional; not used), and the bundled
lossless LOX reader lox_io.py plus vendor/plotly.min.js.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import sys
import re
import numpy as np
from skimage.measure import find_contours, approximate_polygon
from lox_io import read_lox

ROOT=Path(__file__).resolve().parent
COLOR_CAVE='#26c6d4'
COLOR_MINE='#efaa55'
MINE_RE=re.compile(r'minier|\bmine[s]?\b|\bgallerie minerarie\b|\bquarry\b|\bcava\b',re.I)


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def parent_group(survey_id, lookup, mode='auto'):
    if mode == 'survey':
        return survey_id
    curr=survey_id
    visited=set()
    while curr in lookup and curr not in visited:
        visited.add(curr)
        node=lookup[curr]
        parent_id=node['parent']
        if mode == 'auto':
            parent_name=lookup.get(parent_id,{}).get('name','').casefold()
            if parent_name in ('grotte','miniere','caves','mines'):
                return curr
            if node['name'].casefold() in ('grotte','miniere','caves','mines','catasto'):
                return None
        if parent_id == curr or (curr != 0 and parent_id == 0):
            return curr
        curr=parent_id
    return 0 if survey_id == 0 and 0 in lookup else None


def infer_kind(sid, lookup):
    seen=set()
    while sid in lookup and sid not in seen:
        seen.add(sid)
        node=lookup[sid]
        if MINE_RE.search(node['name']+' '+node['title']):
            return 'mine'
        if node['parent']==sid:break
        sid=node['parent']
    return 'cave'


SPECIAL_SURVEYS=('catasto','surface','terrain','terreno')


def _subtrees_with_geometry(model, lookup, used):
    """Survey ids whose subtree owns at least one shot, mesh or (non-catalog) station."""
    filled=set()
    for sid in used:
        curr=sid;seen=set()
        while curr in lookup and curr not in seen and curr not in filled:
            seen.add(curr);filled.add(curr)
            parent=lookup[curr]['parent']
            if parent==curr:break
            curr=parent
    return filled


def _auto_branches(model, lookup, used):
    """Root branches for `auto` grouping when no grotte/miniere category exists.

    Empty placeholder branches (no shots, meshes or stations) are ignored, and a
    chain of single branches is followed down until it splits, so hierarchical
    Therion projects (project -> system -> caves) are grouped by cave.
    """
    filled=_subtrees_with_geometry(model, lookup, used)
    children=defaultdict(list)
    for s in model['surveys']:
        if s['parent']!=s['id']:children[s['parent']].append(s['id'])
    top={s['id']:s for s in model['surveys'] if s['id']!=0 and s['parent']==0
         and s['name'].casefold() not in SPECIAL_SURVEYS}
    non_empty={sid:s for sid,s in top.items() if sid in filled}
    if non_empty:top=non_empty
    seen=set()
    while len(top)==1:
        parent=next(iter(top))
        if parent in seen:break
        seen.add(parent)
        kids=children[parent]
        if any(lookup[c]['name'].casefold() in SPECIAL_SURVEYS for c in kids):break
        kids=[c for c in kids if c in filled]
        if len(kids)>1:
            top={c:lookup[c] for c in kids}
        elif len(kids)==1 and parent not in used:
            top={kids[0]:lookup[kids[0]]}
        else:
            break
    return top


def display_name(survey, lookup):
    """Survey title, unless it is merely inherited from the parent survey."""
    title=survey['title'];name=survey['name']
    parent=lookup.get(survey['parent'])
    if title and name and parent is not None and parent['id']!=survey['id'] and title==parent['title']:
        return name
    return title or name


def prepare_groups(model, mode='auto'):
    lookup={s['id']:s for s in model['surveys']}
    if not lookup:
        return {},{},{}
    used={s['survey'] for s in model['shots']}
    used.update(s['survey'] for s in model['scraps'])
    # Catalog entrance markers are visible as points, not a separate cave group.
    used.update(s['survey'] for s in model['stations']
                if lookup[s['survey']]['name'].casefold() not in SPECIAL_SURVEYS)
    if mode == 'survey':
        top={sid:lookup[sid] for sid in sorted(used)}
    elif mode == 'top':
        top={s['id']:s for s in model['surveys'] if s['id']!=0 and s['parent']==0}
        if not top:top={0:lookup[0]}
    else:
        top={s['id']:s for s in model['surveys']
             if lookup.get(s['parent'],{}).get('name','').casefold() in ('grotte','miniere','caves','mines')}
        if not top:
            top=_auto_branches(model, lookup, used)
        if not top:top={0:lookup[0]}
    mapping={}
    for sid in lookup:
        curr=sid;seen=set();gid=None
        while curr in lookup and curr not in seen:
            seen.add(curr)
            if curr in top:
                gid=curr;break
            parent=lookup[curr]['parent']
            if parent==curr:break
            curr=parent
        if gid is not None:
            mapping[sid]=gid
        elif sid in used:
            # A file may contain shots attached to an unusual survey branch.
            # Preserve all such geometry with a dedicated group.
            top[sid]=lookup[sid]
            mapping[sid]=sid
    return top,lookup,mapping


def stats(model, x0, y0, mode='auto'):
    top,lookup,mapping=prepare_groups(model,mode)
    groups={sid:{'id':sid,'code':s['name'],'name':display_name(s,lookup),
                 'kind':infer_kind(sid,lookup),'shots':0,'length':0,'stations':0,
                 'minZ':1e10,'maxZ':-1e10,'triangles':0,'volumeType':[],
                 'bounds':[1e12,1e12,1e12,-1e12,-1e12,-1e12]}
            for sid,s in top.items()}
    for station in model['stations']:
        gid=mapping.get(station['survey'])
        if gid not in groups:continue
        o=groups[gid];o['stations']+=1
        x,y,z=station['xyz'];o['minZ']=min(o['minZ'],z);o['maxZ']=max(o['maxZ'],z)
        b=o['bounds'];b[0]=min(b[0],x-x0);b[1]=min(b[1],y-y0);b[2]=min(b[2],z)
        b[3]=max(b[3],x-x0);b[4]=max(b[4],y-y0);b[5]=max(b[5],z)
    st_map={s['id']:s['xyz'] for s in model['stations']}
    for shot in model['shots']:
        gid=mapping.get(shot['survey'])
        if gid not in groups:raise ValueError(f'Unmapped shot survey: {shot["survey"]}')
        o=groups[gid];o['shots']+=1
        if shot['from'] in st_map and shot['to'] in st_map:
            o['length']+=math.dist(st_map[shot['from']],st_map[shot['to']])
    for scrap in model['scraps']:
        gid=mapping.get(scrap['survey'])
        if gid not in groups:raise ValueError(f'Unmapped mesh survey: {scrap["survey"]}')
        o=groups[gid];o['triangles']+=len(scrap['triangles'])
        name=lookup[scrap['survey']]['name']
        typ='estimated' if name.endswith('_estimated') else 'synthetic' if name.endswith('_synthetic') else 'measured'
        if typ not in o['volumeType']:o['volumeType'].append(typ)
        for x,y,z in scrap['points']:
            o['minZ']=min(o['minZ'],z);o['maxZ']=max(o['maxZ'],z)
            b=o['bounds'];b[0]=min(b[0],x-x0);b[1]=min(b[1],y-y0);b[2]=min(b[2],z)
            b[3]=max(b[3],x-x0);b[4]=max(b[4],y-y0);b[5]=max(b[5],z)
    return groups,lookup,st_map,mapping


def build_geometry(model,x0,y0,mode='auto',decimals=3):
    groups,lookup,st_map,mapping=stats(model,x0,y0,mode)
    assets=[]
    paths=defaultdict(lambda:[[],[],[]])
    for shot in model['shots']:
        gid=mapping[shot['survey']]
        a=st_map[shot['from']];b=st_map[shot['to']]
        xyz=paths[gid]
        xyz[0].extend((round(a[0]-x0,decimals),round(b[0]-x0,decimals),None))
        xyz[1].extend((round(a[1]-y0,decimals),round(b[1]-y0,decimals),None))
        xyz[2].extend((round(a[2],decimals),round(b[2],decimals),None))
    for gid in sorted(paths):
        g=groups[gid]
        assets.append({'type':'line','gid':gid,'name':g['name'],'kind':g['kind'],
                       'x':paths[gid][0],'y':paths[gid][1],'z':paths[gid][2]})
    for scrap in model['scraps']:
        gid=mapping[scrap['survey']]
        px=[];py=[];pz=[]
        for x,y,z in scrap['points']:
            px.append(round(x-x0,decimals));py.append(round(y-y0,decimals));pz.append(round(z,decimals))
        tris=list(scrap['triangles'])
        name=lookup[scrap['survey']]['name']
        typ='estimated' if name.endswith('_estimated') else 'synthetic' if name.endswith('_synthetic') else 'measured'
        assets.append({'type':'mesh','gid':gid,'name':groups[gid]['name'],'kind':groups[gid]['kind'],
                       'confidence':typ,'x':px,'y':py,'z':pz,
                       'i':[t[0] for t in tris],'j':[t[1] for t in tris],
                       'k':[t[2] for t in tris]})
    entrance=[]
    for s in model['stations']:
        if s['flags'] & 2:
            x,y,z=s['xyz']
            entrance.append({'name':html.escape(s['name']),'comment':html.escape(s['comment']),
                             'x':round(x-x0,decimals),'y':round(y-y0,decimals),'z':round(z,decimals),
                             'east':round(x,2),'north':round(y,2),'survey':s['survey']})
    out_groups=[]
    for gid,o in sorted(groups.items(),key=lambda p:(p[1]['kind']!='cave',p[1]['name'].casefold())):
        if o['minZ']>9e9:o['minZ']=None;o['maxZ']=None
        o['length']=round(o['length'],1)
        out_groups.append(o)
    return out_groups,assets,entrance


def build_contours(model,x0,y0,interval=10,min_length=12,epsilon=0.35,surface_index=0):
    if not model['surfaces']:
        return [],{'present':False,'reason':'LOX senza superficie; impossibile derivare isoipse'}
    if not 0 <= surface_index < len(model['surfaces']):
        raise ValueError(f'Surface index {surface_index} outside 0..{len(model["surfaces"])-1}')
    surface=model['surfaces'][surface_index]
    w,h=surface['width'],surface['height'];cal=surface['calibration']
    # LOX layout: row-major from SOUTH to NORTH. Calibration (xorigin,yorigin,dx,dy,dx2,dy2).
    raster=np.asarray(surface['elevations'],dtype=np.float64).reshape((h,w))
    good=np.isfinite(raster)&(raster>-9000)&(raster<9000)
    if not np.any(good):
        return [], {"present":False,"reason":"No valid numeric elevations in LOX surface"}
    lo=float(np.min(raster[good]));hi=float(np.max(raster[good]))
    if not bool(np.all(good)):
        raster=np.where(good,raster,np.nan)
    levels=range(int(math.ceil(lo/interval))*interval,int(math.floor(hi/interval))*interval+1,interval)
    tiers={'10':{k:[] for k in ('x','y','z')},'20':{k:[] for k in ('x','y','z')},
           '50':{k:[] for k in ('x','y','z')},'100':{k:[] for k in ('x','y','z')}}
    label_points=[]
    line_count=0
    for level in levels:
        tier='100' if level%100==0 else '20' if level%20==0 else '50' if level%50==0 else '10'
        for poly in find_contours(raster,float(level),fully_connected='low'):
            if len(poly)<2:continue
            # skimage row,col in SOUTH->NORTH direction, simplification in pixel units.
            points=approximate_polygon(poly,tolerance=epsilon)
            if len(points)<2:continue
            d=np.diff(points,axis=0)
            length=float(np.sum(np.hypot(d[:,0]*cal[5]+d[:,1]*cal[3],d[:,0]*cal[4]+d[:,1]*cal[2])))
            if length<min_length:continue
            xs=(cal[0]+points[:,1]*cal[2]+points[:,0]*cal[3]-x0).round(1).tolist()
            ys=(cal[1]+points[:,1]*cal[4]+points[:,0]*cal[5]-y0).round(1).tolist()
            dest=tiers[tier]
            dest['x'].extend(xs);dest['x'].append(None)
            dest['y'].extend(ys);dest['y'].append(None)
            dest['z'].extend([level]*len(xs));dest['z'].append(None)
            line_count+=1
            if level%100==0 and length>300 and len(label_points)<160:
                i=len(xs)//2
                label_points.append([xs[i],ys[i],int(level)])
    data=[]
    for name,coords in tiers.items():
        data.append({'type':'contour','tier':name,**coords})
    return data,{'present':True,'resolution_m':round(math.hypot(cal[2],cal[4]),2),
                 'width':w,'height':h,'min_elevation':round(lo,1),'max_elevation':round(hi,1),
                 'interval_base_m':interval,'contour_fragments':line_count,'labels':label_points,
                 'calibration':cal,'source':'griglia altimetrica interna al LOX, non ortofoto'}


def create_data(input_file,interval=10,x0=None,y0=None,site_name=None,
                group_mode='auto',crs='non dichiarato',z_label='Z (m)',
                surface_index=0,without_contours=False,min_contour_length=12,decimals=3):
    model=read_lox(input_file)
    if model['surfaces'] and not without_contours and not 0<=surface_index<len(model['surfaces']):
        raise ValueError(f'Surface index {surface_index} outside 0..{len(model["surfaces"])-1}')
    if x0 is None or y0 is None:
        stations=model['stations']
        surface=model['surfaces'][surface_index] if model['surfaces'] and not without_contours else None
        lowx=min((s['xyz'][0] for s in stations), default=float('inf'))
        lowy=min((s['xyz'][1] for s in stations), default=float('inf'))
        if not stations:
            # A LOX can contain mesh geometry without station records.
            for scrap in model['scraps']:
                for a,b,_ in scrap['points']:
                    lowx=min(lowx,a);lowy=min(lowy,b)
        if surface:
            cal=surface['calibration'];lowx=min(lowx,cal[0]);lowy=min(lowy,cal[1])
        if not math.isfinite(lowx):lowx=0.
        if not math.isfinite(lowy):lowy=0.
        x0=math.floor(lowx/1000)*1000 if x0 is None else x0
        y0=math.floor(lowy/1000)*1000 if y0 is None else y0
    groups,geom,entrances=build_geometry(model,x0,y0,group_mode,decimals)
    if without_contours:
        contours,info=[],{'present':False,'reason':'Contours explicitly disabled'}
    else:
        contours,info=build_contours(model,x0,y0,interval,min_length=min_contour_length,surface_index=surface_index)
    site_name=site_name or Path(input_file).stem
    stats_data={'sections':len(groups),'caves':sum(o['kind']=='cave' for o in groups),
                'mines':sum(o['kind']=='mine' for o in groups),'stations':len(model['stations']),
                'shots':len(model['shots']),
                'mesh_vertices':sum(len(a['x']) for a in geom if a['type']=='mesh'),
                'mesh_faces':sum(len(a['i']) for a in geom if a['type']=='mesh'),
                'entrances':len(entrances),'surfaces_in_lox':len(model['surfaces']),
                'bitmaps_in_lox':len(model['bitmaps'])}
    if sum(g['shots'] for g in groups)!=stats_data['shots']:
        raise ValueError('Internal mapping lost some surveyed shots')
    if stats_data['mesh_faces']!=sum(len(v['triangles']) for v in model['scraps']):
        raise ValueError('Internal mapping lost some mesh faces')
    data={'meta':{'title':site_name+' / Modello ipogeo 3D','source':Path(input_file).name,
                  'sha256':sha256(input_file),
                  'generated_utc':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                  'crs':crs,'z_label':z_label,'origin':[x0,y0,0],
                  'coordinate_decimals':decimals,
                  'stats':stats_data,'terrain':info},
          'groups':groups,'geometry':geom,'contours':contours,'entrances':entrances}
    return data


def render_html(data,output_file,assets=None,template_file=None,qa_json=None):
    assets=Path(assets or ROOT/'vendor/plotly.min.js')
    template_file=Path(template_file or ROOT/'viewer_template.html')
    lib=assets.read_text(encoding='utf-8')
    template=template_file.read_text(encoding='utf-8')
    # Escape HTML script end tags even if they appear in survey names or comments.
    j=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/')
    if '/*__PLOTLY_JS__*/' not in template or '/*__MODEL_JSON__*/' not in template:
        raise ValueError('Invalid viewer template: missing placeholders')
    title=html.escape(data['meta']['title'].split(' / ')[0],quote=True)
    page=template.replace('__HTML_TITLE__',title).replace('/*__PLOTLY_JS__*/',lib).replace('/*__MODEL_JSON__*/',j)
    output_file=Path(output_file)
    output_file.parent.mkdir(parents=True,exist_ok=True)
    output_file.write_text(page,encoding='utf-8')
    if qa_json:
        path=Path(qa_json);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data['meta'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'html':str(output_file),'bytes':output_file.stat().st_size,
            'groups':len(data['groups']), 'shots':data['meta']['stats']['shots'],
            'mesh_faces':data['meta']['stats']['mesh_faces'],
            'contour_fragments':data['meta']['terrain'].get('contour_fragments',0),
            'input_sha256':data['meta']['sha256']}


def main(argv=None):
    ap=argparse.ArgumentParser(description='Convert any Therion LOX to a single offline 3D HTML; no source changes')
    ap.add_argument('lox',type=Path,help='source LOX file')
    ap.add_argument('-o','--output',type=Path,help='output HTML; default: same basename under output/')
    ap.add_argument('--origin',nargs=2,type=float,metavar=('X0','Y0'),default=[None,None],
                    help='local coordinate origin; auto if omitted')
    ap.add_argument('--site-name',help='viewer title; default: LOX filename')
    ap.add_argument('--crs',default='non dichiarato',help='text label only; no CRS transform is performed')
    ap.add_argument('--z-label',default='Z (m)',help='vertical axis title; no vertical datum is assumed')
    ap.add_argument('--group-mode',choices=['auto','survey','top'],default='auto')
    ap.add_argument('--surface-index',type=int,default=0,help='surface index when LOX contains multiple surfaces')
    ap.add_argument('--no-contours',action='store_true',help='ignore embedded terrain')
    ap.add_argument('--coordinate-decimals',type=int,default=3,
                    help='round drawing coordinates to N decimal places, default 3 (millimeters)')
    ap.add_argument('--min-contour-length',type=float,default=12,
                    help='minimum length of contour fragment in meters')
    ap.add_argument('--assets',type=Path,default=ROOT/'vendor/plotly.min.js')
    ap.add_argument('--qa-json',type=Path,help='write provenance and counts to JSON')
    args=ap.parse_args(argv)
    if not args.lox.is_file():ap.error(f'File not found: {args.lox}')
    if args.min_contour_length < 0:ap.error('--min-contour-length must be >= 0')
    if args.surface_index < 0:ap.error('--surface-index must be >= 0')
    if not 0 <= args.coordinate_decimals <= 9:ap.error('--coordinate-decimals must be 0..9')
    dest=args.output or ROOT/'output'/(args.lox.stem+'_3D.html')
    data=create_data(args.lox,x0=args.origin[0],y0=args.origin[1],
                     site_name=args.site_name,group_mode=args.group_mode,
                     crs=args.crs,z_label=args.z_label,
                     surface_index=args.surface_index,without_contours=args.no_contours,
                     min_contour_length=args.min_contour_length,decimals=args.coordinate_decimals)
    result=render_html(data,dest,args.assets,qa_json=args.qa_json)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if len(data['meta']['terrain'].get('reason','')):
        print('INFO: '+data['meta']['terrain']['reason'],file=sys.stderr)
    if data['meta']['stats']['surfaces_in_lox'] > 1:
        print('WARNING: multiple LOX surfaces; selected surface-index '+str(args.surface_index),file=sys.stderr)


if __name__=='__main__':main()
