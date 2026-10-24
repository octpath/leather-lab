"""Render actual tool meshes, a slot plan and the rear marking passage."""
from pathlib import Path
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
import trimesh

SOURCE=Path(__file__).resolve().parent
PROJECT=SOURCE.parent
FONT=FontProperties(fname=str(SOURCE/'assets/NotoSansJP-Regular.ttf'))
matplotlib.font_manager.fontManager.addfont(FONT.get_file())
plt.rcParams.update({'font.family':FONT.get_name(),'axes.unicode_minus':False})
BG=np.array([250,248,244])/255
CAD=(PROJECT/'3d/lip-balm-tools.scad').read_text()
def value(name):
    return float(re.search(r'^'+name+r'\s*=\s*([\d.]+)\s*;',CAD,re.M).group(1))

def load(name):
    return trimesh.load_mesh(PROJECT/'3d'/name,process=False)

def raster(tri,color='#b87f54',w=1200,h=1000,eye=(1.,-1.5,1.2)):
    eye=np.array(eye,dtype=float);eye/=np.linalg.norm(eye)
    right=np.cross([0,0,1],eye);right/=np.linalg.norm(right);up=np.cross(eye,right)
    p=tri-(tri.min((0,1))+tri.max((0,1)))/2
    q=np.stack([p@right,p@up,p@eye],axis=2)
    lo=q[:,:,:2].min((0,1));hi=q[:,:,:2].max((0,1));mid=(lo+hi)/2
    sc=min((w-60)/(hi[0]-lo[0]),(h-60)/(hi[1]-lo[1]))
    q[:,:,0]=(q[:,:,0]-mid[0])*sc+w/2;q[:,:,1]=-(q[:,:,1]-mid[1])*sc+h/2
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm=np.linalg.norm(n,axis=1);good=norm>1e-10
    n[good]/=norm[good,None]
    light=np.array([-.3,-.7,1.]);light/=np.linalg.norm(light)
    shade=.6+.4*np.clip(n@light,0,1);rgb=np.array(matplotlib.colors.to_rgb(color))
    canvas=np.broadcast_to(BG,(h,w,3)).copy();depth=np.full((h,w),-np.inf)
    for t,sh in zip(q[good&(n@eye>1e-9)],shade[good&(n@eye>1e-9)]):
        x0,x1=max(0,int(np.floor(t[:,0].min()))),min(w-1,int(np.ceil(t[:,0].max())))
        y0,y1=max(0,int(np.floor(t[:,1].min()))),min(h-1,int(np.ceil(t[:,1].max())))
        den=(t[1,0]-t[0,0])*(t[2,1]-t[0,1])-(t[1,1]-t[0,1])*(t[2,0]-t[0,0])
        if x1<x0 or y1<y0 or abs(den)<1e-10:continue
        xx=np.arange(x0,x1+1)[None,:]+.5;yy=np.arange(y0,y1+1)[:,None]+.5
        a=((xx-t[0,0])*(t[2,1]-t[0,1])-(yy-t[0,1])*(t[2,0]-t[0,0]))/den
        b=((t[1,0]-t[0,0])*(yy-t[0,1])-(t[1,1]-t[0,1])*(xx-t[0,0]))/den
        z=(1-a-b)*t[0,2]+a*t[1,2]+b*t[2,2]
        old=depth[y0:y1+1,x0:x1+1];mask=(a>=-1e-8)&(b>=-1e-8)&(a+b<=1+1e-8)&(z>old)
        old[mask]=z[mask];canvas[y0:y1+1,x0:x1+1][mask]=rgb*sh
    return np.uint8(np.clip(canvas*255,0,255))

def planar(ax,mesh,z=.9,color='#ba835b'):
    sec=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1]);loops=sec.discrete
    verts=[];codes=[]
    for p in loops:
        q=p[:-1,:2];signed=np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1))/2
        depth=sum(MPath(o[:,:2]).contains_point(q[0]) for o in loops if abs(np.sum(o[:-1,0]*o[1:,1]-o[:-1,1]*o[1:,0])/2)>abs(signed)+1e-6)
        if (signed>0)!=(depth%2==0):q=q[::-1]
        verts.extend(q.tolist()+[q[0].tolist()]);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(q)-1)+[MPath.CLOSEPOLY])
    ax.add_patch(PathPatch(MPath(np.array(verts),codes),facecolor=color,edgecolor='#715b48',linewidth=.45))
    ax.set_xlim(mesh.bounds[0,0]-2,mesh.bounds[1,0]+2);ax.set_ylim(mesh.bounds[1,1]+2,mesh.bounds[0,1]-2)
    ax.set_aspect('equal');ax.axis('off')

parts=['m1-lower-former.stl','m2-forming-frame.stl','m3-trimming-frame.stl','a-rough-blank.stl','b-back-flap.stl','c-d-ring-tab.stl']
meshes=[load(n) for n in parts]
titles=['M1 下型・背面位置写し通路','M2 成形用上枠','M3 外枠付きケガキガイド','A 粗裁ち用','B 背面兼フラップ','C Dカン留め']
fig,axs=plt.subplots(2,3,figsize=(14,11),facecolor=BG)
for i,(ax,m,title) in enumerate(zip(axs.flat,meshes,titles)):
    if i<3:
        ax.imshow(raster(m.triangles,eye=(1,1.5,1.2) if i==2 else (1,-1.5,1.2)));ax.axis('off')
    else:planar(ax,m,color='#89989c')
    ax.set_title(title,fontproperties=FONT,size=13,pad=10,color='#283039')
