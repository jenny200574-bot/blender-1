"""Proveedor de recetas activo, caché y ledger previo. Sin cliente de red implícito."""
import json,hashlib,math,copy,fcntl
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from seguridad import leer,guardar,ruta,sha,numero

def huella(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def validar(recipe,query,tolerance=.001):
 if not isinstance(recipe,dict) or not recipe.get('source') or not recipe.get('parts'):raise ValueError('Receta sin origen/despiece')
 points=[];ids=set()
 for p in recipe['parts']:
  if not {'id','shape','position_m','rotation_deg','dimensions_m','material','source'}<=set(p):raise ValueError('Pieza incompleta')
  if p['id'] in ids:raise ValueError('ID duplicado')
  ids.add(p['id']);dims=p['dimensions_m']
  if len(dims)!=3 or any(not numero(x) or x<=0 for x in dims):raise ValueError('Medida inválida')
  if any(len(p[k])!=3 or any(not numero(x) for x in p[k]) for k in ['position_m','rotation_deg']):raise ValueError('Transformación inválida')
  mat=p['material']
  if not {'rgba','metallic','roughness'}<=set(mat) or len(mat['rgba'])!=4 or any(not numero(x) or not 0<=x<=1 for x in mat['rgba']+[mat['metallic'],mat['roughness']]):raise ValueError('Material inválido')
  kind=p['shape']
  if kind=='BOX' or p.get('bbox_only'):raise ValueError('Caja/bbox rechazada como acabado')
  if kind=='MESH':
   verts=p.get('vertices_m',[]);faces=p.get('faces',[]);edges={};volume=0
   if len(verts)<4 or not faces or any(len(v)!=3 or any(not numero(a) for a in v) for v in verts):raise ValueError('Malla inválida')
   axis_box=True
   for face in faces:
    if len(set(face))!=len(face) or len(face)<3 or any(not isinstance(i,int) or i<0 or i>=len(verts) for i in face):raise ValueError('Índices inválidos')
    for a,b in zip(face,face[1:]+face[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    a=verts[face[0]]
    for i in range(1,len(face)-1):
     b,c=verts[face[i]],verts[face[i+1]];u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)];cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
     if sum(x*x for x in cross)<1e-24:raise ValueError('Triángulo degenerado')
     axis_box &= sum(abs(x)>1e-12 for x in cross)==1
     volume+=sum(a[j]*(b[(j+1)%3]*c[(j+2)%3]-b[(j+2)%3]*c[(j+1)%3]) for j in range(3))/6
   if any(len(v)!=2 or v[0]!=tuple(reversed(v[1])) for v in edges.values()) or abs(volume)<1e-18:raise ValueError('Malla abierta, winding incoherente o sin volumen')
   if axis_box:raise ValueError('Caja de malla rechazada')
  elif kind in ['ELLIPSOID','CYLINDER','CONE']:
   if not isinstance(p.get('resolution'),int) or p['resolution']<8:raise ValueError('Resolución insuficiente')
   if kind=='CONE' and not 0<=p.get('tip_ratio',-1)<=1:raise ValueError('Cono inválido')
   verts=[[s*dims[0]/2,t*dims[1]/2,u*dims[2]/2] for s in [-1,1] for t in [-1,1] for u in [-1,1]]
  else:raise ValueError('Forma nueva no validable por este contrato')
  # Bounding transform exacto para malla, conservador para primitivas rotadas.
  x,y,z=[math.radians(a) for a in p['rotation_deg']];cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
  for vx,vy,vz in verts:
   vy,vz=cx*vy-sx*vz,sx*vy+cx*vz;vx,vz=cy*vx+sy*vz,-sy*vx+cy*vz;vx,vy=cz*vx-sz*vy,sz*vx+cz*vy;points.append([vx+p['position_m'][0],vy+p['position_m'][1],vz+p['position_m'][2]])
 actual=[max(v[j] for v in points)-min(v[j] for v in points) for j in range(3)]
 if any(abs(a-b)>tolerance for a,b in zip(actual,query['dimensions_m'])):raise ValueError('Geometría no coincide con medidas ADN: '+str(actual))
 return {'passed':True,'dimensions_m':actual,'tolerance_m':tolerance,'part_count':len(ids),'boxes':False,'query_sha256':huella(query)}

class Ledger:
 def __init__(self,path):
  self.path=Path(path)
  local=self.path.parent.parent/'config/politica_ejecucion.json'
  self.policy=local if local.exists() else Path(__file__).resolve().parents[1]/'config/politica_ejecucion.json'
 def presupuesto(self):
  value=leer(self.policy)['presupuesto_total_usd']
  if not numero(value) or value<0:raise ValueError('presupuesto_total_usd inválido')
  return value
 def before(self,estimate,origin,mock=False):
  if not numero(estimate) or estimate<0:raise ValueError('Cotización inválida')
  self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.path.with_suffix('.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);d=leer(self.path) if self.path.exists() else {'entries':[],'spent_usd':0,'reserved_usd':0,'total_cap_usd':self.presupuesto()}
   cap=self.presupuesto();d['total_cap_usd']=cap;remaining=float(Decimal(str(cap))-Decimal(str(d['spent_usd']))-Decimal(str(d['reserved_usd'])))
   if estimate>remaining:raise ValueError('presupuesto_total_usd: reserva total rechazada')
   ref=str(len(d['entries']))+'-'+datetime.now().isoformat();d['entries'].append({'id':ref,'state':'RESERVED_BEFORE_CALL','origin':origin,'estimate_usd':estimate,'mock':mock,'date':datetime.now().astimezone().isoformat()});d['reserved_usd']=float(Decimal(str(d['reserved_usd']))+Decimal(str(estimate)));guardar(self.path,d)
   return {'id':ref,'authorized':True,'remaining_usd':remaining,'reserved_usd':estimate,'mock':mock}
 def settle(self,ref,actual,failed=False):
  with self.path.with_suffix('.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);d=leer(self.path);e=next(x for x in d['entries'] if x['id']==ref['id'])
   if e['state']!='RESERVED_BEFORE_CALL' or not numero(actual) or actual<0 or actual>e['estimate_usd']:raise ValueError('Cargo supera reserva o reserva ya liquidada')
   e.update(state='FAILED' if failed else 'SETTLED',actual_usd=actual);d['reserved_usd']=float(sum((Decimal(str(x['estimate_usd'])) for x in d['entries'] if x['state']=='RESERVED_BEFORE_CALL'),Decimal(0)));d['spent_usd']=float(sum((Decimal(str(x.get('actual_usd',0))) for x in d['entries'] if x['state'] in ['SETTLED','FAILED']),Decimal(0)));guardar(self.path,d)

class Runtime:
 def __init__(self,library,ledger,switch,provider=None,estimate_usd=0,mock=False):self.library=Path(library);self.ledger=Ledger(ledger);self.switch=Path(switch);self.provider=provider;self.estimate=estimate_usd;self.mock=mock
 def generate(self,query):
  key=huella(query);cache=leer(self.library) if self.library.exists() else {'recipes':[]}
  for rec in cache['recipes']:
   if rec.get('query_sha256')==key:
    clean=copy.deepcopy(rec);expected=clean.pop('recipe_sha256',None)
    if expected!=huella(clean):return None,{'state':'FALTA','reason':'Caché alterada'}
    return rec,{'state':'CACHE','sha256':expected,'spent_usd':0}
  if getattr(self,'defer_automatic',False):return None,{'state':'DEFERRED_AUTOMATIC','reason':'El planificador automático agrupa y procesa las recetas faltantes','spent_usd':0}
  if self.switch.exists():return None,{'state':'OFF','reason':'Interruptor .off presente'}
  if self.provider is None:return None,{'state':'FALTA','reason':'Proveedor Argon activo pero sin transporte autorizado; esta programación no hace llamadas reales','enabled_by_default':True,'spent_usd':0}
  estimate=self.provider.quote(query)['reserve_usd'] if hasattr(self.provider,'quote') else self.estimate
  if hasattr(self.provider,'cfg') and self.provider.cfg.get('dry_run',True):return None,{'state':'DRY_RUN','dry_run':self.provider.prepare(query),'spent_usd':0}
  receipt=self.ledger.before(estimate,'recipe_provider',mock=self.mock)
  try:
   recipe=copy.deepcopy(self.provider(query,receipt));usage=recipe.pop('_usage_usd',0 if self.mock else None)
   if not numero(usage) or usage<0 or usage>estimate:raise ValueError('Consumo/cargo no acreditado o superior a reserva')
   metrics=validar(recipe,query);recipe.update(validation=metrics,validated=True,query_sha256=key,reference_dimensions_m=query['dimensions_m'],created_at=datetime.now().astimezone().isoformat(),origin='mock_argon' if self.mock else 'argon');recipe['recipe_sha256']=huella(recipe)
   from buscador_formas import guardar_receta
   stored=guardar_receta(recipe,self.library);self.ledger.settle(receipt,usage);return recipe,{'state':'CREATED','stored':stored,'ledger':receipt,'spent_usd':usage}
  except Exception as exc:
   if self.mock:self.ledger.settle(receipt,0,failed=True)
   # Si la red fallara sin recibo de uso, se mantiene la reserva; nunca se inventa gasto cero.
   return None,{'state':'FALTA','reason':str(exc),'ledger':receipt,'spent_usd':self.estimate}

def contexto(root,d,pk):
 root=Path(root);library=root/'bibliotecas/recetas_aprobadas.json';cfg=d.get('recipe_provider') or {};provider=None;mock=False
 if cfg.get('mode')=='mock':
  if not d.get('fixture_only'):raise ValueError('Mock sólo en fixture declarado, nunca escena real')
  asset=next((a for a in d['assets'] if a['path']==cfg.get('response')),None)
  if not asset or sha(ruta(pk,asset['path']))!=asset['sha256']:raise ValueError('Mock fuera del paquete/hash distinto')
  data=leer(ruta(pk,asset['path']));provider=lambda q,r:copy.deepcopy(data);mock=True
 if provider is None and (root/'config/argon_transporte.json').exists():
  from argon_transporte import Transport
  provider=Transport(root)
 return Runtime(library,root/'evidencia/ledger.json',root/'config/argon_recetas.off',provider,0,mock)
