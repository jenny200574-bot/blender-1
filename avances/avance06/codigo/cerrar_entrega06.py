from pathlib import Path
import json,subprocess,shutil,tarfile
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';py='/opt/myia-motor-v9/respaldo_plan_20261107_193319/herramientas/venv_cpu/bin/python'
for name in ['test_puente_compatibilidad.py','test_aplicacion06.py']:
 r=subprocess.run([py,str(E/'codigo'/name)],capture_output=True,text=True);(E/'evidencias'/(name+'.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError('Tests failed')
for name in ['metricas_oro.json','blender.log','revisor_comparable.json']:
 p=B/'oro_av06'/name
 if p.exists():shutil.copy2(p,E/'evidencias'/('oro_'+name))
for path in [Path('/opt/myia-taller-n8n/cajas/entrada_ssh.sh'),Path('/etc/sudoers.d/myia-taller-n8n'),Path('/opt/myia-taller-n8n/cajas/sello_pago.py')]:
 shutil.copy2(path,E/'fuentes'/(path.name+'_despues'));shutil.copy2(B/'respaldos'/path.name,E/'fuentes'/(path.name+'_antes'))
shutil.copy2(B/'MOTOR_UNICO_20261107/motor/luces_blender.py',E/'codigo/luces_blender_runtime.py');shutil.copy2(B/'respaldos/luces_blender_antes.py',E/'fuentes/luces_blender_antes.py')
subprocess.run(['/usr/sbin/visudo','-c'],check=True,stdout=(E/'evidencias/visudo_c.log').open('w'),stderr=subprocess.STDOUT)
ledger=json.loads((E/'evidencias/ledger.json').read_text());assert ledger['reserved_usd']==0
(E/'evidencias/cierre.json').write_text(json.dumps({'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'tests':16,'all_passed':True,'generador_off':(B/'generador.off').exists(),'live_payment_off':(B/'pago_adn_json.off').exists(),'no_paid_jobs_open':True,'gpu_resumed_by_this_phase':False,'video':None},indent=2))
with tarfile.open(B/'entrega06_evidencia.tar.gz','w:gz') as t:
 t.add(E,arcname='entrega',filter=lambda i:None if '__pycache__' in i.name else i);t.add(B/'esc1_candidata',arcname='entrega/esc1_candidata');t.add(B/'piquito_diseno_cpu_world.blend',arcname='entrega/modelos/piquito_diseno_cpu.blend')
 for p in (B/'preview_cpu_esc1_final').rglob('*.json'):t.add(p,arcname='entrega/evidencias/preview_cpu_esc1_final/'+str(p.relative_to(B/'preview_cpu_esc1_final')))
print('Evidence closed: 16 tests; guards closed; no video')
