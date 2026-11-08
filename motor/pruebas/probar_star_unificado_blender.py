import sys,json,math,os
os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
from pathlib import Path
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'motor'))
import bpy
from mathutils import Vector,Matrix,Euler
from apariencia_3d import construir_parte
from objetos_star import verificar,FaltaDatos
from geometria import rig_declarativo,ik_punto
from eventos import aplicar
from seguridad import guardar
args=sys.argv[sys.argv.index('--')+1:];inp=json.loads(Path(args[0]).read_text());out=Path(args[1]);out.mkdir(parents=True,exist_ok=True);sc=bpy.context.scene;objects={};checks=[]
def check(name,condition,**data):
 checks.append({'name':name,'passed':bool(condition),**data});guardar(out/'regresiones.json',{'checks':checks,'all_passed':all(c['passed'] for c in checks)})
 if not condition:raise AssertionError(name)
for ob in sc.objects:ob.hide_render=True
parent=bpy.data.objects.new(inp['root_id'],None);sc.collection.objects.link(parent);objects[parent.name]=parent
spec=inp['object'];M=Matrix.Translation(spec['position_m'])@Euler([math.radians(x) for x in spec['rotation_deg']]).to_matrix().to_4x4();p=spec['points'][0];p['position_m']=list(M@Vector(inp['point_local_rest']))
root=construir_parte(spec,parent,objects);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();vertices=[]
for ob in root.children_recursive:
 if ob.type=='MESH':
  ev=ob.evaluated_get(dg);mesh=ev.to_mesh();vertices.extend(root.matrix_world.inverted()@ev.matrix_world@v.co for v in mesh.vertices);ev.to_mesh_clear()
lo=[min(p[i] for p in vertices) for i in range(3)];hi=[max(p[i] for p in vertices) for i in range(3)];dims=[b-a for a,b in zip(lo,hi)]
check('rot_deg_tres_ejes_aplicados',max(abs(root.rotation_euler[i]-math.radians(spec['rotation_deg'][i])) for i in range(3))<1e-6)
check('ancla_base_elevada_no_sobrescrita',abs(lo[2])<1e-5 and max(abs(x-y) for x,y in zip(dims,spec['dimensions_m']))<1e-5,dimensions=dims,min_z=lo[2])
pt=objects[root.name+'.'+p['id']];check('world_a_local_exacto', (pt.matrix_world.translation-Vector(p['position_m'])).length<1e-5,error_m=(pt.matrix_world.translation-Vector(p['position_m'])).length)
check('hoja_parentada_a_pivote_sin_alias',objects[inp['moving_piece']].parent.name==inp['pivot_id'])
check('punto_parentado_a_pieza_movil',pt.parent.name==inp['moving_piece'])
rig=rig_declarativo(inp['rig_id'],inp['rig']);rig.matrix_world=M;ik_punto(rig,inp['effector'],pt,2,1024)
apply=json.loads(root['motor_events']);aplicar(sc,apply,inp['fps'],inp['duration_s']);max_contact=0;first=None;last=None
for f in range(1,1+round(inp['fps']*inp['duration_s'])):
 sc.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=rig.evaluated_get(dg);target=pt.evaluated_get(dg).matrix_world.translation;endpoint=ev.matrix_world@ev.pose.bones[inp['effector']].tail;max_contact=max(max_contact,(endpoint-target).length)
 if first is None:first=target.copy()
 last=target.copy()
check('control_c_ik_contacto_por_cuadro',max_contact<inp['contact_tolerance_m'],max_error_m=max_contact)
check('punto_viaja_con_mueble',(last-first).length>inp['minimum_point_travel_m'],travel_m=(last-first).length)
# Vidrio, material individual y bisel en el mismo backend.
glass=construir_parte(inp['glass'],parent,objects);bsdf=glass.data.materials[0].node_tree.nodes.get('Principled BSDF');check('transmission_y_alpha_reales',abs(bsdf.inputs['Transmission Weight'].default_value-inp['glass']['material']['transmission'])<1e-6 and abs(bsdf.inputs['Alpha'].default_value-inp['glass']['material']['alpha'])<1e-6);check('bisel_individual',any(m.type=='BEVEL' and m.segments==inp['glass']['bevel']['segments'] for m in glass.modifiers))
# Dos huecos en pared con rotación arbitraria; paneles por datos.
arch=construir_parte(inp['architecture'],parent,objects);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();wall=objects[inp['wall_id']]
for i,point in enumerate(inp['hole_centers_local']):
 start=wall.matrix_world@Vector([point[0],-1,point[1]]);direction=(wall.matrix_world.to_3x3()@Vector([0,1,0])).normalized();hit=sc.ray_cast(dg,start,direction,distance=2)[0];check('hueco_multiple_'+str(i),not hit)
# Fórmula desconocida/None/bbox: faltas explícitas, nunca AttributeError/fallback.
for value in [None,'tipo_inexistente','bbox']:
 bad=dict(spec,id='negative_'+str(value),formula=value,points=[])
 try:construir_parte(bad,parent,objects)
 except FaltaDatos as exc:check('falta_clara_'+str(value),bool(exc.faltantes) and not isinstance(exc,AttributeError))
 else:check('falta_clara_'+str(value),False)
