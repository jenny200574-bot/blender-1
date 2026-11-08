from pathlib import Path
import subprocess,concurrent.futures,json
B=Path('/opt/myia-motor-v9/avance06_20261107/entrega')
def run(name):
 p=B/'evidencias'/(name+'_puente.json')
 with p.open('w') as f:r=subprocess.run([str(B/'codigo/puente_json.sh'),'ejecutar',name],stdout=f,stderr=subprocess.PIPE,text=True)
 d=json.loads(p.read_text());return {'job':name,'exit':r.returncode,'ok':d.get('ok'),'error':d.get('error'),'output':str(p)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(run,['av06_bird01','av06_light01','av06_live01','av06_audit01']):print(json.dumps(result),flush=True)
