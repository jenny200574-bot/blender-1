"""Descubrimiento universal, agrupado, concurrencia, reparación y altas validadas.
Sin límite de cantidad de llamadas; sólo presupuesto_total_usd y recursos de workers.
Seco predeterminado. Los mocks no entran en bibliotecas reales.
"""
import copy,json,math,fcntl,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
from seguridad import leer,guardar,ruta,sha
from recetas_proveedor import huella,validar,Ledger
from argon_transporte import Transport

def descubrir(d,pk,object_errors,anatomical_errors):
 pk=Path(pk);records=leer(pk/d.get('adn_entities_source','adn_entidades.json')).get('records',[]) if (pk/d.get('adn_entities_source','adn_entidades.json')).exists() else [];inventory=leer(pk/'inventario_set_medido.json').get('objects',[]) if (pk/'inventario_set_medido.json').exists() else [];inventory={x['id']:x for x in inventory};items=[];source_needed=[]
 for er in object_errors:
  bits=er['campo'].split('/');ident=bits[1] if len(bits)>1 else None
  if not ident:continue
  if bits[-1]!='recipe':source_needed.append({'id':ident,'field':er['campo'],'producer':er['modulo'],'missing':er['mensaje']});continue
  rs=[r for r in records if r.get('type')=='OBJECT' and (r.get('id')==ident or ident in r.get('exact_aliases',[]))]
  if len(rs)!=1:source_needed.append({'id':ident,'missing':'Asociación ADN inequívoca','producer':'ADN OBJ/SELLO +4a2'});continue
  r=rs[0];data=r['source_data'];m=data.get('medidas_cm',{});dims=data.get('dimensions_m') or [m[k]/100 for k in ['ancho_cm','fondo_cm','alto_cm']];q=copy.deepcopy(data.get('shape_query') or {});q.update(id=ident,dimensions_m=dims,source=r.get('source'),producer='ADN OBJ/SELLO + 4a2',text=data.get('frase_sello',data.get('text','')));items.append(q)
 for record in d.get('environment',{}).get('unresolved_details',[]):
  o=inventory.get(record['id'])
  if not o:source_needed.append(dict(record,missing='Inventario/medidas ausentes'));continue
  items.append({'id':record['id'],'task':'object_recipe','dimensions_m':o['dimensions_m'],'text':' '.join(record['source_quote']),'source':{'record':record,'inventory':o},'producer':record['producer'],'materials_policy':'Usar datos de entrada o biblioteca con procedencia; nunca declarar cotas/materiales inventados como ADN'})
 for ent in d.get('entities',[]):
  missing=[er for er in anatomical_errors if er['campo'].startswith('entities/'+ent['id']+'/')]
  if missing:items.append({'task':'anatomy_review','id':ent['id'],'anatomy':ent.get('anatomy'),'dna_record':ent.get('dna_record'),'missing':missing,'actions':[a for a in d.get('actions',[]) if a.get('actor')==ent['id']],'source':'ADN y acciones de entrada; propuesta no certifica datos inexistentes'})
  if not ent.get('appearance',{}).get('geometry',{}).get('parts') and ent.get('dna_record') and not ent.get('legacy') and not missing:items.append({'task':'entity_recipe','id':ent['id'],'dna_record':ent['dna_record'],'source':'Entidad sin receta de geometría'})
 unique={huella(q):q for q in items};return {'items':list(unique.values()),'needs_source':source_needed,'detected_total':len(unique)+len(source_needed)}

def cache_get(root,q):
 root=Path(root);p=root/'bibliotecas/recetas_aprobadas.json' if q.get('task','object_recipe') in ['object_recipe','entity_recipe'] else root/'bibliotecas/anatomias_propuestas.json'
 for rec in (leer(p).get('recipes',[]) if p.exists() else []):
  if rec.get('query_sha256')==huella(q):
   obj=copy.deepcopy(rec);expected=obj.pop('recipe_sha256',None)
   if expected!=huella(obj):raise ValueError('Caché de receta alterada')
   return rec
 return None

