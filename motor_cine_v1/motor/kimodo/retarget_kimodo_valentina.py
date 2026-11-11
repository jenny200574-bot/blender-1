"""CPU free: Kimodo SOMA BVH -> Valentina fábrica mold (NEW scene), foot-lock, measure, strip PNG.
Never overwrites gdc-valentina.blend."""
import bpy, addon_utils, json, math, os, sys, time
from mathutils import Vector, Matrix
LAB='/workspace/estudio_animacion/lab'
OUT=sys.argv[sys.argv.index('--')+1]
BVH=sys.argv[sys.argv.index('--')+2]
TAG=os.path.splitext(os.path.basename(BVH))[0]
MOLDE=f'{LAB}/moldes/gdc-valentina.blend'
SCENE_OUT=f'{OUT}/scenes/valentina_kimodo_{TAG}.blend'
os.makedirs(f'{OUT}/scenes', exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=MOLDE)
R={"bvh":BVH,"tag":TAG,"blender":bpy.app.version_string,"molde":"gdc-valentina.blend (copy)","fuente":"Kimodo-SOMA-RP-v1.2 --no-postprocess"}
addon_utils.enable('animation_retargeting', default_set=True)
sc=bpy.context.scene; sc.render.fps=24
T=next(o for o in bpy.data.objects if o.type=='ARMATURE')
def activate(o):
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active=o
bpy.context.view_layer.update()
zs=[(T.matrix_world@b.tail_local).z for b in T.data.bones]; R["molde_altura_huesos_m"]=round(max(zs),3)
bpy.ops.import_anim.bvh(filepath=BVH, use_fps_scale=True, update_scene_duration=True)
S=bpy.context.object
fr0,fr1=S.animation_data.action.frame_range; sc.frame_start=int(fr0); sc.frame_end=min(int(fr1), int(fr0)+240)
S.data.pose_position='REST'; bpy.context.view_layer.update()
hz=[(S.matrix_world@b.tail_local).z for b in S.data.bones]; lz=[(S.matrix_world@b.head_local).z for b in S.data.bones]
span=max(hz)-min(lz); k=1.12/span if span>1e-6 else 1.0; S.scale=(k,k,k); S.data.pose_position='POSE'; bpy.context.view_layer.update()
names=set(b.name for b in S.data.bones)
R["source_bones"]=sorted(names)
# Kimodo SOMA standard tpose BVH names -> Valentina español
# Kimodo SOMA: LeftLeg/RightLeg = thigh (femur); LeftShin/RightShin = tibia
MAP={
  'Hips':'cadera',
  'Spine1':'columna',
  'Chest':'pecho',
  'Neck1':'cuello',
  'Head':'cabeza',
  'LeftShoulder':'hombro_L','LeftArm':'brazo_L','LeftForeArm':'antebrazo_L','LeftHand':'mano_L',
  'RightShoulder':'hombro_R','RightArm':'brazo_R','RightForeArm':'antebrazo_R','RightHand':'mano_R',
  'LeftLeg':'femur_L','LeftShin':'tibia_L','LeftFoot':'pie_L',
  'RightLeg':'femur_R','RightShin':'tibia_R','RightFoot':'pie_R',
  'LeftUpLeg':'femur_L','RightUpLeg':'femur_R',
  'LeftToeBase':'pie_L','RightToeBase':'pie_R',
}
R["map_used"]={k:v for k,v in MAP.items() if k in names}
if len(R["map_used"])<8:
    R["error"]="insufficient bone map"; json.dump(R, open(f'{OUT}/out_{TAG}.json','w'), indent=2); print(json.dumps(R,indent=2)); raise SystemExit(3)
INV={v:k for k,v in R["map_used"].items()}
ALIGN=[v for v in R["map_used"].values() if v.split('_')[0] in ('femur','tibia','brazo','antebrazo')]
def src_dir(n):
    b=S.data.bones[n]; mw=S.matrix_world; return ((mw@b.tail_local)-(mw@b.head_local)).normalized()
def auto_align(arm):
    S.data.pose_position='REST'; bpy.context.view_layer.update()
    for b in arm.data.bones:
        if b.name not in ALIGN or INV.get(b.name) not in names: continue
        pb=arm.pose.bones[b.name]; bpy.context.view_layer.update()
        M=arm.matrix_world@pb.matrix; q=M.col[1].xyz.normalized().rotation_difference(src_dir(INV[b.name]))
        h=pb.matrix.translation.copy(); pb.matrix=Matrix.Translation(h)@(q.to_matrix()@pb.matrix.to_3x3()).to_4x4()
    bpy.context.view_layer.update(); S.data.pose_position='POSE'
