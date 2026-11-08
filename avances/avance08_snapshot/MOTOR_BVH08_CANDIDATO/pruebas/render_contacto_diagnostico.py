"""Hoja REAL de estado bloqueado. No entrega animación ni cambia ninguna compuerta.
Usa sólo ADN/base, poses de biblioteca, ubicación de entrada y 4g vigente.
Nunca sustituye una entidad sin colocación por un punto inventado.
"""
import bpy,sys,json,math,runpy,copy,os
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'));sys.path.insert(0,str(R/'motor/heredado'));os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
from seguridad import leer,guardar,ruta,sha,cuadro
from apariencia_3d import construir_parte
from apariencia_base_cpu import ligar
args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]).resolve();out=Path(args[1]).resolve();out.mkdir(parents=True,exist_ok=False);d=leer(folder/'entrada_normalizada.json');pk=folder/'paquete_normalizado';env=d['environment'];assert sha(ruta(pk,env['path']))==env['sha256'];bpy.ops.wm.open_mainfile(filepath=str(ruta(pk,env['path'])));sc=bpy.context.scene;objects={o.name:o for o in sc.objects};omitted=[];rigs={}
import rig
for e in d['entities']:
 if e['type']!='CHARACTER':continue
 if not e.get('legacy'):
  omitted.append({'entity':e['id'],'reason':'Sin rig/ancla/colocación certificados; no se inventa ubicación'});continue
 old=e['legacy'];arm=rig.crear(e['id'],old['spec'],old['colors']);objects[e['id']]=arm;rigs[e['id']]=arm
 for ob in arm.children_recursive:
  if ob.type=='MESH':ob.hide_render=True;ob['motor_preserve_hidden']=True
 for part in e['appearance']['geometry']['parts']:construir_parte(ligar(part,arm,e),arm,objects)
 # Sólo la postura base de biblioteca; no se afirma resolver el 2B truncado.
 for s in old['segments']:
  for time,loc in [(s['t0'],s['p0']),(s['t1'],s['p1'])]:
   arm.location=loc;arm.rotation_euler[2]=math.radians(s['yaw']);arm.keyframe_insert('location',frame=cuadro(time,d['clock']['fps'])+1);arm.keyframe_insert('rotation_euler',frame=cuadro(time,d['clock']['fps'])+1)
 for fc in arm.animation_data.action.fcurves if hasattr(arm.animation_data.action,'fcurves') else []:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
# Iluminación técnica ya DECLARADA por el paquete histórico, no artística final.
render=d['legacy']['render']
for name,visible in env.get('visibility',{}).items():
 if name in objects:objects[name].hide_render=not visible
for light in render['lights']:
 data=bpy.data.lights.new(light['id'],light['type']);ob=bpy.data.objects.new(light['id'],data);sc.collection.objects.link(ob);ob.location=light['pos'];ob.rotation_euler=[math.radians(v) for v in light['rot_deg']];data.energy=light['energy'];data.color=light['color']
 if data.type=='AREA':data.shape='DISK';data.size=light['size']
if sc.world is None:sc.world=bpy.data.worlds.new('diagnostic_world')
sc.world.use_nodes=True;bg=next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=render['world_color']+[1];sc.view_settings.view_transform=render['view_transform'];sc.view_settings.exposure=render['exposure']
sc.render.fps=round(d['clock']['fps']);sc.frame_start=1;sc.frame_end=cuadro(d['clock']['duration_s'],d['clock']['fps']);sc.render.resolution_x,sc.render.resolution_y=(d.get('render') or {'resolution':[render['width'],render['height']]})['resolution'];sc.render.resolution_percentage=100
cd=bpy.data.cameras.new('diagnostic_camera');cd.sensor_width=d['camera']['sensor_width_mm'];cam=bpy.data.objects.new('diagnostic_camera',cd);sc.collection.objects.link(cam);sc.camera=cam
refs=d['camera']['resolver_inputs'];audit=out/'auditoria_4g';audit.mkdir();data=copy.deepcopy(d);data['actors']=[{'id':e['id'],'spec':{'altura_m':e['dna_record']['source_data']['height_m']}} for e in d['entities'] if e['type']=='CHARACTER'];data['environment'].pop('visibility',None);guardar(audit/'entrada.json',data);oldargv=sys.argv
try:
 sys.argv=['4g','--',str(audit/'entrada.json'),str(ruta(pk,d['camera']['source'])),str(ruta(pk,refs['sb_scene'])),str(ruta(pk,refs['config'])),str(ruta(pk,refs['ajustes'])),str(audit),str(ruta(pk,refs['commands'])),str(ruta(pk,refs['elevations'])),str(ruta(pk,refs['shot_types']))];runpy.run_path(str(R/'motor/camara_v2_blender.py'))
finally:sys.argv=oldargv
# Ocultar moldes de objetos que no están resueltos: no presentarlos como acabados.
for ref,binding in d.get('bindings',{}).items():
 if ref in d.get('requirements',{}).get('object_refs',[]):
  ob=objects.get(binding['scene_object_id'])
  if ob:
   for child in [ob]+list(ob.children_recursive):child.hide_render=True
from eventos import aplicar
presence=[ev for ev in env.get('events',[]) if ev['property']=='hide_render' and ev['object'] in rigs];aplicar(sc,presence,d['clock']['fps'],d['clock']['duration_s'])
report=leer(audit/'camara_v2.json');sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=4;sc.render.resolution_x=320;sc.render.resolution_y=180;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';receipts=[]
for shot in d['camera']['shots']:
 frame=cuadro(shot['t0'],d['clock']['fps'])+1;sc.frame_set(frame);bpy.context.view_layer.update();p=out/(shot['id']+'.png');sc.render.filepath=str(p);bpy.ops.render.render(write_still=True);receipts.append({'shot':shot['id'],'frame':frame,'image':p.name,'sha256':sha(p),'camera_status':next(t['estado'] for t in report['tomas'] if t['vineta']==shot['id']),'scope':'DIAGNOSTICO_BLOQUEADO; postura base; cámara no aprobada; NO escena final'})
bpy.ops.wm.save_as_mainfile(filepath=str(out/'diagnostico.blend'));guardar(out/'recibo.json',{'state':'DIAGNOSTICO_BLOQUEADO_NO_ACEPTACION','images':receipts,'omitted':omitted,'rendered_subjects':list(rigs),'subject_count':len(rigs),'shot_count':len(receipts),'source_result_sha256':sha(folder/'resultado.json'),'technical_light_source':'entrada_normalizada.json#/legacy/render','no_final_video':True,'spend_usd':0,'camera_review':str(audit/'camara_v2.json'),'warnings':['No se ejecutó el 2B truncado ni se completó la escena','Sin ave por falta de ancla/rig; objetos sin receta ocultos; moldes no son finales','La hoja documenta el bloqueo; no convierte datos B en aprobados']})
