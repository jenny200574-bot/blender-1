import os,sys,json,copy
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');M=R/'MOTOR_BVH08_CANDIDATO';sys.path.insert(0,str(M/'motor'));os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
import bpy
from fisica_final import revisar
P=R/'esc1_bvh08';d=json.loads((P/'entrada_escena.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(P/'set.blend'));objects={o.name:o for o in bpy.context.scene.objects};physics=json.loads((P/'argon08_physics_canonica.json').read_text())['physics'];static=[n for n in physics['colliders'] if n in objects and (n=='piso' or n.startswith('muro_') or n=='obj-armario')]
physics['colliders']=static
unit={'clock':{'fps':24,'duration_s':1/24},'entities':[],'contacts':[],'rules':physics};x=revisar(bpy.context.scene,unit,{},objects);x['module_sha256']=__import__('hashlib').sha256((R/'MOTOR_BVH08_CANDIDATO/motor/fisica_final.py').read_bytes()).hexdigest();x['scope']='EXACT_NATIVE_BVH_STATIC_ENVIRONMENT_UNIT_AT_SOURCE_FRAME1; not complete scene preview';x['source_blend']='set.blend unchanged';x['colliders']=static
(R/'entrega/evidencias/colision_estatica08_final.json').write_text(json.dumps(x,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in x.items() if k not in ['com_trace','locked_naturalness_trace']},ensure_ascii=False))

assert x["all_passed"]
