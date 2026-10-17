#!/usr/bin/env python3
"""Make the fixed oct lip-balm case pattern. All geometry is in millimetres.

Run with: python build_pattern.py
Outputs a four-page 1:1 PDF, three vector SVGs, and geometry.json.
The forming blank and the formed front projection are separate coordinate spaces.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from fontTools.ttLib import TTFont as InspectFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "assets" / "NotoSansJP-Regular.ttf"
LOGO = ROOT / "assets" / "oct_logo_transparent.png"
MM = 72 / 25.4
PAGE_W, PAGE_H = 210 * MM, 297 * MM
INK = HexColor("#283039")
MUTED = HexColor("#666c72")
LIGHT = HexColor("#a0a5a9")
CUT = Color(.12,.12,.12)
STITCH = Color(.64,.30,.06)
GUIDE = Color(.20,.43,.57)
CUT_WIDTH_MM = .6/MM
STITCH_WIDTH_MM = .35/MM
GUIDE_WIDTH_MM = .5/MM
GUIDE_DASH_MM = tuple(v/MM for v in (4,2,1,2))
RULE = HexColor("#d6d0c7")

PITCH = 4.0
EDGE = 3.0
BOTTOM_INTERVALS = 10
SEAM_R = PITCH / (2 * math.sin(math.pi / (2 * BOTTOM_INTERVALS)))
CUT_R = SEAM_R + EDGE
FORMING_TO_SEAM = 2.5
MOLD_R = SEAM_R - FORMING_TO_SEAM
STRAIGHT = 51.0
FORMED_H = STRAIGHT + CUT_R
FLAP_EXTENSION = 100.0
FLAP_SNAP_FROM_MOUTH = -88.0
FRONT_SNAP_FROM_MOUTH = 12.0
FRONT_SNAP_PUNCH_NUMBER, FRONT_SNAP_PUNCH_D = 7, 2.1
FLAP_SNAP_PUNCH_NUMBER, FLAP_SNAP_PUNCH_D = 12, 3.6
BLANK_W, BLANK_H = 90.0, 120.0
BLANK_MOUTH_FROM_TOP = 20.0
TAB_W, TAB_H = 14.0, 42.0
TAB_SHORT_RETURN = 12.0
TAB_SKIVE_LENGTH = 10.0
TAB_LONG_LEG = TAB_H - TAB_SHORT_RETURN
TAB_TOP_FROM_MOUTH = 0.0
TAB_FREE_END_FROM_MOUTH = TAB_TOP_FROM_MOUTH + TAB_LONG_LEG
TAB_OUTER_AWL_OFFSET = 1.0


def seam_points():
    pts = [(-SEAM_R, 3 + 4 * i) for i in range(13)]
    pts += [(SEAM_R * math.cos(math.pi - math.pi * j / 10),
             STRAIGHT + SEAM_R * math.sin(math.pi - math.pi * j / 10))
            for j in range(1, 11)]
    pts += [(SEAM_R, STRAIGHT - 4 * i) for i in range(1, 13)]
    return pts


SEAM = seam_points()
# C's blank coordinates: y=0 is the short, skived tip; fold at y=12.
# Fold y=3 onto y=21. The finished rows are y=21 and y=39 in the blank's
# long-leg coordinate system. The lower row does not cross the returned tip.
TAB_LONG_ROWS = [21.0, 39.0]
TAB_BLANK_HOLES = [(x, y) for y in (3.0, *TAB_LONG_ROWS) for x in (3.0, 7.0, 11.0)]
BACK_TAB_SHARED = [(x-TAB_W/2, TAB_FREE_END_FROM_MOUTH-(TAB_H-y))
                   for y in TAB_LONG_ROWS for x in (3.0, 7.0, 11.0)]
BACK_TAB_AWL = [(x, TAB_FREE_END_FROM_MOUTH-(TAB_H-y))
                for y in TAB_LONG_ROWS
                for x in (-TAB_W/2-TAB_OUTER_AWL_OFFSET, TAB_W/2+TAB_OUTER_AWL_OFFSET)]
BACK_TAB_HOLES = BACK_TAB_SHARED + BACK_TAB_AWL


def verify_geometry():
    assert len(SEAM) == 35
    distances = [math.dist(a, b) for a, b in zip(SEAM, SEAM[1:])]
    assert max(abs(d - PITCH) for d in distances) < 1e-10
    assert len({(round(x, 8), round(y, 8)) for x, y in SEAM}) == len(SEAM)
    for x, y in SEAM:
        if y <= STRAIGHT + 1e-9:
            assert abs((CUT_R - abs(x)) - EDGE) < 1e-8
        else:
            assert abs(CUT_R - math.hypot(x, y - STRAIGHT) - EDGE) < 1e-8
    assert all(math.dist(a, b) > 1e-8 for i, a in enumerate(SEAM)
               for b in SEAM[i + 1:])
    assert all(min(x, TAB_W-x, y, TAB_H-y) >= 3 for x,y in TAB_BLANK_HOLES)
    assert 2*TAB_SHORT_RETURN-3 == TAB_LONG_ROWS[0]
    assert 2*TAB_SHORT_RETURN-TAB_LONG_ROWS[0] == 3
    assert 2*TAB_SHORT_RETURN-TAB_LONG_ROWS[1] < 0
    for y in sorted({y for x,y in BACK_TAB_HOLES}):
        row=sorted((x,yy) for x,yy in BACK_TAB_HOLES if yy==y)
        assert len(row)==5
        assert all(abs(math.dist(a,b)-4)<1e-10 for a,b in zip(row,row[1:]))
        assert abs(abs(row[0][0])-TAB_W/2-TAB_OUTER_AWL_OFFSET)<1e-10
    assert len(BACK_TAB_SHARED)==6 and len(BACK_TAB_AWL)==4
    assert all(abs(x)>TAB_W/2 for x,y in BACK_TAB_AWL)
    assert all(abs(x)<TAB_W/2 for x,y in BACK_TAB_SHARED)
    for x,y in BACK_TAB_SHARED:
        blank=(x+TAB_W/2, y-TAB_FREE_END_FROM_MOUTH+TAB_H)
        assert blank in TAB_BLANK_HOLES
    # A and B use the identical shared list, with no independent rounding.
    assert SEAM == seam_points()
    a = MOLD_R
    b = 18.0
    max_inscribed_diameter = 2 * a * math.sqrt(1 - (a / b) ** 2)
    assert max_inscribed_diameter > 16.8
    return {
        "shared_main_hole_count": len(SEAM),
        "adjacent_main_hole_center_distance_mm": [min(distances), max(distances)],
        "cut_edge_to_main_hole_center_mm": EDGE,
        "bottom_arc_length_mm": math.pi * SEAM_R,
        "bottom_chord_sum_mm": 10 * PITCH,
        "semiellipse_body_max_inscribed_circle_diameter_mm": max_inscribed_diameter,
        "tab_rows_finished":2,
        "tab_row_pitch_including_back_only_awl_endpoints_mm":4,
        "back_only_awl_hole_count":len(BACK_TAB_AWL),
        "back_only_awl_hole_distance_outside_C_mm":TAB_OUTER_AWL_OFFSET,
        "tab_short_return_mm":TAB_SHORT_RETURN,
        "tab_attachment_top_y_from_mouth_mm":TAB_TOP_FROM_MOUTH,
        "tab_folded_tip_edge_to_upper_row_mm":2*TAB_SHORT_RETURN-TAB_LONG_ROWS[0],
        "physical_validation": "Trial required: leather stretch, shrinkage, bottom seating, flap, and actual hardware",
    }


QA = verify_geometry()
pdfmetrics.registerFont(TTFont("NotoJP", str(FONT)))
FONT_CMAP = InspectFont(FONT).getBestCmap()
USED_TEXT = []


def ptxy(x, y):
    return x * MM, PAGE_H - y * MM


def text(c, x, y, value, size=8, color=INK, align="left"):
    USED_TEXT.append(value)
    missing = [ch for ch in value if not ch.isspace() and ord(ch) not in FONT_CMAP]
    if missing:
        raise ValueError(f"Missing font glyphs: {missing}")
    c.setFont("NotoJP", size)
    c.setFillColor(color)
    px, py = ptxy(x, y)
    if align == "center":
        c.drawCentredString(px, py, value)
    elif align == "right":
        c.drawRightString(px, py, value)
    else:
        c.drawString(px, py, value)


def line(c, x1, y1, x2, y2, color=INK, width=.22, dash=None):
    c.setStrokeColor(color)
    c.setLineWidth(width * MM)
    c.setDash([v*MM for v in dash] if dash else [])
    c.line(*ptxy(x1, y1), *ptxy(x2, y2))
    c.setDash()


def rect(c, x, y, w, h, color=CUT, width=CUT_WIDTH_MM, dash=None, radius=0):
    c.setStrokeColor(color)
    c.setLineWidth(width * MM)
    c.setDash([v*MM for v in dash] if dash else [])
    if radius:
        c.roundRect(x * MM, PAGE_H - (y+h) * MM, w * MM, h * MM,
                    radius * MM, stroke=1, fill=0)
    else:
        c.rect(x * MM, PAGE_H - (y+h) * MM, w * MM, h * MM, stroke=1, fill=0)
    c.setDash()


def guide_line(c,x1,y1,x2,y2):
    line(c,x1,y1,x2,y2,GUIDE,GUIDE_WIDTH_MM,GUIDE_DASH_MM)


def guide_rect(c,x,y,w,h):
    rect(c,x,y,w,h,GUIDE,GUIDE_WIDTH_MM,GUIDE_DASH_MM)


def dot(c, x, y):
    c.setFillColor(STITCH)
    c.circle(*ptxy(x, y), .20 * MM, stroke=0, fill=1)


def awl_mark(c, x, y):
    # Centre-location symbol, NOT a prescribed hole diameter.
    c.setFillColor(Color(1,1,1))
    c.setStrokeColor(STITCH)
    c.setLineWidth(.35)
    c.circle(*ptxy(x,y),.40*MM,stroke=1,fill=1)
    dot(c,x,y)


def snap(c, x, y, diameter, provisional=False):
    # The circle is the specified punch diameter at 1:1 scale.
    c.setStrokeColor(MUTED if provisional else CUT)
    c.setLineWidth(CUT_WIDTH_MM * MM)
    if provisional:
        c.setDash(1 * MM, .6 * MM)
    c.circle(*ptxy(x, y), diameter / 2 * MM, stroke=1, fill=0)
    c.setDash()
    line(c, x-1.5, y, x+1.5, y, MUTED if provisional else INK, .16)
    line(c, x, y-1.5, x, y+1.5, MUTED if provisional else INK, .16)


def dimension_h(c, x1, x2, y, label, source_y=None):
    if source_y is not None:
        line(c, x1, source_y, x1, y-1.5, LIGHT, .12)
        line(c, x2, source_y, x2, y-1.5, LIGHT, .12)
    line(c, x1, y, x2, y, MUTED, .14)
    for x in (x1, x2):
        line(c, x-1, y+1, x+1, y-1, MUTED, .14)
    text(c, (x1+x2)/2, y-2, label, 7, MUTED, "center")


def dimension_v(c, x, y1, y2, label, source_x=None):
    if source_x is not None:
        line(c, source_x, y1, x-1.5, y1, LIGHT, .12)
        line(c, source_x, y2, x-1.5, y2, LIGHT, .12)
    line(c, x, y1, x, y2, MUTED, .14)
    for y in (y1, y2):
        line(c, x-1, y+1, x+1, y-1, MUTED, .14)
    c.saveState()
    c.translate(*ptxy(x-2, (y1+y2)/2))
    c.rotate(90)
    USED_TEXT.append(label)
    c.setFont("NotoJP", 7)
    c.setFillColor(MUTED)
    c.drawCentredString(0, 0, label)
    c.restoreState()


def u_outline(c, cx, top, radius, straight=STRAIGHT, dash=None, color=CUT, width=CUT_WIDTH_MM, fill=None):
    # Top edge is closed; body has vertical sides and a lower semicircle.
    p = c.beginPath()
    p.moveTo(*ptxy(cx-radius, top))
    p.lineTo(*ptxy(cx+radius, top))
    p.lineTo(*ptxy(cx+radius, top+straight))
    p.arcTo((cx-radius)*MM, PAGE_H-(top+straight+radius)*MM,
          (cx+radius)*MM, PAGE_H-(top+straight-radius)*MM,
          startAng=0, extent=-180)
    p.lineTo(*ptxy(cx-radius, top))
    p.close()
    c.setStrokeColor(color)
    c.setLineWidth(width * MM)
    c.setDash([v*MM for v in dash] if dash else [])
    if fill is not None:
        c.setFillColor(fill)
    c.drawPath(p, stroke=1, fill=fill is not None)
    c.setDash()


def capsule(c, cx, top, radius, total_h):
    p = c.beginPath()
    p.moveTo(*ptxy(cx-radius, top+radius))
    p.arcTo((cx-radius)*MM, PAGE_H-(top+2*radius)*MM,
          (cx+radius)*MM, PAGE_H-top*MM, startAng=180, extent=-180)
    p.lineTo(*ptxy(cx+radius, top+total_h-radius))
    p.arcTo((cx-radius)*MM, PAGE_H-(top+total_h)*MM,
          (cx+radius)*MM, PAGE_H-(top+total_h-2*radius)*MM,
          startAng=0, extent=-180)
    p.close()
    c.setStrokeColor(CUT)
    c.setLineWidth(.6)
    c.drawPath(p, stroke=1, fill=0)


def main_stitch_guide(c,cx,mouth):
    p=c.beginPath()
    p.moveTo(*ptxy(cx-SEAM_R,mouth+3))
    p.lineTo(*ptxy(cx-SEAM_R,mouth+STRAIGHT))
    p.arcTo((cx-SEAM_R)*MM,PAGE_H-(mouth+STRAIGHT+SEAM_R)*MM,
            (cx+SEAM_R)*MM,PAGE_H-(mouth+STRAIGHT-SEAM_R)*MM,
            startAng=180,extent=180)
    p.lineTo(*ptxy(cx+SEAM_R,mouth+3))
    c.setStrokeColor(STITCH)
    c.setLineWidth(.35)
    c.setDash()
    c.drawPath(p,stroke=1,fill=0)


def base(c, title, subtitle, number):
    text(c, 15, 18, title, 16)
    text(c, 15, 27, subtitle, 8, MUTED)
    c.drawImage(ImageReader(str(LOGO)), 178*MM, PAGE_H-19*MM,
                width=20*MM, height=15*MM, preserveAspectRatio=True,
                anchor="c", mask="auto")
    line(c, 15, 274, 65, 274, MUTED, .18)
    for n in range(6):
        x=15+10*n
        line(c, x, 273, x, 275, MUTED, .18)
    text(c, 70, 275, "50 mm | A4・100%（実際のサイズ）で印刷", 8, MUTED)
    line(c, 15, 283, 195, 283, RULE, .18)
    text(c, 15, 291, "oct / リップクリームケース", 8, MUTED)
    text(c, 195, 291, f"{number} / 4", 8, MUTED, "right")


def cover(c):
    c.drawImage(ImageReader(str(LOGO)),178*MM,PAGE_H-19*MM,
                width=20*MM,height=15*MM,preserveAspectRatio=True,
                anchor="c",mask="auto")
    text(c,20,57,"リップクリームケース",22)
    text(c,20,69,"LIP BALM CASE / 型紙",9,MUTED)
    line(c,20,85,190,85,RULE,.18)
    text(c,20,101,"パーツ",9,MUTED)
    text(c,180,101,"ページ",9,MUTED,"center")
    for label,note,page,y in [
        ("A：前面","1枚 / 革絞り前の粗裁ち用",2,120),
        ("B：背面兼フラップ","1枚",3,152),
        ("C：Dカン留め","1枚 / Dカン内幅15 mm用",4,184),
    ]:
        text(c,20,y,label,12)
        text(c,20,y+10,note,8,MUTED)
        text(c,180,y,str(page),10,INK,"center")
    line(c,20,209,35,209,CUT,CUT_WIDTH_MM)
    text(c,40,210,"裁断線",8,CUT)
    line(c,20,217,35,217,STITCH,STITCH_WIDTH_MM)
    for x in (23,27,31):
        dot(c,x,217)
    text(c,40,218,"縫いガイド・穴中心",8,STITCH)
    guide_line(c,20,225,35,225)
    text(c,40,226,"取付位置・折り目安",8,GUIDE)
    text(c,20,237,"A4・100%（実際のサイズ）で印刷してください。",9)
    text(c,20,247,"各パーツページの50 mm線で、印刷倍率を確認してください。",8)
    text(c,20,259,"ホック穴：A＝7号（2.1 mm）／B＝12号（3.6 mm）。",8,MUTED)
    line(c,15,283,195,283,RULE,.18)
    text(c,15,291,"oct / リップクリームケース",8,MUTED)
    text(c,195,291,"1 / 4",8,MUTED,"right")
    c.showPage()


def make_pdf():
    file = OUT / "lip-balm-case-pattern.pdf"
    c = canvas.Canvas(str(file), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle("リップクリームケース | oct")
    c.setAuthor("oct")
    c.setSubject("A4原寸型紙 / 前面、背面兼フラップ、Dカン留め")
    cover(c)

    # Page 2: actual material blank; no false finished projection is overlaid.
    base(c, "A | 前面", "1枚裁断 / 革厚1.0-1.5 mm / 革絞り前の粗裁ち用", 2)
    bx, by = 60, 64
    rect(c, bx, by, BLANK_W, BLANK_H)
    dimension_h(c, bx, bx+BLANK_W, 56, "90 mm", by)
    dimension_v(c, 51, by, by+BLANK_H, "120 mm", bx)
    mouth = by+BLANK_MOUTH_FROM_TOP
    sy = mouth+FRONT_SNAP_FROM_MOUTH
    guide_line(c,105,by,105,by+BLANK_H)
    guide_line(c,bx,mouth,bx+BLANK_W,mouth)
    snap(c, 105, sy, FRONT_SNAP_PUNCH_D)
    line(c,150,mouth,155,mouth,GUIDE,.13)
    text(c,158,mouth+1,"口元の基準",7,GUIDE)
    text(c,158,mouth+6,"上端から20 mm",7,GUIDE)
    line(c, 107, sy, 154, sy+7, MUTED, .13)
    text(c, 158, sy+8, "本体側ホック中心", 7)
    text(c, 158, sy+13, "ハトメ抜き7号（2.1 mm）", 7, MUTED)
    dimension_v(c, 117, mouth, sy, "12 mm")
    text(c,105,173,"ホック中心を基準に型へ位置合わせ",7,GUIDE,"center")
    text(c,20,207,"濃灰の実線＝粗裁ち線　青の一点鎖線＝位置合わせ基準　十字＝ホック中心",8)
    text(c,20,220,"ホックを取り付けてから成形。ホック中心を基準に型へ位置合わせします。",8)
    text(c,20,228,"成形後に口元と外周を切り揃えます。",8)
    text(c,20,240,"革厚1.0-1.5 mm / 縫い代3 mm / 菱目打ち4 mmピッチ",8,MUTED)
    text(c,20,248,"型はホックの表裏が当たらない形状にしてください。",8,MUTED)
    c.showPage()

    # Page 3: back plus a flap whose closure is positioned after forming.
    base(c, "B | 背面兼フラップ", "1枚裁断 / 銀面側（外側）を見た図", 3)
    cx, top = 105, 49
    mouth = top+FLAP_EXTENSION
    capsule(c, cx, top, CUT_R, FORMED_H+FLAP_EXTENSION)
    dimension_h(c, cx-CUT_R, cx+CUT_R, 41, "31.6 mm", top+CUT_R)
    dimension_v(c, 76, top, top+FORMED_H+FLAP_EXTENSION, "166.8 mm", cx-CUT_R)
    snap(c, cx, mouth+FLAP_SNAP_FROM_MOUTH, FLAP_SNAP_PUNCH_D)
    line(c, 108, mouth+FLAP_SNAP_FROM_MOUTH, 133, mouth+FLAP_SNAP_FROM_MOUTH, MUTED, .13)
    text(c, 137, mouth+FLAP_SNAP_FROM_MOUTH+1, "フラップ側ホック中心", 7)
    text(c, 137, mouth+FLAP_SNAP_FROM_MOUTH+6, "成形後に位置を合わせる", 7, MUTED)
    text(c, 137, mouth+FLAP_SNAP_FROM_MOUTH+11, "ハトメ抜き12号（3.6 mm）", 7, MUTED)
    guide_line(c,cx-CUT_R,mouth,cx+CUT_R,mouth)
    line(c,cx+CUT_R,mouth,133,mouth,GUIDE,.13)
    text(c,137,mouth+1,"Aの口元高さ",7,GUIDE)
    main_stitch_guide(c,cx,mouth)
    for x, y in SEAM:
        dot(c, cx+x, mouth+y)
    # C has a short return tucked behind its longer face; the tips do not align.
    guide_rect(c,cx-TAB_W/2,mouth+TAB_TOP_FROM_MOUTH,TAB_W,TAB_LONG_LEG)
    for row_y in sorted({y for x,y in BACK_TAB_HOLES}):
        line(c,cx-8,mouth+row_y,cx+8,mouth+row_y,STITCH,STITCH_WIDTH_MM)
    for x, y in BACK_TAB_SHARED:
        dot(c, cx+x, mouth+y)
    for x,y in BACK_TAB_AWL:
        awl_mark(c,cx+x,mouth+y)
    line(c,cx+TAB_W/2,mouth+TAB_TOP_FROM_MOUTH+13,133,mouth+TAB_TOP_FROM_MOUTH+13,GUIDE,.13)
    text(c,137,mouth+TAB_TOP_FROM_MOUTH+14,"C取付け位置",7,GUIDE)
    text(c,137,mouth+TAB_TOP_FROM_MOUTH+19,"長方形の上端を口元に揃える",7,GUIDE)
    text(c,20,230,"濃灰の実線＝裁断線　茶橙の線・点＝縫いガイド・穴中心　青の一点鎖線＝取付位置",8)
    text(c,20,239,"○＝Bだけに丸錐（穴中心）。Cの外側1 mmに配置。",8,STITCH)
    text(c,20,251,"フラップの長さとホック位置は、リップを入れた状態で合わせてください。",8,MUTED)
    c.showPage()

    # Page 4: a short skived return, secured by two horizontal stitch rows.
    base(c, "C | Dカン留め", "1枚裁断 / 内幅15 mmのDカン用", 4)
    cx, top = 105, 90
    rect(c, cx-TAB_W/2, top, TAB_W, TAB_H, radius=2)
    dimension_h(c, cx-TAB_W/2, cx+TAB_W/2, 80, "14 mm", top)
    dimension_v(c, 86, top, top+TAB_H, "42 mm", cx-TAB_W/2)
    guide_line(c,cx-TAB_W/2,top+TAB_SKIVE_LENGTH,cx+TAB_W/2,top+TAB_SKIVE_LENGTH)
    guide_line(c,cx-TAB_W/2,top+TAB_SHORT_RETURN,cx+TAB_W/2,top+TAB_SHORT_RETURN)
    for row_y in (3, *TAB_LONG_ROWS):
        line(c,cx-4,top+row_y,cx+4,top+row_y,STITCH,STITCH_WIDTH_MM)
    line(c,cx-TAB_W/2,top+10,72,top+10,GUIDE,.13)
    text(c,20,top+9,"先端側10 mm程度を斜め漉き",7,GUIDE)
    line(c,cx+4,top+3,132,top+1,MUTED,.13)
    text(c,136,top+1,"重ね穴：上側の横縫いへ",7,STITCH)
    line(c,cx+TAB_W/2,top+12,132,top+12,GUIDE,.13)
    text(c,136,top+13,"折り返しの目安（12 mm）",7,GUIDE)
    text(c,136,top+18,"短い側を裏へ回す",7,GUIDE)
    line(c,cx+4,top+21,132,top+24,MUTED,.13)
    text(c,136,top+25,"菱目打ち中心（4 mmピッチ）",7,STITCH)
    line(c,cx+4,top+39,132,top+39,MUTED,.13)
    text(c,136,top+40,"下側の横縫い",7,STITCH)
    dimension_h(c,cx-4,cx+4,top+TAB_H+9,"4 mm × 2")
    line(c,cx,top+TAB_H+8,cx,top+TAB_H+10,MUTED,.14)
    text(c,20,165,"濃灰の実線＝裁断線　茶橙の線・点＝縫いガイド・穴中心　青の一点鎖線＝折り目安",8)
    text(c,20,179,"斜め漉き後に短く折り返し、先端側の穴を上側の列に重ねます。",8)
    text(c,20,187,"横縫いの両端はBだけに丸錐。Cにはあけません。",8)
    text(c,20,200,"折り返し位置と重ね穴は、金具を通した状態で合わせてください。",8)
    text(c,20,212,"縫い代3 mm / 4 mmピッチ",8,MUTED)
    # Draw every centre last so labels/leaders cannot obscure the 0.4 mm dots.
    for x,y in TAB_BLANK_HOLES:
        dot(c,cx-TAB_W/2+x,top+y)
    c.showPage()
    c.save()
    return file


def svg_start(w, h, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.9f}mm" height="{h:.9f}mm" viewBox="0 0 {w:.9f} {h:.9f}">',
            f'<title>{escape(title)}</title>',
            '<desc>Dimensions in millimetres. Cut outlines black; hole centres orange. See PDF and geometry.json for specified snap punch diameters.</desc>']


def svg_dot(x, y):
    return f'<circle cx="{x:.9f}" cy="{y:.9f}" r="0.2" fill="#A34D0F"/>'


def write_svgs():
    # These are 2D reference assets, not 3D models or a developed formed skin.
    w=2*CUT_R
    s=svg_start(w, FORMED_H, "A 成形後・投影外形")
    s += [f'<path d="M 0 0 H {w:.9f} V {STRAIGHT:.9f} A {CUT_R:.9f} {CUT_R:.9f} 0 0 1 0 {STRAIGHT:.9f} Z" fill="none" stroke="#1F1F1F" stroke-width="{CUT_WIDTH_MM:.9f}"/>']
    s += [svg_dot(x+CUT_R,y) for x,y in SEAM]
    s += ['</svg>']
    (ROOT/"a-formed-projection.svg").write_text('\n'.join(s),encoding="utf-8")
    # The paper window template is intentionally omitted; retain only the
    # formed contour as a future 3D trimming-guide reference.
    (ROOT/"a-negative-cutting-template.svg").unlink(missing_ok=True)
    h=FLAP_EXTENSION+FORMED_H
    s=svg_start(w,h,"B 背面兼フラップ")
    s += [f'<path d="M 0 {CUT_R:.9f} A {CUT_R:.9f} {CUT_R:.9f} 0 0 1 {w:.9f} {CUT_R:.9f} V {h-CUT_R:.9f} A {CUT_R:.9f} {CUT_R:.9f} 0 0 1 0 {h-CUT_R:.9f} Z" fill="none" stroke="#1F1F1F" stroke-width="{CUT_WIDTH_MM:.9f}"/>']
    s += [f'<path d="M {CUT_R-SEAM_R:.9f} {FLAP_EXTENSION+3:.9f} V {FLAP_EXTENSION+STRAIGHT:.9f} A {SEAM_R:.9f} {SEAM_R:.9f} 0 0 0 {CUT_R+SEAM_R:.9f} {FLAP_EXTENSION+STRAIGHT:.9f} V {FLAP_EXTENSION+3:.9f}" fill="none" stroke="#A34D0F" stroke-width="{STITCH_WIDTH_MM:.9f}"/>']
    dash=' '.join(f'{v:.9f}' for v in GUIDE_DASH_MM)
    s += [f'<path d="M 0 {FLAP_EXTENSION} H {w:.9f}" stroke="#336E91" stroke-width="{GUIDE_WIDTH_MM:.9f}" stroke-dasharray="{dash}"/>',
          f'<rect x="{CUT_R-TAB_W/2:.9f}" y="{FLAP_EXTENSION+TAB_TOP_FROM_MOUTH:.9f}" width="{TAB_W}" height="{TAB_LONG_LEG}" fill="none" stroke="#336E91" stroke-width="{GUIDE_WIDTH_MM:.9f}" stroke-dasharray="{dash}"/>']
    s += [svg_dot(x+CUT_R,y+FLAP_EXTENSION) for x,y in SEAM]
    for yy in sorted({y for x,y in BACK_TAB_HOLES}):
        s += [f'<path d="M {CUT_R-8:.9f} {yy+FLAP_EXTENSION:.9f} H {CUT_R+8:.9f}" stroke="#A34D0F" stroke-width="{STITCH_WIDTH_MM:.9f}"/>']
    s += [svg_dot(x+CUT_R,y+FLAP_EXTENSION) for x,y in BACK_TAB_SHARED]
    for x,y in BACK_TAB_AWL:
        s += [f'<circle cx="{x+CUT_R:.9f}" cy="{y+FLAP_EXTENSION:.9f}" r="0.4" fill="white" stroke="#A34D0F" stroke-width="{STITCH_WIDTH_MM:.9f}"/>',svg_dot(x+CUT_R,y+FLAP_EXTENSION)]
    s += ['</svg>']
    (ROOT/"b-back-flap.svg").write_text('\n'.join(s),encoding="utf-8")
    s=svg_start(TAB_W,TAB_H,"C Dカン留め")
    s += [f'<rect x="0" y="0" width="{TAB_W}" height="{TAB_H}" rx="2" fill="none" stroke="#1F1F1F" stroke-width="{CUT_WIDTH_MM:.9f}"/>',
          f'<path d="M 0 {TAB_SHORT_RETURN} H {TAB_W}" stroke="#336E91" stroke-width="{GUIDE_WIDTH_MM:.9f}" stroke-dasharray="{dash}"/>',
          f'<path d="M 0 {TAB_SKIVE_LENGTH} H {TAB_W}" stroke="#336E91" stroke-width="{GUIDE_WIDTH_MM:.9f}" stroke-dasharray="{dash}"/>']
    for y in (3,*TAB_LONG_ROWS):
        s += [f'<path d="M 3 {y} H 11" stroke="#A34D0F" stroke-width="{STITCH_WIDTH_MM:.9f}"/>']
    s += [svg_dot(x,y) for x,y in TAB_BLANK_HOLES]
    s += ['</svg>']
    (ROOT/"c-d-ring-tab.svg").write_text('\n'.join(s),encoding="utf-8")


def write_data():
    data={
        "units":"mm", "status":"fixed_pdf", "brand":"oct",
        "leather_thickness_range":[1.0,1.5],
        "lip_samples":[{"length":77,"diameter":16},{"length":83,"diameter":15},{"length":67,"diameter":15}],
        "target_effective_insertion_depth":55,
        "coordinate_convention":"x from centreline; y downward from formed pocket mouth. Blank coordinates are separate.",
        "stitch":{"pitch_chord":PITCH,"cut_edge_offset":EDGE,"bottom_intervals":BOTTOM_INTERVALS,
                  "bottom_seam_radius":SEAM_R,"main_hole_centres":SEAM},
        "front_formed":{"cut_width":2*CUT_R,"cut_height":FORMED_H,"cut_bottom_radius":CUT_R,
                        "straight_length":STRAIGHT,"snap_centre":[0,12],
                        "snap_punch_number":FRONT_SNAP_PUNCH_NUMBER,"snap_punch_diameter":FRONT_SNAP_PUNCH_D},
        "front_forming_blank":{"width":90,"height":120,"mouth_reference_from_top":20,
                               "snap_centre_from_top_left":[45,32],
                               "snap_punch_number":FRONT_SNAP_PUNCH_NUMBER,"snap_punch_diameter":FRONT_SNAP_PUNCH_D,
                               "note":"Oversized blank, not a compensated developed skin. Install front snap before forming; datum registration required."},
        "trimming_guide_reference":{"aperture_width":2*CUT_R,"aperture_height":FORMED_H,
                                    "paper_template_included":False,
                                    "note":"Reserved for a future 3D-printed trimming guide. No paper window template in this revision."},
        "forming_target_not_yet_manufactured":{"projected_width":2*MOLD_R,"projected_bottom_radius":MOLD_R,
                                              "projected_straight_length":STRAIGHT,"depth":18,
                                              "body_section":"semiellipse against flat back; lower surface smoothly rounded",
                                              "snap_relief_external_diameter":None,"snap_relief_internal_diameter":None,
                                              "snap_relief_depths":None,
                                              "note":"Both inner and outer hardware need relief. Actual hardware dimensions unknown. No 3D file authored."},
        "back":{"cut_width":2*CUT_R,"cut_height":FLAP_EXTENSION+FORMED_H,
                "flap_extension_from_mouth":FLAP_EXTENSION,"provisional_flap_snap_centre":[0,FLAP_SNAP_FROM_MOUTH],
                "snap_punch":"No.12 / 3.6 mm; determine centre after forming with longest lip fitted",
                "snap_punch_number":FLAP_SNAP_PUNCH_NUMBER,"snap_punch_diameter":FLAP_SNAP_PUNCH_D,
                "main_hole_centres":SEAM,"tab_shared_hole_centres":BACK_TAB_SHARED,
                "tab_back_only_round_awl_centres":BACK_TAB_AWL,
                "tab_back_only_awl_offset_outside_C":TAB_OUTER_AWL_OFFSET},
        "d_ring_tab":{"width":TAB_W,"length":TAB_H,"corner_radius":2,
                      "assumed_d_ring_inner_width":15,"assumed_d_ring_wire_diameter":None,
                      "blank_origin":"top-left of short skived tip",
                      "short_return_length":TAB_SHORT_RETURN,"long_leg_length":TAB_LONG_LEG,
                      "skive_from_short_tip":TAB_SKIVE_LENGTH,
                      "fold_reference_from_short_tip":TAB_SHORT_RETURN,
                      "blank_hole_centres":TAB_BLANK_HOLES,
                      "finished_stitch_rows_blank_y":TAB_LONG_ROWS,
                      "attachment_top_y_from_mouth":TAB_TOP_FROM_MOUTH,
                      "long_free_edge_y_from_mouth":TAB_FREE_END_FROM_MOUTH,
                      "folded_short_tip_y_from_mouth":TAB_FREE_END_FROM_MOUTH-(TAB_H-2*TAB_SHORT_RETURN),
                      "note":"Two horizontal seams; only B has the four outside round-awl endpoints. Fit fold and overlapping holes with actual hardware."},
        "qa":QA,
    }
    (ROOT/"geometry.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"qa.json").write_text(json.dumps(QA,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    pdf=make_pdf()
    write_svgs()
    write_data()
    print(json.dumps({"pdf":str(pdf),"pages":4,"width_mm":2*CUT_R,"formed_height_mm":FORMED_H,"qa":QA},ensure_ascii=False))
