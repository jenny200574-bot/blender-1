import os,sys,json,copy
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');M=R/'MOTOR_UNICO_20261107';sys.path.insert(0,str(M/'motor'));os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
import bpy
import importlib.util
sp=importlib.util.spec_from_file_location("bvh_candidate08",R/"entrega/codigo/fisica_final_offset_publico_prueba08.py");mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);revisar=mod.revisar
P=R/'esc1_candidata';d=json.loads((P/'entrada_escena.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(P/'set.blend'));objects={o.name:o for o in bpy.context.scene.objects};physics=json.loads((P/'argon08_physics_canonica.json').read_text())['physics'];static=[n for n in physics['colliders'] if n in objects and (n=='piso' or n.startswith('muro_') or n=='obj-armario')]
physics['colliders']=static
unit={'clock':{'fps':24,'duration_s':1/24},'entities':[],'contacts':[],'rules':physics};x=revisar(bpy.context.scene,unit,{},objects);x['scope']='EXACT_NATIVE_BVH_STATIC_ENVIRONMENT_UNIT_AT_SOURCE_FRAME1; not complete scene preview';x['source_blend']='set.blend unchanged';x['colliders']=static
(R/'entrega/evidencias/colision_estatica08_offset_publico.json').write_text(json.dumps(x,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in x.items() if k not in ['com_trace','locked_naturalness_trace']},ensure_ascii=False))
