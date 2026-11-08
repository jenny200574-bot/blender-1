"""Previa CPU a partir del blend y del contrato; no cambia fuentes ni servicios."""
import bpy,sys,json,shutil,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from entrada import leer,guardar
import camara
args=sys.argv[sys.argv.index('--')+1:];pk=Path(args[0]);out=Path(args[1]);d=leer(pk/'entrada.json');bpy.ops.wm.open_mainfile(filepath=str(out/'escena.blend'));sc=bpy.context.scene
for name,visible in d['environment'].get('visibility',{}).items():
 obj=bpy.data.objects.get(name)
 if obj is None:raise ValueError('Objeto de visibilidad no existe: '+name)
 obj.hide_render=not visible
for q in d['render']['lights']:
 lo=bpy.data.objects.get(q['id'])
 if lo is None:
  ld=bpy.data.lights.new(q['id'],q['type']);lo=bpy.data.objects.new(q['id'],ld);sc.collection.objects.link(lo)
 lo.location=q['pos'];lo.rotation_euler=[__import__('math').radians(x) for x in q['rot_deg']];lo.data.energy=q['energy'];lo.data.color=q['color']
 if q['type']=='AREA':lo.data.size=q['size']
sc.view_settings.view_transform=d['render']['view_transform'];sc.view_settings.exposure=d['render'].get('exposure',0.)
# Materializar cualquier prop declarado, sin ramificar por identidad.
import formulas_v2 as FV
from mathutils import Matrix
for q in d['props']:
 if bpy.data.objects.get(q['id']) is not None:continue
 root,info=FV.construir(q['id'],leer(pk/q['formula']),q['pos_m'],q['size_m'],q['yaw_deg'])
 if q.get('anchor'):
  anchor=q['anchor'];root.parent=bpy.data.objects[anchor['actor']];root.parent_type='BONE';root.parent_bone=anchor['bone'];root.matrix_parent_inverse=Matrix();root.location=q['local_pos'];root.rotation_euler=[__import__('math').radians(x) for x in q['local_rot_deg']]
if d.get('adn_entities'):
 import adn_geometria
 guardar(out/'adn_campos.json',adn_geometria.aplicar_paquete(leer(pk/d['adn_entities']),sc))
if d['environment'].get('live'):
 import escenario_vivo
 guardar(out/'escenario_vivo_aplicacion.json',escenario_vivo.aplicar(sc,leer(pk/d['environment']['live']),d['fps']))
if '--actualizar-camara' in args:
 old=sc.camera;ob,r=camara.crear(sc,d['camera'],leer(out/'trazas.json'),{a['id']:a for a in d['actors']},d['fps'])
 if old:old.hide_render=True
 guardar(out/'camara_actualizada.json',r)
 # Blender hace respaldo .blend1 al actualizar la copia de trabajo.
 shutil.copy2(out/'escena.blend',out/('escena_antes_camara_'+str(time.time_ns())+'.blend'));bpy.ops.wm.save_as_mainfile(filepath=str(out/'escena.blend'))
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=d['render']['samples'];sc.render.resolution_percentage=100;sc.render.resolution_x=d['render']['width'];sc.render.resolution_y=d['render']['height'];sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
contact=out/'contacto';clip=out/'clip_frames';contact.mkdir(exist_ok=True);clip.mkdir(exist_ok=True)
frames=[1+round(i*(sc.frame_end-1)/5) for i in range(6)]
records=[]
for f in frames:
 sc.frame_set(f);sc.render.filepath=str(contact/f'f{f:05d}.png');bpy.ops.render.render(write_still=True);records.append({'frame':f,'t_s':(f-1)/d['fps'],'path':sc.render.filepath});print('CONTACTO',f,flush=True)
if '--sin-clip' not in args:
 sc.render.resolution_percentage=67
 for i in range(24):
  f=1+round(i*d['fps']/8);sc.frame_set(f);sc.render.filepath=str(clip/f'{i:04d}.png');bpy.ops.render.render(write_still=True);print('CLIP',i,flush=True)
guardar(out/'render_manifest.json',{'motor':'CYCLES CPU','contacto':records,'clip_fps':8,'clip_duracion_s':3,'clip_intervalo_original_s':[0,3],'provisional':d['provisional']})
