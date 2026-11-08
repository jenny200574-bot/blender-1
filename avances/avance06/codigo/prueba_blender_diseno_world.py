from pathlib import Path
import sys,json,math
import bpy
from mathutils import Vector
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';sys.path.insert(0,str(B/'MOTOR_UNICO_20261107/motor'))
from anatomia_aviar import construir
from apariencia_3d import construir_parte
from apariencia_base_cpu import ligar
from luces_blender import configurar
from seguridad import guardar
read=lambda p:json.loads(p.read_text())
for ob in bpy.context.scene.objects:ob.hide_render=True;ob.hide_viewport=True
anatomy=read(E/'evidencias/bird_rig_canonico.json');appearance=read(E/'evidencias/bird_apariencia_canonica.json');rig=construir('ch-piquito-030a',anatomy['rig']);objects={rig.name:rig};entity={'id':rig.name,'anatomy':'avian','rig':anatomy['rig']}
for part in appearance['parts']:construir_parte(ligar(part,rig,entity),rig,objects)
bpy.context.view_layer.update();meshes=[o for n,o in objects.items() if o.type=='MESH'];corners=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box];zmin=min(p.z for p in corners);zmax=max(p.z for p in corners)
profile=read(E/'evidencias/iluminacion_canonica.json');configurar(bpy.context.scene,profile,objects)
w=profile['world'];world=bpy.data.worlds.new(w['id']);world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=w['color_rgba'];bg.inputs['Strength'].default_value=w['strength'];bpy.context.scene.world=world;bpy.context.scene.view_settings.exposure=profile['exposure'];bpy.context.scene.view_settings.gamma=profile['gamma'];bpy.context.scene.view_settings.view_transform=profile['view_transform']
lightchecks=[]
for l in profile['base']:
 ob=objects[l['id']];lightchecks.append({'id':l['id'],'energy_equal':math.isclose(ob.data.energy,l['energy'],abs_tol=1e-5),'size_equal':math.isclose(ob.data.size,l['size'],abs_tol=1e-6),'shape_equal':ob.data.shape==l['shape']})
passed=len(rig.data.bones)==19 and len(meshes)==40 and zmin>=-.001 and zmax<=.101 and all(all(v for k,v in r.items() if k!='id') for r in lightchecks)
result={'passed':passed,'scope':'CPU construction only, not esc1 nor physics/visual approval','bones':len(rig.data.bones),'meshes':len(meshes),'zmin_m':zmin,'zmax_m':zmax,'official_height_m':.1,'tolerance_m':.001,'lights':lightchecks,'gpu_used':False}
guardar(E/'evidencias/blender_diseno_world_resultado.json',result)
if not passed:raise ValueError('Construction failed quantitative checks')
bpy.ops.wm.save_as_mainfile(filepath=str(B/'piquito_diseno_cpu_world.blend'));print(json.dumps(result))