def medir(arm, pies=('pie_L','pie_R'), cad='cadera'):
    feet={p:[] for p in pies}; hips=[]; bad=0; mx=0
    for fr in range(sc.frame_start, sc.frame_end+1):
        sc.frame_set(fr); mw=arm.matrix_world
        for p in pies:
            pb=arm.pose.bones[p]; feet[p].append(((mw@pb.head),(mw@pb.tail)))
        hips.append(mw@arm.pose.bones[cad].head)
        for pb in arm.pose.bones:
            v=mw@pb.head; bad+=any(math.isnan(c) for c in v); mx=max(mx,v.length)
    n=len(hips); o={"frames":n,"nan":bad,"explota":bad>0 or mx>50}
    o["pie_z_min_m"]=round(min(min(a.z,t.z) for p in pies for a,t in feet[p]),3)
    # penetration: frames with foot clearly below floor after aterrizar (~z< -0.02)
    pen=sum(1 for p in pies for a,t in feet[p] if min(a.z,t.z) < -0.02)
    o["penetracion_cuadros"]=pen
    acc=[((hips[i+1]-2*hips[i]+hips[i-1])*576).length for i in range(1,n-1)]
    o["acel_cadera_max_m_s2"]=round(max(acc),2) if acc else None
    o["recorrido_cadera_m"]=round((hips[-1]-hips[0]).length,2)
    jumps=0
    for p in pies:
        z=[min(a.z,t.z) for a,t in feet[p]]
        for i in range(1,n-1):
            if z[i]-z[i-1]>0.08 and z[i]-z[i+1]>0.08: jumps+=1
    o["saltitos"]=jumps
    sl=[]
    for p in pies:
        z=[min(a.z,t.z) for a,t in feet[p]]; zmin=sorted(z)[len(z)//10]
        for i in range(1,n):
            if z[i]-zmin<0.02 and z[i-1]-zmin<0.02:
                d=feet[p][i][0]-feet[p][i-1][0]; sl.append(math.hypot(d.x,d.y)*24)
    sl.sort(); o["pie_apoyado_vel_mediana_m_s"]=round(sl[len(sl)//2],3) if sl else None
    o["pie_apoyado_vel_p90_m_s"]=round(sl[int(len(sl)*.9)],3) if sl else None
    return o,feet,hips
from animation_retargeting import alignment, baking, drivers
t0=time.time(); activate(T); ctx=T.retargeting_context; ctx.selected_source=S
for a,b in R["map_used"].items():
    m=ctx.mappings.add(); m.source=a; m.target=b
alignment.enter_alignment_mode(ctx); auto_align(T); alignment.store_alignments(ctx); alignment.leave_alignment_mode(ctx)
activate(T); baking.transfer_anim(ctx); ctx.setting_disable_drivers=True; drivers.update_drivers(ctx)
R["mwni"]={"ok":T.animation_data is not None and T.animation_data.action is not None,"s":round(time.time()-t0,2)}
zz=[]
for fr in range(sc.frame_start, sc.frame_end+1):
    sc.frame_set(fr); zz.append(min(min((T.matrix_world@T.pose.bones[p].head).z,(T.matrix_world@T.pose.bones[p].tail).z) for p in ('pie_L','pie_R')))
zz.sort(); off=zz[len(zz)//20]; T.location.z-=off; R["offset_piso_m"]=round(off,3)
R["medidas_retarget"],feet,hips=medir(T)
def foot_lock(arm, feet, thr_z=0.025, thr_v=0.35):
    fs=list(range(sc.frame_start, sc.frame_end+1)); n=len(fs); info={}
    for p,tib in (('pie_L','tibia_L'),('pie_R','tibia_R')):
        P=[a.copy() for a,_ in feet[p]]; z=[min(a.z,t.z) for a,t in feet[p]]; zmin=sorted(z)[len(z)//10]
        v=[0]+[math.hypot(*(P[i]-P[i-1]).xy)*24 for i in range(1,n)]
        st=[z[i]-zmin<thr_z and v[i]<thr_v for i in range(n)]
        tgt=[p_.copy() for p_ in P]; segs=[]; i=0
        while i<n:
            if st[i]:
                j=i
                while j+1<n and st[j+1]: j+=1
                if j-i>=2: segs.append((i,j))
                i=j+1
            else: i+=1
        for a,b in segs:
            anc=P[a].copy()
            for k in range(a,b+1): tgt[k]=anc.copy()
        emp=bpy.data.objects.new(f'FL_{p}', None); bpy.context.collection.objects.link(emp); emp.empty_display_size=0.05
        for i,fr in enumerate(fs):
            emp.location=tgt[i]; emp.keyframe_insert('location', frame=fr)
        pb=arm.pose.bones[p]; c=pb.constraints.new('IK'); c.target=emp; c.chain_count=2
        info[p]={"apoyos":len(segs),"cuadros_bloqueados":sum(b-a+1 for a,b in segs)}
    activate(arm)
    bpy.ops.nla.bake(frame_start=sc.frame_start, frame_end=sc.frame_end, only_selected=False, visual_keying=True, clear_constraints=True, bake_types={'POSE'})
    return info
R["foot_lock"]=foot_lock(T, feet)
R["medidas_foot_lock"],_,_=medir(T)
bpy.ops.wm.save_as_mainfile(filepath=SCENE_OUT); R["scene_out"]=SCENE_OUT
cam=next((o for o in bpy.data.objects if o.type=='CAMERA'), None)
if cam is None:
    bpy.ops.object.camera_add(location=(2.2,-3.2,1.4)); cam=bpy.context.object
    cam.rotation_euler=(math.radians(70),0,math.radians(35)); sc.camera=cam
else: sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='FLAT'; sc.display.shading.color_type='MATERIAL'
sc.render.resolution_x=640; sc.render.resolution_y=360; sc.render.image_settings.file_format='PNG'
n=sc.frame_end-sc.frame_start+1
idxs=[sc.frame_start+int(i*(n-1)/5) for i in range(6)]
paths=[]
for i,fr in enumerate(idxs):
    sc.frame_set(fr); path=f'{OUT}/frames_{TAG}_{i:02d}.png'; sc.render.filepath=path; bpy.ops.render.render(write_still=True); paths.append(path)
R["render_frames"]=paths
json.dump(R, open(f'{OUT}/out_{TAG}.json','w'), indent=2)
print('OK', TAG, json.dumps({k:R[k] for k in ('mwni','medidas_retarget','medidas_foot_lock','map_used') if k in R}, indent=2)[:1200])
