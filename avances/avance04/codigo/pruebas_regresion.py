from pathlib import Path
import subprocess,json,re
B=Path('/opt/myia-motor-v9/avance04_20261107');R=B/'MOTOR_UNICO_20261107';PY='/opt/myia-motor-v9/respaldo_plan_20261107_193319/herramientas/venv_cpu/bin/python'
rows=[]
with (B/'entrega/evidencias/suite.log').open('w') as log:
 for f in sorted((R/'pruebas').glob('test_*.py')):
  log.write('\n=== '+f.name+' ===\n');log.flush();r=subprocess.run([PY,'-B',str(f)],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=180);rows.append({'test_file':f.name,'exit_code':r.returncode})
text=(B/'entrega/evidencias/suite.log').read_text();result={'all_passed':all(x['exit_code']==0 for x in rows),'tests_count':sum(int(x) for x in re.findall(r'Ran (\d+) tests?',text)),'rows':rows,'tolerances_changed':False};(B/'entrega/evidencias/suite_resultado.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
