"""Build the full-size A5 Leather Coin Case PDF from geometry.json."""
from pathlib import Path
import json
import math
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parent
GEOMETRY = SOURCE / 'geometry.json'
OUT = PROJECT / 'pdf/a5-leather-coin-case-pattern.pdf'
ASSETS = SOURCE / 'assets'
FONT_PATH = ASSETS / 'NotoSansJP-Regular.ttf'
MM = 72 / 25.4
PW, PH = 210*MM, 297*MM
INK = colors.Color(0.12, 0.12, 0.12)
MUTED = colors.HexColor('#666B6C')
LIGHT = colors.HexColor('#A5AAAB')
RULE = colors.HexColor('#DADDDD')
STITCH = colors.Color(0.64, 0.30, 0.06)
ATTACH = colors.Color(0.20, 0.43, 0.57)
FONT = 'NotoSansJP'
TITLE = 'A5サイズの革で作るコインケース'
pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))
g = json.loads(GEOMETRY.read_text())
p = g['parameters']
W, BODY_H, LINER_H = p['width'], p['body_height'], p['liner_height']
GW, GH = p['gusset_width'], p['gusset_height']
N = 4

c = None

def xy(x,y): return x*MM,(297-y)*MM

def text(x,y,s,size=8,color=INK,align='left'):
    c.setFillColor(color);c.setFont(FONT,size)
    xx,yy=xy(x,y)
    if align=='center':c.drawCentredString(xx,yy,s)
    elif align=='right':c.drawRightString(xx,yy,s)
    else:c.drawString(xx,yy,s)

def line(x1,y1,x2,y2,width=.55,color=INK,dash=None):
    c.saveState();c.setStrokeColor(color);c.setLineWidth(width)
    c.setDash(dash or [])
    c.line(*xy(x1,y1),*xy(x2,y2));c.restoreState()

def poly(points,width=.6,color=INK,dash=None):
    c.saveState();c.setStrokeColor(color);c.setLineWidth(width)
    c.setDash(dash or [])
    path=c.beginPath();path.moveTo(*xy(*points[0]))
    for point in points[1:]:path.lineTo(*xy(*point))
    path.close();c.drawPath(path,stroke=1,fill=0);c.restoreState()

def ring(x,y,r,color=STITCH,width=.5):
    c.saveState();c.setStrokeColor(color);c.setLineWidth(width)
    c.circle(*xy(x,y),r*MM,stroke=1,fill=0);c.restoreState()

def dot(x,y,r=.2):
    c.saveState();c.setFillColor(STITCH)
    c.circle(*xy(x,y),r*MM,stroke=0,fill=1);c.restoreState()

def hole_mark(x,y,kind):
    dot(x,y)
    if kind=='awl':ring(x,y,.45)

def logo():
    image=Image.open(ASSETS/'oct_logo_transparent.png')
    iw,ih=image.size
    scale=min(20/iw,15/ih)
    ww,hh=iw*scale,ih*scale
    xx,yy=xy(178,4+hh)
    c.drawImage(ImageReader(image),xx,yy,width=ww*MM,height=hh*MM,mask='auto')

def footer(page,check=True):
    if check:
        line(15,274,65,274,width=.6)
        for i in range(6):line(15+10*i,274,15+10*i,274-(1.8 if i in [0,5] else 1.0),width=.55)
        text(40,271,'50 mm',7,align='center')
        text(78,274.8,'A4・100%（実際のサイズ）',8)
    line(15,283,195,283,width=.4,color=RULE)
    text(15,291,f'oct / {TITLE}',6.5,MUTED)
    text(195,291,str(page),6.5,MUTED,align='right')

def header(page,title,description):
    logo();text(15,18,title,16);text(15,27,description,8,MUTED)
    footer(page)

def legend(attachment=False):
    line(15,258,23,258,width=.6)
    text(26,259.7,'裁断線',7,MUTED)
    line(46,258,55,258,width=.35,color=STITCH)
    dot(50.5,258)
    text(58,259.7,'縫いガイド・穴中心',7,MUTED)
    hole_mark(104.5,258,'awl')
    text(107,259.7,'丸錐中心',7,MUTED)
    if attachment:
        line(141,258,151,258,width=.5,color=ATTACH,dash=[4,2,1,2])
        text(154,259.7,'取付位置',7,ATTACH)


def snap(x,y,diameter,number,label_x,label_y,optional=False):
    ring(x,y,diameter/2,color=INK,width=.5)
    line(x-.75,y,x+.75,y,width=.4)
    line(x,y-.75,x,y+.75,width=.4)
    label=f'ハトメ抜き{number}号（{diameter:.1f} mm）'
    assert pdfmetrics.stringWidth(label,FONT,7)/MM < W-12
    text(label_x,label_y,label,7,align='center')
    if optional:
        note='任意で穴あけ・ホック取り付け可'
        assert pdfmetrics.stringWidth(note,FONT,7)/MM < W-12
        text(label_x,label_y+4,note,7,align='center')

