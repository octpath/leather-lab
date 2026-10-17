"""Inspect actual extrusion paths. Inspection G-code is never a print deliverable."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

import numpy as np
from shapely import distance
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import nearest_points, unary_union
from reinforcement import load_config
from verify import FILES, KEYS, expected_holes, expected_profile

SOURCE=Path(__file__).resolve().parent
PROJECT=SOURCE.parent
SHIFT=np.array([10.,10.])


def read_paths(path):
    position=np.zeros(3);relative=True;last_e=0.;kind='';width=.42;paths=[]
    for raw in path.read_text().splitlines():
        if raw.startswith(';TYPE:'):kind=raw[6:]
        if raw.startswith(';WIDTH:'):width=float(raw[7:])
        command=raw.split(';',1)[0].strip()
        if command=='M83':relative=True
        elif command=='M82':relative=False
        elif command.startswith('G92 '):
            if 'E' in command:last_e=float(re.search(r'E([-\d.]+)',command).group(1))
        elif re.match(r'^G[01]\s',command):
            fields={k:float(v) for k,v in re.findall(r'([XYZEF])([-\d.]+)',command)}
            target=position.copy()
            for i,k in enumerate('XYZ'):
                if k in fields:target[i]=fields[k]
            extrusion=fields.get('E',0.) if relative else fields.get('E',last_e)-last_e
            if 'E' in fields:last_e=fields['E']
            if extrusion>0 and np.linalg.norm(target[:2]-position[:2])>1e-7:
                paths.append({'a':position[:2]-SHIFT,'b':target[:2]-SHIFT,
                              'z':round(float(target[2]),4),'width':width,'kind':kind})
            position=target
    return paths


def layer_paths(paths,z):
    return [p for p in paths if abs(p['z']-z)<.001 and p['kind']!='Custom']


def crossing_count(paths,a,b):
    probe=LineString([a,b]);points=[]
    for p in paths:
        if p['kind'] not in ['Perimeter','External perimeter','Gap fill']:continue
        hit=probe.intersection(LineString([p['a'],p['b']]))
        if hit.is_empty:continue
        for q in list(hit.geoms) if hasattr(hit,'geoms') else [hit]:
            if q.geom_type=='Point' and all(q.distance(old)>.03 for old in points):points.append(q)
    return len(points)


def inspect(data,config,letter,paths):
    holes=expected_holes(data,letter);part=data[KEYS[letter]]
    width=max(x for x,y in part['outline']);height=max(y for x,y in part['outline'])
    outer=Polygon([(x,height-y) for x,y in part['outline']])
    # Check the narrowest original guide-to-free-edge web, not just a broad area.
    center=min((Point(x,y) for x,y,d in holes),key=lambda q:q.distance(outer.boundary))
    index=np.argmin(np.linalg.norm(holes[:,:2]-[center.x,center.y],axis=1))
    edge=nearest_points(center,outer.boundary)[1]
    vector=np.array([center.x-edge.x,center.y-edge.y]);vector/=np.linalg.norm(vector)
    end=np.array([center.x,center.y])-vector*(holes[index,2]/2+.01)
    web_probe=([edge.x,edge.y],end)
    base_checks=[]
    for z in [.2,1.,2.]:
        layer=layer_paths(paths,z)
        assert layer,(letter,'missing base layer',z)
        lines=MultiLineString([[p['a'],p['b']] for p in layer])
        # Gap fill can have a different width; pair each segment with its own width.
        segments=np.array([LineString([p['a'],p['b']]) for p in layer],dtype=object)
        points=np.array([Point(x,y) for x,y,d in holes],dtype=object)
        widths=np.array([p['width'] for p in layer])
        errors=distance(points[:,None],segments[None,:])-widths[None,:]/2-holes[:,2,None]/2
        opening=float(errors.min())
        assert opening>-.04,(letter,'tool opening reduced',z,opening)
        count=crossing_count(layer,*web_probe)
        assert count>=3,(letter,'thin original edge web',z,count)
        void_windows=expected_profile(data,config,letter,'outline').difference(
            expected_profile(data,config,letter,'base'))
        safe_void=void_windows.buffer(-.08)
        assert lines.intersection(safe_void).is_empty,(letter,'extrusion inside void',z)
        base_checks.append({'z':z,'minimum_tool_radius_error_mm':opening,'narrow_web_paths':count})
    if letter=='A':
        rib_center=np.array([width/2,height-87]);normal=np.array([1.,0.])
    elif letter=='B':
        rib_center=np.array([20.,height-18]);normal=np.array([0.,1.])
    else:
        rib_center=np.array([20. if letter=='C' else width-20,height-18.5]);normal=np.array([0.,1.])
    rib_checks=[]
    for z in [2.4,2.8,3.4]:
        layer=layer_paths(paths,z)
        assert layer,(letter,'missing ribs',z)
        half=config['parameters']['rib_width']/2+.01
        count=crossing_count(layer,rib_center-normal*half,rib_center+normal*half)
        assert count>=3,(letter,'rib needs at least three paths',z,count)
        # A small 0.02 mm allowance joins numerical seams between deposited lines.
        swept=unary_union([LineString([p['a'],p['b']]).buffer(p['width']/2+.02,
                          quad_segs=3) for p in layer])
        components=len(swept.geoms) if swept.geom_type=='MultiPolygon' else 1
        assert components==1,(letter,'disconnected deposited rib paths',z,components)
        field='root' if z<=2+config['parameters']['root_height']+.1001 else 'top'
        target=expected_profile(data,config,letter,field)
        lines=MultiLineString([[p['a'],p['b']] for p in layer])
        assert lines.difference(target.buffer(.04)).is_empty,(letter,'unsupported rib extrusion',z)
        rib_checks.append({'z':z,'rib_crossing_paths':count,'connected_deposition_regions':components,
                           'section_profile':field})
    return {'base_layers':base_checks,'rib_layers':rib_checks,
            'narrow_web_probe':[list(map(float,p)) for p in web_probe],
            'rib_probe_center':rib_center.tolist(),
            'stl_sha256':hashlib.sha256((PROJECT/'3d'/FILES[letter]).read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slicer',default=shutil.which('prusa-slicer'))
    parser.add_argument('--work-dir',type=Path)
    parser.add_argument('--reuse',action='store_true',help='Reuse inspection G-code in work-dir')
    args=parser.parse_args()
    if not args.slicer:raise SystemExit('PrusaSlicer CLI is required for path inspection.')
    data=json.loads((SOURCE/'geometry.json').read_text());config=load_config()
    help_result=subprocess.run([args.slicer,'--help'],capture_output=True,text=True,check=True)
    report={'checked_at':datetime.now(timezone.utc).isoformat(),
            'slicer':help_result.stdout.splitlines()[0],'profile':'source/slice-check.ini',
            'profile_sha256':hashlib.sha256((SOURCE/'slice-check.ini').read_bytes()).hexdigest(),
            'scope':'Geometric path inspection only; not a P1S machine/material validation.',
            'physical_print_verified':False,'parts':{}}
    temporary=tempfile.TemporaryDirectory() if args.work_dir is None else None
    work=Path(temporary.name) if temporary else args.work_dir
    work.mkdir(parents=True,exist_ok=True)
    for letter in KEYS:
        output=work/(letter.lower()+'-inspection.gcode')
        if not args.reuse:
            command=[args.slicer,'--threads','2','--load',str(SOURCE/'slice-check.ini'),
                     '--dont-arrange','--align-xy','10,10','--export-gcode','--output',str(output),
                     str(PROJECT/'3d'/FILES[letter])]
            done=subprocess.run(command,capture_output=True,text=True)
            if done.returncode:raise RuntimeError(done.stdout+'\n'+done.stderr)
        report['parts'][letter]=inspect(data,config,letter,read_paths(output))
        print(letter,'extrusion paths PASS',flush=True)
    (SOURCE/'slice-qa.json').write_text(json.dumps(report,indent=2)+'\n')
    if temporary:temporary.cleanup()


if __name__=='__main__':main()
