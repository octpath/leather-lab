"""Check actual M1/M3 STL geometry, datums, slot edges and tool access."""
from pathlib import Path
import hashlib,json,math,re
import numpy as np
import trimesh
from shapely.geometry import GeometryCollection,Polygon,Point

SOURCE=Path(__file__).resolve().parent
PROJECT=SOURCE.parent
SCAD=(PROJECT/'3d/lip-balm-tools.scad').read_text()
G=json.loads((SOURCE/'geometry.json').read_text())

def parameter(name):
    return float(re.search(r'^'+name+r'\s*=\s*([\d.]+)\s*;',SCAD,re.M).group(1))

def section(mesh,z):
    path=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
    loops=[] if path is None else path.discrete
    solid=GeometryCollection()
    for loop in loops:
        p=Polygon(loop[:,:2]);assert p.is_valid,(z,'invalid section')
        solid=solid.symmetric_difference(p)
    return solid,loops

def topology(path):
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count==1
    assert mesh.area_faces.min()>1e-11 and mesh.volume>0
    return mesh,{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'closed_manifold':True,'components':1,'triangles':len(mesh.faces),
                 'bounds_mm':mesh.bounds.tolist(),'volume_mm3':float(mesh.volume)}

def circle_centres(loops,diameter):
    centres=[]
    for loop in loops:
        p=loop[:-1,:2]
        if max(abs(np.ptp(p,axis=0)-diameter))>.0002:continue
        o=p.mean(axis=0);p=p-o
        fit=np.linalg.lstsq(np.column_stack([2*p,np.ones(len(p))]),(p*p).sum(axis=1),rcond=None)[0]
        centres.append(fit[:2]+o)
    return np.asarray(centres)

m1,q1=topology(PROJECT/'3d/m1-lower-former.stl')
m3,q3=topology(PROJECT/'3d/m3-trimming-frame.stl')
cut=G['front_formed']['cut_bottom_radius'];straight=G['front_formed']['straight_length']
slot=parameter('trim_slot_w');band=parameter('trim_outer_band')
shift=np.array([cut+slot+band,parameter('mouth_extension')])
expected=np.asarray(G['stitch']['main_hole_centres'])+shift
base_checks=[]
for z in [.2,1.0,1.9]:
    _,loops=section(m3,z);got=circle_centres(loops,1.1)
    assert len(got)==35,(z,len(got))
    nearest=np.argmin(np.linalg.norm(expected[:,None,:]-got[None,:,:],axis=2),axis=1)
    assert len(set(nearest))==35
    error=float(np.max(np.linalg.norm(expected-got[nearest],axis=1)))
    assert error<.0001
    base_checks.append({'z_mm':z,'guide_count':35,'diameter_mm':1.1,'max_centre_error_mm':error})
shape,loops=section(m3,1)
# Validate the real inner slit edge, not the new outside perimeter.
edges=[];sagitta=cut*(1-math.cos(math.pi/128))
for loop in loops:
    p=loop[:,:2]-shift
    for a,b in zip(p[:-1],p[1:]):
        side=(max(abs(a[0]-cut),abs(b[0]-cut))<.0001 or max(abs(a[0]+cut),abs(b[0]+cut))<.0001) and min(a[1],b[1])>=-.0001 and max(a[1],b[1])<=straight+.0001
        ra,rb=np.linalg.norm(a-[0,straight]),np.linalg.norm(b-[0,straight])
        bottom=min(a[1],b[1])>=straight-.0001 and min(ra,rb)>cut-sagitta-.0001 and max(ra,rb)<cut+.0001
        if side or bottom:edges.append((a+shift,b+shift))
