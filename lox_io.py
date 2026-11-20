#!/usr/bin/env python3
"""Lettura/scrittura LOX interoperabile, senza compilatore Therion.

Layout implementato dalla serializzazione ufficiale Therion lxFile.cxx/lxFile.h:
https://github.com/therion/therion/tree/master/src/common-utils
Tipi: 1 survey, 2 station, 3 shot, 4 scrap, 5 surface, 6 bitmap.
Ogni chunk contiene <4I (tipo, byte record, numero record, byte dati), record e
dati variabili. Interi uint32 e floating-point IEEE754 binary64 little-endian.

L'API usa dizionari; tutte le coordinate sono XYZ cartesiane in metri.
Nessuna compensazione, conversione di CRS o ricostruzione LRUD e' implicita.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import numbers
from pathlib import Path
import struct
import sys
from collections.abc import Sequence

STATION_SURFACE=1
STATION_ENTRANCE=2
STATION_FIXED=4
STATION_CONTINUATION=8
STATION_HAS_WALLS=16
SHOT_SURFACE=1
SHOT_DUPLICATE=2
SHOT_NOT_VISIBLE=4
SHOT_NOT_LRUD=8
SHOT_SPLAY=16
SECTION_NONE=0
SECTION_OVAL=1
SECTION_SQUARE=2
SECTION_DIAMOND=3
SECTION_TUNNEL=4
BITMAP_JPEG=0
BITMAP_PNG=1

_HEADER=struct.Struct("<4I")
_RECORDS={1:struct.Struct("<6I"),2:struct.Struct("<7I3d"),
          3:struct.Struct("<2I8d3Id"),4:struct.Struct("<8I"),
          5:struct.Struct("<5I6d"),6:struct.Struct("<4I6d")}
_KEYS={1:"surveys",2:"stations",3:"shots",4:"scraps",5:"surfaces",6:"bitmaps"}


class LoxError(ValueError):
    pass


class PackedRows(Sequence):
    """Vista di tuple binarie senza trasformare mesh grandi in milioni di oggetti."""
    def __init__(self,data,fmt):
        self.data=memoryview(data)
        self.fmt=fmt
        self.record=struct.Struct(fmt)
        if len(self.data)%self.record.size:
            raise LoxError("Dimensione array binario non multipla della dimensione record.")
    def __len__(self):
        return len(self.data)//self.record.size
    def __getitem__(self,index):
        if isinstance(index,slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if index<0:index+=len(self)
        if not 0<=index<len(self):raise IndexError(index)
        return self.record.unpack_from(self.data,index*self.record.size)
    def __iter__(self):
        return self.record.iter_unpack(self.data)


def _blob(data,offset,size):
    if offset>len(data) or size>len(data)-offset:
        raise LoxError(f"Puntatore LOX fuori dal chunk: offset={offset}, size={size}, chunk={len(data)}")
    return memoryview(data)[offset:offset+size]


def _string(data,offset,size):
    if not size:return ""
    raw=bytes(_blob(data,offset,size))
    if not raw.endswith(b"\0"):
        raise LoxError("Stringa LOX non terminata con NUL.")
    return raw[:-1].decode("utf-8",errors="strict")


def _doubles_from(data):
    result=array.array("d")
    result.frombytes(data)
    if sys.byteorder!="little":result.byteswap()
    return result


def read_lox(path,validate=True):
    """Legge tutti i chunk; mesh in PackedRows, elevazioni in array('d')."""
    model={key:[] for key in _KEYS.values()}
    chunks=[]
    with Path(path).open("rb") as handle:
        while True:
            head=handle.read(_HEADER.size)
            if not head:break
            if len(head)!=_HEADER.size:raise LoxError("Header LOX troncato.")
            kind,recbytes,count,datasize=_HEADER.unpack(head)
            if kind not in _RECORDS:raise LoxError(f"Tipo chunk LOX non supportato: {kind}")
            fmt=_RECORDS[kind]
            if recbytes!=count*fmt.size:
                raise LoxError(f"Dimensione record incoerente nel chunk {kind}: {recbytes}/{count}.")
            records=handle.read(recbytes)
            data=handle.read(datasize)
            if len(records)!=recbytes or len(data)!=datasize:
                raise LoxError(f"Chunk LOX {kind} troncato.")
            chunks.append({"type":kind,"records":count,"record_bytes":recbytes,"data_bytes":datasize})
            target=model[_KEYS[kind]]
            for row in fmt.iter_unpack(records):
                if kind==1:
                    i,np,ns,parent,tp,ts=row
                    target.append({"id":i,"parent":parent,"name":_string(data,np,ns),"title":_string(data,tp,ts)})
                elif kind==2:
                    i,s,np,ns,cp,cs,flags,x,y,z=row
                    target.append({"id":i,"survey":s,"name":_string(data,np,ns),"comment":_string(data,cp,cs),"flags":flags,"xyz":(x,y,z)})
                elif kind==3:
                    target.append({"from":row[0],"to":row[1],"from_lrud":row[2:6],"to_lrud":row[6:10],
                                   "flags":row[10],"section":row[11],"survey":row[12],"threshold":row[13]})
                elif kind==4:
                    i,s,nv,vp,vs,nt,tp,ts=row
                    if vs!=nv*24 or ts!=nt*12:raise LoxError("Array mesh LOX incoerente.")
                    target.append({"id":i,"survey":s,"points":PackedRows(_blob(data,vp,vs),"<3d"),
                                   "triangles":PackedRows(_blob(data,tp,ts),"<3I")})
                elif kind==5:
                    i,w,h,dp,ds,*cal=row
                    if ds!=w*h*8:raise LoxError("Array quota LOX incoerente con width/height.")
                    target.append({"id":i,"width":w,"height":h,"calibration":cal,
                                   "elevations":_doubles_from(_blob(data,dp,ds))})
                elif kind==6:
                    s,t,dp,ds,*cal=row
                    target.append({"surface":s,"type":t,"calibration":cal,"data":bytes(_blob(data,dp,ds))})
    model["chunks"]=chunks
    if validate:validate_model(model)
    return model


class _Data:
    def __init__(self):self.bytes=bytearray()
    def append(self,data):
        if not data:return (0,0)
        pos=len(self.bytes);self.bytes.extend(data)
        return (pos,len(data))
    def string(self,text):
        text=str(text or "")
        if "\0" in text:raise LoxError("NUL non ammesso nei nomi LOX.")
        return self.append(text.encode("utf-8")+b"\0") if text else (0,0)


def _pack_rows(rows,fmt):
    if isinstance(rows,PackedRows) and rows.fmt==fmt:
        return rows.data
    record=struct.Struct(fmt)
    data=bytearray(len(rows)*record.size)
    for i,row in enumerate(rows):record.pack_into(data,i*record.size,*row)
    return data


def _pack_doubles(values):
    data=array.array("d",values)
    if sys.byteorder!="little":data.byteswap()
    return data.tobytes()


def _finite(values,name):
    if not all(math.isfinite(float(v)) for v in values):
        raise LoxError(f"Valori non finiti in {name}; nessun valore sostituito con zero.")


def validate_model(model):
    surveys=model.get("surveys",[])
    stations=model.get("stations",[])
    sid={s["id"] for s in surveys}
    stid={s["id"] for s in stations}
    if [s["id"] for s in surveys]!=list(range(len(surveys))):
        raise LoxError("Gli ID survey devono essere ordinati e densi da 0.")
    if [s["id"] for s in stations]!=list(range(len(stations))):
        raise LoxError("Gli ID stazione devono essere ordinati e densi da 0.")
    for survey in surveys:
        if survey.get("parent",survey["id"]) not in sid:raise LoxError("Survey padre inesistente.")
    for station in stations:
        if station["survey"] not in sid:raise LoxError("Stazione associata a survey inesistente.")
        if len(station["xyz"])!=3:raise LoxError("Ogni stazione richiede XYZ.")
        _finite(station["xyz"],"coordinate stazione")
    for shot in model.get("shots",[]):
        if shot["from"] not in stid or shot["to"] not in stid:raise LoxError("Visata con stazione inesistente.")
        if shot["survey"] not in sid:raise LoxError("Visata associata a survey inesistente.")
        if shot.get("section",0) not in range(5):raise LoxError("Tipo sezione LOX non valido.")
        for key in ("from_lrud","to_lrud"):
            if len(shot.get(key,[-999]*4))!=4:raise LoxError("Le sezioni devono avere quattro valori LRUD.")
    for scrap in model.get("scraps",[]):
        if scrap["survey"] not in sid:raise LoxError("Mesh associata a survey inesistente.")
        nv=len(scrap["points"])
        for p in scrap["points"]:
            if len(p)!=3:raise LoxError("Vertice mesh senza XYZ.")
            _finite(p,"vertici mesh")
        for tri in scrap["triangles"]:
            if len(tri)!=3 or any(not isinstance(i,numbers.Integral) or i<0 or i>=nv for i in tri):
                raise LoxError("Triangolo con indice fuori dalla mesh.")
    sfid={s["id"] for s in model.get("surfaces",[])}
    if len(sfid)!=len(model.get("surfaces",[])):raise LoxError("ID superficie duplicati.")
    for surface in model.get("surfaces",[]):
        w,h=surface["width"],surface["height"]
        if w<2 or h<2 or len(surface["elevations"])!=w*h:raise LoxError("Dimensioni griglia superficie non valide.")
        if len(surface["calibration"])!=6:raise LoxError("Calibrazione superficie richiede 6 valori.")
        _finite(surface["elevations"],"quote superficie")
        _finite(surface["calibration"],"calibrazione superficie")
    for bitmap in model.get("bitmaps",[]):
        if bitmap["surface"] not in sfid:raise LoxError("Bitmap associata a superficie inesistente.")
        if bitmap.get("type",0) not in (BITMAP_JPEG,BITMAP_PNG):raise LoxError("Tipo bitmap non valido.")
        if len(bitmap["calibration"])!=6:raise LoxError("Calibrazione bitmap richiede 6 valori.")
        _finite(bitmap["calibration"],"calibrazione bitmap")
        data=bitmap["data"]
        if bitmap.get("type",0)==BITMAP_JPEG and not data.startswith(b"\xff\xd8"):
            raise LoxError("La texture dichiarata JPEG non ha una firma JPEG.")
        if bitmap.get("type",0)==BITMAP_PNG and not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise LoxError("La texture dichiarata PNG non ha una firma PNG.")


def write_lox(path,model,validate=True):
    """Scrive un LOX; mesh, LRUD e quote restano quelli esplicitamente forniti."""
    if validate:validate_model(model)
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".part")
    with temporary.open("wb") as handle:
        for kind,key in _KEYS.items():
            items=model.get(key,[])
            if not items:continue
            fmt=_RECORDS[kind]
            records=bytearray(len(items)*fmt.size)
            data=_Data()
            for idx,item in enumerate(items):
                if kind==1:
                    args=(item["id"],*data.string(item.get("name","")),item.get("parent",item["id"]),*data.string(item.get("title","")))
                elif kind==2:
                    args=(item["id"],item["survey"],*data.string(item.get("name","")),*data.string(item.get("comment","")),item.get("flags",0),*item["xyz"])
                elif kind==3:
                    section=item.get("section",SECTION_NONE)
                    args=(item["from"],item["to"],*item.get("from_lrud",[-999.0]*4),*item.get("to_lrud",[-999.0]*4),
                          item.get("flags",SHOT_NOT_LRUD if section==SECTION_NONE else 0),section,item["survey"],item.get("threshold",60.0))
                elif kind==4:
                    points,triangles=item["points"],item["triangles"]
                    args=(item["id"],item["survey"],len(points),*data.append(_pack_rows(points,"<3d")),
                          len(triangles),*data.append(_pack_rows(triangles,"<3I")))
                elif kind==5:
                    args=(item["id"],item["width"],item["height"],*data.append(_pack_doubles(item["elevations"])),*item["calibration"])
                else:
                    args=(item["surface"],item.get("type",BITMAP_JPEG),*data.append(item["data"]),*item["calibration"])
                fmt.pack_into(records,idx*fmt.size,*args)
            if len(records)>0xffffffff or len(data.bytes)>0xffffffff:raise LoxError("Chunk oltre il limite LOX uint32.")
            handle.write(_HEADER.pack(kind,len(records),len(items),len(data.bytes)))
            handle.write(records)
            handle.write(data.bytes)
    temporary.replace(path)
    return summarize(model)


def summarize(model):
    result={key:len(model.get(key,[])) for key in _KEYS.values()}
    result["mesh_points"]=sum(len(s["points"]) for s in model.get("scraps",[]))
    result["mesh_triangles"]=sum(len(s["triangles"]) for s in model.get("scraps",[]))
    result["surface_nodes"]=sum(s["width"]*s["height"] for s in model.get("surfaces",[]))
    result["texture_bytes"]=sum(len(s["data"]) for s in model.get("bitmaps",[]))
    if model.get("stations"):
        xyz=[s["xyz"] for s in model["stations"]]
        result["bounds"]={"min":[min(v[i] for v in xyz) for i in range(3)],"max":[max(v[i] for v in xyz) for i in range(3)]}
    return result


def add_terrain(model,terrain_dir,surface_id=None):
    """Aggiunge DTM+JPEG preparati da terrain.py, conservando le quote delle grotte."""
    root=Path(terrain_dir)
    meta=json.loads((root/"terrain_metadata.json").read_text())
    if meta.get("epsg")!=32632:raise LoxError("Terreno con CRS diverso da EPSG:32632.")
    spec=meta["dtm"]
    # AAIGrid e' nord->sud, storage LOX e' sud->nord.
    with (root/"dtm.asc").open() as handle:
        for _ in range(6):handle.readline()
        rows=[[float(v) for v in line.split()] for line in handle if line.strip()]
    if len(rows)!=spec["height"] or any(len(r)!=spec["width"] for r in rows):
        raise LoxError("DTM ASCII non coerente con metadata.json.")
    offset=float(meta.get("z_offset_m",0))
    heights=array.array("d",(z+offset for row in reversed(rows) for z in row))
    _finite(heights,"quote DTM")
    if any(z<-1000 or z>10000 for z in heights):raise LoxError("DTM contiene sentinelle NoData.")
    r=spec["pixel_size"]
    xmin,ymin,xmax,ymax=spec["bbox"]
    if surface_id is None:surface_id=max((s["id"] for s in model.get("surfaces",[])),default=-1)+1
    model.setdefault("surfaces",[]).append({"id":surface_id,"width":spec["width"],"height":spec["height"],
        "calibration":[xmin+r/2,ymin+r/2,r,0.0,0.0,r],"elevations":heights})
    ortho=meta.get("ortho")
    if ortho:
        x0,y0,_,_=ortho["bbox"]
        pixel=ortho["pixel_size"]
        model.setdefault("bitmaps",[]).append({"surface":surface_id,"type":BITMAP_JPEG,
            "calibration":[x0,y0,pixel,0.0,0.0,pixel],"data":(root/"ortofoto.jpg").read_bytes()})
    return model


def main(argv=None):
    parser=argparse.ArgumentParser(description="Ispeziona e valida un file LOX; non modifica il file.")
    parser.add_argument("path",type=Path)
    parser.add_argument("--roundtrip",type=Path,help="Riscrive lo stesso modello in un nuovo LOX")
    parser.add_argument("--terrain",type=Path,help="Aggiunge il terreno preparato da terrain.py; richiede --roundtrip")
    args=parser.parse_args(argv)
    try:
        model=read_lox(args.path)
        if args.terrain:
            if not args.roundtrip:raise LoxError("--terrain richiede --roundtrip per indicare il nuovo file LOX.")
            add_terrain(model,args.terrain)
        if args.roundtrip:write_lox(args.roundtrip,model)
        print(json.dumps(summarize(model),ensure_ascii=False,indent=2))
    except (LoxError,OSError,UnicodeError,struct.error) as exc:
        print(f"ERRORE LOX: {exc}",file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
