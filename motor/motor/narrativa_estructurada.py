"""Programa 01 estructurado→eventos de presencia. No inventa vuelos ni FX.
La aparición fija hide_render en t[0] del guion (no en t[1]); el intervalo t[1]
acota la acción narrativa pero no retrasa la visibilidad de aparecer.
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

def compilar_presencia(d):
    environment=d['environment'];events=environment.setdefault('events',[]) if d.get('actions') is not None else environment.get('events',[])
    events[:]=[e for e in events if not e.get('compiled_presence')]
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
