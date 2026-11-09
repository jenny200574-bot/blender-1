"""Programa 01 estructurado→eventos de presencia. No inventa vuelos ni FX.
Fuente de verdad: acciones 01 (aparecer/desaparecer) con onset en t[0].
Pistas hide_render previas (p. ej. plantillas Argon/live en environment.events)
se sustituyen si cubren el mismo objeto o action_id; el guard CONFLICTO sigue activo
si quedan dos escritores distintos.
"""
def _inicio_accion(action):
    t=action.get('t')
    if not isinstance(t,list) or len(t)<1:raise ValueError('accion sin intervalo t[0]')
    return float(t[0])

def _claves_presencia(accion, inicio_s):
    aparecer=accion=='aparecer'
  # hide_render: True=oculto. Antes del onset: oculto si aparecer, visible si desaparecer.
    if inicio_s>0:keys=[{'t':0,'value':aparecer,'curve':'CONSTANT'}]
    else:keys=[]
    keys.append({'t':inicio_s,'value':not aparecer,'curve':'CONSTANT'})
    return keys

def _mapa_presencia_01(d):
    by_action={};by_object={}
    for action in d.get('actions',[]) or []:
        if action.get('accion') not in ['aparecer','desaparecer']:continue
        target=action.get('objeto') or action.get('actor')
        if not target:continue
        binding=d.get('bindings',{}).get(target,{})
        target=binding.get('scene_object_id',target)
        by_action[action['id']]=(target,action)
        by_object.setdefault(target,[]).append(action['id'])
    return by_action,by_object

def _presencia_sustituye_pista(event,by_action,by_object):
    """True si la pista legacy hide_render la reemplaza 01 para el mismo actor/objeto."""
    if event.get('property')!='hide_render':return False
    aids=set(event.get('action_ids') or [])
    if event.get('action_id'):aids.add(event['action_id'])
    if aids&by_action.keys():return True
    obj=event.get('object')
    if obj not in by_object:return False
    if aids and not (aids&set(by_object[obj])):return False
  # mismo objeto con aparecer/desaparecer en 01: plantilla Argon/vivo (t[1]) es obsoleta
    return True

def compilar_presencia(d):
    environment=d['environment'];events=environment.setdefault('events',[]) if d.get('actions') is not None else environment.get('events',[])
    by_action,by_object=_mapa_presencia_01(d)
    sustituidos=[e for e in events if _presencia_sustituye_pista(e,by_action,by_object)]
    events[:]=[e for e in events if e not in sustituidos and not e.get('compiled_presence')]
    if sustituidos:environment['presence_superseded']=[{'object':e.get('object'),'property':e.get('property'),'action_id':e.get('action_id'),'action_ids':e.get('action_ids'),'source':e.get('source')} for e in sustituidos]
    receipts=[]
    for action in d.get('actions',[]):
        if action.get('accion') not in ['aparecer','desaparecer']:continue
        target=action.get('objeto') or action.get('actor')
        if not target:continue
        binding=d.get('bindings',{}).get(target,{});target=binding.get('scene_object_id',target);inicio_s=_inicio_accion(action);keys=_claves_presencia(action['accion'],inicio_s)
        event={'object':target,'property':'hide_render','recursive':True,'keys':keys,'action_id':action['id'],'source':{'module':'01','action_id':action['id'],'field':'accion/t/actor/objeto','time_policy':'onset en t[0] del intervalo de acción (inicio explícito 01); t[1] no es frame de aparición'}}
        # No admitir dos escritores si un mismo objeto aparece varias veces: unir su pista.
        prior=next((e for e in events if e['object']==target and e['property']=='hide_render' and e.get('compiled_presence')),None)
        if prior is not None:
            prior['keys']=[k for k in prior['keys'] if k['t']!=inicio_s]+keys[-1:];prior['keys'].sort(key=lambda k:k['t'])
            if inicio_s>0 and not any(k['t']==0 for k in prior['keys']):prior['keys'].insert(0,keys[0])
            prior.setdefault('action_ids',[prior['action_id']]).append(action['id'])
        else:event['compiled_presence']=True;event['action_ids']=[action['id']];events.append(event)
        receipts.append({'action_id':action['id'],'target':target,'onset_s':inicio_s,'fin_accion_s':float(action['t'][1]) if isinstance(action.get('t'),list) and len(action['t'])>1 else None,'kind':'presence_only','source_motion_or_fx_not_fabricated':True})
    anterior=environment.get('presence_compilation')
    if receipts:environment['presence_compilation']=receipts
    if anterior==receipts:return []
    return receipts
