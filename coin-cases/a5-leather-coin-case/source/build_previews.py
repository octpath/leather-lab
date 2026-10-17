"""Render previews from the delivered PDF and actual STL cross-sections."""
from pathlib import Path

import fitz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
from matplotlib.path import Path as PlotPath
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
import trimesh

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parent
IMAGES = PROJECT / 'images'
FONT = SOURCE / 'assets/NotoSansJP-Regular.ttf'


def pdf_preview():
    doc = fitz.open(PROJECT / 'pdf/a5-leather-coin-case-pattern.pdf')
    margin, gap, label_h = 28, 24, 32
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(0.85, 0.85), alpha=False)
        pages.append(Image.frombytes('RGB', [pix.width, pix.height], pix.samples))
    w, h = pages[0].size
    canvas = Image.new('RGB', (2*w+2*margin+gap, 2*(h+label_h)+2*margin+gap), '#eeeeec')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT), 17)
    for i, page in enumerate(pages):
        x = margin + (i % 2)*(w+gap)
        y = margin + (i // 2)*(h+label_h+gap)
        canvas.paste(page, (x, y))
        draw.text((x+4, y+h+4), f'{i+1} / 4', font=font, fill='#555555')
    canvas.save(IMAGES / 'pattern-preview.png')


def section_shape(mesh, z):
    """Use even/odd nesting of closed section loops to recover the solid."""
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    solid = Polygon()
    for loop in section.discrete:
        polygon = Polygon(np.asarray(loop)[:, :2])
        if not polygon.is_valid:
            raise ValueError('Invalid STL section contour')
        solid = solid.symmetric_difference(polygon)
    return solid


def draw_shape(ax, shape, color, edgecolor='none', linewidth=0):
    polygons = list(shape.geoms) if shape.geom_type == 'MultiPolygon' else [shape]
    for polygon in polygons:
        if polygon.is_empty:
            continue
        polygon=orient(polygon,sign=1)
        vertices=[];codes=[]
        for ring in [polygon.exterior,*polygon.interiors]:
            points=np.asarray(ring.coords)
            vertices.extend(points)
            codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(points)-2)+[PlotPath.CLOSEPOLY])
        ax.add_patch(PathPatch(PlotPath(vertices,codes),facecolor=color,
                              edgecolor=edgecolor,linewidth=linewidth))


def templates_preview():
    font = FontProperties(fname=str(FONT))
    fig = plt.figure(figsize=(7.4, 9.6), facecolor='white')
    placements=[('A','本体','a-body-template.stl',[.05,.21,.46,.64]),
                ('B','かぶせ裏','b-flap-liner-template.stl',[.55,.66,.41,.16]),
                ('C','左マチ','c-left-gusset-template.stl',[.55,.43,.41,.18]),
                ('D','右マチ','d-right-gusset-template.stl',[.55,.20,.41,.18])]
    for letter,label,filename,position in placements:
        mesh=trimesh.load_mesh(PROJECT/'3d'/filename)
        material=section_shape(mesh,1.0);cap=section_shape(mesh,1.95)
        root=section_shape(mesh,2.15);top=section_shape(mesh,3.35)
        ax=fig.add_axes(position)
        draw_shape(ax,material,'#e8e2d5','#4b4b45',.35)
        draw_shape(ax,root,'#d9b47b')
        draw_shape(ax,top,'#aa7634')
        draw_shape(ax,material.difference(cap),'#58869a')
        xmin,ymin,xmax,ymax=material.bounds
        ax.set(xlim=(xmin-2,xmax+2),ylim=(ymin-2,ymax+2),aspect='equal')
        ax.axis('off')
        ax.set_title(f'{letter}  |  {label}',fontproperties=font,fontsize=11,pad=12,loc='left')
    fig.text(.07,.95,'A5 LEATHER COIN CASE',fontproperties=font,fontsize=18,color='#333333')
    fig.text(.07,.913,'補強付き3D型紙・個別4ファイル',fontproperties=font,fontsize=12,color='#555555')
    lines = [
        '平板 2mm ＋ 上面リブ 1.4mm ＝ 全高 3.4mm',
        '茶：リブ　青：取付位置　白抜き：工具穴・角丸の貫通窓',
        'ガイド穴 直径1.1mm ／ ホック穴 直径2.1・3.6mm',
        '実際のSTL断面から作成。各パーツの表示倍率は異なります。実機印刷は未確認です。',
    ]
    for i, line in enumerate(lines):
        fig.text(0.07, 0.135-i*0.025, line, fontproperties=font,
                 fontsize=9 if i < 3 else 8, color='#555555')
    fig.savefig(IMAGES / '3d-templates.png', dpi=200)
    plt.close(fig)


def main():
    IMAGES.mkdir(exist_ok=True)
    pdf_preview()
    templates_preview()
    print('Wrote images/pattern-preview.png and images/3d-templates.png')


if __name__ == '__main__':
    main()
