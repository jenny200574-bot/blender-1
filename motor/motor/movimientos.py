"""Escalera semántica exacta. No busca subcadenas ni el menos malo."""
from seguridad import *
ORDEN=('argon','catalogo','kimodo','cmu','retarget','video','mixamo')
CONDICIONES=('action','anatomy','emotion','load','support','context')
def seleccionar(request,candidates,prepare,review):
 missing=[k for k in CONDICIONES if k not in request]
 if missing:return None,[error('motion/request/'+k,'01/2B','Falta condición semántica') for k in missing]
 log=[]
 # Los clips aprobados de caché preceden cualquier candidato que requiera generación.
 candidates=sorted(candidates,key=lambda c:not c.get('catalog_cache',False))
 order=list(dict.fromkeys(([c.get('provider') for c in candidates if c.get('catalog_cache')])+list(ORDEN)))
 for source in order:
  for c in candidates:
   if c.get('provider')!=source:continue
   conflicts=[k for k in CONDICIONES if c.get(k)!=request[k]]
   if conflicts:log.append({'id':c.get('id'),'provider':source,'estado':'INCOMPATIBLE','fields':conflicts});continue
   if not c.get('license_ref'):log.append({'id':c.get('id'),'estado':'AVISO','motivo':'Licencia informativa; uso personal t291, no filtra calidad'})
   if not c.get('approval_ref') and c.get('provider') not in {'kimodo','cmu','retarget','video','mixamo'}:
    log.append({'id':c.get('id'),'estado':'BLOQUEADO','motivo':'Falta aprobación técnica comprobable'});continue
   try:
    track,receipt=prepare(c)
    metrics=review(track,request)
    log.append({'id':c['id'],'provider':source,'preparation':receipt,'review':metrics})
    if metrics.get('passed') is True:return {'track':track,'candidate':c,'metrics':metrics},log
   except Exception as exc:log.append({'id':c.get('id'),'estado':'BLOQUEADO','error':str(exc)})
 return None,log

def verificar_programa(root,d,comprobar_acciones=True,comprobar_integridad=True):
 E=[];m=d.get('motion') or {}
 for f in (['respuesta_2b.json','programa_2b.json'] if comprobar_integridad else []):
  p=Path(root)/f
  if p.exists():
   try:
    x=leer(p)
    if isinstance(x,dict) and (x.get('finish_reason') in ['MAX_TOKENS','length'] or x.get('status') in ['truncated','incomplete']):E.append(error('motion/'+f,'2B/Argon','Respuesta truncada','JSON_TRUNCADO'))
   except ValueError:E.append(error('motion/'+f,'2B/Argon','JSON truncado: recuperar respuesta íntegra','JSON_TRUNCADO'))
 path=m.get('assignments')
 if path and comprobar_acciones:
  try:
   assignments=leer(ruta(root,path));linked={a.get('accion_plan') for a in assignments if isinstance(a,dict)} if isinstance(assignments,list) else set()
   live=(d.get('environment') or {}).get('live_data') or {}
   temporal=live.get('changes',[])+(d.get('environment') or {}).get('events',[])+d.get('fx_events',[])
   linked.update(e.get('action_id') for e in temporal if isinstance(e,dict))
   linked.update(a for e in temporal if isinstance(e,dict) for a in e.get('action_ids',[]))
   for action in d.get('actions',[]):
    if action.get('id') not in linked:E.append(error('actions/'+str(action.get('id')),'01/2B + 4a/4a4 + motor de eventos','Acción sin asignación de movimiento ni evento ejecutable','ACCION_SIN_EJECUCION',dato_encontrado=action,fuente='source_01_integral.json#/acciones',accion='Vincular al rig o al evento correspondiente; no eliminar la acción'))
  except (OSError,ValueError,TypeError):E.append(error('motion/assignments','2B','No se pudo comprobar cobertura de acciones'))
 return E
