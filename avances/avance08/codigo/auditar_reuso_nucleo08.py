import json,hashlib
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';read=lambda p:json.loads(p.read_text());h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=read(R/'preview_cpu08/entrada_normalizada.json');b=read(R/'preflight_bvh08/entrada_normalizada.json')
checks=[]
def ck(name,ok):
 checks.append({'test':name,'passed':bool(ok)});assert ok,name
ck('preflight_bvh08_zero_missing',not read(R/'preflight_bvh08/resultado.json')['errores'])
ck('legacy_complete_input_identical',a['legacy']==b['legacy'])
ck('clock_identical',a['clock']==b['clock'])
ck('entities_and_added_final_geometry_identical',a['entities']==b['entities'])
ck('motion_identical',a['motion']==b['motion'])
ck('camera_identical',a['camera']==b['camera'])
ck('environment_identical',a['environment']==b['environment'])
ck('lighting_identical',a['lighting']==b['lighting'])
ck('props_identical',a['props']==b['props'])
ck('all_numerical_physical_rules_identical',{k:v for k,v in a['rules'].items() if k!='contact_pairs'}=={k:v for k,v in b['rules'].items() if k!='contact_pairs'})
assets_a={x['path']:x for x in a['assets']};assets_b={x['path']:x for x in b['assets']};ck('asset_names_identical',set(assets_a)==set(assets_b));changed=[]
for n in assets_a:
 pa=R/'preview_cpu08/paquete_normalizado'/n;pb=R/'preflight_bvh08/paquete_normalizado'/n
 if h(pa)!=h(pb):changed.append(n)
ck('only_asset_changed_is_contact_pair_metadata',changed==['argon08_physics_canonica.json'])
M0=R/'MOTOR_UNICO_20261107';M=R/'MOTOR_BVH08_CANDIDATO';code=[]
for p in (M0/'motor').rglob('*.py'):
 if h(p)!=h(M/p.relative_to(M0)):code.append(str(p.relative_to(M0)))
ck('only_code_changed_is_final_BVH_validator',code==['motor/fisica_final.py'])
receipt={'passed':True,'checks':checks,'changed_assets':changed,'changed_code':code,'cached_core_source':str(R/'preview_cpu08/nucleo/escena.blend'),'core_complete_and_hash_verified_later':False,'not_approval':'Only establishes whether an already completed core MAY be reused. Does not approve any physical or visual output.'}
(E/'evidencias/reuso_nucleo08_precondiciones.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False))
