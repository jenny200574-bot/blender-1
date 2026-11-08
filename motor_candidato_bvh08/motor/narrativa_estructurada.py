"""Programa 01 estructurado→eventos de presencia. No inventa vuelos ni FX.
La aparición fija visibilidad en el inicio explícito de su intervalo; el estado
narrativo restante se conserva pendiente hasta contar con todos sus ejecutores.
"""
def compilar_presencia(d):
    environment=d['environment'];events=environment.setdefault('events',[]) if d.get('actions') is not None else environment.get('events',[]);known={a for e in events for a in ([e.get('action_id')]+e.get('action_ids',[]))};receipts=[]
    for action in d.get('actions',[]):
        if action.get('accion') not in ['aparecer','desaparecer'] or action['id'] in known:continue
        target=action.get('objeto') or action.get('actor')
        if not target:continue
        binding=d.get('bindings',{}).get(target,{});target=binding.get('scene_object_id',target);time=action['t'][0];visible=action['accion']=='aparecer';keys=[]
        if time>0:keys.append({'t':0,'value':visible,'curve':'CONSTANT'})
        keys.append({'t':time,'value':not visible,'curve':'CONSTANT'});event={'object':target,'property':'hide_render','recursive':True,'keys':keys,'action_id':action['id'],'source':{'module':'01','action_id':action['id'],'field':'accion/t/actor/objeto','time_policy':'inicio explícito del intervalo de acción, no amplitud o trayectoria inventadas'}}
        # No admitir dos escritores si un mismo objeto aparece varias veces: unir su pista.
        prior=next((e for e in events if e['object']==target and e['property']=='hide_render' and e.get('compiled_presence')),None)
        if prior is not None:
            prior['keys']=[k for k in prior['keys'] if k['t']!=time]+[keys[-1]];prior['keys'].sort(key=lambda k:k['t']);prior.setdefault('action_ids',[prior['action_id']]).append(action['id'])
        else:event['compiled_presence']=True;event['action_ids']=[action['id']];events.append(event)
        known.add(action['id'])
        receipts.append({'action_id':action['id'],'target':target,'onset_s':time,'kind':'presence_only','source_motion_or_fx_not_fabricated':True})
    if receipts:environment['presence_compilation']=receipts
    return receipts
