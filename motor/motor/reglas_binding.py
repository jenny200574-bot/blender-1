"""Binding verificable de reglas vigentes, colliders y límites de naturalidad."""
import copy
from seguridad import error,numero
from puentes_fisicos import reglas,RULES
LOCKED={'equilibrio_max_fuera_m','equilibrio_cuadros_fuera_max','saltitos_max'}

def compilar(d):
 source=copy.deepcopy(d.get('rules') or d.get('rules_source') or {});limits=d.get('locked_source_rules_not_yet_fully_integrated') or {};errors=[]
 if limits:
  missing=LOCKED-set(limits)
  if missing:errors.append(error('rules/locked','biblioteca de reglas vigentes','Faltan límites bloqueados: '+', '.join(sorted(missing))))
  for k,v in limits.items():
   if k in LOCKED and (not numero(v) or v<0 or (k!='equilibrio_max_fuera_m' and not isinstance(v,int))):errors.append(error('rules/locked/'+k,'biblioteca de reglas vigentes','Límite bloqueado no válido'))
  source['locked_naturalness']=limits
 if set(RULES)<=set(source):
  canonical,found=reglas(source,(d.get('environment') or {}).get('spatial_manifest'));errors+=found
  if canonical is not None:
   if limits:canonical['locked_naturalness']=copy.deepcopy(limits)
   d['rules']=canonical
 else:canonical=None
 if limits:
  for e in d.get('entities',[]):
   if e.get('type')!='CHARACTER' or not e.get('physics'):continue
   profile=(e.get('legacy') or {}).get('profile') or {};v=e['physics'].get('hop_vertical_max_m_s',profile.get('vel_vertical_max_m_s'))
   if not numero(v) or v<0:errors.append(error('entities/'+e['id']+'/physics/hop_vertical_max_m_s','ADN/perfil físico','Falta umbral vertical del perfil para medir saltitos sin inventarlo',causa='perfil_anatomico:'+e['id']))
   else:e['physics']['hop_vertical_max_m_s']=v
 d['_rules_bridge']={'state':'WAITING_DATA' if canonical is None or errors else 'READY','locked_limits_connected':bool(limits)};return d['_rules_bridge'],errors

def revisar_limites(trace,limits):
 errors=[]
 for ident,rows in trace.items():
  metrics={'equilibrio_max_fuera_m':max((r['outside_m'] for r in rows),default=0),'equilibrio_cuadros_fuera_max':sum(r['outside_m']>r['balance_margin_m'] for r in rows),'saltitos_max':sum(r.get('hop',False) for r in rows)}
  for k,value in metrics.items():
   if k in limits and value>limits[k]:errors.append({'type':'REGLA_BLOQUEADA','entity':ident,'rule':k,'value':value,'limit':limits[k]})
 return errors
