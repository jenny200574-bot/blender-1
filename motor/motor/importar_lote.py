"""Ingesta local en cuarentena: copiar no es aprobar ni activar un movimiento."""
import argparse,shutil
from pathlib import Path
from seguridad import leer,ruta,sha,guardar
KINDS={'recipe','pose','movement','cmu','mixamo','video','profile','material'}
def importar(manifest,destination):
 manifest=Path(manifest);base=manifest.parent;d=leer(manifest);dest=Path(destination);receipts=[]
 for row in d['entries']:
  if row['kind'] not in KINDS:raise ValueError('Tipo sin puente: '+row['kind'])
  p=ruta(base,row['path']);h=sha(p)
  if h!=row['sha256'] or p.stat().st_size!=row['bytes']:raise ValueError('Hash/bytes de lote diferentes')
  target=dest/'cuarentena'/row['kind']/h;target.mkdir(parents=True,exist_ok=True);data=target/('asset'+p.suffix)
  if not data.exists():shutil.copy2(p,data)
  receipt={**row,'stored':str(data.relative_to(dest)),'status':'PENDIENTE_REVISION_TECNICA','runtime_enabled':False};guardar(target/'registro.json',receipt);receipts.append(receipt)
 guardar(dest/'ultimo_lote.json',receipts);return receipts
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('destination');a=p.parse_args();print('Ingresados en cuarentena:',len(importar(a.manifest,a.destination)))
