"""Recuperación gratuita de elementos JSON COMPLETOS de una respuesta truncada.
No rellena ángulos, tiempos ni campos cortados. El original se conserva byte a byte.
Reuso en MOTOR: sólo si misma conducta fuente tiene correspondencia inequívoca ya programada por2B.
"""
import json
from entrada_universal import normal

def prefijo_completo(text):
 decoder=json.JSONDecoder();i=1;r={};partial=None
 def skip(j):
  while j<len(text) and text[j].isspace():j+=1
  return j
 while True:
  i=skip(i)
  if i>=len(text) or text[i]=='}':break
  try:key,j=decoder.raw_decode(text,i)
  except json.JSONDecodeError:break
  j=skip(j)
  if j>=len(text) or text[j]!=':':break
  j=skip(j+1)
  try:value,end=decoder.raw_decode(text,j)
  except json.JSONDecodeError:
   if j>=len(text) or text[j]!='[':break
   values=[];j+=1
   while True:
    j=skip(j)
    try:v,end=decoder.raw_decode(text,j)
    except json.JSONDecodeError:break
    values.append(v);j=skip(end)
    if j>=len(text) or text[j]!=',':break
    j+=1
   r[key]=values;partial=key;break
  r[key]=value;i=skip(end)
  if i>=len(text) or text[i]!=',':break
  i+=1
 r['_recovery']={'truncated':True,'partial_array':partial,'fields_recovered':list(r),'no_incomplete_items_used':True}
 return r

def reutilizar_inequivoco(ctx,r):
 source={a['action_id']:a for a in ctx['actions']};assign=r.setdefault('asignacion',[]);have={a['accion_plan'] for a in assign};added=[]
 def fingerprint(a):return tuple(normal(a.get(k,'')) for k in ('source_kind','tipo','pose_source','emocion','notas'))+(bool(a.get('distancia_m',0)>.01),)
 for aid,s in source.items():
  if aid in have or s['personaje'] not in ctx['specs']:continue
  candidates=[a for a in assign if a['accion_plan'] in source and fingerprint(source[a['accion_plan']])==fingerprint(s)]
  local=[a for a in candidates if a['personaje']==s['personaje']]
  if local:candidates=local
  signatures={(a['movimiento'],a['capa']) for a in candidates}
  if len(signatures)!=1:continue
  a=candidates[0];n={k:v for k,v in a.items() if not k.startswith('_')};n['huesos']=sorted(set.intersection(*(set(x['huesos']) for x in candidates))) if all(x['huesos'] for x in candidates) else [];n.update(personaje=s['personaje'],accion_plan=aid,t0=s['t0'],t1=s['t1']);n['objetivo_punto']=((s.get('enriched_source') or {}).get('gaze') or {}).get('resolved_entity_id') or '';n['objetivo_punto']+=('.cabeza' if n['objetivo_punto'] else '');assign.append(n);have.add(aid);added.append({'action_id':aid,'reused_from':a['accion_plan'],'movement':a['movimiento'],'policy':'misma conducta inequívoca; preferencia mismo actor; tiempos fuente intactos'})
 return added


def completar_catalogo_semantico(ctx,r):
 """Selector conservador nativo: exige verbo y emoción compatibles, margen entre candidatos.
 No crea poses; sólo usa el catálogo emitido en la misma respuesta2B.
 """
 import re,difflib
 have={a['accion_plan'] for a in r['asignacion']};added=[]
 def words(s):return re.findall(r'[a-z]+',normal(s).replace('_',' '))
 for a in ctx['actions']:
  if a['action_id'] in have or a['personaje'] not in ctx['specs'] or a['source_kind']!='accion_01':continue
  verb=normal(a['tipo']);emotion=words(a.get('emocion',''));rank=[]
  if not emotion:continue
  for m in r['movimientos']:
   ww=words(m['nombre']+' '+m.get('descripcion',''))
   if verb not in ww:continue
   score=max((difflib.SequenceMatcher(None,e,w).ratio() for e in emotion for w in ww if len(w)>3),default=0)
   rank.append((score,m['nombre']))
  rank.sort(reverse=True)
  if not rank or rank[0][0]<.78 or (len(rank)>1 and rank[0][0]-rank[1][0]<.12):continue
  n={'personaje':a['personaje'],'accion_plan':a['action_id'],'movimiento':rank[0][1],'t0':a['t0'],'t1':a['t1'],'objetivo_punto':'','capa':'gesto','huesos':[]};r['asignacion'].append(n);have.add(a['action_id']);added.append({'action_id':a['action_id'],'movement':rank[0][1],'policy':'selector motor: verbo exacto + emoción; margen>=.12','confidence':rank[0][0],'production_approved':False})
 return added
