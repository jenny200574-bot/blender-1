"""Contrato universal: sólo valores del paquete y errores con productor."""
import json,math,hashlib
from pathlib import Path
def leer(p):return json.loads(Path(p).read_text())
def guardar(p,x):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
def validar(root,diagnostico=False):
 root=Path(root);errors=[]
 def check(ok,path,module,msg):
  if not ok:errors.append({'campo':path,'modulo':module,'mensaje':msg})
 def number(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
 try:d=leer(root/'entrada.json')
 except Exception:return {},[{'campo':'entrada.json','modulo':'exportador n8n','mensaje':'Archivo ausente o JSON inválido'}]
 required=['scene','fps','duration_s','environment','actors','props','catalog','assignments','camera','rules','solver','render','provisional']
 for k in required:check(k in d,k,'exportador','Campo ausente')
 if errors:return d,errors
 check(number(d['fps']) and d['fps']>0,'fps','01','FPS inválido');check(number(d['duration_s']) and d['duration_s']>0,'duration_s','01','Duración inválida')
 if errors:return d,errors
 ids=[x.get('id') for x in d['actors']];check(bool(ids) and None not in ids and len(ids)==len(set(ids)),'actors','ADN/01','IDs ausentes/repetidos o sin actores')
 from esqueleto_adn import huesos
 for actor in d['actors']:
  prefix='actors/'+str(actor.get('id'))
  for k in ['spec','colors','segments','profile','initial_pose_id','floor_z','solver_policy']:check(k in actor,prefix+'/'+k,'ADN/01/2B','Campo ausente')
  if any(k not in actor for k in ['spec','colors','segments','profile','initial_pose_id','floor_z','solver_policy']):continue
  check(isinstance(actor['solver_policy'].get('foot_anchoring'),bool),prefix+'/solver_policy/foot_anchoring','perfil/2B','Política explícita de pies ausente')
  spec=actor['spec']
  for k in ['altura_m','cabezas','complexion','atletico','extras','altura_referencia_perfil_m']:check(k in spec,prefix+'/spec/'+k,'ADN','Falta especificación')
  for k in ['altura_m','cabezas']:check(number(spec.get(k)) and spec[k]>0,prefix+'/spec/'+k,'ADN','Medida ausente o inválida')
  if not all(k in spec for k in ['altura_m','cabezas','complexion','atletico','extras']) or any(not number(spec.get(k)) or spec[k]<=0 for k in ['altura_m','cabezas']):continue
  try:
   bones=huesos(spec)
   for bone in bones:
    colors=actor['colors'];color=colors.get(bone['nombre'],colors.get(bone['grupo'],colors.get('_')))
    check(isinstance(color,(list,tuple)) and len(color)>=3 and all(number(v) and 0<=v<=1 for v in color[:3]),prefix+'/colors/'+bone['nombre'],'ADN/01.parametros_3d','RGB ausente o inválido')
  except Exception:check(False,prefix+'/spec','ADN','Especificación anatómica incompatible con rig')
  check(number(actor['floor_z']),prefix+'/floor_z','4a2/colocación','Suelo no entregado')
  segs=actor['segments'];check(bool(segs),prefix+'/segments','01','Sin colocación')
  for seg in segs:
   ok=all(k in seg for k in ['t0','t1','p0','p1','yaw']);check(ok,prefix+'/segments','01','Segmento incompleto')
   if ok:
    check(0<=seg['t0']<seg['t1']<=d['duration_s'],prefix+'/segments/t','01','Tiempo fuera de escena')
    check(all(isinstance(seg[k],list) and len(seg[k])==3 and all(number(v) for v in seg[k]) for k in ['p0','p1']),prefix+'/segments/pos','01/4a2','Coordenadas incompletas')
  if segs:check(min(x['t0'] for x in segs)==0 and max(x['t1'] for x in segs)==d['duration_s'],prefix+'/segments/t','01','Colocación no cubre duración completa')
  for k in ['retraso_tronco_s','retraso_brazos_s','umbral_fase_intermedia_deg','suavizado_inicio_fin','vel_max_deg_s','anclaje_pies','margen_equilibrio_m','correccion_equilibrio_max_deg','vel_vertical_max_m_s','masa_rel','temblor_deg','vuela','anclaje_excursion_max_m']:check(number(actor['profile'].get(k)),prefix+'/profile/'+k,'ADN/perfil físico','Parámetro técnico no entregado')
 cp=None;assign=None
 for field in ['catalog','assignments']:
  try:value=leer(root/d[field])
  except Exception:check(False,field,'2B','Archivo/JSON ausente');continue
  if field=='catalog':cp=value
  else:assign=value
 if cp is not None and assign is not None:
  for x in assign:
   check(x.get('personaje') in ids,'assignments/personaje','2B','Actor no entregado');check(x.get('movimiento') in cp.get('movimientos',{}),'assignments/movimiento','2B','Movimiento ausente');check(number(x.get('t0')) and number(x.get('t1')) and 0<=x['t0']<x['t1']<=d['duration_s'],'assignments/t','2B/01','Tiempo inválido')
  for actor in d['actors']:check(actor.get('initial_pose_id') in cp.get('poses',{}),'actors/initial_pose_id','2B','Pose inicial ausente')
 env=d['environment']
 if env.get('mode')=='blend':
  q=root/env.get('path','')
  check(q.is_file(),'environment/path','4a2','Falta blend')
  if q.is_file():check(hashlib.sha256(q.read_bytes()).hexdigest()==env.get('sha256'),'environment/sha256','4a2','Blend cambió o sin hash')
 elif env.get('mode')!='formulas':check(False,'environment/mode','4a2','Tipo de escenario desconocido')
 for q in d['props']:
  check((root/q['formula']).is_file(),'props/formula','objetos/FX/2B','Falta geometría/fórmula')
  if q.get('anchor'):check(q['anchor'].get('actor') in ids,'props/anchor','objetos/2B','Host del ancla ausente')
 if not diagnostico:
  live=env.get('live')
  if not live:check(False,'environment/live','4a/4a4 escenario vivo','Falta segundo módulo de escenario')
  else:
   try:
    from escenario_vivo import faltantes
    errors.extend(faltantes(leer(root/live)))
   except Exception:check(False,'environment/live','4a/4a4 escenario vivo','Archivo vivo ausente o inválido')
  if d.get('adn_entities'):
   try:
    from adn_geometria import analizar
    for record in leer(root/d['adn_entities'])['records']:
     if record['id'] in ids:errors.extend(analizar(record)['missing'])
   except Exception:check(False,'adn_entities','ADN Maestro 03/04','ADN estructurado ilegible')
 if not diagnostico:
  for x in d['provisional']:errors.append({'campo':x.get('campo','scene'),'modulo':x.get('modulo','fuentes'),'mensaje':x['mensaje']})
 return d,errors

def posicion(actor,t):
 segs=actor['segments'];s=segs[0]
 for q in segs:
  if q['t0']<=t:s=q
 u=max(0,min(1,(t-s['t0'])/(s['t1']-s['t0'])))
 pos=[a+(b-a)*u for a,b in zip(s['p0'],s['p1'])];rot=s['yaw']
 if isinstance(rot,list):rot=rot[0]+((rot[-1]-rot[0]+180)%360-180)*u
 return pos,float(rot),s
