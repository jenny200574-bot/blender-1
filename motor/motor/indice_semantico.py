"""Puente real asignación→solicitud→índice. No vuelve a escribir al solver bueno.
Una asignación es procedencia, NO aprobación ni licencia del movimiento.
"""
from seguridad import leer,ruta,sha,error
CONDICIONES=('action','anatomy','emotion','load','support','context')
def compilar(d,pk):
    m=d['motion']
    if 'requests' in m:return {'state':'explicit','requests':len(m['requests'])},[]
    catalog=leer(ruta(pk,m['catalog']));rows=leer(ruta(pk,m['assignments']));entities={e['id']:e for e in d['entities']};actions={a['id']:a for a in d.get('actions',[])};requests=[];candidates=[];missing=[]
    for i,row in enumerate(rows):
        ent=entities.get(row.get('personaje'));mid=row.get('movimiento');movement=catalog.get('movimientos',{}).get(mid)
        if ent is None or movement is None:missing.append({'row':i,'field':'personaje/movimiento','producer':'2B','message':'Asignación apunta fuera de entidad o catálogo'});continue
        action=actions.get(row.get('accion_plan'));support=[{'pose':f.get('pose'),'end_fraction':f.get('t_fin_frac'),'points':f.get('apoyos'),'anchor':f.get('anclar_apoyo')} for f in movement.get('fases',[])]
        semantics={'action':action.get('accion') if action else row.get('_source_kind'),'anatomy':ent['anatomy'],'emotion':action.get('emocion') if action else None,'load':action.get('objeto') if action else None,'support':support,'context':{'action_ref':row.get('accion_plan'),'pose':action.get('pose') if action else None,'layer':row.get('capa')}}
        req=dict(semantics,id='request_'+str(i),entity=ent['id'],t0=row['t0'],t1=row['t1'],execution='legacy_kernel',source={'path':m['assignments'],'sha256':sha(ruta(pk,m['assignments'])),'row':i});requests.append(req)
        poses={f['pose']:catalog['poses'].get(f['pose']) for f in movement.get('fases',[])};missing_poses=[k for k,v in poses.items() if v is None]
        if missing_poses:missing.append({'row':i,'field':'poses','producer':'2B/catalogo','missing':missing_poses})
        candidates.append(dict(semantics,id='candidate_'+str(i),entity=ent['id'],provider='catalogo',execution='legacy_kernel',request_id=req['id'],movement_id=mid,movement=movement,poses=poses,assignment=row,approval_ref=movement.get('approval_ref'),license_ref=movement.get('license_ref'),validated=movement.get('validado') is True,source={'path':m['catalog'],'sha256':sha(ruta(pk,m['catalog']))}))
    m['requests']=requests;m['candidates']=candidates;m['semantic_index']={'schema':'exact_conditions_v1','providers':['argon','catalogo','kimodo','cmu'],'library_refs':d.get('libraries',[]),'entries':[{'request':q['id'],'entity':q['entity'],'candidate_ids':[c['id'] for c in candidates if all(c[k]==q[k] for k in CONDICIONES) and c['entity']==q['entity']]} for q in requests],'missing':missing,'source':'asignaciones reales; se preserva el orden/capas/objetivos del núcleo'}
    # Lista explícita, nunca inventar una licencia o promocionar validado:false.
    unverified=[c['movement_id'] for c in candidates if not c['validated'] or not c['approval_ref']]
    no_license=sorted({c['movement_id'] for c in candidates if not c['license_ref']})
    if no_license:d.setdefault('warnings',[]).append({'codigo':'LICENCIA_INFORMATIVA','severidad':'AVISO','campo':'motion/semantic_index/license','modulo':'biblioteca de movimientos','mensaje':'Uso personal t291: licencia no bloquea; validación técnica sigue obligatoria','movement_ids':no_license})
    errors=[]
    if missing:errors.append(error('motion/semantic_index/source','2B/Argon + catálogo','Índice construido; faltan referencias reales: '+str(missing),'INDICE_DATO_FALTANTE'))
    if unverified:errors.append(error('motion/semantic_index/approval','2B/Argon + biblioteca de movimientos','Faltan validación/aprobación técnica comprobables de movimientos: '+', '.join(sorted(set(unverified))),'BIBLIOTECA_SIN_VALIDAR',movement_ids=sorted(set(unverified))))
    return {'state':'compiled','requests':len(requests),'candidates':len(candidates),'actual_assignments':len(rows),'unverified_movement_ids':sorted(set(unverified))},errors
