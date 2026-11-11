"""Strong foot-lock (primary-foot root plant) + clear review MP4 for Kimodo→Valentina.
NEW scene only; never overwrites gdc-valentina.blend.
"""
import bpy, addon_utils, json, math, os, sys, time
from mathutils import Vector, Matrix, Euler
import numpy as np

LAB='/workspace/estudio_animacion/lab'
OUT=sys.argv[sys.argv.index('--')+1]
BVH=sys.argv[sys.argv.index('--')+2]
TAG=os.path.splitext(os.path.basename(BVH))[0]
MOLDE=f'{LAB}/moldes/gdc-valentina.blend'
SCENE_OUT=f'{OUT}/revision/valentina_kimodo_{TAG}_pies.blend'
os.makedirs(f'{OUT}/revision', exist_ok=True); os.makedirs(f'{LAB}/img', exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=MOLDE)
R={"bvh":BVH,"tag":TAG,"blender":bpy.app.version_string,"molde":"gdc-valentina.blend (copy)"}
addon_utils.enable('animation_retargeting', default_set=True)
sc=bpy.context.scene; sc.render.fps=24
T=next(o for o in bpy.data.objects if o.type=='ARMATURE')

def activate(o):
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active=o

bpy.context.view_layer.update()
bpy.ops.import_anim.bvh(filepath=BVH, use_fps_scale=True, update_scene_duration=True)
S=bpy.context.object
fr0,fr1=S.animation_data.action.frame_range
sc.frame_start=int(fr0); sc.frame_end=min(int(fr1), int(fr0)+240)
S.data.pose_position='REST'; bpy.context.view_layer.update()
hz=[(S.matrix_world@b.tail_local).z for b in S.data.bones]
lz=[(S.matrix_world@b.head_local).z for b in S.data.bones]
span=max(hz)-min(lz); k=1.12/span if span>1e-6 else 1.0
S.scale=(k,k,k); S.data.pose_position='POSE'; bpy.context.view_layer.update()
names=set(b.name for b in S.data.bones)

MAP={
  'Hips':'cadera','Spine1':'columna','Chest':'pecho','Neck1':'cuello','Head':'cabeza',
  'LeftShoulder':'hombro_L','LeftArm':'brazo_L','LeftForeArm':'antebrazo_L','LeftHand':'mano_L',
  'RightShoulder':'hombro_R','RightArm':'brazo_R','RightForeArm':'antebrazo_R','RightHand':'mano_R',
  'LeftLeg':'femur_L','LeftShin':'tibia_L','LeftFoot':'pie_L',
  'RightLeg':'femur_R','RightShin':'tibia_R','RightFoot':'pie_R',
}
MAP={a:b for a,b in MAP.items() if a in names}
INV={v:k for k,v in MAP.items()}
ALIGN=[v for v in MAP.values() if v.split('_')[0] in ('femur','tibia','brazo','antebrazo')]

def src_dir(n):
    b=S.data.bones[n]; mw=S.matrix_world
    return ((mw@b.tail_local)-(mw@b.head_local)).normalized()

def auto_align(arm):
    S.data.pose_position='REST'; bpy.context.view_layer.update()
    for b in arm.data.bones:
        if b.name not in ALIGN or INV.get(b.name) not in names: continue
        pb=arm.pose.bones[b.name]; bpy.context.view_layer.update()
        M=arm.matrix_world@pb.matrix
        q=M.col[1].xyz.normalized().rotation_difference(src_dir(INV[b.name]))
        h=pb.matrix.translation.copy()
        pb.matrix=Matrix.Translation(h)@(q.to_matrix()@pb.matrix.to_3x3()).to_4x4()
    bpy.context.view_layer.update(); S.data.pose_position='POSE'

def get_tips(arm):
    tips={p:[] for p in ('pie_L','pie_R')}
    for fr in range(sc.frame_start, sc.frame_end+1):
        sc.frame_set(fr); mw=arm.matrix_world
        for p in tips:
            h=(mw@arm.pose.bones[p].head).copy(); t=(mw@arm.pose.bones[p].tail).copy()
            tips[p].append(h if h.z<=t.z else t)
    return tips

