from pathlib import Path
import sys,json,shutil,subprocess,datetime,re
from zoneinfo import ZoneInfo
B=Path(__file__).resolve().parent;R=B/'MOTOR_UNICO_20261107';T=B/'pruebas_aisladas_01';PY='/opt/myia-motor-v9/respaldo_plan_20261107_193319/herramientas/venv_cpu/bin/python'
sys.path.insert(0,str(R/'motor'));from seguridad import guardar,leer
for rel in ['motor/orquestador.py','motor/nucleo_bueno_cpu.py','motor/heredado/movimiento_natural.py','motor/seguridad.py']:shutil.copy2(R/rel,T/rel)
features=list(leer(R/'config/funciones_produccion.json')['features']);home=B/'activacion_funciones_20261107';home.mkdir(exist_ok=False);report=[]
for index,name in enumerate(features,1):
 stage=home/(str(index).zfill(2)+'_'+name);stage.mkdir();config=leer(R/'config/funciones_produccion.json');guardar(stage/'config_antes.json',config);moved=[]
 for label,root in [('motor',R),('test',T)]:
  flag=root/'motor/heredado'/(name+'.off')
  if flag.exists():shutil.move(str(flag),str(stage/(label+'_'+flag.name)));moved.append((str(flag),str(stage/(label+'_'+flag.name))))
 updated=json.loads(json.dumps(config));updated['features'][name]=True;guardar(R/'config/funciones_produccion.json',updated)
 old=T/('resultados_antes_'+str(index));old.mkdir()
 for rel in ['evidencia/montaje_colores_dev2','evidencia/fixture_negativa_oclusor','paquetes/fixture_negativa_oclusor']:
  p=T/rel
  if p.exists():shutil.move(str(p),str(old/rel.replace('/','__')))
 passed=True;count=0
 with (stage/'suite.log').open('w') as log:
  for test in sorted((T/'pruebas').glob('test_*.py')):
   log.write('\n=== '+test.name+' ===\n');log.flush();r=subprocess.run([PY,'-B',str(test)],cwd=T,stdout=log,stderr=subprocess.STDOUT,timeout=180);passed=passed and r.returncode==0
  for test in [B/'pruebas_operativas/test_puente_y_prevalidacion.py',B/'pruebas_operativas/test_atomicidad_operativa.py']:
   log.write('\n=== '+test.name+' ===\n');log.flush();r=subprocess.run([PY,'-B',str(test)],cwd=B,stdout=log,stderr=subprocess.STDOUT,timeout=90);passed=passed and r.returncode==0
 text=(stage/'suite.log').read_text();counts=[int(x) for x in re.findall(r'Ran (\d+) tests?',text)];count=sum(counts)
 if not passed:
  for flag,backup in moved:shutil.copy2(backup,flag)
  guardar(R/'config/funciones_produccion.json',config)
 row={'feature':name,'tests_passed':passed,'tests_count':count,'rolled_back':not passed,'fecha_bogota':datetime.datetime.now(ZoneInfo('America/Bogota')).isoformat()};report.append(row);guardar(home/'resultado.json',report)
 temp='/tmp/myia_funcion_'+str(index)+'.json';subprocess.run(['docker','exec','myia-taller-n8n','n8n','export:workflow','--id=debwaH9svFMoTnOf','--output='+temp],check=True,stdout=subprocess.DEVNULL);subprocess.run(['docker','cp','myia-taller-n8n:'+temp,str(stage/'workflow_guardado.json')],check=True,stdout=subprocess.DEVNULL);(stage/'workflow_guardado.json').chmod(0o600)
 print(json.dumps(row),flush=True)
 if not passed:raise SystemExit(2)
print('ACTIVACION_COMPLETA',len(report),flush=True)