def agrupar(items,cfg,policy,grouped=True):
 groups=[];by={}
 for q in items:
  key=(q.get('task','object_recipe'),q.get('anatomy'),q.get('units','METRIC'))
  by.setdefault(key,[]).append(q)
 capacity=max(1,(cfg['max_output_tokens']-policy['tokens_margen_grupo'])//policy['tokens_salida_estimados_por_receta']) if grouped else 1
 for key,values in by.items():
  for i in range(0,len(values),capacity):groups.append(values[i:i+capacity])
 return groups

def batch_query(items,errors=None):return {'task':'recipe_batch','id':huella(items),'items':items,'repair_errors':errors or [],'instructions':'Devuelve un resultado por ID exacto, sin perder elementos. No mezclar identidades. Receta válida o FALTA con productor; no certificar anatomía por inferencia.'}

def planificar(root,items):
 root=Path(root);policy=leer(root/'config/politica_ejecucion.json');t=Transport(root);pending=[];cached=[]
 for q in items:
  (cached if cache_get(root,q) else pending).append(q)
 result={'pending_items':pending,'cache_hits':[q['id'] for q in cached],'presupuesto_total_usd':policy['presupuesto_total_usd'],'no_call_count_cap':True,'max_workers_resource_bound':policy['max_workers'],'mode':'DRY_RUN'}
 for grouped,name in [(False,'ungrouped'),(True,'grouped')]:
  batches=agrupar(pending,t.cfg,policy,grouped);quotes=[t.quote(batch_query(b)) for b in batches];result[name]={'calls':len(batches),'batch_sizes':[len(b) for b in batches],'estimated_usd':round(sum(q['estimated_usd'] for q in quotes),8),'reserve_usd':round(sum(q['reserve_usd'] for q in quotes),8),'requests':[q['request'] for q in quotes]};result[name]['within_budget']=result[name]['reserve_usd']<=policy['presupuesto_total_usd']
 result['estimate_scope']='Offline byte/3 y salida máxima por llamada, no uso real; sin HTTP count_tokens; grupos separados por contrato/anatomía/unidades. Reparaciones pueden añadir llamadas y costo dentro del mismo presupuesto.';return result

def validate_one(recipe,q):
 if recipe.get('status')=='FALTA':raise ValueError('DATOS_FALTANTES: '+str(recipe.get('missing','fuente no entregada')))
 if q.get('task','object_recipe') in ['object_recipe','entity_recipe']:return validar(recipe,q)
 if recipe.get('status') not in ['PROPOSAL','PROPOSAL_OR_FALTA'] or not recipe.get('source') or not isinstance(recipe.get('profile'),dict) or not recipe['profile']:raise ValueError('Perfil anatómico sin estructura/procedencia explícita')
 if recipe.get('certified') and not recipe.get('certification_source'):raise ValueError('Certificación inventada rechazada')
 return {'passed':True,'advisory_only':True,'never_removes_source_data_blocks':True}

def store(root,recipe,q,metrics,mock):
 root=Path(root);path=root/('bibliotecas/anatomias_propuestas.json' if q.get('task')=='anatomy_review' else 'bibliotecas/recetas_aprobadas.json');path.parent.mkdir(parents=True,exist_ok=True)
 with path.with_suffix('.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if cache_get(root,q):return
  data=leer(path) if path.exists() else {'recipes':[]};obj=copy.deepcopy(recipe);obj.update(query_sha256=huella(q),validation=metrics,validated=True,origin='fixture_mock_parallel' if mock else 'argon_parallel',created_at=datetime.now().astimezone().isoformat(),reference_dimensions_m=q.get('dimensions_m'));obj['recipe_sha256']=huella(obj);data['recipes'].append(obj);guardar(path,data)

def ejecutar(root,items,mode='dry',provider=None,fixture_only=False):
 root=Path(root);policy=leer(root/'config/politica_ejecucion.json');transport=Transport(root);ledger=Ledger(root/'evidencia/ledger.json')
 if mode=='mock' and not fixture_only:raise ValueError('Mock sólo en fixture; nunca sustituye receta real')
 if (root/'config/argon_automatico.off').exists() or (root/'config/argon_recetas.off').exists():return {'mode':mode,'state':'OFF','calls':[],'calls_count':0,'saved':[],'faltantes':[],'network_sent':False}
 if mode=='real' and (root/'config/argon_envio.off').exists():return {'mode':mode,'state':'ENVIO_REAL_APAGADO','calls':[],'calls_count':0,'saved':[],'faltantes':[{'id':q['id'],'reason':'ENVIO_REAL_APAGADO'} for q in items]}
 pending=[q for q in items if not cache_get(root,q)];batches=agrupar(pending,transport.cfg,policy);lock=threading.Lock();calls=[];saved=[];faltas=[]
 def worker(batch):
  remaining=batch;seen=set();repair=[]
  while remaining:
   query=batch_query(remaining,repair);quote=transport.quote(query)
   try:ref=ledger.before(quote['reserve_usd'],'argon_automatic_'+mode,mock=mode!='real')
   except ValueError as exc:
    with lock:faltas.extend({'id':q['id'],'reason':'PRESUPUESTO_TOTAL_AGOTADO','producer':'presupuesto_total_usd'} for q in remaining)
    return
   call={'ids':[q['id'] for q in remaining],'repair':bool(repair),'ledger_before':ref,'quote_usd':quote['reserve_usd'],'thread':threading.get_ident(),'network_sent':False}
   with lock:calls.append(call)
   if mode=='dry':ledger.settle(ref,0);call['state']='DRY_RUN_NO_PROVIDER';return
   try:
    response=provider(query,ref) if mode=='mock' else transport(query,ref);actual=response.pop('_usage_usd',0 if mode=='mock' else None)
    if actual is None:raise ValueError('Uso no acreditado; reserva conservada')
    ledger.settle(ref,actual);call['actual_usd']=actual;results=response.get('responses',[]);ids=[x.get('id') for x in results]
    if len(ids)!=len(set(ids)) or any(ident not in call['ids'] for ident in ids):raise ValueError('IDs extra/duplicados en lote')
    by={x['id']:x for x in results};errors=[]
    for q in remaining:
     try:
      answer=by.get(q['id'],{}).get('recipe') or by.get(q['id'],{});metrics=validate_one(answer,q);store(root,answer,q,metrics,mode=='mock')
      with lock:saved.append({'id':q['id'],'validation':metrics})
     except Exception as exc:errors.append({'id':q['id'],'error':str(exc),'producer':q.get('producer','ADN/4a2')})
    if not errors:call['state']='VALIDATED';return
    signature=huella(errors)
    if signature in seen:
     with lock:faltas.extend(errors)
     call['state']='FALTA_REPEATED_NO_PROGRESS';return
    seen.add(signature);repair=errors;remaining=[q for q in remaining if q['id'] in {e['id'] for e in errors}];call['state']='REPAIR_PENDING'
   except Exception as exc:
    # Una falla de red/JSON se reintenta con reparación; uso desconocido conserva reserva.
    if mode=='mock':
     try:ledger.settle(ref,0,failed=True)
     except ValueError:pass
    errors=[{'id':q['id'],'reason':type(exc).__name__,'producer':q.get('producer','motor/Argon')} for q in remaining]
    signature=huella(errors)
    if signature in seen:
     with lock:faltas.extend(errors)
     call['state']='FALTA_REPEATED_NO_PROGRESS';return
    seen.add(signature);repair=errors;call['state']='TRANSPORT_REPAIR_PENDING'
 with ThreadPoolExecutor(max_workers=max(1,policy['max_workers'])) as pool:
  futures=[pool.submit(worker,b) for b in batches]
  for f in as_completed(futures):f.result()
 return {'mode':mode,'calls':calls,'calls_count':len(calls),'saved':saved,'faltantes':faltas,'cache_hits':len(items)-len(pending),'no_call_count_cap':True,'production_approved':False}


def aplicar_cache_entorno(root,d,items):
 pending=d.get('environment',{}).get('unresolved_details',[]);by={q['id']:q for q in items};applied=[];remaining=[]
 for record in pending:
  q=by.get(record['id']);recipe=cache_get(root,q) if q else None
  if not recipe:remaining.append(record);continue
  if recipe.get('origin','').startswith('fixture_mock') and not d.get('fixture_only'):raise ValueError('No activar receta de mock en escena real')
  inv=q.get('source',{}).get('inventory',{})
  if inv.get('parent') or not all(k in inv for k in ['position_m','rotation_euler_rad']):remaining.append(record);continue
  parts=copy.deepcopy(recipe['parts'])
  for part in parts:part['id']=record['id']+'.'+part['id']
  d.setdefault('props',[]).append({'id':record['id'],'position_m':inv['position_m'],'rotation_deg':[math.degrees(v) for v in inv['rotation_euler_rad']],'geometry':parts,'points':[],'source':q['source'],'replace_legacy_geometry':True,'shape_provenance':{'step':4,'recipe_sha256':recipe['recipe_sha256']}});applied.append(record['id'])
 d['environment']['unresolved_details']=remaining;return {'applied':applied,'remaining':len(remaining)}
