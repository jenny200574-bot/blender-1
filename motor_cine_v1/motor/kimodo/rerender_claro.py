"""Re-render existing foot-locked scenes with visible floor/grid, stamps, material colors.
Does not overwrite the mold. Does not change animation."""
import bpy, math, os, sys
from mathutils import Euler, Vector

OUT=sys.argv[sys.argv.index('--')+1]
BLEND=sys.argv[sys.argv.index('--')+2]
TAG=os.path.splitext(os.path.basename(BLEND))[0].replace('valentina_kimodo_','').replace('_pies','')
STARTFR=int(os.environ.get('STARTFR','0'))
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
if hasattr(sc,'eevee'):
    try: sc.eevee.taa_render_samples=8
    except Exception: pass
sc.render.resolution_x=640; sc.render.resolution_y=720
sc.render.image_settings.file_format='PNG'
sc.render.fps=24
# color management: recover material color, don't blow floor
sc.view_settings.view_transform='Standard'
sc.view_settings.look='None'
sc.view_settings.exposure=0.0
sc.view_settings.gamma=1.0

# hide leftover mold floor if present
for name in ('piso','Piso','ground','Ground','plano','Plane'):
    o=bpy.data.objects.get(name)
    if o:
        o.hide_render=True; o.hide_viewport=True

# world
world=sc.world
if world and world.use_nodes:
    bg=world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs[0].default_value=(0.22,0.24,0.26,1)
        bg.inputs[1].default_value=0.35

# sun
sun=next((o for o in bpy.data.objects if o.type=='LIGHT'), None)
if sun:
    sun.data.energy=1.4
    sun.data.color=(1,1,1)

# floor checker: finer, higher contrast, slightly below 0
fl=bpy.data.objects.get('piso_cuadros')
if fl is None:
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0,0,-0.001))
    fl=bpy.context.object; fl.name='piso_cuadros'
fl.hide_render=False; fl.hide_viewport=False
mat=bpy.data.materials.get('piso_chk') or bpy.data.materials.new('piso_chk')
mat.use_nodes=True
nt=mat.node_tree
nt.nodes.clear()
outn=nt.nodes.new('ShaderNodeOutputMaterial')
bsdf=nt.nodes.new('ShaderNodeBsdfPrincipled')
chk=nt.nodes.new('ShaderNodeTexChecker')
texc=nt.nodes.new('ShaderNodeTexCoord')
# object coords so scale is in meters: 0.15 m tiles
mapn=nt.nodes.new('ShaderNodeMapping')
mapn.inputs['Scale'].default_value=(8,8,8)  # with object coords of 40m plane? 
# Use object coordinates: plane local xy roughly -20..20; scale 8 => 0.125 m period? 
# Generated 0-1 with scale N => N checks. Object on 40-size plane: coords -20..20.
# Safer: generated + high scale
chk.inputs['Scale'].default_value=80
chk.inputs['Color1'].default_value=(0.82,0.82,0.78,1)
chk.inputs['Color2'].default_value=(0.18,0.18,0.20,1)
nt.links.new(texc.outputs['Generated'], chk.inputs['Vector'])
nt.links.new(chk.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value=0.95
nt.links.new(bsdf.outputs['BSDF'], outn.inputs['Surface'])
fl.data.materials.clear(); fl.data.materials.append(mat)

# cameras: tip down to show floor under feet; keep body large
def setup_cam(cam, side=True):
    cam.data.type='ORTHO'
    cam.data.ortho_scale=2.4
    cam.hide_render=False; cam.hide_viewport=False
    if side:
        cam.rotation_euler=Euler((math.radians(68),0,math.radians(90)),'XYZ')
    else:
        cam.rotation_euler=Euler((math.radians(68),0,0),'XYZ')

cam_side=bpy.data.objects.get('cam_side')
cam_front=bpy.data.objects.get('cam_front')
setup_cam(cam_side, True); setup_cam(cam_front, False)
# hide mold camera
cam0=bpy.data.objects.get('CAM')
if cam0: cam0.hide_render=True

# render stamp: clip + frame, always visible
sc.render.use_stamp=True
sc.render.use_stamp_frame=True
sc.render.use_stamp_frame_range=False
sc.render.use_stamp_time=False
sc.render.use_stamp_date=False
sc.render.use_stamp_camera=False
sc.render.use_stamp_scene=False
sc.render.use_stamp_filename=False
for attr in ('use_stamp_render_time','use_stamp_rendertime','use_stamp_memory','use_stamp_hostname','use_stamp_lens'):
    if hasattr(sc.render, attr):
        setattr(sc.render, attr, False)
sc.render.use_stamp_note=True
sc.render.stamp_note_text=TAG.replace('_',' ')
sc.render.stamp_font_size=22
sc.render.stamp_foreground=(1,1,0.15,1)
sc.render.stamp_background=(0,0,0,0.65)

# hide source armature
src=next((o for o in bpy.data.objects if o.type=='ARMATURE' and o.name!= 'ESQ_gdc-valentina'), None)
if src:
    src.hide_render=True; src.hide_viewport=True

# text object: keep as backup, place slightly in front; also hide if stamp is used
txt=bpy.data.objects.get('frame_counter')
if txt:
    txt.hide_render=True  # stamp is clearer

arm=bpy.data.objects['ESQ_gdc-valentina']
side_dir=f'{OUT}/revision/frames_{TAG}_side'
front_dir=f'{OUT}/revision/frames_{TAG}_front'
os.makedirs(side_dir, exist_ok=True); os.makedirs(front_dir, exist_ok=True)

fr0=sc.frame_start if STARTFR<=0 else max(sc.frame_start, STARTFR)
print('RENDER_RANGE', fr0, sc.frame_end, 'tag', TAG)
for fr in range(fr0, sc.frame_end+1):
    sc.frame_set(fr)
    h=arm.matrix_world @ arm.pose.bones['cadera'].head
    cam_side.location=(h.x+2.6, h.y, 1.35)
    cam_front.location=(h.x, h.y-2.7, 1.35)
    sc.camera=cam_side; sc.render.filepath=f'{side_dir}/f{fr:04d}.png'; bpy.ops.render.render(write_still=True)
    sc.camera=cam_front; sc.render.filepath=f'{front_dir}/f{fr:04d}.png'; bpy.ops.render.render(write_still=True)

print('RENDER_OK', TAG)
