import sys,json,shutil,copy,hashlib
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';P0=R/'esc1_candidata';P=R/'esc1_bvh08';M0=R/'MOTOR_UNICO_20261107';M=R/'MOTOR_BVH08_CANDIDATO'
assert not P.exists() and not M.exists()
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert read(E/'evidencias/bvh08_offset_cajas.json')['passed']
repair=read(E/'evidencias/av08_contactos05/respuesta.json');assert read(E/'evidencias/av08_contactos05/schema_validacion.json')['passed']
src=read(E/'config/contact05_sources.json');items=src['items']
expected={frozenset(z['objects']) for z in read(E/'evidencias/colision_estatica08_offset_publico.json')['errors']}
assert len(expected)==4
pairs=[]
for z in repair['additional_surface_contacts']:
 a,b=z['a_index'],z['b_index'];assert isinstance(a,int) and isinstance(b,int) and a!=b and 0<=a<len(items) and 0<=b<len(items)
 pairs.append([items[a]['id'],items[b]['id']])
assert len(pairs)==4 and {frozenset(x) for x in pairs}==expected
shutil.copytree(P0,P);shutil.copytree(M0,M)
shutil.copy2(M/'motor/fisica_final.py',R/'respaldos/fisica_final_original_motor_bvh08.py')
shutil.copy2(E/'codigo/fisica_final_offset_publico_prueba08.py',M/'motor/fisica_final.py')
sys.path[:0]=[str(M/'motor'),str(E/'codigo')]
from seguridad import guardar
from validar_fisica08 import validar
from puentes_fisicos import reglas
x=read(P/'argon08_physics_canonica.json');old=copy.deepcopy(x['physics'])
for pair in pairs:
 assert frozenset(pair) not in {frozenset(v) for v in x['physics']['contact_pairs']}
 x['physics']['contact_pairs'].append(pair)
x['composition08']['surface_repair']={'response':'av08_contactos05/respuesta.json','sha256':sha(E/'evidencias/av08_contactos05/respuesta.json'),'scope':'Exactly four native-observed depth0 constructive surface pairs; depth is NOT exempted'}
s03=read(E/'config/physics03_sources.json');mesh=s03['compiled_mesh_ids'];known={o['id'] for o in s03['measured_inventory']['objects'] if o['type']=='MESH'}|{o['id'] for group in mesh.values() for ps in group.values() for o in ps}
assert not validar(x,known,mesh['character_meshes'],set(mesh['prop_meshes']))
canonical,errors=reglas(x['physics']);assert canonical is not None and not errors
assert {k:v for k,v in old.items() if k!='contact_pairs'}=={k:v for k,v in canonical.items() if k!='contact_pairs'}
guardar(P/'argon08_physics_canonica.json',x);d=read(P/'entrada_escena.json');d['rules_source']=canonical
for z in d['assets']:z.update(sha256=sha(P/z['path']),bytes=(P/z['path']).stat().st_size)
for z in d['sources']:z['sha256']=sha(P/z['path'])
guardar(P/'entrada_escena.json',d)
codechanges=[]
for p in sorted((M0/'motor').rglob('*.py')):
 q=M/p.relative_to(M0)
 if sha(p)!=sha(q):codechanges.append(str(p.relative_to(M0)))
assert codechanges==['motor/fisica_final.py']
receipt={'candidate':str(P),'source_candidate_untouched':str(P0),'engine':str(M),'original_engine_untouched':str(M0),'changed_code_files':codechanges,'original_sha256':sha(M0/'motor/fisica_final.py'),'candidate_sha256':sha(M/'motor/fisica_final.py'),'extra_surface_contact_pairs':pairs,'contact_pairs_exempt_depth':False,'all_numeric_physical_limits_unchanged':True,'new_numerical_ray_progress':'max(1e-7,max(1,abs(world_hit))*2**-20), fail closed above penetration_tolerance/16','new_evaluated_surface_probes':'Triangle centroids and unique triangle-edge midpoints; catches vertex-only coaxial penetration blind spot','scene_approved':False,'regression_required':True}
guardar(E/'evidencias/candidata_bvh08_preparada.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
