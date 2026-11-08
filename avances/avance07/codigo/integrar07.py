import json,sys,shutil,copy
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance07_20261107');E=B/'entrega';R=B/'MOTOR_UNICO_20261107';P=B/'esc1_candidata';sys.path.insert(0,str(R/'motor'))
from seguridad import guardar,sha
from orquestador import ejecutar
read=lambda p:json.loads(p.read_text());shutil.copytree(P,B/'esc1_antes_integracion07');policy=R/'bibliotecas/politica_busqueda_formas_cpu.json';backup=B/'respaldos/politica_busqueda_formas_antes_MESH.json';assert not backup.exists();shutil.copy2(policy,backup);pd=read(policy);prior=copy.deepcopy(pd);assert 'MESH' not in pd['primitive_shapes'];pd['primitive_shapes'].append('MESH');guardar(policy,pd);assert {k:v for k,v in pd.items() if k!='primitive_shapes'}=={k:v for k,v in prior.items() if k!='primitive_shapes'},'Do not change threshold/tolerance'
d=read(P/'entrada_escena.json');live=copy.deepcopy(d['environment']['live_data']);actionmap={a['actor']:a['id'] for a in d['actions'] if a['id'] in ['a6','a7','a8','a9','a10']};annotated=[]
for row in live['changes']:
 if row['object'] in actionmap and row['property']=='hide_render':row['action_id']=actionmap[row['object']];annotated.append({'actor':row['object'],'action_id':row['action_id'],'source':'source_01.json: exact actor/id, declared interval18..21'})
assert len(annotated)==5;d['environment']['live_data']=live;guardar(E/'evidencias/live_canonico07_integrado.json',live);guardar(P/'escenario_vivo.json',live);guardar(P/'argon07_vivo_canonico.json',live)
for a in d['assets']:a.update(sha256=sha(P/a['path']),bytes=(P/a['path']).stat().st_size)
for s in d['sources']:s['sha256']=sha(P/s['path'])
guardar(P/'entrada_escena.json',d);guardar(E/'evidencias/integracion07.json',{'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'backups':[str(backup),str(B/'esc1_antes_integracion07')],'mesh_capability':'MESH renderer and strict closed-volume validator already existed; add only MESH to new-copy search allowlist after real manifold tests; no new code execution','minimum_score_unchanged':pd['minimum_score']==prior['minimum_score'],'same_27_tracks_numeric_values':True,'actor_visibility_source_action_annotations':annotated,'duplicate_writer_policy':'Preserve native conflict detection. Explicit action_id prevents the fallback source01 writer from also claiming that action; no deletion/masking of true conflict.','engine_python_code_changed':False,'automatic_paid_off':(R/'config/argon_recetas.off').exists()})
r=ejecutar(P/'entrada_escena.json',B/'prevalidacion_cpu07_final',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False);summary={'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':r['estado'],'faltantes':len(r['errores']),'errores':r['errores'],'master':r.get('master'),'full_cpu_preview_passed':not r['errores'] and bool(r.get('master')),'gpu_used':False,'paid_network_calls_in_preflight':0,'production_approved':False};guardar(E/'evidencias/prevalidacion_cpu07_final_resultado.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='errores'}))
