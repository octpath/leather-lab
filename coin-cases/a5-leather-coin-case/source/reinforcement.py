"""Shared 2D reinforcement geometry and checks; coordinates use source y-down."""
import json
import re
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

SOURCE = Path(__file__).resolve().parent
KEYS = {'A':'body', 'B':'liner', 'C':'gusset_left', 'D':'gusset_right'}
RESOLUTION = 24


def load_config():
    return json.loads((SOURCE/'reinforcement.json').read_text())


def check_scad_defaults(path, data, config):
    """Prevent validation of JSON settings that differ from the exported CAD."""
    text = path.read_text()
    expected = dict(config['parameters'])
    expected.update(plate_t=data['printing']['plate_thickness'],
                    guide_d=data['printing']['guide_diameter'],
                    snap7_d=data['printing']['snap7_diameter'],
                    snap12_d=data['printing']['snap12_diameter'])
    for name,value in expected.items():
        match = re.search(r'^'+re.escape(name)+r'\s*=\s*([^;]+);',text,re.M)
        assert match, f'Missing OpenSCAD setting: {name}'
        raw = match.group(1).strip()
        actual = {'true':True,'false':False}.get(raw) if isinstance(value,bool) else float(raw)
        assert actual == value, f'Update both reinforcement.json and OpenSCAD: {name}'


def part_spec(data, config, letter):
    spec = config['parts'][letter]
    if 'mirror_of' not in spec:
        return spec
    width = max(x for x,y in data[KEYS[letter]]['outline'])
    original = config['parts'][spec['mirror_of']]
    return {'windows':[[width-x,y,w,h] for x,y,w,h in original['windows']],
            'rib_segments':[[[width-x,y] for x,y in segment]
                            for segment in original['rib_segments']]}


def circles(part, guide_diameter, relief=0):
    holes = [(h['x'],h['y'],guide_diameter) for h in part['holes']]
    for key in ['snap','optional_snap']:
        if key in part:
            h = part[key]; holes.append((h['x'],h['y'],h['diameter']))
    return [Point(x,y).buffer(d/2+relief,quad_segs=RESOLUTION) for x,y,d in holes]


def window_shapes(data, config, letter):
    p = config['parameters']
    if not p['windows_enabled']:
        return []
    outline = Polygon(data[KEYS[letter]]['outline'])
    width,height = outline.bounds[2:]
    windows = []
    for x,y,w,h in part_spec(data,config,letter)['windows']:
        x = width/2+(x-width/2)*p['window_spacing_scale']
        y = height/2+(y-height/2)*p['window_spacing_scale']
        w *= p['window_scale_x']; h *= p['window_scale_y']
        assert min(w,h) >= 2*p['minimum_web'], 'Window too narrow'
        radius = min(p['window_radius'],w/2-.1,h/2-.1)
        windows.append(box(x-w/2+radius,y-h/2+radius,
                           x+w/2-radius,y+h/2-radius).buffer(radius,quad_segs=RESOLUTION))
    return windows


