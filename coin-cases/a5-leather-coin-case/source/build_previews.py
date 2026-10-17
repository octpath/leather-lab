"""Render previews from the delivered PDF and actual STL cross-sections."""
from pathlib import Path

import fitz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon as PolygonPatch, Rectangle
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
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
        ax.add_patch(PolygonPatch(np.asarray(polygon.exterior.coords),
                                 facecolor=color, edgecolor=edgecolor, linewidth=linewidth))
        for hole in polygon.interiors:
            ax.add_patch(PolygonPatch(np.asarray(hole.coords), facecolor='white',
                                     edgecolor=edgecolor, linewidth=linewidth))


def templates_preview():
    font = FontProperties(fname=str(FONT))
    mesh = trimesh.load_mesh(PROJECT / '3d/a5-leather-coin-case-templates.stl')
    material = section_shape(mesh, 1.0)
    top = section_shape(mesh, 1.95)
    engraving = material.difference(top)
    fig = plt.figure(figsize=(6, 9), facecolor='white')
    ax = fig.add_axes([0.09, 0.16, 0.82, 0.72])
    ax.add_patch(Rectangle((0, 0), 148, 210, facecolor='white',
                           edgecolor='#aeb4b7', linewidth=0.9, linestyle=(0, (4, 3))))
    draw_shape(ax, material, '#e8e2d5', '#4b4b45', 0.35)
    draw_shape(ax, engraving, '#58869a')
    for name, xy in {'A':(40.5, 151), 'B':(40.5, 10.5),
                     'C':(99, 173), 'D':(99, 100)}.items():
        ax.text(*xy, name, ha='center', va='center', fontproperties=font,
                fontsize=14, color='#484740')
    ax.set(xlim=(-3, 151), ylim=(-3, 213), aspect='equal')
    ax.axis('off')
    fig.text(0.09, 0.95, 'A5 LEATHER COIN CASE', fontproperties=font, fontsize=17, color='#333333')
    fig.text(0.09, 0.916, '3D型紙・4枚一括配置', fontproperties=font, fontsize=12, color='#555555')
    lines = [
        '板厚 2mm  /  位置写し穴 直径1.1mm',
        'ホック穴：7号 直径2.1mm・12号 直径3.6mm',
        '白抜き：貫通穴　青：上面の浅い溝',
        '実際のSTL断面から作成した上面図。原寸ではありません。',
    ]
    for i, line in enumerate(lines):
        fig.text(0.09, 0.135-i*0.025, line, fontproperties=font,
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
