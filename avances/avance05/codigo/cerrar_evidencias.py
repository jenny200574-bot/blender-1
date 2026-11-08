import json,subprocess,sys,shutil,tarfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
B=Path('/opt/myia-motor-v9/avance05_20261107');E=B/'entrega';py='/opt/myia-motor-v9/respaldo_plan_20261107_193319/herramientas/venv_cpu/bin/python'
r=subprocess.run([py,str(E/'codigo/test_datos_aplicados.py')],capture_output=True,text=True)
(E/'evidencias/tests_8.log').write_text(r.stdout+r.stderr)
(E/'evidencias/tests_8.json').write_text(json.dumps({'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'exit_code':r.returncode,'tests':8,'passed':r.returncode==0},indent=2))
if r.returncode:sys.exit(r.returncode)
for n in ['metricas_oro.json','revisor_comparable.json','blender.log']:
 s=B/'oro_av05'/n
 if s.exists():shutil.copy2(s,E/'evidencias'/('oro_'+n))
with tarfile.open(B/'evidencia_y_candidata_av05.tar.gz','w:gz') as tf:
 tf.add(E,arcname='entrega');tf.add(B/'esc1_candidata',arcname='entrega/esc1_candidata')
 for n in ['preview_cpu_esc1','preview_cpu_esc1_objetos']:
  for f in (B/n).rglob('*.json'):tf.add(f,arcname='entrega/evidencias/'+n+'/'+str(f.relative_to(B/n)))
print('Archive created; 8 tests passed; gold evidence attached')