def medir(arm, pies=('pie_L','pie_R'), cad='cadera', lock_w=None, primary=None):
    feet={p:[] for p in pies}; hips=[]; bad=0; mx=0
    tips=get_tips(arm)
    fs=list(range(sc.frame_start, sc.frame_end+1)); n=len(fs)
    for fr in fs:
        sc.frame_set(fr); mw=arm.matrix_world
        for p in pies:
            pb=arm.pose.bones[p]; feet[p].append(((mw@pb.head).copy(),(mw@pb.tail).copy()))
        hips.append((mw@arm.pose.bones[cad].head).copy())
        for pb in arm.pose.bones:
            v=mw@pb.head; bad+=any(math.isnan(c) for c in v); mx=max(mx,v.length)
    o={"frames":n,"nan":bad,"explota":bad>0 or mx>50}
    o["pie_z_min_m"]=round(min(t.z for p in tips for t in tips[p]),4)
    o["penetracion_cuadros"]=sum(1 for p in tips for t in tips[p] if t.z<-0.02)
    acc=[((hips[i+1]-2*hips[i]+hips[i-1])*576).length for i in range(1,n-1)]
    o["acel_cadera_max_m_s2"]=round(max(acc),2) if acc else None
    o["recorrido_cadera_m"]=round((hips[-1]-hips[0]).length,2)
    jumps=0
    for p in tips:
        z=[t.z for t in tips[p]]
        for i in range(1,n-1):
            if z[i]-z[i-1]>0.08 and z[i]-z[i+1]>0.08: jumps+=1
    o["saltitos"]=jumps
    sl=[]; sl_pri=[]
    for p in tips:
        z=[t.z for t in tips[p]]; zmin=sorted(z)[n//10]
        for i in range(1,n):
            d=tips[p][i]-tips[p][i-1]; v=math.hypot(d.x,d.y)*24
            if z[i]-zmin<0.015 and z[i-1]-zmin<0.015: sl.append(v)
            if primary is not None and primary[i]==p and primary[i-1]==p and lock_w and lock_w[p][i]>=0.999:
                sl_pri.append(v)
            elif lock_w and lock_w[p][i]>=0.999 and lock_w[p][i-1]>=0.999 and primary is None:
                sl_pri.append(v)
    sl.sort(); sl_pri.sort()
    def pack(a):
        if not a: return None
        return {"median":round(a[len(a)//2],4),"p90":round(a[int(len(a)*.9)],4),"max":round(a[-1],4),"n":len(a)}
    o["pie_apoyado_vel_mediana_m_s"]=round(sl[len(sl)//2],4) if sl else None
    o["pie_apoyado_vel_p90_m_s"]=round(sl[int(len(sl)*.9)],4) if sl else None
    o["pie_apoyado_vel_max_m_s"]=round(sl[-1],4) if sl else None
    o["muestras_apoyo"]=len(sl)
    o["pie_primario_lock"]=pack(sl_pri)
    return o, tips, hips

from animation_retargeting import alignment, baking, drivers
t0=time.time(); activate(T); ctx=T.retargeting_context; ctx.selected_source=S
for a,b in MAP.items():
    m=ctx.mappings.add(); m.source=a; m.target=b
alignment.enter_alignment_mode(ctx); auto_align(T); alignment.store_alignments(ctx); alignment.leave_alignment_mode(ctx)
activate(T); baking.transfer_anim(ctx); ctx.setting_disable_drivers=True; drivers.update_drivers(ctx)
R["mwni"]={"ok":True,"s":round(time.time()-t0,2)}

zz=[]
for fr in range(sc.frame_start, sc.frame_end+1):
    sc.frame_set(fr)
    zz.append(min(min((T.matrix_world@T.pose.bones[p].head).z,(T.matrix_world@T.pose.bones[p].tail).z) for p in ('pie_L','pie_R')))
zz.sort(); off=zz[len(zz)//20]; T.location.z-=off; R["offset_piso_m"]=round(off,4)

# measure BEFORE lock (no primary yet)
R["medidas_antes"], tips0, hips0 = medir(T)

fs=list(range(sc.frame_start, sc.frame_end+1)); n=len(fs)

# Kimodo contacts
npz=os.path.splitext(BVH)[0]+'.npz'
kim=None
if os.path.isfile(npz):
    d=np.load(npz); fc=d['foot_contacts']; n_ch=fc.shape[1]
    L=np.any(fc[:,:n_ch//2],1); Rg=np.any(fc[:,n_ch//2:],1)
    idx=(np.linspace(0,len(L)-1,n)).astype(int)
    kim={'pie_L':L[idx].astype(bool),'pie_R':Rg[idx].astype(bool)}
    R["kimodo_contacts"]=True
else:
    R["kimodo_contacts"]=False

def strong_foot_lock(arm, tips0, kim=None, thr_z=0.025, thr_v=0.15, min_seg=3, borde=6):
    t0=time.time(); info={}
    st={}
    for p in tips0:
        tip=tips0[p]
        z=[t.z for t in tip]; zmin=sorted(z)[max(0,n//12)]
        v=[0.0]+[math.hypot(tip[i].x-tip[i-1].x, tip[i].y-tip[i-1].y)*24 for i in range(1,n)]
        base=[(z[i]-zmin<thr_z) and (v[i]<thr_v) for i in range(n)]
        hyst=[False]*n; planted=False
        for i in range(n):
            if not planted:
                if base[i]: planted=True
            else:
                if (z[i]-zmin>thr_z*1.9) or (v[i]>thr_v*2.5): planted=False
            hyst[i]=planted
        if kim is not None and p in kim:
            near=[z[i]-zmin<thr_z*2.0 for i in range(n)]
            st[p]=[bool(hyst[i] or (kim[p][i] and near[i])) for i in range(n)]
        else:
            st[p]=hyst
        info[p]={"zmin":round(float(zmin),4)}

    locks={p:[None]*n for p in tips0}; w={p:[0.0]*n for p in tips0}
    for p in tips0:
        segs=[]; i=0
        while i<n:
            if st[p][i]:
                j=i
                while j+1<n and st[p][j+1]: j+=1
                if j-i+1>=min_seg: segs.append((i,j))
                i=j+1
            else: i+=1
        for (a,b) in segs:
            xs=sorted(tips0[p][k].x for k in range(a,b+1))
            ys=sorted(tips0[p][k].y for k in range(a,b+1))
            Lxy=Vector((xs[len(xs)//2], ys[len(ys)//2], 0.0))
            for f in range(max(0,a-borde), min(n,b+borde+1)):
                if f<a: wf=(1-(a-f)/(borde+1))**2
                elif f>b: wf=(1-(f-b)/(borde+1))**2
                else: wf=1.0
                if wf>=w[p][f]:
                    w[p][f]=wf; locks[p][f]=Lxy
        info[p]["apoyos"]=len(segs)
        info[p]["cuadros_bloqueados"]=int(sum(1 for x in w[p] if x>=0.999))
        info[p]["contact_frames"]=int(sum(st[p]))
        info[p]["segs"]=segs

    # contact age for primary
    age={p:[0]*n for p in tips0}
    for p in tips0:
        for i in range(n):
            age[p][i]=(age[p][i-1]+1) if i>0 and w[p][i]>=0.999 and w[p][i-1]>=0.999 else (1 if w[p][i]>=0.999 else 0)
    primary=[None]*n
    for i in range(n):
        full=[p for p in tips0 if w[p][i]>=0.999]
        if len(full)==1: primary[i]=full[0]
        elif len(full)>=2: primary[i]=max(full, key=lambda p: age[p][i])
        else:
            soft=[p for p in tips0 if w[p][i]>0.05]
            if soft: primary[i]=max(soft, key=lambda p: w[p][i])

    # One-shot primary-foot root plant with short crossfade at switches (HALF=4).
    base=arm.location.copy()
    HALF=4
    def foot_delta(p,i):
        if p is None or locks[p][i] is None: return Vector((0,0,0))
        dxy=locks[p][i]-tips0[p][i]
        return Vector((dxy.x, dxy.y, 0.0))*w[p][i]
    raw=[foot_delta(primary[i],i) for i in range(n)]
    changes=[i for i in range(1,n) if primary[i]!=primary[i-1] and primary[i] and primary[i-1]]
    delta=[r.copy() for r in raw]
    for c in changes:
        a=max(0,c-HALF); b=min(n-1,c+HALF)
        for i in range(a,b+1):
            tt=(i-a)/(b-a) if b>a else 1.0
            tt=tt*tt*(3-2*tt)
            p0=primary[c-1]; p1=primary[c]
            delta[i]=foot_delta(p0,i).lerp(foot_delta(p1,i), tt)
    for i,fr in enumerate(fs):
        arm.location=base+delta[i]
        arm.keyframe_insert('location', frame=fr)
    info["crossfade_half"]=HALF
    info["primary_changes"]=changes

    # Markers: green sphere when primary-locked, red when free (mesh+material for Workbench MATERIAL)
    mat_g=bpy.data.materials.new('mark_green'); mat_g.use_nodes=True
    mat_g.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.1,0.95,0.25,1)
    mat_g.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(0.1,0.95,0.25,1)
    try: mat_g.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=2.0
    except Exception: pass
    mat_r=bpy.data.materials.new('mark_red'); mat_r.use_nodes=True
    mat_r.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.95,0.2,0.15,1)
    markers={}
    for p in ('pie_L','pie_R'):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(0,0,0.04))
        g=bpy.context.object; g.name=f'MARK_G_{p}'; g.data.materials.append(mat_g)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(0,0,0.04))
        r=bpy.context.object; r.name=f'MARK_R_{p}'; r.data.materials.append(mat_r)
        markers[p]=(g,r)
    for i,fr in enumerate(fs):
        sc.frame_set(fr); mw=arm.matrix_world
        for p in ('pie_L','pie_R'):
            h=mw@arm.pose.bones[p].head; tt=mw@arm.pose.bones[p].tail
            tip=h if h.z<=tt.z else tt
            g,r=markers[p]
            loc=Vector((tip.x, tip.y, 0.04))
            g.location=loc; r.location=loc
            locked=bool(primary[i]==p and w[p][i]>=0.999)
            g.scale=(1,1,1) if locked else (0.001,0.001,0.001)
            r.scale=(0.001,0.001,0.001) if locked else (1,1,1)
            g.keyframe_insert('location', frame=fr); g.keyframe_insert('scale', frame=fr)
            r.keyframe_insert('location', frame=fr); r.keyframe_insert('scale', frame=fr)

    info["s"]=round(time.time()-t0,2)
    info["method"]="primary_foot_root_plant+crossfade4+kimodo_contacts"
    info["primary_lock_frames"]=int(sum(1 for i in range(n) if primary[i] and w[primary[i]][i]>=0.999))
    return info, markers, w, primary

R["foot_lock"], markers, lock_w, primary = strong_foot_lock(T, tips0, kim)
R["medidas_despues"], tips2, hips2 = medir(T, lock_w=lock_w, primary=primary)
# also attach primary metrics to antes for fair compare
_, _, _ = None, None, None
R["medidas_antes"]["pie_primario_lock_note"]="computed after lock definition; see despues.pie_primario_lock"
# recompute before primary slide using tips0 + same primary/w
sl_pri=[]
for p in tips0:
    for i in range(1,n):
        if primary[i]==p and primary[i-1]==p and lock_w[p][i]>=0.999:
            d=tips0[p][i]-tips0[p][i-1]; sl_pri.append(math.hypot(d.x,d.y)*24)
sl_pri.sort()
if sl_pri:
    R["medidas_antes"]["pie_primario_lock"]={"median":round(sl_pri[len(sl_pri)//2],4),"p90":round(sl_pri[int(len(sl_pri)*.9)],4),"max":round(sl_pri[-1],4),"n":len(sl_pri)}

S.hide_render=True; S.hide_viewport=True
for c in [o for o in bpy.data.objects if o.type=='CAMERA']:
    c.hide_render=True; c.hide_viewport=True

bpy.ops.mesh.primitive_plane_add(size=40, location=(0,0,-0.001))
fl=bpy.context.object; fl.name='piso_cuadros'
mat=bpy.data.materials.new('piso_chk'); mat.use_nodes=True
nt=mat.node_tree; nt.nodes.clear()
outn=nt.nodes.new('ShaderNodeOutputMaterial')
bsdf=nt.nodes.new('ShaderNodeBsdfPrincipled')
chk=nt.nodes.new('ShaderNodeTexChecker'); chk.inputs['Scale'].default_value=16
chk.inputs['Color1'].default_value=(0.75,0.75,0.7,1)
chk.inputs['Color2'].default_value=(0.12,0.12,0.14,1)
nt.links.new(chk.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(bsdf.outputs['BSDF'], outn.inputs['Surface'])
fl.data.materials.append(mat)

bpy.ops.object.text_add(location=(0,0,1.85))
txt=bpy.context.object; txt.name='frame_counter'
txt.data.body='f000'; txt.data.size=0.11; txt.data.align_x='CENTER'
tm=bpy.data.materials.new('txtmat'); tm.use_nodes=True
tm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(1,1,0.15,1)
txt.data.materials.append(tm)

def make_cam(name, loc):
    cam=bpy.data.objects.new(name, bpy.data.cameras.new(name))
    sc.collection.objects.link(cam); cam.data.type='ORTHO'; cam.data.ortho_scale=2.35
    cam.location=loc; return cam

cx=sum(h.x for h in hips2)/len(hips2); cy=sum(h.y for h in hips2)/len(hips2)
cam_side=make_cam('cam_side', Vector((cx+2.8, cy, 1.15)))
cam_side.rotation_euler=Euler((math.radians(78),0,math.radians(90)),'XYZ')
cam_front=make_cam('cam_front', Vector((cx, cy-2.9, 1.15)))
cam_front.rotation_euler=Euler((math.radians(78),0,0),'XYZ')
world=sc.world or bpy.data.worlds.new('World'); sc.world=world
world.use_nodes=True
bg=world.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value=(0.45,0.48,0.52,1); bg.inputs[1].default_value=0.6
bpy.ops.object.light_add(type='SUN', location=(3,-2,5)); bpy.context.object.data.energy=2.5

sc.render.engine='BLENDER_EEVEE'
if hasattr(sc,'eevee'):
    try: sc.eevee.taa_render_samples=8
    except Exception: pass
# also show object colors for markers
sc.display.shading.color_type='MATERIAL'

sc.render.resolution_x=640; sc.render.resolution_y=720
sc.render.image_settings.file_format='PNG'
sc.render.fps=24

side_dir=f'{OUT}/revision/frames_{TAG}_side'
front_dir=f'{OUT}/revision/frames_{TAG}_front'
os.makedirs(side_dir, exist_ok=True); os.makedirs(front_dir, exist_ok=True)

if os.environ.get('SKIP_RENDER')=='1':
    bpy.ops.wm.save_as_mainfile(filepath=SCENE_OUT)
    R['scene_out']=SCENE_OUT
    json.dump(R, open(f'{OUT}/revision/out_{TAG}.json','w'), indent=2)
    print('DONE_METRICS', TAG)
    print('ANTES', json.dumps(R['medidas_antes']))
    print('DESPUES', json.dumps(R['medidas_despues']))
    print('LOCK', json.dumps({k:R['foot_lock'][k] for k in R['foot_lock']}))
    raise SystemExit(0)

for fr in range(sc.frame_start, sc.frame_end+1):
    sc.frame_set(fr)
    txt.data.body=f'{TAG}  f{fr:03d}'
    h=T.matrix_world @ T.pose.bones['cadera'].head
    txt.location=(h.x, h.y, 1.85)
    # text yellow object color
    cam_side.location=(h.x+2.8, h.y, 1.15)
    cam_front.location=(h.x, h.y-2.9, 1.15)
    sc.camera=cam_side; sc.render.filepath=f'{side_dir}/f{fr:04d}.png'; bpy.ops.render.render(write_still=True)
    sc.camera=cam_front; sc.render.filepath=f'{front_dir}/f{fr:04d}.png'; bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=SCENE_OUT)
R["scene_out"]=SCENE_OUT
R["side_dir"]=side_dir; R["front_dir"]=front_dir
R["frame_range"]=[sc.frame_start, sc.frame_end]
json.dump(R, open(f'{OUT}/revision/out_{TAG}.json','w'), indent=2)
print('DONE', TAG)
print('ANTES', json.dumps(R['medidas_antes']))
print('DESPUES', json.dumps(R['medidas_despues']))
print('LOCK', json.dumps({k:R['foot_lock'][k] for k in R['foot_lock']}))
