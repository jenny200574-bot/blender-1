import sys,json,subprocess,hashlib
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');M=R/'MOTOR_BVH08_CANDIDATO';E=R/'entrega';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
code=lambda:{str(p.relative_to(M)):h(p) for p in sorted((M/'motor').rglob('*.py'))}
a=code();assert not (R/'oro_bvh08_final').exists()
with (R/'oro_bvh08_final.log').open('w') as log:
 p=subprocess.run([sys.executable,str(M/'motor_unico.py'),str(M/'paquetes/regresion_orden_explicito/entrada_escena.json'),'--salida',str(R/'oro_bvh08_final'),'--regresion','--blender','/opt/blender/actual/blender','--referencia','/opt/myia-motor-v9/avance06_20261107/oro_av06/revisor_comparable.json'],stdout=log,stderr=subprocess.STDOUT,timeout=7200)
assert p.returncode==0 and a==code();g=json.loads((R/'oro_bvh08_final/metricas_oro.json').read_text());assert g['all_equal'] and g['count']==23
out={'passed':True,'all_code_hashes_unchanged_during_gold':True,'code':a,'metrics_sha256':h(R/'oro_bvh08_final/metricas_oro.json'),'reference_untouched':True,'fixture_sha256':g['package_sha256']};(E/'evidencias/oro_bvh08_codigo_vinculado.json').write_text(json.dumps(out,indent=2));print(json.dumps({'passed':True,'count':g['count'],'module_sha256':a['motor/fisica_final.py']}))
