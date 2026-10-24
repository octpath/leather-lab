/*
oct / Lip Balm Case — PLA trial tools v01
Units: mm. All single parts are already placed for printing.
Choose part below; F6, then File > Export > STL.

M1 = male former and ribbed base
M2 = wide U-shaped clamping frame (not a female cover)
M3 = outer reinforced frame, cutting slots and stitch-transfer guides
A  = 90 x 120 rough-blank template
B  = back + flap template
C  = short-return D-ring tab template

The fixed PDF cut contours and all stitch centres are retained.
Mould dimensions and clearances are TRIAL parameters.
Fit the front snap AFTER forming; mark its centre through the back of M1.
PLA, P1S, 0.4 mm nozzle. Guide web / print tolerances need a physical check.
*/

/* [Output] */
part = "M1"; // [M1,M2,M3,A,B,C,assembly,layout]

/* [Transfer templates] */
plate_t = 2;
guide_d = 1.1;
stud_hole_d = 2.1; // A: No.7 punch, male snap
socket_hole_d = 3.6; // B: No.12 punch, female snap
template_ribs = true;
template_rib_h = 1.4;
template_rib_w = 1.2;

/* [Trial forming geometry] */
// Seam-to-former distance changed from the preliminary 2.5 to 2.8.
// This leaves a 0.55 mm web beside the 1.1 mm transfer holes at defaults.
forming_to_seam = 2.8;
mold_depth = 18;
leather_allowance = 1.5;
fit_clearance = 0.2;
mouth_extension = 8;

/* [Rear snap-centre marking access] */
snap_access_d = 6;
snap_mark_guide_t = 2;

/* [Structural frame] */
press_band = 18;
press_plate_t = 4;
press_rib_h = 4;
press_rib_w = 3;
base_t = 8;
base_pocket_depth = 4;
base_rib_w = 3;
base_cell = 14;

/* [Mouth trim arch] */
mouth_arch = true;
arch_width_y = 4;
arch_wall = 3;
arch_root_h = 6;

/* [Outer trimming frame] */
trim_slot_w = 1.5; // slot INNER edge is the fixed cutting contour
trim_outer_band = 12;
trim_rib_h = 3;
trim_rib_w = 2.4;
trim_bridge_w = 3;
trim_bridge_overlap = 1.2;
trim_bridge_y = [13,29,45]; // straight sides only; the bottom arc stays open

/* [Hidden] */
$fn = 128;
eps = 0.02;
pitch = 4;
seam_offset = 3;
seam_r = pitch / (2*sin(180/20));
cut_r = seam_r + seam_offset;
straight = 51;
formed_h = straight + cut_r;
flap_extension = 100;
snap_y = 12;
flap_snap_y = -88;
blank_w = 90;
blank_h = 120;
blank_mouth_y = 20;
tab_w = 14;
tab_h = 42;
tab_radius = 2;
mold_r = seam_r - forming_to_seam;
opening_r = mold_r + leather_allowance + fit_clearance;
press_outer_r = opening_r + press_band;
min_guide_web = seam_r - guide_d/2 - opening_r;
main_holes = concat(
    [for(i=[0:12]) [-seam_r, 3+4*i]],
    [for(j=[1:10]) [seam_r*cos(180-18*j), straight+seam_r*sin(180-18*j)]],
    [for(i=[1:12]) [seam_r, straight-4*i]]
);
tab_shared = [for(y=[9,27]) for(x=[-4,0,4]) [x,y]];
back_only = [for(y=[9,27]) for(x=[-8,8]) [x,y]];
tab_holes = [for(y=[3,21,39]) for(x=[3,7,11]) [x,y]];

assert(plate_t>0 && guide_d>0);
assert(stud_hole_d>0 && socket_hole_d>0);
assert(mold_r>0 && mold_depth>16);
assert(min_guide_web>=0.45,
       str("Trim guide web too thin: ",min_guide_web,
           " mm. Increase forming_to_seam, or reduce allowance/clearance after checking leather."));
