// A5 Leather Coin Case — full-size marking templates, units: mm.
// Canonical cut outlines and centers: ../source/geometry.json.
include <../source/template-data.scad>

part = "A"; // [A,B,C,D,layout]
plate_t = 2;
guide_d = 1.1;
snap7_d = 2.1;
snap12_d = 3.6;
include_optional_flap_snap = true;
engrave_attachment_lines = true;
attachment_width = 0.6;
attachment_depth = 0.3;
ribs_enabled = true;
rib_height = 1.4;
rib_width = 1.6;
rib_inset = 6;
root_flare = 0.3;
root_height = 0.3;
windows_enabled = true;
frame_width = 9;
window_radius = 2;
window_scale_x = 1;
window_scale_y = 1;
window_spacing_scale = 1;
minimum_web = 1.4;
tool_relief = 0.8; // Additional radius above the 2 mm datum plate only.
$fn = 96;
epsilon = 0.02;

assert(plate_t > 0, "plate_t must be positive");
assert(guide_d > 0 && guide_d < 4, "guide_d must leave material at the free-end guides");
assert(snap7_d > 0 && snap12_d > 0, "snap diameters must be positive");
assert(!engrave_attachment_lines ||
       (attachment_depth > 0 && attachment_depth < plate_t &&
        attachment_width > 0 && attachment_width < 1.5),
       "Attachment markings must stay shallow and separate");
assert(rib_width >= minimum_web && rib_inset > root_flare && root_flare >= 0);
assert(root_height > 0 && root_height < rib_height);
assert(frame_width > rib_inset+rib_width+root_flare);
assert(window_radius > 0 && tool_relief >= 0);

module tool_holes(guides, hardware, relief=0) {
        for (p=guides)
            translate(p) circle(d=guide_d+2*relief);
        for (p=hardware)
            if (!p[3] || include_optional_flap_snap)
                translate([p[0],p[1]])
                    circle(d=(p[2] == 7 ? snap7_d : snap12_d)+2*relief);
}

module windows(spec, width, height) {
    if (windows_enabled)
        for (p=spec) {
            w=p[2]*window_scale_x; h=p[3]*window_scale_y;
            r=min(window_radius,w/2-0.1,h/2-0.1);
            assert(min(w,h) >= 2*minimum_web);
            translate([width/2+(p[0]-width/2)*window_spacing_scale,
                       height/2+(p[1]-height/2)*window_spacing_scale])
                offset(r=r) square([w-2*r,h-2*r],center=true);
        }
}

module base_profile(outline,guides,hardware,spec,width,height) {
    difference() {
        polygon(outline);
        tool_holes(guides,hardware);
        windows(spec,width,height);
    }
}

module attachment_marks(width, attachment_y) {
    if (engrave_attachment_lines)
        for (y=attachment_y)
            // Leave the raised edge frame and central spine fully supported.
            for (span=[[-epsilon,1.5],[8,width/2-2],
                       [width/2+2,width-8],[width-1.5,width+epsilon]])
                translate([span[0],y-attachment_width/2])
                    square([span[1]-span[0],attachment_width]);
}

module rib_raw(outline,segments,hardware) {
    intersection() {
        offset(r=-rib_inset) polygon(outline);
        union() {
            difference() {
                offset(r=-rib_inset) polygon(outline);
                offset(r=-rib_inset-rib_width) polygon(outline);
            }
            for (s=segments)
                hull() for (p=s) translate(p) circle(d=rib_width);
            for (p=hardware)
                if (!p[3] || include_optional_flap_snap)
                    translate([p[0],p[1]])
                        circle(r=(p[2] == 7 ? snap7_d : snap12_d)/2+tool_relief+rib_width);
        }
    }
}

module rib_profile(outline,guides,hardware,spec,segments,width,height,flare=0) {
    difference() {
        intersection() {
            offset(r=-rib_inset+flare) polygon(outline);
            offset(r=flare) rib_raw(outline,segments,hardware);
        }
        tool_holes(guides,hardware,tool_relief);
        windows(spec,width,height);
    }
}

module flat_template(outline,guides,hardware,height,width,spec,segments,attachment_y=[]) {
    // Boolean operations on 2D profiles keep the many circular guides precise.
    translate([0,height,0]) mirror([0,1,0]) union() {
        linear_extrude(plate_t-attachment_depth)
            base_profile(outline,guides,hardware,spec,width,height);
        translate([0,0,plate_t-attachment_depth]) linear_extrude(attachment_depth)
            difference() {
                base_profile(outline,guides,hardware,spec,width,height);
                attachment_marks(width,attachment_y);
            }
        if (ribs_enabled) {
            translate([0,0,plate_t]) linear_extrude(root_height)
                rib_profile(outline,guides,hardware,spec,segments,width,height,root_flare);
            translate([0,0,plate_t+root_height]) linear_extrude(rib_height-root_height)
                rib_profile(outline,guides,hardware,spec,segments,width,height);
        }
    }
}

module template_a() {
    flat_template(outline_a,guides_a,hardware_a,height_a,width_a,windows_a,rib_segments_a,attachment_a);
}
module template_b() {
    flat_template(outline_b,guides_b,hardware_b,height_b,width_b,windows_b,rib_segments_b);
}
module template_c() {
    flat_template(outline_c,guides_c,hardware_c,height_c,width_c,windows_c,rib_segments_c);
}
module template_d() {
    flat_template(outline_d,guides_d,hardware_d,height_d,width_d,windows_d,rib_segments_d);
}

module select_template(name) {
    if (name == "A") template_a();
    else if (name == "B") template_b();
    else if (name == "C") template_c();
    else if (name == "D") template_d();
    else assert(false, "Use part = layout, A, B, C or D");
}

if (part == "layout") {
    // Same layout as the PDF's A5 material plan. Each island is a separate part.
    for (pose=layout_poses)
        translate([pose[1][0],pose[1][1],0])
            rotate([0,0,pose[2]]) select_template(pose[0]);
} else select_template(part);
