import os,sys,json,importlib.util
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');sys.path.insert(0,str(R/'MOTOR_UNICO_20261107/motor'));os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
import bpy
sp=importlib.util.spec_from_file_location('bvh_candidate08',R/'entrega/codigo/fisica_final_offset_publico_prueba08.py');mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
base=json.loads((R/'esc1_candidata/argon08_physics_canonica.json').read_text())['physics'];tests=[]
def cube(name,position,size):
 bpy.ops.mesh.primitive_cube_add(size=size,location=position);o=bpy.context.object;o.name=name;return o
A=cube('unitA',(20,20,20),2);B=cube('unitB',(23,20,20),2)
for name,pos,size,contacts,expected in [('disjoint',(23,20,20),2,[],True),('penetration',(21.5,20,20),2,[],False),('contained',(20,20,20),.5,[],False),('touch_strict',(22,20,20),2,[],False),('touch_explicit_surface',(22,20,20),2,[['unitA','unitB']],True)]:
 B.location=pos;B.scale=(size/2,)*3;bpy.context.view_layer.update();rules=dict(base,colliders=['unitA','unitB'],allowed_collision_pairs=[],contact_pairs=contacts);d={'clock':{'fps':24,'duration_s':1/24},'entities':[],'contacts':[],'rules':rules};x=mod.revisar(bpy.context.scene,d,{}, {'unitA':A,'unitB':B});tests.append({'case':name,'expected_pass':expected,'actual_pass':x['all_passed'],'passed':x['all_passed']==expected,'max_penetration_m':x['max_penetration_m'],'errors':x['errors']})
out={'passed':all(x['passed'] for x in tests),'tests':tests,'physical_penetration_tolerance_m_unchanged':base['penetration_tolerance_m'],'ray_advance_m':1e-6,'scope':'Native BVH candidate at source-like float coordinate magnitudes; no production approval'};(R/'entrega/evidencias/bvh08_offset_cajas.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
assert out['passed']