assert(press_band>=10);
assert(base_t-base_pocket_depth>=3);
assert(snap_access_d>stud_hole_d && snap_mark_guide_t>=plate_t);
assert(guide_d<2);

module round_rect(w,h,r=2) {
    translate([r,r]) offset(r=r) square([w-2*r,h-2*r]);
}

// Closed projected outline, rounded bottom, straight top.
module u_solid(r, top=0, end=straight) {
    union() {
        translate([-r,top]) square([2*r,end-top]);
        translate([0,end]) circle(r=r);
    }
}

// A U-frame has an OPEN mouth; the arch is a separate integral 3D feature.
module u_band(ro,ri,top=0,end=straight) {
    difference() {
        u_solid(ro,top,end);
        u_solid(ri,top-40,end);
    }
}

module back_shape() {
    hull() {
        translate([0,-flap_extension+cut_r]) circle(r=cut_r);
        translate([0,straight]) circle(r=cut_r);
    }
}

module guide_holes(points,z0=-eps,h=plate_t+2*eps,d=guide_d) {
    for(p=points) translate([p[0],p[1],z0]) cylinder(d=d,h=h);
}

module slot2(a,b,w=0.65) {
    hull() {
        translate(a) circle(d=w,$fn=32);
        translate(b) circle(d=w,$fn=32);
    }
}

module stroke3(a,b,w=1.2,z=plate_t,h=template_rib_h) {
    translate([0,0,z]) linear_extrude(h) slot2(a,b,w);
}

module engraved_text(label,p,size=3,z=plate_t,depth=0.35) {
    translate([p[0],p[1],z-depth]) linear_extrude(depth+eps)
        text(label,size=size,font="DejaVu Sans:style=Book",halign="center",valign="center");
}

module shallow_line(a,b,w=0.45,z=plate_t,depth=0.3) {
    translate([0,0,z-depth]) linear_extrude(depth+eps) slot2(a,b,w);
}

module former_raw() {
    // Extrusion direction maps local +z to global +y.
    // The upper half ellipse is invariant along the straight pocket body.
    translate([0,straight,base_t]) rotate([90,0,0])
        linear_extrude(straight+mouth_extension)
            intersection() {
                scale([mold_r,mold_depth]) circle(r=1);
                translate([-mold_r-1,0]) square([2*mold_r+2,mold_depth+1]);
            }
    // Lower quarter ellipsoid, tangent to the straight body at y=straight.
    intersection() {
        translate([0,straight,base_t]) scale([mold_r,mold_r,mold_depth]) sphere(r=1);
        translate([-mold_r-1,straight,base_t]) cube([2*mold_r+2,mold_r+1,mold_depth+1]);
    }
}

module rear_snap_access() {
    top = base_t+mold_depth;
    taper_h = (snap_access_d-stud_hole_d)/2;
    taper_z = top-snap_mark_guide_t-taper_h;
    assert(taper_z>base_t);
    translate([0,snap_y,-eps]) cylinder(d=snap_access_d,h=taper_z+eps);
    translate([0,snap_y,taper_z])
        cylinder(d1=snap_access_d,d2=stud_hole_d,h=taper_h);
    translate([0,snap_y,top-snap_mark_guide_t-eps])
        cylinder(d=stud_hole_d,h=snap_mark_guide_t+2*eps);
}

module M1_lower() {
    difference() {
        union() {
            linear_extrude(base_t)
                translate([-blank_w/2,-blank_mouth_y]) round_rect(blank_w,blank_h,5);
            former_raw();
        }
        // Underside open pockets leave a 4 mm deck and a 3 mm rib grid.
        // Keep the perimeter and clamping landings solid.
        for(x=[-33.5:base_cell:22.5]) for(y=[-7.5:base_cell:76.5])
            translate([x,y,-eps]) linear_extrude(base_pocket_depth+eps)
                round_rect(base_cell-base_rib_w,base_cell-base_rib_w,1.4);
        // The old 14 mm hardware recess is removed: form before fitting the snap.
        rear_snap_access();
        shallow_line([-43,0],[-34,0],0.6,base_t,0.45);
        shallow_line([34,0],[43,0],0.6,base_t,0.45);
        engraved_text("M1",[0,91],5,base_t,0.5);
    }
}

