import json,sys,copy,shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';R=B/'MOTOR_UNICO_20261107';P=B/'esc1_candidata';sys.path.insert(0,str(R/'motor'))
from seguridad import guardar,sha
from orquestador import ejecutar
read=lambda p:json.loads(p.read_text());assert read(E/'evidencias/assets_blender_resultado.json')['passed'];assert read(E/'evidencias/vivo_assets_cpu07.json')['passed'];assert read(E/'evidencias/validacion_live07.json')['passed'];canon=read(E/'evidencias/adn_canonico_final.json');assert len(canon['records'])==4 and canon['axes_validated']
shutil.copytree(P,B/'esc1_antes_aplicar07');d=read(P/'entrada_escena.json');dna=read(P/'adn_entidades.json');before=copy.deepcopy(dna);existing={r['id'] for r in dna['records']};assert not existing&{r['id'] for r in canon['records']}
for record in canon['records']:
 record['source_data']['shape_query']={'required_features':[p['id'] for p in record['source_data']['construction_3d']['parts']]};dna['records'].append(record)
cofre=read(E/'evidencias/cofre_con_candados07.json');cofre['source_data']['shape_query']={'required_features':[p['id'] for p in cofre['source_data']['construction_3d']['parts']]};ci=next(i for i,r in enumerate(dna['records']) if r['id']=='gdc-cofre-abecedario');dna['records'][ci]=cofre
assert all(r==dna['records'][i] for i,r in enumerate(before['records']) if r['id']!='gdc-cofre-abecedario'),'Unrelated existing seals must remain byte-equivalent data'
for record in canon['records']:
 ident=record['id'];d['bindings'][ident]['rotation_deg']=record['source_data']['construction_3d']['placement']['rotation_deg'];d['bindings'][ident]['reference_kind']='OBJECT'
axis=canon['axes'];d['coordinates']={'unit':axis['unit'],'up':axis['up'].lstrip('+'),'forward':axis['forward'],'origin':axis['origin'],'source':'argon07_adn_respuesta.json#/axes + fuente07_4a2_escenario.json; source metric/depth set frame only, NOT anatomical/2B approval'}
resolved=[n for n in d.get('provisional',[]) if n['campo'] in ['ejes','changes/object,time,property,value']];d['provisional']=[n for n in d.get('provisional',[]) if n not in resolved];d.setdefault('normalization_history',[]).extend({'resolved_note':n,'reason':'AV07 source-declared set frame or fully parameterized live asset tracks verified in real CPU Blender. 2B/anatomical axes/physics are NOT approved.'} for n in resolved)
# All old required ADN refs still enter the real compiler; explicit FX alone must not bypass the ADN bridge.
d['props']=[dict(id=ref,dna_ref=True) for ref in d['requirements']['object_refs']]+read(E/'evidencias/live_fx_canonico07.json')['props']
live=read(E/'evidencias/live_canonico07.json');d['environment']['live_data']=live;d['environment']['events']=[];d['environment'].setdefault('visibility',{})['obj-candados-cofre']=False # preserve/hide old 8-vertex proxy, no duplicated3bodies
# Independently verify the only three recoverable governing values. Never add7unknowns or profile/approval defaults.
phys=read(E/'evidencias/av07_physics01/respuesta.json');source=read(E/'fuentes/reglas_fuente_normalizador.json')['parameters'];expected={'com_accel_max_m_s2':source['aceleracion_max_com_m_s2'],'joint_speed_max_deg_s':source['vel_max_deg_s'],'slip_max_m_per_frame':source['resbale_pie_max_cm_cuadro']/100};values={r['field']:json.loads(r['value_json']) for r in phys['rows'] if r['state']!='FALTA'};assert values==expected;d['rules_source']=values
# Local candidate asset files are backed up by full copy above. Protected source packages/seals untouched.
guardar(P/'adn_entidades.json',dna);guardar(P/'escenario_vivo.json',live)
files=[(E/'evidencias/av07_adn_final05/respuesta.json','argon07_adn_respuesta.json'),(E/'evidencias/adn_canonico_final.json','argon07_adn_canonico.json'),(E/'evidencias/live_canonico07.json','argon07_vivo_canonico.json'),(E/'evidencias/av07_live02/respuesta.json','argon07_vivo_plantillas.json'),(E/'evidencias/av07_liveparts02/respuesta.json','argon07_vivo_geometria.json'),(E/'evidencias/av07_liveparts03/respuesta.json','argon07_vivo_geometria_correccion.json'),(E/'evidencias/av07_fxland01/respuesta.json','argon07_fx_aterrizaje.json'),(E/'evidencias/vivo_assets_cpu07.json','argon07_assets_cpu_verificados.json'),(E/'fuentes/reglas_fuente_normalizador.json','fuente07_reglas_bloqueadas.json'),(E/'fuentes/escenario.json','fuente07_4a2_escenario.json'),(E/'fuentes/inventario_actual_4b1.json','fuente07_4b1_inventario_actual.json'),(E/'fuentes/glosario_4a2.json','fuente07_glosario_4a2.json')]
for src,dst in files:
 assert not (P/dst).exists();shutil.copy2(src,P/dst);d['assets'].append({'path':dst,'sha256':sha(P/dst),'bytes':(P/dst).stat().st_size,'type':'json'});d['sources'].append({'module':'AV07 source/validated generated design; no physics/2B/visual approval','path':dst,'sha256':sha(P/dst)})
for a in d['assets']:a.update(sha256=sha(P/a['path']),bytes=(P/a['path']).stat().st_size)
for s in d['sources']:s['sha256']=sha(P/s['path'])
# New defensive .off in new engine copy only; never activate an existing flag or trigger network in free preflight.
off=R/'config/argon_recetas.off';assert not off.exists();off.write_text('AVANCE07 free preflight: automatic paid recipe generation disabled. Manual calls require phase ledger and explicit opening.\n')
guardar(P/'entrada_escena.json',d);guardar(E/'evidencias/aplicacion07.json',{'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'applied':['4NEW LOCAL source-specific ADN designs, no legacy identity aliases','27live tracks and59states;54asset assertions executed;5actor assertions held for full scene','3recoverable governing values only;7remain absent','source4a2 set unit/axes frame, not2B certification'],'old_global_seals_overwritten':False,'old_proxy_hidden_not_deleted':'obj-candados-cofre','original_2B_changed':False,'Piquito_physics_or_anchor_invented':False,'production_approved':False})
r=ejecutar(P/'entrada_escena.json',B/'prevalidacion_cpu07',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False);summary={'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':r['estado'],'faltantes':len(r['errores']),'errores':r['errores'],'master':r.get('master'),'full_cpu_preview_passed':not r['errores'] and bool(r.get('master')),'gpu_used':False,'paid_network_calls_in_preflight':0,'production_approved':False};guardar(E/'evidencias/prevalidacion_cpu07_resultado.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='errores'}))
