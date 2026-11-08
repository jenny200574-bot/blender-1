import sys,json,shutil,hashlib
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance04_20261107');R=B/'MOTOR_UNICO_20261107';sys.path.insert(0,str(B/'entrega/codigo'));from traductor_02t import build,safe
src=Path('/opt/myia-motor-v9/v9_motor_unico_20261107/trabajo/cn-los-guardianes-de-la-9fb323be/cap01_ep-89b93118ad/esc_1/20261107_202225_e5f51627')
work=B/'scene_esc1_fuente2';shutil.copytree(src,work)
d=json.loads((work/'entrada_escena.json').read_text());paths={a['path'] for a in d['assets']};attached=[]
template=json.loads((R/'paquetes/guardianes_t316/entrada_escena.json').read_text())
if not d['camera'].get('resolver_inputs'):
 a=safe(work,d['camera']['source']);b=safe(R/'paquetes/guardianes_t316',template['camera']['source'])
 if hashlib.sha256(a.read_bytes()).digest()!=hashlib.sha256(b.read_bytes()).digest():raise ValueError('Camera source differs; cannot attach resolver inputs')
 d['camera']['resolver_inputs']=template['camera']['resolver_inputs']
for key,rel in d['camera']['resolver_inputs'].items():
 p=safe(work,rel)
 if not p.exists():
  source=safe(R/'paquetes/guardianes_t316',rel)
  if not source.is_file():continue
  p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
 if rel not in paths:
  d['assets'].append({'path':rel,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'type':'json'});attached.append(rel);paths.add(rel)
(work/'entrada_escena.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));receipt=build(work/'entrada_escena.json',B/'scene_esc1_02t')
receipt['attached_existing_camera_sources']=attached;(B/'entrega/evidencias/02t_esc1_recibo.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
sys.path.insert(0,str(R/'motor'));from orquestador import ejecutar
result=ejecutar(B/'scene_esc1_02t/entrada_escena.json',B/'prevalidacion_esc1',prueba_cpu=True,solo_validar=True)
summary={'estado':result['estado'],'faltantes':len(result['errores']),'errores':result['errores'],'paid_calls':0,'rendered':False,'attached_existing_camera_sources':attached};(B/'entrega/evidencias/esc1_resultado.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({'estado':result['estado'],'faltantes':len(result['errores']),'attached_camera_sources':len(attached)}))
