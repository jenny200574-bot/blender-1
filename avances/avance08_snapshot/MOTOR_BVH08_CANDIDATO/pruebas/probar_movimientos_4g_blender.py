import bpy,sys,runpy,copy,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import leer,guardar
from puente_sb4g import MOVES
args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]);out=Path(args[1]);out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(folder/'escena.blend'));d=leer(folder/'entrada_normalizada.json');root=folder/'paquete_normalizado';refs=d['camera']['resolver_inputs'];audit=folder/'auditoria_4g';sb=leer(root/d['camera']['source']);commands=leer(root/refs['commands']);sbe=leer(root/refs['sb_scene']);old=sys.argv
try:
 sys.argv=['4g','--',str(audit/'entrada.json'),str(root/d['camera']['source']),str(root/refs['sb_scene']),str(audit/'config.json'),str(root/refs['ajustes']),str(out),str(root/refs['commands']),str(root/refs['elevations']),str(root/refs['shot_types'])];ns=runpy.run_path(str(R/'motor/camara_v2_blender.py'))
finally:sys.argv=old
checks={};details={};v0=sb['vinetas'][0]
for mode in sorted(MOVES):
 v=copy.deepcopy(v0);v['segmentos']=[{'t_abs':v['t_abs'],'movimiento':mode,'args':{'degrees':3,'distance':.02,'percent':1,'dir_lr':'R','dir_ud':'UP','dir_rot':'CCW','dir_orbit':'R','dir_io':'OUT'},'curva':'suave_entrada_salida'}];S=ns['leer_toma'](v,sbe['vinetas'][0],commands[v['vineta']],'prueba');state=[];tray,err,extra=ns['construir'](v,S,(0,1),'prueba',state);ok=tray is not None and not err and len(tray)==8 and all(x['estado']=='ejecutado' for x in state if x['comando']==mode);checks[mode]=ok;details[mode]={'frames':len(tray or []),'error':err,'states':state}
 if mode=='WHIPPAN':checks['WHIPPAN_yaw_no_roll']=abs(extra['tramos'][0]['fin']['yaw'])>0 and extra['tramos'][0]['fin']['roll']==extra['tramos'][0]['ini']['roll']
for label,mode,args_ in [('PAN_giro_grados','PAN',{'giro_grados':3}),('CRANE_height_m','CRANE',{'height_m':-.02}),('CRANE_metros','CRANE',{'metros':.02,'dir_ud':'UP'}),('PAN_anclas','PAN',{'anchors':[[0,0,.7],[.1,0,.7]]}),('CRANE_extremos','CRANE',{'extremos':[1.2,1.22]}),('WHIPPAN_empty','WHIPPAN',{'label':'support_fixture.anchor_origin'})]:
 v=copy.deepcopy(v0);v['segmentos']=[{'t_abs':v['t_abs'],'movimiento':mode,'args':args_,'curva':'suave_entrada_salida'}];S=ns['leer_toma'](v,sbe['vinetas'][0],commands[v['vineta']],'alias');state=[];tray,err,extra=ns['construir'](v,S,(0,1),'alias',state);checks[label]=tray is not None and not err and all(x['estado']=='ejecutado' for x in state if x['comando']==mode)
checks['sin_alias_subcadena']=ns['buscar_id']('bird',list(ns['ACT'])) is None
checks['todos_los_cuadros']=ns['muestras'](1,16)==list(range(1,17))
checks['HALF_UP']=ns['fr'](.0625)==2
checks['cache_otros_declarada']='OTROS' in ns
# Verificación independiente del constructor no facial, leyendo el .blend, no el recibo.
rig=bpy.data.objects['bird_fixture'];target=bpy.data.objects['support_fixture.anchor_origin'];bpy.context.scene.frame_set(16);bpy.context.view_layer.update();checks['ancla_parent_real']=rig.parent==target;checks['ancla_movil_evaluada']=(rig.matrix_world.translation-target.matrix_world.translation).length<1e-6 and target.matrix_world.translation.x>.3;checks['rig_19_huesos']=len(rig.data.bones)==19;checks['bisagra_parent_real']=bpy.data.objects['prop_lid'].parent.name=='lid_hinge';checks['control_bisagra_aplicado']=abs(bpy.data.objects['lid_hinge'].rotation_axis_angle[0])>.9
from objetos_finales import obtener_raiz
bpy.ops.mesh.primitive_cube_add();mold=bpy.context.object;mold.name='referencia_nueva_42';mapping={mold.name:mold};point=obtener_raiz({'id':mold.name,'position_m':[2,3,4],'geometry':[],'reference_kind':'POINT'},mapping,bpy.context.scene);checks['POINT_no_molde_visible']=point.type=='EMPTY' and mold.hide_render and list(point.location)==[2,3,4]
save={'checks':checks,'details':details,'all_passed':all(checks.values()),'move_count':len(MOVES),'cpu':True,'spend_usd':0};guardar(out/'regresiones.json',save);assert all(checks.values()),[k for k,v in checks.items() if not v]
