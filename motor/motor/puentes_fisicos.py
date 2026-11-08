"""01/2B/Star→contactos y reglas comunes. Ni defaults físicos ni contactos vacíos por truncamiento."""
import copy
from seguridad import error,leer,ruta,numero,exigir,sha
RULES={'bone_length_error_m','root_speed_max_m_s','root_accel_max_m_s2','com_accel_max_m_s2','slip_max_m_per_frame','joint_speed_max_deg_s','penetration_tolerance_m','reject_surface_intersections','colliders','allowed_collision_pairs'}
MAP={'error_largo_hueso_max_m':'bone_length_error_m','velocidad_raiz_max_m_s':'root_speed_max_m_s','aceleracion_raiz_max_m_s2':'root_accel_max_m_s2','aceleracion_com_max_m_s2':'com_accel_max_m_s2','vel_articular_max_deg_s':'joint_speed_max_deg_s','penetracion_max_m':'penetration_tolerance_m','rechazar_interseccion_superficies':'reject_surface_intersections','colisionadores':'colliders','pares_colision_permitidos':'allowed_collision_pairs'}

def reglas(source,manifest=None):
    if not isinstance(source,dict):return None,[error('rules/source_parameters','biblioteca de reglas vigentes','Reglas fuente deben ser objeto estructurado')]
    source=copy.deepcopy(source);out={};errors=[]
    for key,value in source.items():
        target=MAP.get(key,key)
        if target in RULES or target in {'contact_pairs'}:
            if target in out and out[target]!=value:errors.append(error('rules/'+target,'biblioteca de reglas vigentes','Dos nombres de regla aportan valores contradictorios','CONFLICTO',tipo='conflicto'))
            out[target]=value
    if 'resbale_max_cm_cuadro' in source:
        if not numero(source['resbale_max_cm_cuadro']):return None,[error('rules/resbale_max_cm_cuadro','biblioteca de reglas vigentes','Resbale debe ser número finito, no texto')]
        value=source['resbale_max_cm_cuadro']/100
        if 'slip_max_m_per_frame' in out and value!=out['slip_max_m_per_frame']:errors.append(error('rules/slip_max_m_per_frame','biblioteca de reglas vigentes','Resbale en cm y m contradictorio','CONFLICTO',tipo='conflicto'))
        out['slip_max_m_per_frame']=value
    if 'colliders' not in out and manifest is not None:
        objects=manifest.get('objects') if isinstance(manifest,dict) else None
        if isinstance(manifest,dict) and manifest.get('complete') is True and isinstance(objects,list) and all(isinstance(o,dict) and isinstance(o.get('id'),str) and o['id'] and isinstance(o.get('collider'),bool) for o in objects):out['colliders']=[o['id'] for o in objects if o['collider']]
        else:errors.append(error('environment/spatial_manifest/collider','4a2/manifiesto espacial','Inventario medido no declara qué piezas son colliders; no tomar marcadores/decorados por colisionadores'))
    missing=sorted(RULES-set(out))
    if missing:errors.append(error('rules/source_parameters','biblioteca de reglas vigentes + 4a2/manifiesto','No están en la fuente estos parámetros: '+', '.join(missing),'REGLAS_DATOS_FALTANTES',dato_esperado=missing))
    for key,value in out.items():
        if key.endswith(('_m','_m_s','_m_s2','_deg_s','_per_frame')) and (not numero(value) or value<0):errors.append(error('rules/'+key,'biblioteca de reglas vigentes','Límite debe ser finito, no negativo y con unidades explícitas'))
    if 'reject_surface_intersections' in out and not isinstance(out['reject_surface_intersections'],bool):errors.append(error('rules/reject_surface_intersections','biblioteca de reglas vigentes','Se exige booleano explícito'))
    if 'colliders' in out and (not isinstance(out['colliders'],list) or any(not isinstance(v,str) or not v for v in out['colliders'])):errors.append(error('rules/colliders','4a2/manifiesto espacial','IDs de colliders deben ser lista explícita'))
    if 'allowed_collision_pairs' in out and (not isinstance(out['allowed_collision_pairs'],list) or any(not isinstance(v,list) or len(v)!=2 or any(not isinstance(x,str) or not x for x in v) for v in out['allowed_collision_pairs'])):errors.append(error('rules/allowed_collision_pairs','biblioteca de reglas vigentes','Pares permitidos deben aportar dos IDs por entrada'))
    return (out if not errors else None),errors