module press_ribs() {
    // Two U ribs plus cross ties; top ribs never touch the leather.
    for(shift=[4,13])
        linear_extrude(press_rib_h)
            u_band(opening_r+shift+press_rib_w/2,
                   opening_r+shift-press_rib_w/2,-mouth_extension);
    for(y=[4,23,42,58]) for(s=[-1,1]) {
        // At the rounded end, ribs are radial rather than square overhangs.
        if(y<straight)
            linear_extrude(press_rib_h)
                translate([s>0 ? opening_r+2 : -press_outer_r+2,y-press_rib_w/2])
                    square([press_band-4,press_rib_w]);
    }
    for(a=[35,90,145])
        translate([0,straight,0]) rotate([0,0,a])
            linear_extrude(press_rib_h)
                translate([opening_r+2,-press_rib_w/2]) square([press_band-4,press_rib_w]);
}

module M2_press() {
    difference() {
        union() {
            linear_extrude(press_plate_t)
                u_band(press_outer_r,opening_r,-mouth_extension);
            intersection() {
                translate([0,0,press_plate_t]) press_ribs();
                linear_extrude(press_plate_t+press_rib_h)
                    u_band(press_outer_r,opening_r,-mouth_extension);
            }
            // Four planar top clamping landings, connected to the rib grid.
            for(y=[10,39]) for(s=[-1,1])
                translate([s*(opening_r+press_band/2),y,press_plate_t])
                    linear_extrude(press_rib_h) offset(r=1)
                        square([12,10],center=true);
            // Bottom clamp landing.
            translate([0,straight+opening_r+press_band/2,press_plate_t])
                linear_extrude(press_rib_h) offset(r=1) square([12,10],center=true);
        }
        // Datum witnesses line up with y=0 on the lower board.
        shallow_line([-press_outer_r+0.5,0],[-opening_r-0.5,0],0.5,
                     press_plate_t+press_rib_h,0.5);
        shallow_line([opening_r+0.5,0],[press_outer_r-0.5,0],0.5,
                     press_plate_t+press_rib_h,0.5);
        engraved_text("M2",[0,straight+opening_r+press_band/2],3.3,
                      press_plate_t+press_rib_h,0.45);
    }
}

module mouth_arch_profile() {
    intersection() {
        difference() {
            offset(r=leather_allowance+fit_clearance+arch_wall)
                scale([mold_r,mold_depth]) circle(r=1);
            offset(r=leather_allowance+fit_clearance)
                scale([mold_r,mold_depth]) circle(r=1);
        }
        translate([-cut_r,0])
            square([2*cut_r,mold_depth+leather_allowance+fit_clearance+arch_wall+eps]);
    }
}

// The datum face is y=0; the complete arch sits ABOVE the mouth (negative y).
// Its feet are carried by the external frame, leaving every stitch guide clear.
module mouth_arch_mounts() {
    slot_outer = cut_r+trim_slot_w;
    root_x = opening_r+arch_wall-1.6;
    assert(root_x>opening_r && arch_root_h>plate_t);
    for(s=[-1,1]) scale([s,1,1]) hull() {
        translate([root_x,-arch_width_y,0]) cube([1.6,arch_width_y,arch_root_h]);
        translate([slot_outer+2,-arch_width_y,0])
            cube([trim_outer_band-4,arch_width_y,plate_t+trim_rib_h]);
    }
}

module trim_bridges_2d() {
    slot_outer = cut_r+trim_slot_w;
    for(y=trim_bridge_y) for(s=[-1,1]) scale([s,1,1])
        translate([cut_r-trim_bridge_overlap,y-trim_bridge_w/2])
            square([trim_slot_w+2*trim_bridge_overlap,trim_bridge_w]);
}

