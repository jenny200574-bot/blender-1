from pathlib import Path
import json,shutil,sys
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';P=B/'esc1_candidata';R=B/'MOTOR_UNICO_20261107';sys.path.insert(0,str(R/'motor'));from seguridad import guardar,sha
from orquestador import ejecutar
shutil.copytree(P,B/'esc1_antes_alias_role');read=lambda p:json.loads(p.read_text());d=read(P/'entrada_escena.json');dna=read(P/'adn_entidades.json');ent=next(e for e in d['entities'] if e['id']=='ch-piquito-030a');rec=next(r for r in dna['records'] if r['id']==ent['id']);art=read(P/'argon_piquito06_apariencia.json');evidence=read(E/'evidencias/bird_apariencia_canonica.json');containers=[ent['appearance']['geometry'],ent['dna_record']['source_data']['generated_geometry_candidate'],rec['source_data']['generated_geometry_candidate'],art,evidence]
for c in containers:
 for p in c['parts']:
  assert isinstance(p['feature'],str) and p['feature'];p['role']=p['feature']
guardar(E/'evidencias/bird_apariencia_canonica.json',evidence);guardar(P/'argon_piquito06_apariencia.json',art);guardar(P/'adn_entidades.json',dna)
for a in d['assets']:a.update(sha256=sha(P/a['path']),bytes=(P/a['path']).stat().st_size)
for s in d['sources']:s['sha256']=sha(P/s['path'])
guardar(P/'entrada_escena.json',d);guardar(E/'evidencias/alias_feature_role.json',{'mapping':'part.role = part.feature (exact model string)','reason':'Native geometry contract uses role, typed generator named the same semantic key feature','numeric_values_changed':False,'part_count':40,'source':'av06_bird_appearance02 + av06_crest03'})
r=ejecutar(P/'entrada_escena.json',B/'preview_cpu_esc1_final',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False);summary={'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':r['estado'],'faltantes':len(r['errores']),'errores':r['errores'],'master':r.get('master'),'gpu_used':False,'paid_network_calls_in_preview':0,'production_approved':False};guardar(E/'evidencias/preview_cpu_final_resultado.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='errores'}))