def part(key,origin,label,label_y=None):
    data=g[key];ox,oy=origin
    guide=data.get('seam_guide',[])
    for a,b in zip(guide,guide[1:]):line(ox+a[0],oy+a[1],ox+b[0],oy+b[1],width=.35,color=STITCH)
    poly([(ox+x,oy+y) for x,y in data['outline']])
    for h in data['holes']:hole_mark(ox+h['x'],oy+h['y'],h['kind'])
    box=data['outline'];cx=(min(x for x,y in box)+max(x for x,y in box))/2
    if label_y is not None:text(ox+cx,oy+label_y,label,10,MUTED,align='center')

def main():
    global c
    OUT.parent.mkdir(parents=True,exist_ok=True)
    c = canvas.Canvas(str(OUT),pagesize=(PW,PH),pageCompression=1)
    c.setTitle(f'{TITLE} | oct')
    c.setAuthor('oct')
    c.setSubject(f'{TITLE} 原寸型紙 / 縫い代3mm・菱目打ち4mmピッチ')
    c.setCreator('oct')

    # 1 - cover
    logo()
    text(20,53,TITLE,22)
    text(20,65,'A5 LEATHER COIN CASE / 原寸型紙',8,MUTED)
    line(20,84,190,84,width=.5,color=RULE)
    text(20,96,'パーツ',8,MUTED)
    text(176,96,'ページ',8,MUTED,align='right')
    entries=[('A：本体','1枚',2),('B：かぶせ裏','1枚',3),('C：マチ・左','1枚',3),('D：マチ・右','1枚 / C・Dは左右対称',3)]
    for i,(title,note,page) in enumerate(entries):
        y=113+23*i
        text(20,y,title,11)
        text(176,y,str(page),8,align='right')
        text(20,y+9,note,8,MUTED)
    line(20,203,190,203,width=.4,color=RULE)
    text(20,215,'裁断配置（A5・参考）',9)
    text(176,215,'4',8,align='right')
    line(20,224,30,224,width=.6)
    text(33,225.3,'裁断線',7,MUTED)
    line(75,224,85,224,width=.35,color=STITCH)
    dot(80,224)
    text(88,225.3,'縫いガイド・穴中心',7,MUTED)
    line(20,231,30,231,width=.5,color=ATTACH,dash=[4,2,1,2])
    text(33,232.3,'取付位置',7,ATTACH)
    text(20,237,'革厚1～1.4 mm / 縫い代3 mm / 菱目打ち4 mmピッチ',8)
    text(20,246,'厚みが出る場合は、マチの縫い代を斜め漉き。',8,MUTED)
    text(20,258,'A4・100%（実際のサイズ）で印刷してください。',8)
    text(20,266,'各パーツページの50 mm線を実測し、印刷倍率を確認してください。',8)
    text(20,274,'穴径は使用する金具に合わせてください。',8,MUTED)
    footer(1,check=False)
    c.showPage()

    # 2 - body
    header(2,'A | 本体','1枚裁断 / 取り付け境界の丸錐穴は本体のみ。')
    ox=(210-W)/2;oy=55
    part('body',(ox,oy),'A',label_y=(g['attachment_y']['base_start']+g['attachment_y']['base_end'])/2)
    for y in g['attachment_y'].values():line(ox,oy+y,ox+W,oy+y,width=.5,color=ATTACH,dash=[4,2,1,2])
    s=g['body']['snap'];snap(ox+s['x'],oy+s['y'],s['diameter'],s['punch_no'],ox+s['x'],oy+s['y']+6)
    s=g['liner']['snap'];snap(ox+s['x'],oy+s['y'],s['diameter'],s['punch_no'],ox+s['x'],oy+s['y']+6,optional=True)
    legend(attachment=True)
    c.showPage()

    # 3 - flap liner and both mirrored gussets, all at full scale
    header(3,'B・C・D | かぶせ裏・マチ','各1枚裁断 / C・Dは左右対称。')
    text(20,47,'B | かぶせ裏',10)
    oy=55
    part('liner',(ox,oy),'B',label_y=9)
    s=g['liner']['snap'];snap(ox+s['x'],oy+s['y'],s['diameter'],s['punch_no'],ox+s['x'],oy+s['y']+6)
    gx_left=(210-2*GW-10)/2
    gx_right=gx_left+GW+10
    gy=145
    for key,letter,title,gx in [('gusset_left','C','C | マチ・左',gx_left),('gusset_right','D','D | マチ・右',gx_right)]:
        text(gx,137,title,10)
        part(key,(gx,gy),letter,label_y=18)
    legend()
    c.showPage()

    # 4 - true-size A5 material layout
    header(4,'裁断配置 | A5','全パーツを1枚のA5革から裁断。')
    sx,sy=31,44
    poly([(sx,sy),(sx+148,sy),(sx+148,sy+210),(sx,sy+210)],width=.4,color=LIGHT,dash=[6,4])
    text(sx,40,'A5 / 148 × 210 mm',7,MUTED)
    letters=['A','B','C','D']
    for entry,letter in zip(g['layout']['parts'],letters):
        points=entry['outline'];poly([(sx+x,sy+y) for x,y in points])
        xx=(min(x for x,y in points)+max(x for x,y in points))/2
        yy=(min(y for x,y in points)+max(y for x,y in points))/2
        text(sx+xx,sy+yy+1.3,letter,10,MUTED,align='center')
    text(31,262,'パーツ間2 mm、外周3 mm以上の余白。',7,MUTED)
    c.showPage()
    c.save()
    print(OUT)


if __name__ == '__main__':
    main()
