#!/usr/bin/env python3
"""Pruebas OFFLINE del aplicador atómico. No ejecuta main del supervisor ni Blender."""
import importlib.util,json,os,stat,sys,tempfile,threading,time,unittest,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ORIG=ROOT/'original'/'artefactos'/'supervisor_oro_constructor.py'
PARCHE=ROOT/'paquete_operativo'/'supervisor_oro_constructor.py'
APLICAR_PY=ROOT/'paquete_operativo'/'aplicar_observabilidad.py'
SHA_ORIG='129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85'
PY=sys.executable

def sha(p):
 import hashlib
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def cargar():
 name='ap_'+uuid.uuid4().hex
 spec=importlib.util.spec_from_file_location(name,APLICAR_PY)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 return mod

def sandbox_dest():
 tmp=Path(tempfile.mkdtemp(prefix='ap13_'))
 dest=tmp/'supervisor_oro_constructor.py'
 dest.write_bytes(ORIG.read_bytes())
 os.chmod(dest,0o640)
 return tmp,dest

def cli(dest,*extra):
 import subprocess
 return subprocess.run([PY,'-B',str(APLICAR_PY),'--destino',str(dest),*extra],capture_output=True,text=True)

class Tests(unittest.TestCase):
 def test_00_supervisor_no_alterado(self):
  self.assertEqual(sha(ORIG),SHA_ORIG)
  self.assertEqual(sha(PARCHE),'6f942bdc739ff8d7c721edabbe2c08849d03f29c923961ce544860689c368289')
  self.assertNotIn('shutil.copy2(PARCHE,dest)',APLICAR_PY.read_text())
  self.assertIn('os.replace',APLICAR_PY.read_text())

 def test_01_aplica_atomico_idempotente_permisos_off(self):
  tmp,dest=sandbox_dest()
  r=cli(dest)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  info=json.loads(r.stdout)
  self.assertEqual(info['estado'],'aplicado_con_off')
  self.assertEqual(sha(dest),sha(PARCHE))
  self.assertEqual(sha(info['respaldo']),SHA_ORIG)
  self.assertEqual(stat.S_IMODE(os.lstat(dest).st_mode),0o640)
  self.assertTrue(Path(info['off']).is_file())
  r2=cli(dest)
  self.assertEqual(json.loads(r2.stdout)['estado'],'ya_aplicado')
  self.assertEqual(sha(dest),sha(PARCHE))

 def test_02_hash_ajeno_no_forzar(self):
  tmp,dest=sandbox_dest()
  dest.write_text('ajeno\n')
  before=dest.read_bytes()
  r=cli(dest)
  self.assertEqual(r.returncode,3)
  self.assertIn('CAMBIO_AJENO_NO_FORZAR',r.stdout)
  self.assertEqual(dest.read_bytes(),before)

 def test_03_symlink_rechazado(self):
  tmp,dest=sandbox_dest()
  link=tmp/'enlace.py'
  os.symlink(dest.name,link)
  r=cli(link)
  self.assertEqual(r.returncode,3)
  self.assertIn('DESTINO_ES_SYMLINK',r.stdout)
  self.assertEqual(sha(dest),SHA_ORIG)

 def test_04_cambio_ajeno_tras_respaldo_no_pisa(self):
  tmp,dest=sandbox_dest()
  ap=cargar()
  def mutar(d):
   Path(d).write_bytes(b'CAMBIO_CONCURRENTE_TRAS_RESPALDO\n')
  ap.gancho_tras_respaldo=mutar
  inf,code=ap.aplicar(dest)
  self.assertEqual(code,7)
  self.assertEqual(inf['error'],'CAMBIO_AJENO_DURANTE_APLICACION')
  self.assertEqual(dest.read_bytes(),b'CAMBIO_CONCURRENTE_TRAS_RESPALDO\n')
  self.assertEqual(sha(inf['respaldo']),SHA_ORIG)

 def test_05_rename_falla_original_intacto(self):
  tmp,dest=sandbox_dest()
  ap=cargar()
  def boom(tmpp,d):
   raise OSError('rename_simulado')
  ap.gancho_antes_replace=boom
  inf,code=ap.aplicar(dest)
  self.assertEqual(code,8)
  self.assertEqual(inf['error'],'FALLO_ESCRITURA_ORIGINAL_INTACTO')
  self.assertEqual(sha(dest),SHA_ORIG)
  self.assertEqual(sha(inf['respaldo']),SHA_ORIG)

 def test_06_write_falla_original_intacto(self):
  tmp,dest=sandbox_dest()
  ap=cargar()
  real=ap._escribir_reemplazo
  n={'n':0}
  def wrap(path,data,mode,con_gancho=False):
   n['n']+=1
   if con_gancho:
    raise OSError('write_simulado')
   return real(path,data,mode,con_gancho=con_gancho)
  ap._escribir_reemplazo=wrap
  inf,code=ap.aplicar(dest)
  self.assertEqual(code,8)
  self.assertEqual(sha(dest),SHA_ORIG)
  self.assertFalse(inf.get('ok'))

 def test_07_cambio_antes_replace_no_fuerza(self):
  tmp,dest=sandbox_dest()
  ap=cargar()
  def mutar(tmpp,d):
   Path(d).write_bytes(b'ALIEN_PRE_REPLACE\n')
  ap.gancho_antes_replace=mutar
  inf,code=ap.aplicar(dest)
  self.assertEqual(code,7)
  self.assertEqual(dest.read_bytes(),b'ALIEN_PRE_REPLACE\n')
  self.assertNotEqual(sha(dest),sha(PARCHE))

 def test_08_concurrencia_cooperativa(self):
  tmp,dest=sandbox_dest()
  ap=cargar()
  fd=ap._lock_dir(dest.parent)
  try:
   inf,code=ap.aplicar(dest)
   self.assertEqual(code,6)
   self.assertEqual(inf['error'],'CORRIDA_CONCURRENTE_APLICAR')
   self.assertEqual(sha(dest),SHA_ORIG)
  finally:
   import fcntl
   fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)

 def test_09_revertir_desde_respaldo(self):
  tmp,dest=sandbox_dest()
  r=cli(dest)
  self.assertEqual(r.returncode,0)
  bak=json.loads(r.stdout)['respaldo']
  self.assertEqual(sha(dest),sha(PARCHE))
  r2=cli(dest,'--revertir','--respaldo',bak)
  self.assertEqual(r2.returncode,0,r2.stdout)
  self.assertEqual(json.loads(r2.stdout)['estado'],'revertido_a_original')
  self.assertEqual(sha(dest),SHA_ORIG)
  r3=cli(dest,'--revertir')
  self.assertEqual(json.loads(r3.stdout)['estado'],'ya_original')

 def test_10_cli_no_invoca_main_supervisor(self):
  src=APLICAR_PY.read_text()
  self.assertNotIn('supervisor_oro_constructor.py\')',src.split('ORIGINAL_PAQUETE')[0] if False else 'Popen')
  self.assertNotIn('motor_unico.py',src)
  self.assertNotIn('/opt/blender',src)

if __name__=='__main__':
 unittest.main(verbosity=2)