module trim_outer_ribs_2d() {
    slot_outer = cut_r+trim_slot_w;
    ro = slot_outer+trim_outer_band;
    intersection() {
        u_band(ro,slot_outer,-mouth_extension);
        union() {
            u_band(ro-1,ro-1-trim_rib_w,-mouth_extension);
            u_band(slot_outer+1.8+trim_rib_w,slot_outer+1.8,-mouth_extension);
            for(y=trim_bridge_y) for(s=[-1,1]) scale([s,1,1])
                translate([slot_outer+1.8,y-trim_rib_w/2])
                    square([trim_outer_band-2.8,trim_rib_w]);
        }
    }
}

module M3_trim() {
    slot_outer = cut_r+trim_slot_w;
    ro = slot_outer+trim_outer_band;
    assert(trim_slot_w>=1 && trim_outer_band>=10 && trim_rib_w>=1.2);
    assert(trim_bridge_overlap>0 && trim_bridge_overlap<seam_offset-guide_d/2);
    assert(arch_width_y>0 && arch_width_y<=mouth_extension && arch_wall>0);
    for(y=trim_bridge_y)
        assert(y-trim_bridge_w/2>0 && y+trim_bridge_w/2<straight,
               "Connectors must not interrupt the bottom semicircle.");
    difference() {
      union() {
        // Cut the 35 holes in 2D: the complete guide land stays exactly 2 mm high.
        linear_extrude(plate_t) difference() {
            union() {
                u_band(cut_r,opening_r);
                u_band(ro,slot_outer,-mouth_extension);
                trim_bridges_2d();
            }
            for(p=main_holes) translate(p) circle(d=guide_d);
        }
        if(template_ribs)
            translate([0,0,plate_t]) linear_extrude(trim_rib_h)
                trim_outer_ribs_2d();
        if(mouth_arch) {
            rotate([90,0,0]) linear_extrude(arch_width_y) mouth_arch_profile();
            mouth_arch_mounts();
        }
      }
      for(s=[-1,1])
          shallow_line([s*(ro-3.5),0],[s*(ro-.9),0],.5,
                       plate_t+trim_rib_h,.35);
      engraved_text("M3",[0,straight+slot_outer+trim_outer_band/2],2.5,
                    plate_t,.3);
    }
}

module A_blank() {
    datum_holes=[for(x=[10,30,45,60,80]) [x,20]];
    difference() {
        union() {
            linear_extrude(plate_t) square([blank_w,blank_h]);
            if(template_ribs) {
                for(x=[5,45,85]) stroke3([x,5],[x,115],template_rib_w);
                for(y=[5,20,115]) stroke3([5,y],[85,y],template_rib_w);
            }
        }
        // Windows lighten the large template, leaving its datum and snap spine.
        for(x=[10,50]) for(v=[[5,10],[25,11],[42,68]])
            translate([x,v[0],-eps]) linear_extrude(plate_t+template_rib_h+2*eps)
                round_rect(30,v[1],2.5);
        guide_holes(datum_holes,-eps,plate_t+template_rib_h+2*eps);
        guide_holes(datum_holes,plate_t,template_rib_h+eps,guide_d+1.5);
        guide_holes([[45,32]],-eps,plate_t+template_rib_h+2*eps,stud_hole_d);
        guide_holes([[45,32]],plate_t,template_rib_h+eps,
                    max(stud_hole_d+0.5,guide_d+1.5));
        shallow_line([3,20],[87,20],0.4);
        shallow_line([45,24],[45,39],0.4);
        shallow_line([41,32],[49,32],0.4);
        engraved_text("A",[22,19],3.4);
    }
}

module attachment_corner_slots() {
    for(s=[-1,1]) for(y=[0,30]) {
        dir=y==0 ? 1 : -1;
        slot2([s*7,y],[s*(7-1.4),y],0.6);
        slot2([s*7,y],[s*7,y+dir*1.4],0.6);
    }
}

