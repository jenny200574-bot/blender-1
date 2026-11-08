"""Revisión geométrica por viñeta: proyección y oclusión. No aprobación artística."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parent))
from entrada import leer,guardar
args=sys.argv[sys.argv.index('--')+1:];pk=Path(args[0]);out=Path(args[1]);d=leer(pk/'entrada.json');bpy.ops.wm.open_mainfile(filepath=str(out/'escena.blend'));sc=bpy.context.scene;frames=out/'auditoria_camara';frames.mkdir(exist_ok=True);reports=[]
for i,shot in enumerate(d['camera']['shots']):
 t=(shot['t0']+shot['t1'])/2;fr=1+round(t*d['fps']);sc.frame_set(fr);bpy.context.view_layer.update();obj=bpy.data.objects[shot['target']]
 if shot.get('target_type')=='object':
  stack=[obj];corners=[]
  while stack:
   q=stack.pop();stack.extend(q.children)
   if q.type=='MESH':corners.extend(q.matrix_world@Vector(c) for c in q.bound_box)
  lo=Vector([min(x[j] for x in corners) for j in range(3)]);hi=Vector([max(x[j] for x in corners) for j in range(3)]);target=(lo+hi)/2
 else:
  actor=next(a for a in d['actors'] if a['id']==shot['target']);target=obj.matrix_world@obj.pose.bones['cabeza'].tail-Vector((0,0,actor['spec']['altura_m']/actor['spec']['cabezas']*.45))
 xy=world_to_camera_view(sc,sc.camera,target);direction=target-sc.camera.matrix_world.translation;hit,loc,normal,index,first,matrix=sc.ray_cast(bpy.context.evaluated_depsgraph_get(),sc.camera.matrix_world.translation,direction.normalized(),distance=direction.length)
 q=first;own=False
 while q:
  if q==obj:own=True;break
  q=q.parent
 file=frames/f'{i+1:02d}.png';sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=4;sc.render.resolution_x=640;sc.render.resolution_y=360;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.filepath=str(file);bpy.ops.render.render(write_still=True)
 visible_vertices=None
 if shot.get('target_type')=='object':
  stack=[obj];points=[]
  while stack:
   mesh=stack.pop();stack.extend(mesh.children)
   if mesh.type=='MESH':points.extend(mesh.matrix_world@v.co for v in list(mesh.data.vertices)[::max(1,len(mesh.data.vertices)//24)])
  visible_vertices=0
  for point in points:
   rr=point-sc.camera.matrix_world.translation;hit2,loc2,n2,id2,first2,m2=sc.ray_cast(bpy.context.evaluated_depsgraph_get(),sc.camera.matrix_world.translation,rr.normalized(),distance=rr.length+.0001);q=first2
   while q:
    if q==obj:visible_vertices+=1;break
    q=q.parent
 reports.append({'vineta':i+1,'target':shot['target'],'t_s':t,'frame':fr,'target_center_in_frame':xy.z>0 and 0<=xy.x<=1 and 0<=xy.y<=1,'visible_proxy_vertices':visible_vertices,'occluded':bool(hit and not own),'first_hit':first.name if hit else None,'image':str(file),'aprobacion_artistica':False});print('CAMARA',i+1,reports[-1]['target_center_in_frame'],reports[-1]['occluded'],flush=True)
guardar(out/'auditoria_camara.json',reports)