a=np.array([x[0] for x in edges]);b=np.array([x[1] for x in edges]);ab=b-a
v=expected[:,None,:]-a[None,:,:]
t=np.clip(np.sum(v*ab,axis=2)/np.sum(ab*ab,axis=1),0,1)
d=np.linalg.norm(v-t[:,:,None]*ab,axis=2).min(axis=1)
assert max(abs(d-3))<.005,d.tolist()
# The entire 180-degree rounded-bottom slot must remain open, including tangencies.
arc=[]
for angle in np.linspace(0,math.pi,361):
    p=shift+[math.cos(angle)*(cut+slot/2),straight+math.sin(angle)*(cut+slot/2)]
    gap=Point(p).distance(shape)
    assert gap>slot/2-.01,(angle,gap)
    arc.append(gap)
# Both straight sides have exactly the requested 3 mm closed intervals.
bridges=json.loads(re.search(r'^trim_bridge_y\s*=\s*(\[[^;]+\])',SCAD,re.M).group(1))
for y in [3,7,10,17,23,35,39,49]:
    for s in [-1,1]:assert Point(shift+[s*(cut+slot/2),y]).distance(shape)>slot/2-.01
for y in bridges:
    for s in [-1,1]:assert shape.contains(Point(shift+[s*(cut+slot/2),y]))
# Every guide has a 5 mm diameter unobstructed vertical approach above its 2 mm land.
access=[]
for z in [2.05,2.8,4.1,5.1,6.1,10.1,15.1,20.1,22.1]:
    sh,_=section(m3,z)
    gap=min(Point(p).distance(sh) for p in expected)
    assert gap>=2.5-.001,(z,gap)
    access.append({'z_mm':z,'minimum_tool_clear_radius_mm':float(gap)})
assert abs(m3.bounds[0,2])<.0001
assert max(abs(m3.bounds[:,0]-[0,2*shift[0]]))<.0001
snap=np.array([45.,32.]);top=parameter('base_t')+parameter('mold_depth')
snap_checks=[]
for z,diameter in [(10,6),(20,6),(top-1.5,2.1),(top-.2,2.1)]:
    sh,ls=section(m1,z);centres=circle_centres(ls,diameter)
    assert len(centres)==1,(z,diameter,centres.tolist())
    error=float(np.linalg.norm(centres[0]-snap));assert error<.0001
    assert Point(snap).distance(sh)>diameter/2-.002
    snap_checks.append({'z_mm':z,'diameter_mm':diameter,'centre_error_mm':error})
# The old 14 mm hardware recess is filled back to the male forming surface.
sh,_=section(m1,25)
assert sh.contains(Point(snap+[3,0])) and sh.contains(Point(snap+[-3,0]))
q1.update({'snap_punch_number':7,'snap_mark_diameter_mm':2.1,'rear_passage_diameter_mm':6,
           'snap_centre_xy_mm':snap.tolist(),'snap_passage_checks':snap_checks,'old_hardware_recess_removed':True})
q3.update({'guide_checks':base_checks,'slit_width_mm':slot,'slit_inner_edge_is_cut_line':True,
           'seam_allowance_STL_range_mm':[float(d.min()),float(d.max())],
           'bottom_arc_continuous_degrees':180,'bottom_arc_samples':361,'minimum_half_slot_clearance_mm':float(min(arc)),
           'straight_bridge_centres_from_mouth_mm':bridges,'straight_bridge_width_mm':parameter('trim_bridge_w'),
           'tool_approach_diameter_checked_mm':5,'tool_approach_checks':access,'mouth_arch_y_from_mouth_mm':[-parameter('arch_width_y'),0]})
report={'units':'mm','scope':'CAD geometry only; actual P1S slicing and physical strength are separate checks',
        'M1':q1,'M3':q3,'fixed_PDF_stitch_centres_and_cut_contour_preserved':True,'physical_print_verified':False}
(SOURCE/'3d-qa.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: M1/M3 closed, rear 7号 passage,35 guides,3 mm allowance,continuous bottom slot,5 mm tool approach')
print(json.dumps({'M1_triangles':q1['triangles'],'M3_triangles':q3['triangles'],'M3_size_mm':np.ptp(m3.bounds,axis=0).tolist()},indent=2))