def profiles(data, config, letter):
    part = data[KEYS[letter]]; p = config['parameters']
    outline = Polygon(part['outline']); width,height = outline.bounds[2:]
    tool_holes = circles(part,data['printing']['guide_diameter'])
    windows = window_shapes(data,config,letter)
    voids = unary_union(tool_holes+windows)
    base = outline.difference(voids)
    engravings = Polygon()
    if letter == 'A':
        # Do not cut underneath the raised frame or central spine.
        spans = [(-.02,1.5),(8,width/2-2),(width/2+2,width-8),(width-1.5,width+.02)]
        engravings = unary_union([box(x0,y-.3,x1,y+.3)
                                 for y in data['attachment_y'].values() for x0,x1 in spans])
    cap = base.difference(engravings)
    top = root = Polygon()
    if p['ribs_enabled']:
        inset = outline.buffer(-p['rib_inset'],quad_segs=RESOLUTION)
        ring = inset.difference(outline.buffer(-p['rib_inset']-p['rib_width'],quad_segs=RESOLUTION))
        strokes = [LineString(s).buffer(p['rib_width']/2,quad_segs=RESOLUTION)
                   for s in part_spec(data,config,letter)['rib_segments']]
        bosses = []
        for field in ['snap','optional_snap']:
            if field in part:
                snap = part[field]
                bosses.append(Point(snap['x'],snap['y']).buffer(
                    snap['diameter']/2+p['tool_relief']+p['rib_width'],quad_segs=RESOLUTION))
        raw = unary_union([ring,*strokes,*bosses]).intersection(inset)
        relief = unary_union(circles(part,data['printing']['guide_diameter'],p['tool_relief']))
        top = raw.difference(unary_union([relief,*windows]))
        root = raw.buffer(p['root_flare'],quad_segs=RESOLUTION).intersection(
            outline.buffer(-p['rib_inset']+p['root_flare'],quad_segs=RESOLUTION)
        ).difference(unary_union([relief,*windows]))
    return {'outline':outline,'holes':tool_holes,'windows':windows,
            'base':base,'cap':cap,'root':root,'top':top,'engravings':engravings}


def validate(data, config):
    p = config['parameters']
    assert p['minimum_web'] > 0 and p['rib_width'] >= p['minimum_web']
    assert 0 < p['root_height'] < p['rib_height']
    assert 0 <= p['root_flare'] < p['rib_inset']
    assert p['frame_width'] > p['rib_inset']+p['rib_width']+p['root_flare']
    assert p['tool_relief'] >= 0 and p['window_radius'] > 0
    results = {}
    for letter in KEYS:
        s = profiles(data,config,letter); outline=s['outline']; windows=s['windows']
        assert s['base'].geom_type == 'Polygon' and s['base'].is_valid,letter
        hole_edge = min(outline.boundary.distance(h) for h in s['holes'])
        assert hole_edge >= p['minimum_web']-1e-8,(letter,'hole to edge',hole_edge)
        window_edge = min((outline.boundary.distance(w) for w in windows),default=None)
        if windows:
            assert all(outline.contains(w) for w in windows),letter
            assert window_edge >= p['frame_width']-1e-8,(letter,'frame',window_edge)
        hole_window = min((w.distance(h) for w in windows for h in s['holes']),default=None)
        window_gap = min((a.distance(b) for i,a in enumerate(windows) for b in windows[i+1:]),default=None)
        for gap in [hole_window,window_gap]:
            assert gap is None or gap >= p['minimum_web']-1e-8,(letter,'web',gap)
        rib_window = None
        if p['ribs_enabled']:
            assert s['top'].geom_type == 'Polygon' and s['top'].is_valid,(letter,'disconnected ribs')
            assert s['root'].difference(s['base']).area < 1e-8,(letter,'unsupported rib root')
            assert s['top'].difference(s['root']).area < 1e-8,(letter,'unsupported upper rib')
            assert s['root'].intersection(s['engravings']).area < 1e-8,(letter,'hidden groove')
            rib_window = min((s['root'].distance(w) for w in windows),default=None)
            assert rib_window is None or rib_window >= p['minimum_web']-1e-8,(letter,'rib to window',rib_window)
        results[letter] = {'windows':len(windows),'minimum_hole_edge_web':hole_edge,
                           'minimum_window_edge_frame':window_edge,'minimum_window_hole_web':hole_window,
                           'minimum_window_gap':window_gap,'minimum_window_rib_gap':rib_window,
                           'connected_rib_skeleton':p['ribs_enabled'],
                           'base_area_mm2':s['base'].area,'rib_area_mm2':s['top'].area}
    return results


if __name__ == '__main__':
    geometry=json.loads((SOURCE/'geometry.json').read_text())
    print(json.dumps(validate(geometry,load_config()),indent=2))
