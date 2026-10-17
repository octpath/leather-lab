"""Generate CAD coordinate data and render the default marking templates."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

import numpy as np
import trimesh
from reinforcement import check_scad_defaults, load_config, part_spec, validate

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parent
SCAD = PROJECT / '3d/a5-leather-coin-case-templates.scad'
OUTPUTS = {
    'A': 'a-body-template.stl',
    'B': 'b-flap-liner-template.stl',
    'C': 'c-left-gusset-template.stl',
    'D': 'd-right-gusset-template.stl',
    'layout': 'a5-leather-coin-case-templates.stl',
}
KEYS = {'A':'body','B':'liner','C':'gusset_left','D':'gusset_right'}


def write_data():
    data = json.loads((SOURCE/'geometry.json').read_text())
    reinforcement = load_config()
    check_scad_defaults(SCAD,data,reinforcement)
    validate(data,reinforcement)
    lines = ['// Generated from geometry.json by build_templates.py; units: mm.']
    for part,key in KEYS.items():
        d=data[key];letter=part.lower()
        max_x=max(p[0] for p in d['outline']);max_y=max(p[1] for p in d['outline'])
        hardware=[]
        if 'snap' in d:
            h=d['snap'];hardware.append([h['x'],h['y'],h['punch_no'],False])
        if 'optional_snap' in d:
            h=d['optional_snap'];hardware.append([h['x'],h['y'],h['punch_no'],True])
        values={f'outline_{letter}':d['outline'],
                f'guides_{letter}':[[h['x'],h['y']] for h in d['holes']],
                f'hardware_{letter}':hardware,
                f'width_{letter}':max_x,f'height_{letter}':max_y}
        spec=part_spec(data,reinforcement,part)
        values[f'windows_{letter}']=spec['windows']
        values[f'rib_segments_{letter}']=spec['rib_segments']
        if part=='A':values['attachment_a']=list(data['attachment_y'].values())
        for name,value in values.items():lines.append(f'{name} = {json.dumps(value,separators=(",",":"))};')
    poses=[[p['part'],p['translate'],p['rotation']] for p in data['layout']['poses']]
    lines.append('layout_poses = '+json.dumps(poses,separators=(',',':'))+';')
    (SOURCE/'template-data.scad').write_text('\n'.join(lines)+'\n')


def render(part):
    output=PROJECT/'3d'/OUTPUTS[part]
    command=['openscad','--hardwarnings','--export-format','binstl',
             '-D',f'part="{part}"','-o',str(output),str(SCAD)]
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen')
    result=subprocess.run(command,capture_output=True,text=True,env=env)
    if result.returncode or not output.exists():
        raise RuntimeError(f'OpenSCAD failed for {part}:\n{result.stdout}\n{result.stderr}')
    print(f'Wrote {output.relative_to(PROJECT)} ({output.stat().st_size} bytes)',flush=True)


def assemble_layout():
    """Place the four disjoint, already-rendered solids without a Boolean union."""
    data=json.loads((SOURCE/'geometry.json').read_text())
    meshes=[]
    for pose in data['layout']['poses']:
        mesh=trimesh.load_mesh(PROJECT/'3d'/OUTPUTS[pose['part']],process=False)
        angle=np.deg2rad(pose['rotation']);cs,sn=np.cos(angle),np.sin(angle)
        tx,ty=pose['translate']
        transform=np.array([[cs,-sn,0,tx],[sn,cs,0,ty],[0,0,1,0],[0,0,0,1]])
        mesh.apply_transform(transform);meshes.append(mesh)
    output=PROJECT/'3d'/OUTPUTS['layout']
    trimesh.util.concatenate(meshes).export(output)
    print(f'Wrote {output.relative_to(PROJECT)} (4 independent plates)',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=int,default=2,choices=range(1,5))
    parser.add_argument('--data-only',action='store_true')
    parser.add_argument('--layout-only',action='store_true',help='Reuse existing individual STL files')
    args=parser.parse_args()
    write_data()
    if args.data_only:return
    if not args.layout_only:
        if not shutil.which('openscad'):raise SystemExit('OpenSCAD CLI is required.')
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(render,KEYS))
    assemble_layout()


if __name__=='__main__':main()
