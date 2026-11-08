"""Emisores independientes y estados por toma→reloj global. Ceros son valores.
El formato histórico por_toma se interpreta sólo mediante un mapa declarado.
Nunca impone dependencias entre lámparas, canales ni mínimos artísticos.
"""
from seguridad import error

def compilar(profile,shots):
    errors=[];events=[];ids=[s['id'] for s in shots];byid={s['id']:s for s in shots}
    def fail(field,msg):errors.append(error(field,'4a2/escenario vivo + perfil de iluminación',msg,'LUZ_DATO_FALTANTE'))
    emitters=profile.get('emitters',[]);eid=[e.get('id') for e in emitters]
    if len(eid)!=len(set(eid)):fail('lighting/emitters','IDs de emisor repetidos');return [],errors
    states={e['id']:dict(e.get('states_by_shot',{})) for e in emitters}
    legacy=profile.get('legacy_states')
    if legacy is not None:
        mapping=profile.get('legacy_channels',{});bindings=profile.get('legacy_shot_ids',{})
        for source_shot,channels in legacy.get('por_toma',{}).items():
            target=bindings.get(str(source_shot))
            if target not in byid:fail('lighting/legacy_shot_ids/'+str(source_shot),'Falta correspondencia explícita con ID del SB');continue
            for channel,factor in channels.items():
                if channel not in mapping:fail('lighting/legacy_channels/'+channel,'Falta lista de emisores del canal; no se infiere por nombres');continue
                for emitter in mapping[channel]:
                    if emitter not in states:fail('lighting/emitters/'+emitter,'Canal apunta a emisor no declarado');continue
                    if target in states[emitter]:fail('lighting/emitters/'+emitter,'Estado duplicado normalizado/histórico para '+target);continue
                    states[emitter][target]={'factor':factor,'curve':'CONSTANT','intentional_blackout':factor==0,'source':profile.get('source')}
    for emitter in emitters:
        keys=[]
        for shot in shots:
            state=states[emitter['id']].get(shot['id'])
            if state is None:fail('lighting/'+emitter['id']+'/'+shot['id'],'Falta estado de emisor para la toma');continue
            factor=state.get('factor');curve=state.get('curve')
            if not isinstance(factor,(int,float)) or isinstance(factor,bool) or not 0<=factor<=1:fail('lighting/'+emitter['id'],'Factor fuera de [0,1]');continue
            if curve not in ['CONSTANT','LINEAR','SMOOTH']:fail('lighting/'+emitter['id'],'Falta curva explícita');continue
            if state.get('intentional_blackout'):
                curve='CONSTANT'
                if keys:keys[-1]['curve']='CONSTANT'
            keys.append({'t':shot['t0'],'value':factor,'curve':curve})
        for target in emitter.get('targets',[]):
            prop=target['property'];base=target['base_value'];converted=[]
            for k in keys:
                value=[v*k['value'] for v in base] if isinstance(base,list) else base*k['value']
                converted.append(dict(k,value=value))
            events.append({'object':target['object'],'property':prop,'keys':converted,'source':emitter.get('source',profile.get('source')),'material':target.get('material'),'emitter_id':emitter['id']})
        if not emitter.get('targets'):fail('lighting/'+emitter['id']+'/targets','Emisor sin binding de luz/emisión/World')
    return events,errors
