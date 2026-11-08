"""16 manejadores reales accesibles sólo desde entrada_escena.json.
La compuerta no confunde backend genérico con traductor de ADN ya terminado.
Las capacidades no resueltas permanecen A, no se convierten en pedidos de datos B.
"""
from pathlib import Path
import sys,subprocess,shutil,datetime,os
from seguridad import *
from contrato import cargar,validar
from movimientos import verificar_programa
from auditar_sb import auditar
from apariencia_3d import validar_adn
from geometria import validar_rig
from dialogos import compilar
from montaje_cpu import planificar,ejecutar as montar
ROOT=Path(__file__).resolve().parents[1]
NAMES=['Fuentes y gasto','Argon/cache íntegra','Preparar y puentes','Contrato y capacidades','ADN/apariencia','Escenario base y vivo','Objetos y puntos Star','Esqueletos y restricciones','Escalera de movimientos','Retarget, pulida y contactos','Cámara SB/4g','Luz global','Revisión vinculante','Empaquetado del mismo worker (CPU; GPU fuera de alcance)','Render por tomas','Montaje y salida']

def grupo(e):
    if e.get('tipo')=='crear capacidad' or e['codigo'] in {'CAPACIDAD_PENDIENTE','ANATOMIA_NO_SOPORTADA','ACCION_SIN_EJECUCION'}:return 'A'
    if e['campo']=='environment/live_data' and not e.get('capability_bound'):return 'A'
    if e['codigo']=='PROVISIONAL' and e.get('modulo')=='ADN/ancla':return 'A'
    if e['codigo']=='PROVISIONAL' and e['campo'] in {'apariencia','adn_entities','changes/object,time,property,value'}:return 'A'
    return 'B'

