"""Verify the actual PDF vectors and STL sections against geometry.json."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import math
import re

import fitz
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from shapely.geometry import Point, Polygon
import trimesh

SOURCE=Path(__file__).resolve().parent
PROJECT=SOURCE.parent
MM=72/25.4
FILES={'A':'a-body-template.stl','B':'b-flap-liner-template.stl',
       'C':'c-left-gusset-template.stl','D':'d-right-gusset-template.stl',
       'layout':'a5-leather-coin-case-templates.stl'}
KEYS={'A':'body','B':'liner','C':'gusset_left','D':'gusset_right'}


def near_color(actual,expected):
    return actual is not None and max(abs(a-b) for a,b in zip(actual,expected))<1e-5


def hardware(part):
    result=[]
    for field in ['snap','optional_snap']:
        if field in part:
            h=part[field];result.append((h['x'],h['y'],h['diameter']))
    return result


def expected_holes(data,letter):
    p=data[KEYS[letter]]
    h=max(y for x,y in p['outline'])
    return np.array([[q['x'],h-q['y'],data['printing']['guide_diameter']] for q in p['holes']]
                    +[[x,h-y,d] for x,y,d in hardware(p)])


def layout_holes(data):
    arrays=[]
    for pose in data['layout']['poses']:
        a=expected_holes(data,pose['part']).copy()
        angle=math.radians(pose['rotation'])
        rotation=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
        a[:,:2]=a[:,:2]@rotation.T+pose['translate']
        arrays.append(a)
    return np.vstack(arrays)


def fit_circles(section):
    circles=[]
    for path in section.discrete:
        points=np.asarray(path)[:-1,:2]
        if len(points)<16:continue
        origin=points.mean(axis=0)
        u=points-origin
        cx,cy,c=np.linalg.lstsq(np.c_[2*u,np.ones(len(u))],(u*u).sum(axis=1),rcond=None)[0]
        radius=math.sqrt(max(0,c+cx*cx+cy*cy))
        residual=np.max(np.abs(np.linalg.norm(u-[cx,cy],axis=1)-radius))
        if .3<radius<2.2 and residual<.003:
            circles.append([cx+origin[0],cy+origin[1],2*radius])
    return np.array(circles)


def verify_mesh(data,name):
    path=PROJECT/'3d'/FILES[name]
    m=trimesh.load_mesh(path,process=True)
    assert m.is_watertight and m.is_winding_consistent and m.volume>0,name
    parts=m.split(only_watertight=False)
    expected=layout_holes(data) if name=='layout' else expected_holes(data,name)
    component_count=4 if name=='layout' else 1
    assert len(parts)==component_count,(name,len(parts))
    assert m.euler_number==2*component_count-2*len(expected),(name,m.euler_number)
    thickness=data['printing']['plate_thickness']
    assert abs(m.bounds[0,2])<.0001 and abs(m.bounds[1,2]-thickness)<.0001,name
    if name=='layout':
        pp=np.array([p for e in data['layout']['parts'] for p in e['outline']])
        target=np.array([[pp[:,0].min(),210-pp[:,1].max(),0],
                         [pp[:,0].max(),210-pp[:,1].min(),thickness]])
    else:
        poly=np.array(data[KEYS[name]]['outline'])
        target=np.array([[0,0,0],[poly[:,0].max(),poly[:,1].max(),thickness]])
    assert np.max(np.abs(m.bounds-target))<.002,(name,m.bounds,target)
    errors=[]
    for z in [.05,thickness/2,thickness-.05]:
        section=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
        actual=fit_circles(section)
        assert len(actual)==len(expected),(name,z,len(actual),len(expected))
        ri,ci=linear_sum_assignment(cdist(expected[:,:2],actual[:,:2]))
        center_error=np.max(np.linalg.norm(expected[ri,:2]-actual[ci,:2],axis=1))
        diameter_error=np.max(np.abs(expected[ri,2]-actual[ci,2]))
        assert center_error<.002 and diameter_error<.005,(name,z,center_error,diameter_error)
        errors.append({'z':z,'center_max_error':float(center_error),'diameter_max_error':float(diameter_error)})
    return {'file':str(path.relative_to(PROJECT)),'watertight':True,'winding_consistent':True,
            'components':len(parts),'through_holes':len(expected),'euler_number':int(m.euler_number),
            'bounds':m.bounds.tolist(),'volume_mm3':float(m.volume),'sections':errors,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_geometry(data):
    for letter,key in KEYS.items():
        p=data[key];outline=Polygon(p['outline'])
        assert outline.is_valid and not outline.is_empty,key
        for h in p['holes']:
            center=Point(h['x'],h['y'])
            assert outline.contains(center),key
            assert outline.boundary.distance(center)>=2-1e-9,key
        assert len({(round(h['x'],9),round(h['y'],9)) for h in p['holes']})==len(p['holes']),key
    width=data['parameters']['gusset_width']
    mirror=Polygon([(width-x,y) for x,y in data['gusset_left']['outline']])
    assert mirror.symmetric_difference(Polygon(data['gusset_right']['outline'])).area<1e-8
    for group in ['front','base','slope']:
        points=sorted(h['station'] for h in data['gusset_left']['holes'] if h['group']==group)
        assert all(abs(b-a-4)<1e-9 for a,b in zip(points,points[1:]))
        for side in ['L','R']:
            for small in [h for h in data['gusset_left']['holes'] if h['group']==group]:
                large=next(h for h in data['body']['holes'] if h['id']==side+'_'+small['id'])
                assert large['station']==small['station']
    flap=[h for h in data['body']['holes'] if h['id'].startswith('flap_')]
    assert all(abs(math.dist((a['x'],a['y']),(b['x'],b['y']))-4)<1e-9 for a,b in zip(flap,flap[1:]))
    polys=[Polygon(e['outline']) for e in data['layout']['parts']]
    sheet=Polygon([(3,3),(145,3),(145,207),(3,207)])
    assert all(sheet.covers(p) for p in polys)
    assert all(a.distance(b)>=2-1e-8 for i,a in enumerate(polys) for b in polys[i+1:])


def verify_pdf(data):
    path=PROJECT/'pdf/a5-leather-coin-case-pattern.pdf'
    doc=fitz.open(path)
    assert len(doc)==4 and doc.metadata['author']=='oct'
    assert data['name']['japanese'] in doc.metadata['title']
    for i,page in enumerate(doc):
        assert np.max(np.abs(np.array([page.rect.width,page.rect.height])/MM-[210,297]))<.0001
        assert '\ufffd' not in page.get_text()
        fonts=[f for f in page.get_fonts() if 'NotoSansJP-Regular' in f[3]]
        assert fonts and all(len(doc.extract_font(f[0])[3])>0 for f in fonts)
        if i:
            assert any(it[0]=='l' and abs(it[1].y-274*MM)<.002 and abs(it[2].y-it[1].y)<.002
                       and abs(abs(it[2].x-it[1].x)-50*MM)<.002 for d in page.get_drawings() for it in d['items'])
    all_centers=[]
    for placement in data['pdf']['parts']:
        part=data[placement['key']];ox,oy=placement['origin'];page=doc[placement['page']-1]
        poly=np.array(part['outline']);width,height=poly.max(axis=0)
        expected=np.array([[(ox+h['x'])*MM,(oy+h['y'])*MM] for h in part['holes']])
        centers=[];guide_found=False;cut_found=False
        for draw in page.get_drawings():
            rect=draw['rect'];x,y=(rect.x0+rect.x1)/2,(rect.y0+rect.y1)/2
            if near_color(draw.get('fill'),[.64,.30,.06]) and abs(rect.width/MM-.4)<.0001 and abs(rect.height/MM-.4)<.0001:
                if ox*MM-.01<=x<=(ox+width)*MM+.01 and oy*MM-.01<=y<=(oy+height)*MM+.01:centers.append([x,y])
            if near_color(draw.get('color'),[.64,.30,.06]) and abs((draw.get('width') or 0)-.35)<.0001:guide_found=True
            if near_color(draw.get('color'),[.12,.12,.12]) and abs((draw.get('width') or 0)-.6)<.0001:
                if abs(rect.width/MM-width)<.0001 and abs(rect.height/MM-height)<.0001:cut_found=True
        assert len(centers)==len(expected) and guide_found and cut_found,placement['key']
        ri,ci=linear_sum_assignment(cdist(expected,centers))
        error=np.max(np.linalg.norm(expected[ri]-np.array(centers)[ci],axis=1))/MM
        assert error<.0001,error
        boundary=Polygon([(ox+x,oy+y) for x,y in part['outline']])
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    if 'ハトメ抜き' in span['text'] or '任意で穴あけ' in span['text']:
                        x0,y0,x1,y1=np.array(span['bbox'])/MM
                        if placement['key'] in ['body','liner']:
                            assert boundary.covers(Polygon([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])),span['text']
        all_centers.append({'part':placement['part'],'centers':len(centers),'max_error_mm':float(error)})
    body_place=data['pdf']['parts'][0];ox,oy=body_place['origin']
    for y in data['attachment_y'].values():
        matches=[d for d in doc[1].get_drawings() if near_color(d.get('color'),[.20,.43,.57]) and
                 abs(d['rect'].y0/MM-(oy+y))<.0001 and abs(d['rect'].width/MM-data['parameters']['width'])<.0001]
        assert matches
        for draw in matches:
            assert abs(draw['width']-.5)<.0001
            assert [float(x) for x in re.search(r'\[(.*?)\]',draw['dashes']).group(1).split()]==[4,2,1,2]
    snaps=[]
    for pi in [1,2]:
        matches=[d['rect'] for d in doc[pi].get_drawings() if abs(d['rect'].width/MM-2.1)<.0001 and abs(d['rect'].height/MM-2.1)<.0001]
        assert len(matches)==1
        q=matches[0];snaps.append([(q.x0+q.x1)/2/MM,(q.y0+q.y1)/2/MM])
    assert math.dist(*snaps)<.0001
    return {'file':str(path.relative_to(PROJECT)),'pages':4,'japanese_font':'Noto Sans JP Regular, embedded',
            'cut_width_pt':.6,'guide_width_pt':.35,'point_diameter_mm':.4,
            'attachment_width_pt':.5,'attachment_dash_pt':[4,2,1,2],
            'part_centers':all_centers,'optional_A_and_B_snap_centers':snaps,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    data=json.loads((SOURCE/'geometry.json').read_text())
    verify_geometry(data)
    report={'checked_at':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
            'units':'mm','physical_print_verified':False,'physical_leather_assembly_verified':False,
            'geometry':'PASS: fixed-pitch groups, shared seam stations, symmetry, A5 spacing',
            'pdf':verify_pdf(data),'stl':{}}
    for name in FILES:
        report['stl'][name]=verify_mesh(data,name)
        print(name,'PASS',report['stl'][name]['through_holes'],'through holes',flush=True)
    total=sum(report['stl'][n]['volume_mm3'] for n in KEYS)
    assert abs(total-report['stl']['layout']['volume_mm3'])<.2
    (SOURCE/'qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PDF, source geometry and all five STL files: PASS')


if __name__=='__main__':main()
