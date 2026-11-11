"""Contrato del MOTOR. El puente conserva fuentes; este módulo las interpreta.
Unidades m/grados/s, +Z arriba; conversión de segundos a frames base1.
La previs técnica provisional nunca equivale a ADN/escena aprobados.
"""
import json, math, hashlib, re, unicodedata
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import esqueleto_adn as EA

def leer(p): return json.loads(Path(p).read_text())
def guardar(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  import datetime,shutil
  shutil.copy2(p,str(p)+'.bak_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def normal(s): return ''.join(c for c in unicodedata.normalize('NFKD',str(s).lower()) if not unicodedata.combining(c))
def frame(t,fps):return int((Decimal(str(t))*Decimal(str(fps))).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
def contrato(paquete,provisional=False):
 root=Path(paquete).resolve();p=leer(root/'plan_tomas.json');warnings=[];errors=[];specs={};excluded=[]
 if not p.get('ejes_source'):warnings.append({'code':'EJES_NO_CERTIFICADOS','assumption':'previs técnica usa +Y frente,+Z arriba; fuente intacta'})
 fps=p.get('fps');dur=p.get('duracion_s')
 if not isinstance(fps,int) or fps<=0 or not isinstance(dur,(int,float)) or dur<=0:raise ValueError('FPS/duración inválidos')
 if frame(dur,fps)!=p.get('frame_count'):raise ValueError('Reloj no coincide con duración')
 for x in p['escena']['personajes']:
  pid=x['id'];text=(root/x['adn_file']).read_text();tn=normal(text)
  # No convertir ave en humano; conflicto de ancla queda pendiente, no se elige lado.
  if re.search(r'\b(ave|pajarito|pajaro|canario|bird)\b',re.split(r'2[.]\s*fisonomia',tn)[0]):
   excluded.append(pid);warnings.append({'code':'ANATOMIA_AVIAR_NO_SOPORTADA','id':pid,'detail':'sin rig ni lado de hombro resuelto; no se simula humano'});continue
  s=EA.leer_adn(text,pid);missing=[k for k in ('altura_m','cabezas') if not isinstance(x.get(k),(int,float)) or x[k]<=0]
  if missing:
   item={'code':'ADN_MEDIDAS_FALTANTES','id':pid,'fields':missing}
   if not provisional:errors.append(item);continue
   warnings.append({**item,'PROVISIONAL_SOLO_TECNICO':{k:s[k] for k in missing},'origin':'defaults explícitos del parser histórico, NO valores aprobados'})
  for k in ('altura_m','cabezas'):
   if isinstance(x.get(k),(int,float)) and x[k]>0:s[k]=x[k]
  if s['altura_m']<=0 or s['cabezas']<=0 or any(math.dist(b['cabeza'],b['cola'])<1e-7 for b in EA.huesos(s)):errors.append({'code':'ESQUELETO_DEGENERADO','id':pid});continue
  specs[pid]=s
 if excluded:warnings.append({'code':'ANCLA_CONFLICTIVA_NO_RESUELTA','ids':excluded,'detail':'Se conservan fuentes 01/ADN; no se elige hombro'})
 actions=[]
 for i,a in enumerate(p['acciones']):
  t0,t1=a['t0'],a['t1']
  if not (0<=t0<t1<=dur+1e-6):errors.append({'code':'ACCION_TIEMPO_INVALIDO','index':i});continue
  aid=(a.get('source_verbatim') or {}).get('id') or f"{a.get('source_kind')}_{a['personaje']}_{a.get('source_segment_index',i)}"
  actions.append({**a,'action_id':aid})
 result={'version':'motor_universal_t923/v1','source_plan':str(root/'plan_tomas.json'),'package':str(root),'plan':p,'specs':specs,'actions':actions,'excluded_characters':excluded,'warnings':warnings,'errors':errors,'fps':fps,'duration_s':dur,'N':frame(dur,fps),'technical_only':bool(warnings),'can_build':not errors,'provisional_requested':provisional}
 return result

def posicion(ctx,pid,t):
 segs=sorted((s for s in ctx['plan']['segmentos_01'] if s['personaje']==pid),key=lambda s:s['t0'])
 if not segs:raise ValueError('Sin posición fuente para '+pid)
 s=segs[0]
 for a in segs:
  if a['t0']<=t:s=a
 u=max(0,min(1,(t-s['t0'])/(s['t1']-s['t0'])))
 pos=[a+(b-a)*u for a,b in zip(s['pos_inicio_m'],s['pos_fin_m'])];yaw=s.get('yaw_deg')
 if isinstance(yaw,list):yaw=yaw[0]+((yaw[-1]-yaw[0]+180)%360-180)*u
 return pos,float(yaw or 0),s

def evidencia_2b(ctx):
 p=ctx['plan'];characters=[]
 for x in p['escena']['personajes']:
  characters.append({'id':x['id'],'names':x['names'],'entity_type':x['entity_type'],'ADN_integral':(Path(ctx['package'])/x['adn_file']).read_text(),'spec_motor':ctx['specs'].get(x['id']),'unsupported':x['id'] in ctx['excluded_characters']})
 fields=('personaje','tipo','t0','t1','action_id','source_kind','pose_source','mirada_source','emocion','notas','objeto','cambio','pos_inicio_m','pos_fin_m','yaw_deg','distancia_m','velocidad_m_s','enriched_source')
 acts=[]
 for a in ctx['actions']:
  d={k:a[k] for k in fields if k in a}
  if d.get('enriched_source'):d['enriched_source']=d['enriched_source'].get('gaze')
  acts.append(d)
 return {'canal':p['canal'],'capitulo':p['capitulo'],'escena':p['escena']['id'],'fps':ctx['fps'],'duracion_s':ctx['duration_s'],'guion_completo':p['guion_completo_verbatim'],'personajes':characters,'props':p['escena']['props'],'acciones':acts,'avisos':ctx['warnings']}