def ejecutar(entrada,salida,prueba_cpu=False,blender=None,solo_validar=False):
    # Software rasterizer only: no physical GPU for EEVEE CPU.
    os.environ.update(LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',MESA_LOADER_DRIVER_OVERRIDE='llvmpipe',EGL_PLATFORM='surfaceless')
    pk=Path(entrada).resolve().parent;source_pk=pk;out=Path(salida).resolve();out.mkdir(parents=True,exist_ok=True);d,errors=cargar(pk);stages=[];artifacts={};runtime=blender or shutil.which('blender');worker_ok=False
    def add(field,module,msg,code='DATO_FALTANTE',kind='completar dato',**kw):errors.append(error(field,module,msg,code,tipo=kind,**kw))
    def stage(n,handler):
        initial=len(errors)
        try:data=handler()
        except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.SubprocessError) as exc:
            add('stages/'+str(n),'motor/orquestador',str(exc),'ETAPA_FALLIDA','crear capacidad');data={'error':str(exc)}
        record={'n':n,'nombre':NAMES[n-1],'handler':handler.__name__,'estado':'BLOQUEADA' if len(errors)>initial else 'EJECUTADA','artefacto':data,'aprobada_produccion':False};stages.append(record);guardar(out/'etapas.json',stages);return data
    if not d:
        guardar(out/'resultado.json',{'estado':'BLOQUEADO','errores':errors,'etapas':[],'gasto_usd':0});return leer(out/'resultado.json')
    fps=(d.get('clock') or {}).get('fps');dur=(d.get('clock') or {}).get('duration_s');valid_clock=numero(fps) and numero(dur) and fps>0 and dur>0
    def fuentes():
        if not prueba_cpu and ((ROOT/'motor_unico.off').exists() or (ROOT/'config/integracion_final.off').exists()):add('execution','interruptor','Versión apagada; no producción','APAGADO')
        audit=[]
        for a in d.get('assets',[]):
            p=ruta(pk,a['path']);ok=p.is_file() and sha(p)==a['sha256'] and p.stat().st_size==a['bytes'];audit.append({'path':a['path'],'ok':ok})
            if not ok:add('assets/'+a['path'],'empaquetador','Archivo ausente/hash diferente','HASH_DISTINTO')
        guardar(out/'fuentes.json',{'files':audit,'spend_usd':0,'gpu':False,'network_paid':False,'box_copy_only':True});return {'checked':len(audit),'spend_usd':0}
    stage(1,fuentes)
    def argon():
        e=verificar_programa(pk,d,comprobar_acciones=False);errors.extend(e);return {'new_calls':0,'cache_checked':True,'errors':len(e)}
    stage(2,argon)
    def puentes():
        nonlocal pk,d
        from adn_inspeccion import enriquecer
        from perfiles_puente import adaptar
        d=adaptar(enriquecer(d))
        legacy_render=(d.get('legacy') or {}).get('render') or {}
        if not d.get('render') and all(k in legacy_render for k in ['width','height','samples']):
            preset=leer(ROOT/'config/preset_cpu.json');d['render']={'engine':preset['engine'],'seed':preset['seed'],'resolution':[legacy_render['width'],legacy_render['height']],'samples':legacy_render['samples'],'source':{'values':'legacy/render','technical_preset_sha256':sha(ROOT/'config/preset_cpu.json')}}
        from puentes_fisicos import compilar as compilar_fisicos
        physical_receipt,physical_errors=compilar_fisicos(d,pk,prueba_cpu=prueba_cpu);errors.extend(physical_errors);guardar(out/'puentes_fisicos.json',{'receipt':physical_receipt,'errors':physical_errors})
        if not prueba_cpu:exigir('no_facial')
        from anatomia_perfiles import compilar as compilar_anatomia
        anatomical_receipts,anatomical_errors=compilar_anatomia(d);errors.extend(anatomical_errors);guardar(out/'anatomia_perfiles.json',{'receipts':anatomical_receipts,'errors':anatomical_errors})
        if anatomical_errors and (ROOT/'config/argon_transporte.json').exists() and not leer(ROOT/'config/politica_ejecucion.json')['argon_automatico']:
            from argon_transporte import Transport
            transport=Transport(ROOT);plans=[]
            if transport.cfg.get('dry_run',True):
                for ent in d['entities']:
                    missing=[er for er in anatomical_errors if er['campo'].startswith('entities/'+ent['id']+'/')]
                    if missing:
                        query={'task':'anatomy_review','id':ent['id'],'anatomy':ent.get('anatomy'),'dna_record':ent.get('dna_record'),'missing':missing,'actions':[a for a in d.get('actions',[]) if a.get('actor')==ent['id']],'source':'ADN y programa de entrada; faltantes NO se certifican por inferencia'}
                        plans.append(transport.prepare(query))
            guardar(out/'argon_anatomia_seco.json',{'plans':plans,'advisory_only':True,'does_not_remove_missing_source_data':True})
        from perfiles_catalogo import compilar as compilar_perfiles_catalogo
        profile_receipts,profile_errors=compilar_perfiles_catalogo(d,ROOT);errors.extend(profile_errors);guardar(out/'perfiles_catalogo.json',{'receipts':profile_receipts,'errors':profile_errors})
        from reglas_binding import compilar as compilar_reglas
        rule_receipt,rule_errors=compilar_reglas(d);errors.extend(rule_errors);guardar(out/'reglas_binding.json',{'receipt':rule_receipt,'errors':rule_errors})
        from objetos_adn import compilar as compilar_objetos
        from recetas_proveedor import contexto as contexto_recetas
        recipe_runtime=contexto_recetas(ROOT,d,pk)
        automatic_enabled=leer(ROOT/'config/politica_ejecucion.json')['argon_automatico'] and not d.get('fixture_only',False) and not solo_validar
        recipe_runtime.defer_automatic=automatic_enabled or solo_validar
        object_receipt,object_errors=compilar_objetos(d,pk,leer(ROOT/'bibliotecas/formulas_star_estrictas.json'),leer(ROOT/'bibliotecas/politica_busqueda_formas_cpu.json'),runtime=recipe_runtime);errors.extend(object_errors);guardar(out/'objetos_adn.json',{'receipt':object_receipt,'errors':object_errors})
        if automatic_enabled:
            from argon_automatico import descubrir,planificar,aplicar_cache_entorno,ejecutar as generar_automatico
            discovery=descubrir(d,pk,object_errors,anatomical_errors)
            guardar(out/'argon_descubrimiento.json',discovery)
            guardar(out/'argon_plan_automatico.json',planificar(ROOT,discovery['items']))
            mode='dry' if leer(ROOT/'config/argon_transporte.json').get('dry_run',True) else 'real'
            generated=generar_automatico(ROOT,discovery['items'],mode=mode)
            guardar(out/'argon_ejecucion_automatica.json',generated)
            if mode=='real' and generated['saved']:
                errors[:]=[er for er in errors if er not in object_errors]
                recipe_runtime.defer_automatic=False
                object_receipt,object_errors=compilar_objetos(d,pk,leer(ROOT/'bibliotecas/formulas_star_estrictas.json'),leer(ROOT/'bibliotecas/politica_busqueda_formas_cpu.json'),runtime=recipe_runtime)
                errors.extend(object_errors)
            guardar(out/'argon_cache_entorno.json',aplicar_cache_entorno(ROOT,d,discovery['items']))
        from vivo_binding import compilar as compilar_vivo
        vivo_receipt,vivo_errors=compilar_vivo(d);errors.extend(vivo_errors);guardar(out/'vivo_binding.json',{'receipt':vivo_receipt,'errors':vivo_errors})
        notes=d.get('provisional',[]);d['provisional']=[note for note in notes if note.get('campo')!='changes/object,time,property,value'];d.setdefault('normalization_history',[]).extend({'resolved_note':note,'reason':'Puente de cambios programado; la falta de parámetros/subpiezas del productor se conserva como B explícita, no se publica una escena incompleta.'} for note in notes if note.get('campo')=='changes/object,time,property,value')
        redundant=[note for note in d.get('provisional',[]) if note.get('campo') in {'apariencia','adn_entities'}]
        d['provisional']=[note for note in d.get('provisional',[]) if note not in redundant]
        d.setdefault('normalization_history',[]).extend({'resolved_note':note,'reason':'Diagnóstico duplicado: las exigencias explícitas por entidad siguen bloqueando; no se ha terminado ni alterado el ADN/ropa/cara.'} for note in redundant)
        if redundant:d.setdefault('warnings',[]).append({'codigo':'ADN_DIAGNOSTICOS_CONSOLIDADOS','severidad':'AVISO','mensaje':'Se consolidaron avisos duplicados. T314 habilita base CPU; su acabado se verifica después de compilar, nunca por quitar diagnósticos.'})
        from puente_sb4g import preparar as preparar_4g
        camera_receipt,camera_errors=preparar_4g(d,pk);errors.extend(camera_errors);guardar(out/'puente_sb4g.json',{'receipt':camera_receipt,'errors':camera_errors})
        from traductor_adn import compilar as compilar_adn
        adn_receipts,adn_errors=compilar_adn(d,prueba_cpu=prueba_cpu);errors.extend(adn_errors);guardar(out/'traduccion_adn.json',{'receipts':adn_receipts,'errors':adn_errors})
        from narrativa_estructurada import compilar_presencia
        guardar(out/'presencia_desde_01.json',compilar_presencia(d))
        from indice_semantico import compilar as compilar_indice
        index_receipt,index_errors=compilar_indice(d,pk);errors.extend(index_errors);guardar(out/'indice_semantico.json',{'receipt':index_receipt,'index':d['motion'].get('semantic_index'),'requests':d['motion'].get('requests'),'candidates':d['motion'].get('candidates')})
        from catalogos_crecimiento import conectar as conectar_catalogo
        guardar(out/'catalogo_reuso.json',conectar_catalogo(d,ROOT/'bibliotecas/movimientos_aprobados'))
        if (d.get('lighting') or {}).get('emitters'):
            from luces_por_datos import compilar as compilar_luces
            light_events,light_errors=compilar_luces(d['lighting'],d['camera']['shots']);errors.extend(light_errors);d['lighting']['events']=d['lighting'].get('events',[])+light_events;guardar(out/'puente_luz_por_toma.json',{'events':light_events,'errors':light_errors})
        target=out/'paquete_normalizado'
        if target.exists():archivar(target)
        target.mkdir()
        for asset in d['assets']:
            p=ruta(target,asset['path']);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ruta(pk,asset['path']),p)
        pk=target;guardar(pk/'entrada_escena.json',d)
        guardar(out/'entrada_normalizada.json',d);return {'path':'entrada_normalizada.json','entities_preserved':len(d.get('entities',[])),'actions_preserved':len(d.get('actions',[])),'segments_preserved':len(d.get('segments',[]))}
    stage(3,puentes)
    def contrato():
        contract_errors=validar(d,pk)
        for item in contract_errors:
            if item['campo']=='environment/live_data' and (d.get('environment') or {}).get('_vivo_bridge'):item.update(capability_bound=True,causa='escenario_vivo',modulo='4a4 + 01 + 4a2')
        errors.extend(contract_errors)
        if 'actions' not in d:add('dialogue/source','guion/01','Falta el programa completo de acciones para certificar los tiempos de diálogo; no se inventa una escena muda')
        if valid_clock:
            timeline=compilar(d.get('actions',[]),(d.get('camera') or {}).get('shots',[]),fps,dur,[e['id'] for e in d.get('entities',[])],'source_01_integral.json' if (pk/'source_01_integral.json').exists() else 'entrada_escena.json',transition_convention=d['camera'].get('transition_semantics','outgoing'));errors.extend(timeline['errores']);guardar(out/'tiempos_dialogo.json',timeline);artifacts['dialogue']='tiempos_dialogo.json'
        return {'required_finish':['rostros_finales','ropa_final'],'voice_lipsync':'Omni después del motor; no requerido ni bloqueante','dialogue_output':artifacts.get('dialogue')}
    stage(4,contrato)
    def apariencia():
        count=0
        for e in d['entities']:
            if e['type']!='CHARACTER':continue
            geo=(e.get('appearance') or {}).get('geometry')
            if not isinstance(geo,dict):
                add('entities/'+e['id']+'/appearance/geometry','motor/traductor ADN→3D','ADN descriptivo sí existe. Falta terminar su traductor a despiece final de cara/rasgos/ropa; no pedir otra vez todo el ADN. Backend declarativo ampliado no equivale a traducción de esta prosa.','CAPACIDAD_PENDIENTE','crear capacidad',fuente=(e.get('dna_record') or {}).get('source'));continue
            missing=validar_adn(geo)
            if missing:add('entities/'+e['id']+'/appearance/geometry','ADN→3D/SELLO','Despiece final incompleto: '+','.join(missing),'GEOMETRIA_INCOMPLETA')
            else:count+=1
        return {'entities_ready':count,'generic_backend':'apariencia_3d.py','prose_translation':'No se certifica sólo porque existe el backend'}
    stage(5,apariencia)
    def escenario():
        env=d.get('environment') or {};base=env.get('mode')
        if base=='blend':
            p=ruta(pk,env['path'])
            if sha(p)!=env['sha256']:add('environment/base','4a2','El blend no coincide con el hash','HASH_DISTINTO')
        elif base!='geometry':add('environment/mode','4a2','Falta escenario construible')
        if 'events' not in env:add('environment/events','motor/puente 4a-4a4','Falta compilar texto de estado a eventos ejecutables y conciliarlo con 01. No convertir esta capacidad faltante en tarea manual para Ricardo.','CAPACIDAD_PENDIENTE','crear capacidad')
        else:
            from eventos import validar_eventos
            errors.extend(validar_eventos(env['events'],dur))
        if env.get('unresolved_details'):
            errors.append(error('environment/catalog_unresolved','4a2/escenario vivo + catálogo/generador de formas','Faltan recetas compatibles para '+str(len(env['unresolved_details']))+' elementos de ambiente; no convertir sus cajas de ubicación en acabado. Lista exacta en dato_esperado.','DETALLE_ESCENARIO_DATOS',causa='recetas_decoracion_ambiente',dato_esperado=env['unresolved_details']))
        return {'base':base,'hash_checked':base=='blend','events_ready':'events' in env,'executor':'eventos.aplicar'}
    stage(6,escenario)
    def objetos():
        bindings=d.get('bindings',{});refs=d.get('requirements',{}).get('object_refs',[]);ready=sum(ref in bindings for ref in refs)
        for action in d.get('actions',[]):
            if action.get('accion')=='aparecer' and (action.get('objeto') or action.get('actor')):
                # La aparición se representa como acción temporal, no se descarta un actor vacío.
                target=action.get('objeto') or action.get('actor');events=(d.get('environment') or {}).get('events',[])+d.get('fx_events',[])
                if not any(x.get('action_id')==action['id'] or action['id'] in x.get('action_ids',[]) for x in events):add('actions/'+action['id']+'/event','motor/compilador eventos','Compilar aparición sobre '+target+' con la curva/estado de la fuente. No se interpreta como un humano sin nombre.','CAPACIDAD_PENDIENTE','crear capacidad')
        if 'props' not in d:add('props','motor/ADN OBJ→3D','Falta despiece/pivotes/controles finales de los objetos descriptivos, aunque su binding espacial ya esté medido.','CAPACIDAD_PENDIENTE','crear capacidad')
        guardar(out/'bindings_resueltos.json',bindings);return {'spatial_bindings':ready,'requested':len(refs),'backend_points':'geometria.registrar_puntos','hinges':'constructor_final.py (locales, eje y c explícitos)'}
    stage(7,objetos)
    def anatomias():
        for e in d['entities']:
            if e['type']!='CHARACTER':continue
            if not e.get('legacy'):
                if not e.get('rig') and d.get('_anatomy_bridge',{}).get(e['id'])!='WAITING_DATA':add('entities/'+e['id']+'/rig','motor/ADN→esqueleto','Backend aviar real disponible; falta conectar/derivar esqueleto y roles del ADN de esta entidad.','CAPACIDAD_PENDIENTE','crear capacidad')
                elif e.get('rig'):errors.extend(validar_rig(e['rig']))
            if 'physics' not in e and d.get('_anatomy_bridge',{}).get(e['id'])!='WAITING_DATA':add('entities/'+e['id']+'/physics','motor/adaptador perfiles anatómicos','Conectar masas, intervalos de apoyo y puntos del perfil existente al revisor general; no pedir a Ricardo que escriba un perfil técnico.','CAPACIDAD_PENDIENTE','crear capacidad')
        return {'backend_humanoid':'heredado/armar.py (solver bueno conservado)','backend_avian':'anatomia_aviar.py (19 roles mínimos con dedos, alas, cola y pico)','backend_generic':'geometria.rig_declarativo'}
    stage(8,anatomias)
    def seleccion():
        errors.extend(verificar_programa(pk,d,comprobar_integridad=False))
        m=d.get('motion') or {}
        if not m.get('requests') and not d.get('legacy'):add('motion/requests','01/2B','Faltan solicitudes semánticas')
        if 'requests' not in m:add('motion/requests','motor/puente 2B-catálogo','Falta normalizar las asignaciones reales como solicitudes e índice semántico común; no hay selección final desde todas las bibliotecas.','CAPACIDAD_PENDIENTE','crear capacidad')
        return {'order':['argon','catalogo','kimodo','cmu'],'selector':'movimientos.seleccionar','candidate_count':len(m.get('candidates',[]))}
    stage(9,seleccion)
    def pulida():
        if solo_validar:return {"state":"PREFLIGHT_SIN_EJECUCION", "retarget_jobs_pending":len((d.get("motion") or {}).get("retarget_jobs",[]))}
        if 'contacts' not in d and d.get('_physical_bridge_status',{}).get('contacts')!='WAITING_PRODUCER':add('contacts','motor/puente 01-2B-Star','Falta adaptar contactos reales del programa a IK/soportes comunes. Backend IK ya implementado.','CAPACIDAD_PENDIENTE','crear capacidad')
        numeric=leer(ROOT/'config/runtime_cpu.json')['numeric_python']
        for i,job in enumerate((d.get('motion') or {}).get('retarget_jobs',[])):
            if not job.get('raw_bvh'):
                add('motion/retarget_jobs/'+str(i)+'/raw_bvh','biblioteca/mocap','Falta BVH fuente por hash; un recibo externo no sustituye ejecutar pulida');continue
            from catalogos_crecimiento import buscar_bvh
            ent=next(e for e in d['entities'] if e['id']==job['entity']);cached=buscar_bvh(ROOT/'bibliotecas/movimientos_aprobados',job,d['clock'],sha(ruta(pk,job['raw_bvh'])),ent.get('physics'))
            if cached:
                destination=pk/'_generado'/('cache_'+cached['sha256']+'.bvh');destination.parent.mkdir(exist_ok=True)
                if not destination.exists():shutil.copy2(ruta(ROOT/'bibliotecas/movimientos_aprobados',cached['path']),destination)
                job['bvh']=str(destination.relative_to(pk));job['catalog_reused']=cached['id'];continue
            request=out/('pulida_job_'+str(i)+'.json');guardar(request,job);dest=pk/'_generado'/('pulida_'+str(i))
            if dest.exists():archivar(dest)
            dest.parent.mkdir(exist_ok=True)
            with (out/('pulida_'+str(i)+'.log')).open('w') as log:r=subprocess.run([numeric,str(ROOT/'motor/pulida_job.py'),str(pk),str(request),str(dest)],stdout=log,stderr=subprocess.STDOUT,timeout=600)
            if r.returncode:raise RuntimeError('Pulida real falló; no sigue con el BVH sin pulir')
            job['bvh']=str((dest/'pulido.bvh').relative_to(pk));job['polish_receipt']=leer(dest/'recibo.json')
            if sha(dest/'pulido.bvh')!=job['polish_receipt']['output_sha256']:raise ValueError('Salida de pulida modificada')
            for p in (dest/'pulido.bvh',dest/'recibo.json'):d['assets'].append({'path':str(p.relative_to(pk)),'sha256':sha(p),'bytes':p.stat().st_size})
        guardar(pk/'entrada_escena.json',d)
        return {'retarget':'retarget.transferir','polish':'pulida_estricta.pulir','contacts':'geometria.ik_punto','bug_keywords_fixed':True,'off_respected':True}
    stage(10,pulida)
    def camara():
        c=d.get('camera') or {}
        if c.get('source'):a=auditar(leer(ruta(pk,c['source'])));errors.extend(a['errors']);guardar(out/'auditoria_sb.json',a)
        if (c.get('source') and not c.get('_bridge_4g')) or (not c.get('source') and not all('trajectory' in s for s in c.get('shots',[]))):add('camera/translator_4g','motor/puente SB-4g','Falta cerrar el adaptador de todos los comandos de este SB al constructor final. Resolutor 4g anterior conservado; tomas 4/6/9/11 no revalidadas aún sobre entidades finales.','CAPACIDAD_PENDIENTE','crear capacidad')
        return {'requested_shots':len(c.get('shots',[])),'coordinate_backend':'camara_final.py + rig_camara_coords.py','legacy_resolver':'camara_v2_blender.py'}
    stage(11,camara)
    def luz():
        light=d.get('lighting')
        if light:
            from eventos import validar_eventos
            errors.extend(validar_eventos(light['events'],dur))
            if 'view_transform' not in light:add('lighting/view_transform','4a2/preset','Transformación de color ausente')
        return {'global_clock':True,'source_light_not_silently_disabled':True,'ready':bool(light)}
    stage(12,luz)
    def revision():
        nonlocal worker_ok
        if d.get('_rules_bridge',{}).get('state')!='WAITING_DATA' and (not d.get('rules') or not all(k in d['rules'] for k in ['colliders','allowed_collision_pairs','com_accel_max_m_s2','slip_max_m_per_frame','joint_speed_max_deg_s','penetration_tolerance_m','reject_surface_intersections'])):add('rules/physical_binding','motor/adaptador reglas vigentes','Conectar las reglas/preset por hash y colliders del set al revisor final, sin alterar tolerancias históricas.','CAPACIDAD_PENDIENTE','crear capacidad')
        if solo_validar:return {'state':'VALIDACION_SIN_CONSTRUIR','blocking_errors':len(errors),'network_paid':False,'rendered':False}
        if not runtime:add('render/blender','runtime CPU','Falta ruta del Blender instalado')
        if errors:return {'state':'NO_CONSTRUIR_NI_RENDERIZAR','reason':'Compuerta previa bloqueada','backend':'constructor_final.py + fisica_final.py + núcleo bueno'}
        from compatibilidad_artefacto import sellar_paquete
        if pk.name=='paquete_normalizado':sellar_paquete(ROOT, pk)
        # El núcleo histórico se ejecuta como biblioteca de construcción interna, no como otro producto.
        core=None
        if any(e.get('legacy') for e in d['entities'] if e['type']=='CHARACTER'):
            seed=out/'paquete_nucleo';seed.mkdir(exist_ok=False)
            for asset in d['assets']:
                target=seed/asset['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ruta(pk,asset['path']),target)
            guardar(seed/'entrada.json',d['legacy']);coreout=out/'nucleo';coreout.mkdir()
            with (out/'nucleo.log').open('w') as log:r=subprocess.run([runtime,'-b','--disable-autoexec','-t','2','--python-exit-code','17','-P',str(ROOT/'motor/nucleo_bueno_cpu.py'),'--',str(seed),str(coreout)]+(['--habilitar'] if prueba_cpu else []),stdout=log,stderr=subprocess.STDOUT,timeout=7200)
            if r.returncode:raise RuntimeError('Falló núcleo bueno; ver nucleo.log')
            core=coreout/'escena.blend'
        args=[runtime,'-b','--disable-autoexec','-t','2','--python-exit-code','17','-P',str(ROOT/'motor/constructor_final.py'),'--',str(pk),str(out)]+([str(core)] if core else [])
        with (out/'constructor.log').open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=7200,env=dict(os.environ,MOTOR_UNICO_CPU_PRUEBA='1' if prueba_cpu else '0'))
        if r.returncode:
            receipt=leer(out/'worker_resultado.json') if (out/'worker_resultado.json').exists() else {}
            if receipt.get('faltantes_datos'):
                for missing in receipt['faltantes_datos']:errors.append(error(missing['campo'],missing['modulo'],missing['mensaje'],missing.get('codigo','DATO_FALTANTE'),tipo='completar dato'))
                return {'state':'BLOQUEADO_POR_DATOS','producer_errors':receipt['faltantes_datos']}
            raise RuntimeError('Constructor o compuerta rechazó la escena; ver constructor.log y worker_resultado.json')
        worker_ok=leer(out/'worker_resultado.json')['estado']=='CONSTRUIDO_REVISADO';return leer(out/'revision_final.json')
    stage(13,revision)
    def empaquetar():
        files=[]
        for p in sorted((ROOT/'motor').rglob('*.py')):
            if 'archivo' not in p.parts and '__pycache__' not in p.parts:files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
        for p in sorted((ROOT/'bibliotecas').rglob('*.json')):files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
        guardar(out/'worker_manifiesto.json',{'mode':'CPU','gpu_authorized':False,'entry_sha256':sha(entrada),'normalized_entry_sha256':sha(pk/'entrada_escena.json'),'code':files,'scene_sha256':sha(out/'escena.blend') if worker_ok else None,'same_code_required':True});return {'mode':'CPU_ONLY','code_files':len(files),'gpu_created':False}
    stage(14,empaquetar)
    def render():
        if errors or not worker_ok:return {'state':'BLOQUEADO_SIN_VIDEO','frames_rendered':0}
        if not d.get('render'):add('render','preset de salida','Falta resolución/muestras/preset');return {'state':'BLOQUEADO_SIN_VIDEO'}
        with (out/'render.log').open('w') as log:r=subprocess.run([runtime,'-b','--disable-autoexec',str(out/'escena.blend'),'-t','2','--python-exit-code','17','-P',str(ROOT/'motor/render_cpu.py'),'--',str(pk),str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=7200)
        if r.returncode:raise RuntimeError('Render CPU falló; no se monta master')
        artifacts['clips']=leer(out/'clips.json');return artifacts['clips']
    stage(15,render)
    def montaje():
        if errors or 'clips' not in artifacts:return {'state':'BLOQUEADO_SIN_MASTER','partial_master':False}
        plan=planificar(d['camera']['shots'],fps,dur,d['camera'].get('transition_semantics','outgoing'));result=montar([out/x['file'] for x in artifacts['clips']],plan,fps,d['render']['resolution'],dur,[],pk,out/'entrega');artifacts['master']=result['path'];return result
    stage(16,montaje)
    for e in errors:e['grupo']=grupo(e)
    result={'validation_only':solo_validar,'estado':'BLOQUEADO' if errors else ('VALIDADO' if solo_validar else 'COMPLETO'),'version':'20261107-dev6-cpu','validation_scope':'FIXTURE_SINTETICO' if d.get('fixture_only') else 'ESCENA_REAL','production_approved':False,'fecha_bogota':datetime.now().astimezone().isoformat(),'errores':errors,'grupo_A':[e for e in errors if e['grupo']=='A'],'grupo_B':[e for e in errors if e['grupo']=='B'],'avisos':d.get('warnings',[]),'etapas':stages,'coverage':{'expected_frames':cuadro(dur,fps) if valid_clock else None,'requested_shots':len((d.get('camera') or {}).get('shots',[])),'requested_entities':len(d.get('requirements',{}).get('entity_ids',[])),'package_entities':len(d.get('entities',[])),'frames_built':cuadro(dur,fps) if worker_ok else 0,'shots_approved':len(d['camera']['shots']) if worker_ok else 0,'entities_built':len(d['entities']) if worker_ok else 0,'actions_preserved':len(d.get('actions',[])),'segments_preserved':len(d.get('segments',[]))},'execution_policy':{'mode':'CPU','external_spend_usd':0,'gpu_enabled':False,'total_cap_usd':leer(ROOT/'config/politica_ejecucion.json')['presupuesto_total_usd'],'per_call_cap_usd':None},'gasto_usd':0,'master':artifacts.get('master'),'dialogue':artifacts.get('dialogue'),'required_finish':['rostros_finales','ropa_final'],'voice_lipsync':'FUERA_DEL_MOTOR: Omni posterior según t295','servidor_213':'SIN_COTEJAR / sin despliegue nuevo'}
    from causas import consolidar
    result['consolidacion']=consolidar(errors);guardar(out/'causas_consolidadas.json',result['consolidacion'])
    if not errors and pk.name=='paquete_normalizado':
        from compatibilidad_artefacto import sellar_paquete
        sellar_paquete(ROOT, pk)
    guardar(out/'resultado.json',result);return result
