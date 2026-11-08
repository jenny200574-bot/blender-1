from pathlib import Path
import bpy,sys,json,math,os
from mathutils import Vector
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';sys.path.insert(0,str(B/'MOTOR_UNICO_20261107/motor'))
from seguridad import guardar
from apariencia_3d import construir_parte
from recetas_proveedor import validar
read=lambda p:json.loads(p.read_text());canon=read(E/'evidencias/adn_canonico_refinado07.json');assert len(canon['records'])==4
for ob in bpy.context.scene.objects:ob.hide_render=True;ob.hide_viewport=True
objects={};roots=[];checks=[]
for record in canon['records']:
 g=record['source_data']['construction_3d'];root=bpy.data.objects.new(record['id'],None);bpy.context.scene.collection.objects.link(root);root.location=g['placement']['position_m'];root.rotation_euler=[math.radians(x) for x in g['placement']['rotation_deg']];objects[root.name]=root;roots.append(root)
 for part in g['parts']:construir_parte(part,root,objects)
 bpy.context.view_layer.update();meshes=list(root.children);coords=[v.co for ob in meshes for v in ob.data.vertices];bbox=[max(v[k] for v in coords)-min(v[k] for v in coords) for k in range(3)]
 # Part local transforms matter; use world vertices then inverse root to compare canonical source dimensions.
 inv=root.matrix_world.inverted();coords=[inv@(ob.matrix_world@v.co) for ob in meshes for v in ob.data.vertices];actual=[max(v[k] for v in coords)-min(v[k] for v in coords) for k in range(3)];passed=all(abs(a-b)<=.001 for a,b in zip(actual,record['source_data']['dimensions_m']))
 nonmanifold=[]
 import bmesh
 for ob in meshes:
  bm=bmesh.new();bm.from_mesh(ob.data)
  if any(not edge.is_manifold for edge in bm.edges):nonmanifold.append(ob.name)
  bm.free()
 checks.append({'id':record['id'],'passed':passed and not nonmanifold,'parts':len(meshes),'dimensions_m':actual,'expected_dimensions_m':record['source_data']['dimensions_m'],'nonmanifold_parts':nonmanifold})
result={'passed':all(c['passed'] for c in checks),'scope':'REAL Blender CPU construction of4newsource-specific assets ONLY; not esc1 motion/physics/visual production approval','checks':checks,'gpu_used':False,'production_approved':False};guardar(E/'evidencias/assets_blender_refinado07.json',result)
if not result['passed']:raise ValueError('Asset build or manifold check failed')
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=16;sc.render.resolution_x=512;sc.render.resolution_y=512;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
world=bpy.data.worlds.new('av07.inspection.world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.25,.25,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7;sc.world=world
ld=bpy.data.lights.new('av07.inspection.area','AREA');lo=bpy.data.objects.new(ld.name,ld);sc.collection.objects.link(lo);ld.energy=500;ld.size=3
cd=bpy.data.cameras.new('av07.inspection.camera');cam=bpy.data.objects.new(cd.name,cd);sc.collection.objects.link(cam);cd.type='ORTHO';sc.camera=cam
thumbdir=E/'modelos_refinados';thumbdir.mkdir(exist_ok=True)
for i,root in enumerate(roots):
 for other in roots:
  for child in other.children_recursive:child.hide_render=other!=root
 bpy.context.view_layer.update();corners=[ob.matrix_world@Vector(c) for ob in root.children for c in ob.bound_box];center=sum(corners,Vector())/len(corners);size=max(max(v[k] for v in corners)-min(v[k] for v in corners) for k in range(3));cam.location=center+Vector((2,-4,3)).normalized()*max(1,size*3);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=size*1.45;lo.location=center+Vector((1,-2,3))*max(.3,size);lo.rotation_euler=(center-lo.location).to_track_quat('-Z','Y').to_euler();sc.render.filepath=str(thumbdir/('asset_'+str(i)+'.png'));bpy.ops.render.render(write_still=True)
for root in roots:
 for ob in root.children_recursive:ob.hide_render=False
path=thumbdir/'assets_diseno07_refinado.blend';assert not path.exists();bpy.ops.wm.save_as_mainfile(filepath=str(path));print(json.dumps(result))
