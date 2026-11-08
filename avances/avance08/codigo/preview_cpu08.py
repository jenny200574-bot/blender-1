import sys,json,hashlib,os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';M=R/'MOTOR_UNICO_20261107';P=R/'esc1_candidata';sys.path.insert(0,str(M/'motor'));sys.path.insert(0,str(E/'codigo'))
from orquestador import ejecutar
from validar_fisica08 import validar
read=lambda p:json.loads(p.read_text());assert read(E/'evidencias/preflight08.json')['faltantes']==0
assert read(E/'evidencias/physics08_sanity_final.json')['passed'];assert (M/'config/argon_recetas.off').exists();assert read(M/'config/politica_ejecucion.json')['argon_automatico'] is False
# Close manual spending; automatic/live paths were already off. No network calls in CPU preview.
(E/'config/generador.off').write_text('AV08 paid generation closed before free CPU preview; require new explicitly authorized phase to reopen.\n')
ledger=E/'evidencias/ledger.json';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
src=read(E/'config/physics03_sources.json');mesh=src['compiled_mesh_ids'];known={o['id'] for o in src['measured_inventory']['objects'] if o['type']=='MESH'}|{o['id'] for group in mesh.values() for ps in group.values() for o in ps};assert not validar(read(P/'argon08_physics_canonica.json'),known,mesh['character_meshes'],set(mesh['prop_meshes']))
assert read(P/'entrada_escena.json')['rules_source']==read(P/'argon08_physics_canonica.json')['physics']
x=ejecutar(P/'entrada_escena.json',R/'preview_cpu08',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=False)
summary={'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'estado':x['estado'],'faltantes_o_errores':len(x['errores']),'errores':x['errores'],'master':x.get('master'),'gpu_used':False,'paid_calls':0,'ledger_unchanged':hashlib.sha256(ledger.read_bytes()).hexdigest()==before,'full_cpu_preview_passed':not x['errores'] and bool(x.get('master')),'production_approved':False}
(E/'evidencias/preview_cpu08_resultado.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