def contactos(source,duration):
    result=[];errors=[]
    if not isinstance(source,list):return None,[error('motion/contacts','01/2B + Star','Falta lista completa explícita de contactos/anclas; no convertir ausencia/truncamiento en lista vacía','CONTACTOS_DATOS_FALTANTES')]
    if not numero(duration) or duration<=0:return None,[error('clock/duration_s','01/SB','Duración de escena no válida para contactos')]
    for i,item in enumerate(source):
        if not isinstance(item,dict):errors.append(error('contacts/'+str(i),'01/2B/Star','Contacto no estructurado'));continue
        if all(k in item for k in ['entity','bone','target_point','chain_length','iterations','t0','t1','tolerance_m']):c=copy.deepcopy(item)
        elif all(k in item for k in ['actor','hueso','objetivo_punto','cadena','iteraciones','t','tolerancia_m']) and isinstance(item['t'],list) and len(item['t'])==2:c={'entity':item['actor'],'bone':item['hueso'],'target_point':item['objetivo_punto'],'chain_length':item['cadena'],'iterations':item['iteraciones'],'t0':item['t'][0],'t1':item['t'][1],'tolerance_m':item['tolerancia_m'],'source':item.get('source','01/2B/Star')}
        else:errors.append(error('contacts/'+str(i),'01/2B/Star','Falta efector/target inequívoco, intervalo, cadena/iteraciones o tolerancia; no escoger mano por nombre'));continue
        if any(not isinstance(c[k],str) or not c[k] for k in ['entity','bone','target_point']):errors.append(error('contacts/'+str(i),'01/2B/Star','Actor/hueso/punto deben ser IDs explícitos no vacíos'));continue
        if not (numero(c['t0']) and numero(c['t1']) and 0<=c['t0']<c['t1']<=duration) or not numero(c['tolerance_m']) or c['tolerance_m']<=0 or any(isinstance(c[k],bool) or not isinstance(c[k],int) or c[k]<1 for k in ['chain_length','iterations']):errors.append(error('contacts/'+str(i),'01/2B/Star','Intervalo o parámetros de contacto inválidos'));continue
        result.append(c)
    return (result if not errors else None),errors

def compilar(d,root,prueba_cpu=False):
    needs='contacts' not in d or not d.get('rules')
    if needs and not prueba_cpu:exigir('puentes_fisicos')
    errors=[];receipt={};status=d.setdefault('_physical_bridge_status',{})
    if 'contacts' not in d:
        m=d.get('motion') or {};candidate=m.get('program') or ('programa_2b.json' if (root/'programa_2b.json').is_file() else None);program={}
        if candidate:
            try:
                asset=next((a for a in d.get('assets',[]) if a.get('path')==candidate),None)
                if not asset or sha(ruta(root,candidate))!=asset.get('sha256'):raise ValueError('Programa no cubierto por hash del paquete')
                program=leer(ruta(root,candidate))
            except (ValueError,OSError):errors.append(error('motion/program','01/2B + manifiesto del paquete','Programa no legible/íntegro o no cubierto por SHA-256; no consumir un archivo suelto','FUENTE_NO_VERIFICADA'))
        if not isinstance(program,dict):program={}
        source=program.get('contacts',program.get('contactos'))
        if program.get('status') not in (None,'complete') and program.get('contacts_complete') is not True:source=None
        # anclas=[] de respuesta recuperada/truncada NO acredita ausencia de contactos.
        # physics_validated=true escrito por el modelo tampoco autoriza anclas ni aprueba la física.
        if source is None and program.get('status')=='complete' and program.get('physics_validated') is True:
            errors.append(error('motion/program/physics_validated','revisor_propuesta_fisica','physics_validated=true del programa no autoriza anclas ni aprueba la física','MODELO_NO_APRUEBA',tipo='rechazo'))
        result,e=contactos(source,d['clock']['duration_s']);errors+=e
        if result is not None:d['contacts']=result
        status['contacts']='READY' if result is not None else 'WAITING_PRODUCER';receipt['contacts']={'state':status['contacts'],'count':len(result) if result is not None else None}
    had_rules=bool(d.get('rules'));proposal_block=False
    if 'argon_physics_proposal' in d:
        from revisor_propuesta_fisica import aplicar
        rev,rev_err=aplicar(d,d['argon_physics_proposal'],d.get('inventario_fisico'),prueba_cpu=prueba_cpu);errors+=rev_err
        receipt['revisor_propuesta_fisica']={'estado':rev['estado'],'approved':False,'production_approved':False,'scene_physics_approved':False,'physics_validated':False,'faltantes':rev['faltantes']}
        if rev['estado']!='PROPUESTA_EN_LIMITE':proposal_block=True
    if not d.get('rules') and not proposal_block:
        source=d.get('rules_source') or (d.get('legacy') or {}).get('rules') or {};env=d.get('environment') or {};manifest=env.get('spatial_manifest') if isinstance(env,dict) else None;result,e=reglas(source,manifest);errors+=e
        if result is not None:d['rules']=result
        status['rules']='READY' if result is not None else 'WAITING_PRODUCER';receipt['rules']={'state':status['rules'],'source_parameters_preserved':True}
    elif not had_rules and d.get('rules'):
        status['rules']='READY';receipt['rules']={'state':'READY','source_parameters_preserved':True,'origen':'revisor_propuesta_fisica'}
    elif proposal_block and not d.get('rules'):
        status['rules']='WAITING_PRODUCER';receipt['rules']={'state':'WAITING_PRODUCER','source_parameters_preserved':True}
    return receipt,errors
