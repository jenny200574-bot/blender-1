"""Catálogo de movimientos verificados por contenido; sólo admisión tras revisión técnica."""
import copy,shutil,json,hashlib,fcntl
from pathlib import Path
from datetime import datetime
from seguridad import leer,guardar,sha,ruta,numero

def firma(request):
 fields=('action','anatomy','emotion','load','support','context')
 return hashlib.sha256(json.dumps({k:request.get(k) for k in fields},sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def bvh_info(path):
 text=Path(path).read_text();import re
 frames=re.search(r'Frames:\s*(\d+)',text);step=re.search(r'Frame Time:\s*([\d.eE+-]+)',text);channels=[int(x) for x in re.findall(r'CHANNELS\s+(\d+)',text)]
 if not frames or not step or not channels:raise ValueError('BVH sin jerarquía/reloj')
 n=int(frames[1]);dt=float(step[1]);rows=text[step.end():].strip().splitlines()
 if n<1 or dt<=0 or len(rows)!=n:raise ValueError('Reloj/cuadros BVH inválidos')
 import math
 for row in rows:
  values=[float(x) for x in row.split()]
  if len(values)!=sum(channels) or any(not math.isfinite(x) for x in values):raise ValueError('Canales BVH inválidos')
 return {'frames':n,'frame_time_s':dt,'duration_s':n*dt,'joint_names':re.findall(r'(?:ROOT|JOINT)\s+(\S+)',text),'sha256':sha(path)}

def registrar(root,path,*,origin,source,skeleton,profile,metrics,request=None,prompt=None,tracks=None):
 root=Path(root)
 if (root/'.off').exists():return {'state':'OFF'}
 if origin not in ['kimodo','cmu','retarget','video','mixamo','catalogo']:raise ValueError('Origen sin puente registrado')
 if metrics.get('all_passed') is not True or metrics.get('errors') or not any(k not in ['all_passed','errors'] for k in metrics):raise ValueError('No hay métricas de revisión técnica aprobadas')
 if not source or not skeleton or not profile or (not prompt and not source):raise ValueError('Metadatos incompletos')
 info=bvh_info(path);h=info['sha256'];root.mkdir(parents=True,exist_ok=True)
 with (root/'catalogo.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);index=root/'catalogo.json';d=leer(index) if index.exists() else {'schema':'motion_catalog_v1','entries':[]}
  key=firma(request) if request is not None else None
  existing=next((x for x in d['entries'] if x['sha256']==h and x['skeleton']==skeleton and x['profile']==profile and x.get('signature')==key),None)
  if existing:return {'state':'REUSED','record':existing}
  destination=root/'bvh'/(h+'.bvh');destination.parent.mkdir(exist_ok=True)
  if not destination.exists():shutil.copy2(path,destination)
  rec={'id':h[:24]+'.'+str(len(d['entries'])),'path':str(destination.relative_to(root)),**info,'origin':origin,'source':source,'prompt':prompt,'skeleton':skeleton,'profile':profile,'metrics':metrics,'signature':key,'request':request,'tracks':tracks,'created_at':datetime.now().astimezone().isoformat(),'technical_approved':True}
  d['entries'].append(rec);guardar(index,d);return {'state':'ADDED','record':rec}

def reusar(root,request,skeleton=None,profile=None):
 root=Path(root);p=root/'catalogo.json'
 if (root/'.off').exists() or not p.exists():return None
 for rec in reversed(leer(p)['entries']):
  if rec.get('signature')!=firma(request) or not rec.get('technical_approved'):continue
  if skeleton is not None and skeleton!=rec['skeleton']:continue
  if profile is not None and profile!=rec['profile']:continue
  file=ruta(root,rec['path'])
  if not file.is_file() or sha(file)!=rec['sha256']:continue
  return copy.deepcopy(rec)
 return None

def conectar(d,library):
 m=d.setdefault('motion',{});receipts=[]
 for req in m.get('requests',[]):
  entity=next((e for e in d['entities'] if e['id']==req.get('entity')),{});skeleton=entity.get('rig');profile=entity.get('physics');rec=reusar(library,req,skeleton,profile)
  if not rec:continue
  if not rec.get('tracks'):receipts.append({'request':req.get('id',firma(req)),'state':'BVH_DISPONIBLE_REQUIERE_MAPA_RETARGET','record':rec['id']});continue
  c={**{k:req[k] for k in ['action','anatomy','emotion','load','support','context']},'id':'cache_'+rec['id'],'entity':req['entity'],'provider':'catalogo','catalog_cache':True,'approval_ref':rec['sha256'],'tracks':rec['tracks'],'cache_record':rec['id']};m.setdefault('candidates',[]).insert(0,c);receipts.append({'request':req.get('id',firma(req)),'state':'REUSED_BEFORE_GENERATION','record':rec['id']})
 # Un BVH ya aprobado se reusa antes de pulir/generar otra vez el mismo contenido.
 for job in m.get('retarget_jobs',[]):
  if not job.get('raw_bvh'):continue
  p=Path(library)/'catalogo.json'
  if not p.exists():continue
  for rec in leer(p)['entries']:
   if rec.get('source',{}).get('input_sha256')==job.get('raw_sha256') and rec['profile']==job.get('profile') and rec['skeleton']==job.get('skeleton'):
    job['_catalog_reuse']=rec;break
 return receipts

def configuracion_job(job,clock):
 return {'clock':clock,'parameters':{k:job.get(k) for k in ['mapping','unit_scale','axis_quaternion','root_source','root_target','footlock','effector_map']}}
def buscar_bvh(root,job,clock,input_sha256,profile):
 root=Path(root);p=root/'catalogo.json'
 if not p.exists() or (root/'.off').exists():return None
 for rec in reversed(leer(p)['entries']):
  source=rec.get('source',{})
  if source.get('input_sha256')!=input_sha256 or source.get('job_configuration')!=configuracion_job(job,clock) or rec['profile']!=profile:continue
  file=ruta(root,rec['path'])
  if file.is_file() and sha(file)==rec['sha256'] and rec.get('technical_approved'):return rec
 return None
