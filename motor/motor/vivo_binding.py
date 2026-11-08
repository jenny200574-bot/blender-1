"""Estados/changes 4a/4a4→propiedades y reloj global, IDs exactos; no adivina submallas."""
import copy,math
from seguridad import error,numero
from eventos import validar_eventos,PROPIEDADES

def compilar(d):
 env=d['environment'];live=env.get('live_data') or {};tracks=copy.deepcopy(env.get('events',[]));errors=[];compiled=[];actions={a['id']:a for a in d.get('actions',[])};bindings=d.get('bindings',{})
 for i,row in enumerate(live.get('changes',[])):
  if not isinstance(row,dict):errors.append(error('environment/changes/'+str(i),'4a/4a4','Cambio no estructurado'));continue
  obj=row.get('object',row.get('objeto'));prop=row.get('property',row.get('propiedad'));source=row.get('source') or live.get('source');target=row.get('target_piece') or (bindings.get(obj) or {}).get('scene_object_id') or obj
  if not target or not prop:errors.append(error('environment/changes/'+str(i),'4a2 + 4a4','Falta objeto/pieza y propiedad explícita; no cambiar el objeto entero si la frase habla de una página'));continue
  keys=copy.deepcopy(row.get('keys'));action=actions.get(row.get('action_id'))
  if keys is None:
   interval=row.get('t') or (action.get('t') if action else None)
   if not isinstance(interval,list) or len(interval)!=2 or 'from' not in row or 'to' not in row or 'curve' not in row:errors.append(error('environment/changes/'+str(i),'01 + 4a4','Faltan intervalo, extremos o curva; 01 aporta el intervalo por action_id'));continue
   keys=[{'t':interval[0],'value':row['from'],'curve':row['curve']},{'t':interval[1],'value':row['to'],'curve':row['curve']}]
  if row.get('units')=='deg':
   for key in keys:key['value']=[math.radians(x) for x in key['value']] if isinstance(key['value'],list) else math.radians(key['value'])
  event={'object':target,'property':prop,'keys':keys,'source':source}
  for key in ['material','action_id','recursive']:
   if key in row:event[key]=row[key]
  if event not in tracks:tracks.append(event)
  compiled.append(event)
 state=live.get('state_for_scene') or {};required=list(dict.fromkeys(state.get('inicio',[])+state.get('fin',[])));bindings_state=live.get('state_bindings') or {};assertions=live.get('expected_states',[]);assertion_ids={a.get('id') for a in assertions};unbound=[text for text in required if not bindings_state.get(text) or not set(bindings_state[text])<=assertion_ids]
 if live.get('status')!='complete' or unbound:errors.append(error('environment/live_source','4a4 + 01 + 4a2','Sólo llegaron estados narrativos inicio/fin; faltan subpiezas/materiales/valores/curvas para cambios de letras, color y FX. Los tiempos explícitos de 01 se reutilizan; no se piden otra vez.','VIVO_DATOS_FALTANTES',causa='escenario_vivo'))
 for item in assertions:
  if not isinstance(item,dict):errors.append(error('environment/expected_states','4a4','Aserción de estado no estructurada'));continue
  if item.get('property') not in PROPIEDADES:errors.append(error('environment/expected_states','motor/vivo binding','Propiedad de estado sin ejecutor','CAPACIDAD_PENDIENTE',tipo='crear capacidad'))
  if not all(k in item for k in ['id','object','property','t','value','tolerance','source']) or not numero(item.get('t')) or not 0<=item['t']<=d['clock']['duration_s'] or not numero(item.get('tolerance')) or item['tolerance']<0:errors.append(error('environment/expected_states','4a4 + 01','Aserción de estado sin propiedad/valor/tiempo/tolerancia/procedencia explícitos'))
 env['expected_states']=assertions
 errors+=validar_eventos(tracks,d['clock']['duration_s']);env['events']=tracks;env['_vivo_bridge']={'state':'WAITING_DATA' if errors else 'READY','changes_compiled':len(compiled),'source_status':live.get('status'),'unbound_states':unbound,'assertions':len(assertions)}
 return env['_vivo_bridge'],errors
