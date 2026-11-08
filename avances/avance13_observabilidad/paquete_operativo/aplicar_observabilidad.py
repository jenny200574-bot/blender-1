#!/usr/bin/env python3
"""Aplica el parche de observabilidad sobre una COPIA del supervisor operativo.

No se autoejecuta. No lanza oro/constructor/Blender. Falla si el hash base no es
el original ni el parche (cambio ajeno: no forzar). Deja observabilidad_cierre.off.

Reemplazo: temporal + os.replace en el mismo directorio (POSIX atómico para el
nombre). Candado advisory fcntl.flock. No es CAS perfecto: un escritor que
ignore el lock puede competir. Python 3.12+ (VPS 3.12.3 / box 3.13).
"""
import argparse,fcntl,hashlib,json,os,stat,sys
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

def sha_bytes(data):
 return hashlib.sha256(data).hexdigest()

def gancho_tras_respaldo(dest):
 """Punto de prueba; no-op en producción."""
 return None

def gancho_antes_replace(tmp,dest):
 """Punto de prueba; no-op en producción."""
 return None

def _informe(**kw):
 return kw

def _fsync_dir(path):
 fd=os.open(str(path),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)

def _lstat_regular(path):
 st=os.lstat(path)
 if stat.S_ISLNK(st.st_mode):
  raise ValueError('DESTINO_ES_SYMLINK')
 if not stat.S_ISREG(st.st_mode):
  raise ValueError('DESTINO_NO_REGULAR')
 return st

def _escribir_reemplazo(dest,data,mode,con_gancho=False):
 dest=Path(dest)
 tmp=dest.parent/('.%s.tmp.%d.%s'%(dest.name,os.getpid(),os.urandom(4).hex()))
 fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 try:
  os.write(fd,data)
  os.fchmod(fd,stat.S_IMODE(mode))
  os.fsync(fd)
 except Exception:
  os.close(fd)
  try:os.unlink(tmp)
  except OSError:pass
  raise
 os.close(fd)
 try:
  if con_gancho:
   gancho_antes_replace(tmp,dest)
   if sha(dest)!=ORIG:
    try:os.unlink(tmp)
    except OSError:pass
    raise ValueError('CAMBIO_AJENO_DURANTE_APLICACION')
  os.replace(str(tmp),str(dest))
 except Exception:
  try:os.unlink(tmp)
  except OSError:pass
  raise
 _fsync_dir(dest.parent)

