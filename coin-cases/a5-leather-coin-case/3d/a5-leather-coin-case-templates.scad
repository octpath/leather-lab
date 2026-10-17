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
$fn = 96;
epsilon = 0.02;

assert(plate_t > 0, "plate_t must be positive");
assert(guide_d > 0 && guide_d < 4, "guide_d must leave material at the free-end guides");
assert(snap7_d > 0 && snap12_d > 0, "snap diameters must be positive");
assert(!engrave_attachment_lines ||
       (attachment_depth > 0 && attachment_depth < plate_t &&
        attachment_width > 0 && attachment_width < 1.5),
       "Attachment markings must stay shallow and separate");

module flat_template(outline, guides, hardware, height, width, attachment_y=[]) {
    // Source y points downward. Convert to an upward-y, flat-bottom CAD part.
    translate([0, height, 0]) mirror([0, 1, 0])
    difference() {
        linear_extrude(height=plate_t) polygon(points=outline);
        for (p=guides)
            translate([p[0], p[1], -epsilon])
                cylinder(d=guide_d, h=plate_t+2*epsilon);
        for (p=hardware)
            if (!p[3] || include_optional_flap_snap)
                translate([p[0], p[1], -epsilon])
                    cylinder(d=p[2] == 7 ? snap7_d : snap12_d,
                             h=plate_t+2*epsilon);
        if (engrave_attachment_lines)
            for (y=attachment_y)
                // Avoid all stitch guides: center line plus short edge marks.
                for (span=[[-epsilon,1.5],[8,width-8],[width-1.5,width+epsilon]])
                    translate([span[0],y-attachment_width/2,plate_t-attachment_depth])
                        cube([span[1]-span[0],attachment_width,attachment_depth+epsilon]);
    }
}

module template_a() {
    flat_template(outline_a, guides_a, hardware_a, height_a, width_a, attachment_a);
}
module template_b() {
    flat_template(outline_b, guides_b, hardware_b, height_b, width_b);
}
module template_c() {
    flat_template(outline_c, guides_c, hardware_c, height_c, width_c);
}
module template_d() {
    flat_template(outline_d, guides_d, hardware_d, height_d, width_d);
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