module B_back() {
    b_holes=concat(main_holes,tab_shared,back_only);
    difference() {
        union() {
            // Cut the flat holes in 2D first. This retains the geometry while
            // avoiding dozens of slow 3D cylinder Boolean operations.
            linear_extrude(plate_t) difference() {
                back_shape();
                translate([-5.5,-73]) round_rect(11,65,3);
                translate([-5,35]) round_rect(10,19,2.5);
                for(p=b_holes) translate(p) circle(d=guide_d);
                translate([0,flap_snap_y]) circle(d=socket_hole_d);
                attachment_corner_slots();
            }
            if(template_ribs) {
                for(s=[-1,1]) {
                    stroke3([s*7.5,-73],[s*7.5,-8],template_rib_w);
                    stroke3([s*9,34],[s*9,53],template_rib_w);
                }
            }
        }
        // Lines are shallow visual references; corner slots can transfer C's position.
        shallow_line([-7,0],[7,0],0.4);
        shallow_line([-7,30],[7,30],0.4);
        shallow_line([-7,0],[-7,30],0.4);
        shallow_line([7,0],[7,30],0.4);
        shallow_line([-cut_r+1,0],[cut_r-1,0],0.4);
        // Outer row endpoints are B-only round-awl positions.
        for(p=back_only)
            translate([p[0],p[1],plate_t-0.25]) linear_extrude(0.25+eps)
                difference() { circle(d=2.2,$fn=40); circle(d=1.8,$fn=40); }
        engraved_text("B",[0,-79],4);
        engraved_text("FIT",[0,-93],2.5);
    }
}

module C_tab() {
    difference() {
        union() {
            linear_extrude(plate_t) round_rect(tab_w,tab_h,tab_radius);
            if(template_ribs)
                for(x=[3,11]) for(v=[[6.5,8],[15,17],[25,35]])
                    stroke3([x,v[0]],[x,v[1]],template_rib_w);
        }
        guide_holes(tab_holes,-eps,plate_t+template_rib_h+2*eps);
        guide_holes(tab_holes,plate_t,template_rib_h+eps,guide_d+1.2);
        // Two interrupted slots: skive limit at y=10, fold datum at y=12.
        for(y=[10,12]) for(v=[[1.8,5],[9,12.2]])
            translate([0,0,-eps]) linear_extrude(plate_t+template_rib_h+2*eps)
                slot2([v[0],y],[v[1],y],0.65);
        for(y=[3,21,39]) shallow_line([2,y],[12,y],0.4);
        engraved_text("C",[7,31],3.4);
    }
}

module choose_part() {
    if(part=="M1") translate([blank_w/2,blank_mouth_y,0]) M1_lower();
    else if(part=="M2") translate([press_outer_r,mouth_extension,0]) M2_press();
    else if(part=="M3")
        translate([cut_r+trim_slot_w+trim_outer_band,mouth_extension,0]) M3_trim();
    else if(part=="A") A_blank();
    else if(part=="B") translate([cut_r,flap_extension,0]) B_back();
    else if(part=="C") C_tab();
    else if(part=="assembly") {
        color("tan") M1_lower();
        color([0.25,0.5,0.65,0.8]) translate([0,0,base_t+leather_allowance+18]) M2_press();
        color([0.8,0.45,0.15,0.9]) translate([0,0,base_t+leather_allowance+40]) M3_trim();
    }
    else if(part=="layout") {
        translate([45,20,0]) M1_lower();
        translate([132,8,0]) M2_press();
        translate([132,110,0]) M3_trim();
        translate([175,0,0]) A_blank();
        translate([190,245,0]) B_back();
        translate([225,145,0]) C_tab();
    }
    else assert(false,"Unknown part selector");
}

echo(part=part,cut_width=2*cut_r,forming_width=2*mold_r,
     guide_d=guide_d,guide_web=min_guide_web,
     snap_mark_d=stud_hole_d,snap_access_d=snap_access_d,trim_slot_w=trim_slot_w);
choose_part();