def _lock_dir(directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 path=directory/'supervisor_oro_constructor.apply.lock'
 fd=os.open(str(path),os.O_RDWR|os.O_CREAT,0o644)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  os.close(fd)
  raise RuntimeError('CORRIDA_CONCURRENTE_APLICAR')
 return fd

def aplicar(destino,solo_verificar=False,revertir=False,respaldo=None):
 dest_arg=Path(destino)
 if dest_arg.is_symlink():
  return _informe(ok=False,error='DESTINO_ES_SYMLINK',path=str(dest_arg)),3
 dest=dest_arg.resolve()
 if not dest.exists():
  return _informe(ok=False,error='DESTINO_AUSENTE',path=str(dest)),2
 try:
  st=_lstat_regular(dest)
 except ValueError as e:
  return _informe(ok=False,error=str(e),path=str(dest)),3
 if sha(ORIGINAL_PAQUETE)!=ORIG:
  return _informe(ok=False,error='PAQUETE_ORIGINAL_ALTERADO'),2
 nuevo=sha(PARCHE)
 parche_data=PARCHE.read_bytes()
 if sha_bytes(parche_data)!=nuevo:
  return _informe(ok=False,error='PAQUETE_PARCHE_ALTERADO'),2
 lockfd=None
 try:
  lockfd=_lock_dir(dest.parent)
 except RuntimeError as e:
  return _informe(ok=False,error=str(e),path=str(dest)),6
 try:
  st=_lstat_regular(dest)
  data=dest.read_bytes()
  actual=sha_bytes(data)
  informe={'ok':True,'destino':str(dest),'sha_actual':actual,'sha_original_esperado':ORIG,'sha_parche':nuevo,'bytes_actual':len(data),'modo':stat.S_IMODE(st.st_mode)}
  if actual not in {ORIG,nuevo}:
   informe.update(ok=False,error='CAMBIO_AJENO_NO_FORZAR',detalle='El archivo destino no es la fuente operativa conocida ni el parche de este paquete.')
   return informe,3
  if solo_verificar:
   informe['estado']='original' if actual==ORIG else 'parche_ya_aplicado'
   return informe,0
  if revertir:
   return _revertir(dest,st,data,actual,nuevo,informe,respaldo)
  if actual==nuevo:
   informe['estado']='ya_aplicado'
   return informe,0
  return _commit_parche(dest,st,data,informe,parche_data,nuevo)
 finally:
  if lockfd is not None:
   try:fcntl.flock(lockfd,fcntl.LOCK_UN)
   except OSError:pass
   os.close(lockfd)

def _commit_parche(dest,st,data,informe,parche_data,nuevo):
 respaldo_dir=dest.parent/'respaldos_observabilidad'
 respaldo_dir.mkdir(parents=True,exist_ok=True)
 stamp=datetime.now(ZoneInfo('America/Bogota')).strftime('%Y%m%d_%H%M%S')
 bak=respaldo_dir/('supervisor_oro_constructor.py.'+stamp+'.orig')
 _escribir_reemplazo(bak,data,st.st_mode,con_gancho=False)
 if sha(bak)!=ORIG:
  informe.update(ok=False,error='RESPALDO_HASH_DISTINTO',respaldo=str(bak))
  return informe,4
 gancho_tras_respaldo(dest)
 if sha(dest)!=ORIG:
  informe.update(ok=False,error='CAMBIO_AJENO_DURANTE_APLICACION',detalle='Destino cambió tras el respaldo; no se reemplaza ni se fuerza el original sobre el cambio ajeno.',respaldo=str(bak),sha_durante=sha(dest))
  return informe,7
 try:
  _escribir_reemplazo(dest,parche_data,st.st_mode,con_gancho=True)
 except ValueError as e:
  if str(e)=='CAMBIO_AJENO_DURANTE_APLICACION':
   informe.update(ok=False,error='CAMBIO_AJENO_DURANTE_APLICACION',detalle='Destino cambió antes del replace; no se fuerza.',respaldo=str(bak),sha_durante=sha(dest))
   return informe,7
  raise
 except Exception as e:
  if sha(dest)!=ORIG:
   informe.update(ok=False,error='FALLO_ESCRITURA_DESTINO_ALTERADO',detalle=str(e))
   return informe,8
  informe.update(ok=False,error='FALLO_ESCRITURA_ORIGINAL_INTACTO',detalle=str(e),respaldo=str(bak),sha_despues=sha(dest))
  return informe,8
 if sha(dest)!=nuevo:
  try:
   _escribir_reemplazo(dest,data,st.st_mode,con_gancho=False)
  except Exception as e:
   informe.update(ok=False,error='APLICADO_HASH_DISTINTO_REVERTIDO_FALLO',detalle=str(e),respaldo=str(bak))
   return informe,5
  informe.update(ok=False,error='APLICADO_HASH_DISTINTO_REVERTIDO',respaldo=str(bak),sha_despues=sha(dest))
  return informe,5
 off_dest=dest.parent/'observabilidad_cierre.off'
 if not off_dest.exists():
  _escribir_reemplazo(off_dest,OFF.read_bytes(),0o644,con_gancho=False)
 informe.update(estado='aplicado_con_off',respaldo=str(bak),off=str(off_dest),sha_despues=sha(dest),modo_despues=stat.S_IMODE(os.lstat(dest).st_mode))
 return informe,0

def _revertir(dest,st,data,actual,nuevo,informe,respaldo):
 if actual==ORIG:
  informe['estado']='ya_original'
  return informe,0
 if actual!=nuevo:
  informe.update(ok=False,error='CAMBIO_AJENO_NO_FORZAR')
  return informe,3
 if respaldo:
  bak=Path(respaldo)
 else:
  cands=sorted((dest.parent/'respaldos_observabilidad').glob('supervisor_oro_constructor.py.*.orig'))
  if not cands:
   informe.update(ok=False,error='RESPALDO_AUSENTE')
   return informe,4
  bak=cands[-1]
 if not bak.is_file() or bak.is_symlink():
  informe.update(ok=False,error='RESPALDO_INVALIDO',respaldo=str(bak))
  return informe,4
 bak_data=bak.read_bytes()
 if sha_bytes(bak_data)!=ORIG:
  informe.update(ok=False,error='RESPALDO_HASH_DISTINTO',respaldo=str(bak))
  return informe,4
 if sha(dest)!=nuevo:
  informe.update(ok=False,error='CAMBIO_AJENO_DURANTE_APLICACION')
  return informe,7
 _escribir_reemplazo(dest,bak_data,st.st_mode,con_gancho=False)
 if sha(dest)!=ORIG:
  informe.update(ok=False,error='REVERTIDO_HASH_DISTINTO',sha_despues=sha(dest))
  return informe,5
 informe.update(estado='revertido_a_original',respaldo=str(bak),sha_despues=sha(dest))
 return informe,0

def main(argv=None):
 p=argparse.ArgumentParser()
 p.add_argument('--destino',required=True,help='Ruta del supervisor_oro_constructor.py a reemplazar')
 p.add_argument('--solo-verificar',action='store_true')
 p.add_argument('--revertir',action='store_true')
 p.add_argument('--respaldo',help='Ruta de un .orig verificado para --revertir')
 a=p.parse_args(argv)
 informe,code=aplicar(a.destino,solo_verificar=a.solo_verificar,revertir=a.revertir,respaldo=a.respaldo)
 print(json.dumps(informe,ensure_ascii=False,indent=2))
 return code

if __name__=='__main__':
 sys.exit(main())
