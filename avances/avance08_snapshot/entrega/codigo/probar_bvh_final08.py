import os,sys,json,importlib.util
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');sys.path.insert(0,str(R/'MOTOR_BVH08_CANDIDATO/motor'));os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
import bpy
import fisica_final as mod
base=json.loads((R/'esc1_bvh08/argon08_physics_canonica.json').read_text())['physics'];tests=[]
def cube(name,position,size):
 bpy.ops.mesh.primitive_cube_add(size=size,location=position);o=bpy.context.object;o.name=name;return o
A=cube('unitA',(20,20,20),2);B=cube('unitB',(23,20,20),2)
for name,pos,size,contacts,expected in [('disjoint',(23,20,20),2,[],True),('penetration',(21.5,20,20),2,[],False),('contained',(20,20,20),.5,[],False),('touch_exact_no_transversal_overlap',(22,20,20),2,[],True),('touch_transversal_strict',(22,20.2,20.3),2,[],False),('penetration_with_declared_surface_contact',(21.5,20,20),2,[['unitA','unitB']],False),('touch_explicit_surface',(22,20,20),2,[['unitA','unitB']],True),('penetration_above_1mm_with_contact',(21.9984,20,20),2,[['unitA','unitB']],False),('below_1mm_with_contact',(21.9995,20,20),2,[['unitA','unitB']],True)]:
 B.location=pos;B.scale=(size/2,)*3;bpy.context.view_layer.update();rules=dict(base,colliders=['unitA','unitB'],allowed_collision_pairs=[],contact_pairs=contacts);d={'clock':{'fps':24,'duration_s':1/24},'entities':[],'contacts':[],'rules':rules};x=mod.revisar(bpy.context.scene,d,{}, {'unitA':A,'unitB':B});tests.append({'case':name,'expected_pass':expected,'actual_pass':x['all_passed'],'passed':x['all_passed']==expected,'max_penetration_m':x['max_penetration_m'],'errors':x['errors']})
A.location=(20,20,20);A.scale=(5,.1,1);B.location=(20,20,20);B.scale=(.1,5,1);bpy.context.view_layer.update()
d['rules']['contact_pairs']=[['unitA','unitB']];x=mod.revisar(bpy.context.scene,d,{}, {'unitA':A,'unitB':B});tests.append({'case':'interlocked_bars_with_surface_contact','expected_pass':False,'actual_pass':x['all_passed'],'passed':not x['all_passed'],'max_penetration_m':x['max_penetration_m'],'errors':x['errors']})
A.location=(2000,2000,2000);A.scale=(1,1,1);B.location=(2000,2000,2000);B.scale=(.25,.25,.25);bpy.context.view_layer.update()
try:
 x=mod.revisar(bpy.context.scene,d,{}, {'unitA':A,'unitB':B});tests.append({'case':'insufficient_world_precision_fails_closed','passed':False,'unexpected_result':x['all_passed']})
except ValueError as e:
 tests.append({'case':'insufficient_world_precision_fails_closed','passed':str(e).startswith('PRECISION_FLOAT32_INSUFICIENTE'),'message':str(e)})
out={'module_sha256':__import__('hashlib').sha256((R/'MOTOR_BVH08_CANDIDATO/motor/fisica_final.py').read_bytes()).hexdigest(),'passed':all(x['passed'] for x in tests),'tests':tests,'physical_penetration_tolerance_m_unchanged':base['penetration_tolerance_m'],'ray_advance':'max(1e-7,max(1,abs(world_hit))*2**-20); fail closed above tolerance/16','scope':'Actual isolated candidate-engine collision unit; 20m stress, 2000m precision guard; NOT complete scene approval'}
(R/'entrega/evidencias/bvh08_regresion11.json').write_text(json.dumps(out,indent=2));print(json.dumps(out));assert out['passed']
