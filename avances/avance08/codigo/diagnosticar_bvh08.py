import os,sys,json,itertools
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');M=R/'MOTOR_UNICO_20261107';sys.path.insert(0,str(M/'motor'));os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
import bpy,bmesh
from fisica_final import revisar
P=R/'esc1_candidata';bpy.ops.wm.open_mainfile(filepath=str(P/'set.blend'));objects={o.name:o for o in bpy.context.scene.objects};rules=json.loads((P/'argon08_physics_canonica.json').read_text())['physics'];names=[n for n in rules['colliders'] if n in objects and (n=='piso' or n.startswith('muro_') or n=='obj-armario')];top=[];checks=[]
for name in names:
 bm=bmesh.new();bm.from_mesh(objects[name].data);top.append({'mesh':name,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)});bm.free()
for a,b in itertools.combinations(names,2):
 rs=dict(rules,colliders=[a,b]);unit={'clock':{'fps':24,'duration_s':1/24},'entities':[],'contacts':[],'rules':rs}
 try:
  x=revisar(bpy.context.scene,unit,{},objects);checks.append({'pair':[a,b],'all_passed':x['all_passed'],'errors':x['errors']})
 except Exception as exc:checks.append({'pair':[a,b],'exception':type(exc).__name__+': '+str(exc)})
out={'scope':'PAIRWISE_EXACT_NATIVE_STATIC_BVH_DIAGNOSTIC_NOT_FULL_SCENE','topology':top,'checks':checks,'exceptions':sum('exception' in x for x in checks)}
(R/'entrega/evidencias/bvh08_antes_parche.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'topology':top,'exceptions':out['exceptions'],'failing_pairs':[x for x in checks if 'exception' in x or not x.get('all_passed',False)]},ensure_ascii=False))