fig.suptitle('oct / リップクリームケース 3Dツール',fontproperties=FONT,size=20,y=.97,color='#283039')
fig.text(.05,.035,'ホックは成形後に取り付け。M1の背面から中心を写す。M3は幅1.5mmのスリットの内側をなぞる。',fontproperties=FONT,size=11,color='#687078')
fig.subplots_adjust(left=.035,right=.975,top=.9,bottom=.09,hspace=.2,wspace=.18)
fig.savefig(PROJECT/'images/3d-tools.png',dpi=140,facecolor=BG);plt.close(fig)

m=meshes[2]
fig,axs=plt.subplots(1,2,figsize=(13,8),facecolor=BG,gridspec_kw={'width_ratios':[1.4,1]})
axs[0].imshow(raster(m.triangles,eye=(1,1.5,1.2)));axs[0].axis('off')
axs[0].set_title('アーチは口元より上側へ・外枠で支持',fontproperties=FONT,size=13,pad=10)
planar(axs[1],m)
axs[1].set_title('革に当たる面の平面図',fontproperties=FONT,size=13,pad=10)
# Plot the real cutting contour in blue; bridge gaps stay visible as dashes.
import json
G=json.loads((SOURCE/'geometry.json').read_text());r=G['front_formed']['cut_bottom_radius'];cx=r+value('trim_slot_w')+value('trim_outer_band');my=value('mouth_extension')
for s in [-1,1]:
    axs[1].plot([cx+s*r]*2,[my,my+51],color='#336e91',lw=1.1,ls=(0,(4,3)))
theta=np.linspace(0,np.pi,300)
axs[1].plot(cx+r*np.cos(theta),my+51+r*np.sin(theta),color='#336e91',lw=1.1)
fig.suptitle('oct / M3 外枠・裁断スリット',fontproperties=FONT,size=21,y=.96,color='#283039')
fig.text(.05,.11,'左右：3mm幅の接続部を各3か所。底の半円：接続部のない連続スリット。',fontproperties=FONT,size=11,color='#687078')
fig.text(.05,.07,'スリット幅1.5mm。青線に一致する内側の縁が裁断線。外枠の外周は裁断線ではありません。',fontproperties=FONT,size=11,color='#336e91')
fig.text(.05,.03,'35穴・穴径1.1mm・縫い代3mmを保持。穴の上には直径5mmの工具通路を確保（CAD確認）。',fontproperties=FONT,size=10.5,color='#687078')
fig.subplots_adjust(left=.02,right=.975,top=.87,bottom=.18,wspace=.12)
fig.savefig(PROJECT/'images/m3-cutting-frame.png',dpi=150,facecolor=BG);plt.close(fig)

m=meshes[0]
fig,axs=plt.subplots(1,2,figsize=(12,7),facecolor=BG)
axs[0].imshow(raster(m.triangles,eye=(1,-1.5,1.2)));axs[0].axis('off')
axs[0].set_title('成形面の出口 Ø2.1mm（7号相当）',fontproperties=FONT,size=13,pad=10)
# Actual STL section through the centre of the rear passage (world y=32).
sec=m.section(plane_origin=[0,32,0],plane_normal=[0,1,0])
for loop in sec.discrete:axs[1].fill(loop[:,0],loop[:,2],color='#b87f54',alpha=.85)
# Plot edges as a view of the true passage; white highlights show the exact bore profile.
axs[1].fill([42,48,48,46.05,46.05,43.95,43.95,42],[-1,-1,22.05,24,27,27,24,22.05],color=BG)
axs[1].annotate('背面から印を写す',xy=(45,15),xytext=(45,-6),ha='center',fontproperties=FONT,size=11,color='#336e91',arrowprops={'arrowstyle':'->','color':'#336e91','lw':1.5})
axs[1].text(53,13,'通路 Ø6mm',fontproperties=FONT,size=11,color='#283039')
axs[1].text(53,24.5,'先端約2mm：Ø2.1mm',fontproperties=FONT,size=10,color='#283039')
axs[1].set_xlim(23,78);axs[1].set_ylim(-8,31);axs[1].set_aspect('equal');axs[1].axis('off')
axs[1].set_title('ホック中心を通る実メッシュ断面',fontproperties=FONT,size=13,pad=10)
fig.suptitle('oct / M1 背面からのホック位置写し',fontproperties=FONT,size=21,y=.95,color='#283039')
fig.text(.05,.075,'成形・乾燥後に中心を軽く写し、型を外して7号で穴あけ。ホックはその後に取り付けます。',fontproperties=FONT,size=11,color='#687078')
fig.text(.05,.03,'位置：口元から12mm・左右中央。従来のØ14mmの金具逃げは取り除き、成形面を復元。',fontproperties=FONT,size=10.5,color='#687078')
fig.subplots_adjust(left=.02,right=.98,top=.85,bottom=.15,wspace=.08)
fig.savefig(PROJECT/'images/m1-snap-marking.png',dpi=150,facecolor=BG);plt.close(fig)
print('3D overview, M1 passage and M3 slot previews rendered')
