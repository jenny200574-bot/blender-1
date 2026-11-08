"""Archivos versionados, rutas confinadas y reloj único. Nunca borra."""
import hashlib,json,math,shutil
from pathlib import Path
from datetime import datetime
from fractions import Fraction

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def leer(path):
 def no_const(x):raise ValueError('Número JSON no finito')
 def unique(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Clave JSON repetida: '+k)
   d[k]=v
  return d
 return json.loads(Path(path).read_text(),parse_constant=no_const,object_pairs_hook=unique)
def ruta(root,path):
 if not isinstance(path,str) or not path or Path(path).is_absolute():raise ValueError('Ruta relativa obligatoria')
 base=Path(root).resolve(); p=(base/path).resolve()
 if not p.is_relative_to(base):raise ValueError('Ruta fuera del paquete')
 return p
def archivar(path):
 p=Path(path)
 if p.exists():
  a=p.parent/'archivo'/datetime.now().strftime('%Y%m%d_%H%M%S_%f');a.mkdir(parents=True,exist_ok=False);shutil.move(str(p),str(a/p.name));return a/p.name

def guardar(path,data):
 # Escritura atómica: lectores paralelos nunca ven un archivo ausente o parcial.
 import os,tempfile,stat
 payload=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 mode=stat.S_IMODE(p.stat().st_mode) if p.exists() else 0o600
 if p.exists():
  archive=p.parent/'archivo';archive.mkdir(parents=True,exist_ok=True)
  previous=Path(tempfile.mkdtemp(prefix=datetime.now().strftime('%Y%m%d_%H%M%S_%f_'),dir=archive))
  shutil.copy2(p,previous/p.name)
 fd,temporary=tempfile.mkstemp(prefix='.'+p.name+'.',suffix='.tmp',dir=p.parent)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'w',encoding='utf-8') as stream:
   stream.write(payload);stream.flush();os.fsync(stream.fileno())
  os.replace(temporary,p)
  directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(directory)
  finally:os.close(directory)
 finally:
  if os.path.exists(temporary):os.unlink(temporary)
def numero(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def cuadro(t,fps):
 # HALF_UP explícito, una sola cuantización de todos los bordes.
 v=Fraction(str(t))*Fraction(str(fps));return (2*v.numerator+v.denominator)//(2*v.denominator)
def error(campo,modulo,mensaje,codigo='DATO_FALTANTE',tipo='completar dato',**context):
 return dict(codigo=codigo,severidad='BLOQUEO',campo=campo,modulo=modulo,mensaje=mensaje,tipo=tipo,dato_encontrado=context.pop('dato_encontrado',None),dato_esperado=context.pop('dato_esperado',mensaje),accion=context.pop('accion','Implementar capacidad y probarla' if tipo=='crear capacidad' else 'Revisar y completar desde el productor indicado; no inventar'),fuente=context.pop('fuente',None),**context)

def exigir(capability):
 p=Path(__file__).resolve().parents[1]/'config'/(capability+'.off')
 if p.exists():raise ValueError('Capacidad apagada por '+p.name)

def exigir_desarrollo(capability):
 """Interruptor de desarrollo: producción OFF; prueba CPU sólo por bandera del CLI."""
 import os
 p=Path(__file__).resolve().parents[1]/'config'/(capability+'.off')
 if p.exists() and os.environ.get('MOTOR_UNICO_CPU_PRUEBA')!='1':raise ValueError('Capacidad de desarrollo apagada: '+p.name)