# Puerta de receta REAL, no un tablero al que se haya llamado hoja.
import copy
door=copy.deepcopy(spec);door.update(id='hoja_universo_nuevo',formula='puerta_bisagra',dimensions_m=[.9,.08,2.1],position_m=[20,2,1],rotation_deg=[15,25,35],points=[],pivots=[],controls=[])
root_door=construir_parte(door,parent,objects);bpy.context.view_layer.update();pivot=objects[root_door.name+'.bisagra'];leaf=objects[root_door.name+'.body'];panel=objects[root_door.name+'.panel'];knob=objects[root_door.name+'.pomo']
check('puerta_real_hoja_panel_pomo_parentados',all(o.parent==pivot for o in [leaf,panel,knob]))
from geometria import registrar_puntos
world_point=root_door.matrix_world@Vector([.2,0,1]);point_spec={'id':'pin_puerta','frame':'WORLD','pieza_movil':leaf.name,'position_m':list(world_point),'rotation_deg':[0,0,0],'source':'fixture puerta real'};point=registrar_puntos(root_door,[point_spec],objects)['pin_puerta'];bpy.context.view_layer.update();start=point.matrix_world.translation.copy()
event={'object':pivot.name,'property':'rotation_euler','keys':[{'t':0,'value':[0,0,0],'curve':'LINEAR'},{'t':1,'value':[0,0,math.pi/2],'curve':'LINEAR'}],'source':'control c 0→1 de puerta real'};aplicar(sc,[event],inp['fps'],inp['duration_s']);sc.frame_set(inp['fps']);bpy.context.view_layer.update();finish=point.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation
check('puerta_real_control_c_mueve_punto_world',(finish-start).length>.1,travel_m=(finish-start).length)
# Visibilidad en jerarquía: conservar molde/cápsula archivados ocultos.
old=bpy.data.objects.new('molde_archivado_de_prueba',None);sc.collection.objects.link(old);old.parent=root_door;old.hide_render=True;old['motor_preserve_hidden']=True
presence={'object':root_door.name,'property':'hide_render','recursive':True,'keys':[{'t':0,'value':True,'curve':'CONSTANT'},{'t':.5,'value':False,'curve':'CONSTANT'}],'source':'01 fixture'};aplicar(sc,[presence],inp['fps'],inp['duration_s']);sc.frame_set(1);check('presencia_oculta_geometria_descendiente',leaf.hide_render and knob.hide_render);sc.frame_set(1+round(.5*inp['fps']));check('presencia_muestra_solo_final_no_molde',not leaf.hide_render and old.hide_render)
# Un emisor parentado conserva WORLD, ceros y su color; ninguna coordenada fija.
from luces_blender import configurar
ld=bpy.data.lights.new('emisor_parentado_datos','POINT');lo=bpy.data.objects.new(ld.name,ld);sc.collection.objects.link(lo);lo.parent=root_door;objects[lo.name]=lo;lo['source_recipe_sha256']='fixture de emisor de receta'
try:configurar(sc,{'base':[]},objects)
except FaltaDatos:check('emisor_sin_perfil_es_falta_no_default',True)
else:check('emisor_sin_perfil_es_falta_no_default',False)
profile={'base':[{'id':lo.name,'type':'POINT','position_m':[31,7,9],'rotation_deg':[10,20,30],'energy':0,'color':[.1,.8,.4],'frame':'WORLD','source':'fixture por datos'}]};configurar(sc,profile,objects);bpy.context.view_layer.update();check('emisor_parentado_marco_world_sin_coordenada_fija',(lo.matrix_world.translation-Vector([31,7,9])).length<1e-5);check('emisor_energia_cero_color_independiente',lo.data.energy==0 and abs(lo.data.color[1]-.8)<1e-6)
# Un molde bbox escalado no multiplica las dimensiones del objeto nuevo.
from objetos_finales import obtener_raiz
bpy.ops.mesh.primitive_cube_add(size=1,location=(42,8,3));mold=bpy.context.object;mold.name='objeto_escalado_de_otro_mundo';mold.scale=(3,4,5);objects[mold.name]=mold;spec_root={'id':mold.name,'position_m':[42,8,3],'rotation_deg':[10,20,30],'geometry':[{'placeholder':'presencia de diseño explícito'}]};final_root=obtener_raiz(spec_root,objects,sc);bpy.context.view_layer.update();check('molde_escalado_archivado_no_doble_escala',max(abs(x-1) for x in final_root.matrix_world.to_scale())<1e-5 and mold.hide_render and bool(mold.get('motor_preserve_hidden')) and final_root.name==spec_root['id'])
sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(out/'prueba_integrada.blend'));guardar(out/'regresiones.json',{'checks':checks,'all_passed':all(c['passed'] for c in checks),'spend_usd':0,'cpu':True})
