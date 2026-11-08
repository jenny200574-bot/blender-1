import json,hashlib,shutil
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');p=R/'MOTOR_BVH08_CANDIDATO/motor/fisica_final.py';backup=R/'respaldos/fisica_final_bvh08_antes_cache_aabb.py';assert not backup.exists();shutil.copy2(p,backup);s=p.read_text()
needle="        allow={frozenset(x) for x in rules['allowed_collision_pairs']};touch={frozenset(x) for x in rules.get('contact_pairs',[])}"
assert s.count(needle)==1
s=s.replace(needle,"        # Same exact min/max as aabb_separados, computed once per mesh/frame.\n        bounds={name:tuple((min(v[j] for v in vs),max(v[j] for v in vs)) for j in range(3)) for name,vs in verts.items()}\n"+needle)
needle="                if aabb_separados(verts[a],verts[b]):continue";assert s.count(needle)==1
s=s.replace(needle,"                if any(bounds[a][j][1]<bounds[b][j][0] or bounds[b][j][1]<bounds[a][j][0] for j in range(3)):continue")
compile(s,str(p),'exec');p.write_text(s)
h=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
receipt={'backup':str(backup),'before_sha256':h(backup),'after_sha256':h(p),'scope':'Only cache identical AABB min/max once per mesh per frame instead of recomputing for every pair','physical_tolerances_changed':False,'gold_and_collision_units_must_be_rerun':True}
(R/'entrega/evidencias/optimizacion_aabb08.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt))
