#!/usr/bin/env python3
"""Aplica el parche de observabilidad sobre una COPIA del supervisor operativo.

No se autoejecuta. No lanza oro/constructor/Blender. Falla si el hash base no es
el original ni el parche (cambio ajeno: no forzar). Deja observabilidad_cierre.off.
"""
import argparse,hashlib,json,os,shutil,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ORIG='129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85'
AQUI=Path(__file__).resolve().parent
PARCHE=AQUI/'supervisor_oro_constructor.py'
OFF=AQUI/'config'/'observabilidad_cierre.off'
ORIGINAL_PAQUETE=AQUI.parent/'original'/'artefactos'/'supervisor_oro_constructor.py'

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--destino',required=True,help='Ruta del supervisor_oro_constructor.py a reemplazar')
 p.add_argument('--solo-verificar',action='store_true')
 a=p.parse_args()
 dest=Path(a.destino).resolve()
 if not dest.is_file():
  print(json.dumps({'ok':False,'error':'DESTINO_AUSENTE','path':str(dest)},ensure_ascii=False));return 2
 if sha(ORIGINAL_PAQUETE)!=ORIG:
  print(json.dumps({'ok':False,'error':'PAQUETE_ORIGINAL_ALTERADO'},ensure_ascii=False));return 2
 nuevo=sha(PARCHE)
 actual=sha(dest)
 informe={'ok':True,'destino':str(dest),'sha_actual':actual,'sha_original_esperado':ORIG,'sha_parche':nuevo,'bytes_actual':dest.stat().st_size}
 if actual not in {ORIG,nuevo}:
  informe.update(ok=False,error='CAMBIO_AJENO_NO_FORZAR',detalle='El archivo destino no es la fuente operativa conocida ni el parche de este paquete.')
  print(json.dumps(informe,ensure_ascii=False,indent=2));return 3
 if a.solo_verificar:
  informe['estado']='original' if actual==ORIG else 'parche_ya_aplicado'
  print(json.dumps(informe,ensure_ascii=False,indent=2));return 0
 if actual==nuevo:
  informe['estado']='ya_aplicado'
  print(json.dumps(informe,ensure_ascii=False,indent=2));return 0
 respaldo=dest.parent/'respaldos_observabilidad'
 respaldo.mkdir(parents=True,exist_ok=True)
 stamp=datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d_%H%M%S')
 bak=respaldo/('supervisor_oro_constructor.py.'+stamp+'.orig')
 shutil.copy2(dest,bak)
 if sha(bak)!=ORIG:
  informe.update(ok=False,error='RESPALDO_HASH_DISTINTO');print(json.dumps(informe,ensure_ascii=False,indent=2));return 4
 shutil.copy2(PARCHE,dest)
 if sha(dest)!=nuevo:
  shutil.copy2(bak,dest)
  informe.update(ok=False,error='APLICADO_HASH_DISTINTO_REVERTIDO');print(json.dumps(informe,ensure_ascii=False,indent=2));return 5
 off_dest=dest.parent/'observabilidad_cierre.off'
 if not off_dest.exists():
  shutil.copy2(OFF,off_dest)
 informe.update(estado='aplicado_con_off',respaldo=str(bak),off=str(off_dest),sha_despues=sha(dest))
 print(json.dumps(informe,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':
 sys.exit(main())
