"""Worker del mismo contrato, CPU; construcción, contactos, cámara, revisión y render.
No redes, pagos ni GPU. Se lanza sólo después de la compuerta de datos.
"""
import sys,json,math,subprocess,os,signal,time,traceback
from pathlib import Path
sys.stdout.reconfigure(line_buffering=True);sys.stderr.reconfigure(line_buffering=True) # Blender ignora PYTHONUNBUFFERED: sin esto un SIGKILL deja el log en 0 bytes.
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'motor'))
from seguridad import *
import bpy
from mathutils import Vector,Matrix
from geometria import rig_declarativo,registrar_puntos,ik_punto
from apariencia_3d import construir_parte
import anatomia_aviar,eventos,camara_final
from movimientos import seleccionar
from retarget import transferir
from montaje_cpu import planificar
args=sys.argv[sys.argv.index('--')+1:];pk=Path(args[0]);out=Path(args[1]);d=leer(pk/'entrada_escena.json');fps=d['clock']['fps'];dur=d['clock']['duration_s'];n=cuadro(dur,fps);sc=bpy.context.scene;objects={};rigs={};receipts={};errors=[]
from progreso_camara import Interrupcion
class Interrumpido(Interrupcion):
    codigo='CANCELADO'
def _senal(num,_frame):raise Interrumpido('señal '+signal.Signals(num).name+' durante la etapa '+str(EN_CURSO.get('etapa')))
for _s in (signal.SIGTERM,signal.SIGINT):signal.signal(_s,_senal)
EN_CURSO={'etapa':None,'pid':os.getpid(),'inicio_unix':time.time()}
def _progreso(**k):
    EN_CURSO.update(k,actualizado_unix=time.time());out.mkdir(parents=True,exist_ok=True);parcial=out/'progreso_worker.json.parcial'
    parcial.write_text(json.dumps(EN_CURSO,ensure_ascii=False,default=str),encoding='utf-8');os.replace(parcial,out/'progreso_worker.json')
def inicio(n):_progreso(etapa=str(n),estado='EN_CURSO',etapa_desde_unix=time.time());print('ETAPA_INICIO '+str(n),flush=True)
def etapa(n,data):receipts[str(n)]=data;guardar(out/'etapas_worker.json',receipts);_progreso(ultima_terminada=str(n),estado='ENTRE_ETAPAS');print('ETAPA_FIN '+str(n),flush=True)
try:
    import apariencia_3d
    from recetas_proveedor import contexto as contexto_recetas
    from compatibilidad_artefacto import exigir_paquete, exigir_nucleo, ReusoIncompatible
    apariencia_3d.RECIPE_RUNTIME=contexto_recetas(ROOT,d,pk)
    motivos=exigir_paquete(ROOT, pk)
    if len(args)>2:motivos+=exigir_nucleo(ROOT, Path(args[2]), d.get('legacy'))
    if motivos:raise ReusoIncompatible(motivos)
    if len(args)>2:
        bpy.ops.wm.open_mainfile(filepath=args[2]);sc=bpy.context.scene
    elif d['environment']['mode']=='blend':
        bpy.ops.wm.open_mainfile(filepath=str(ruta(pk,d['environment']['path'])));sc=bpy.context.scene
    else:
        # Preservar objetos de inicio ocultos, nunca guardarlos como una escena fuente.
        for ob in sc.objects:ob.hide_render=True;ob.hide_viewport=True
    sc.render.fps=fps;sc.frame_start=1;sc.frame_end=n
    inicio(6)
    # 6: MISMO escenario base, sin sustituirlo por un fondo ni apagar luces fuente.
    if d['environment']['mode']=='blend' and len(args)>2:
        # El núcleo importa objetos; recuperar el World exacto de la misma fuente.
        with bpy.data.libraries.load(str(ruta(pk,d['environment']['path'])),link=False) as (a,b):
            world=d['environment'].get('world_id')
            if world:b.worlds=[world]
            elif len(a.worlds)==1:b.worlds=list(a.worlds)
            else:raise ValueError('4a2: varios Worlds; hace falta ID de World para esta variante')
        sc.world=b.worlds[0]
    for ob in sc.objects:objects[ob.name]=ob
    if d['environment']['mode']=='geometry':
        root=bpy.data.objects.new('environment_root',None);sc.collection.objects.link(root)
        for part in d['environment']['geometry']:construir_parte(part,root,objects)
    from detalle_entorno import aplicar as detallar_entorno
    if d['environment'].get('visual_preset'):
        from render_estilo import configurar as preset_visual
        preset_visual(sc,d['environment']['visual_preset'])
    detalle_recibo=detallar_entorno(d['environment'].get('catalog_jobs',[]),objects)
    guardar(out/'detalle_entorno.json',detalle_recibo)
    etapa(6,{'objects':len(sc.objects),'preserves_source_lights':True})
    inicio('5/8')
    # 8/5: conservar el solver bueno de humanos; otro backend por anatomía, NO por canal.
    for e in d['entities']:
        if e['type']!='CHARACTER':continue
        if e['id'] in objects and objects[e['id']].type=='ARMATURE':rig=objects[e['id']]
        elif e['anatomy']=='avian':rig=anatomia_aviar.construir(e['id'],e['rig'])
        elif e['anatomy']=='declarative':rig=rig_declarativo(e['id'],e['rig'])
        else:raise ValueError('Humanoide debe llegar del núcleo bueno, no se sustituye por otro solver')
        rigs[e['id']]=rig;objects[e['id']]=rig
        if 'placement' in e:rig.location=e['placement']['position_m'];rig.rotation_euler=[math.radians(x) for x in e['placement']['rotation_deg']]
        if e.get('legacy'):
            for child in rig.children_recursive:
                if child.type=='MESH':child.hide_render=True;child['motor_preserve_hidden']=True # etapa 5/8: cápsulas del rig legacy; las cabezas ADN se publican después con cabeza_visible_constructor.
        from apariencia_base_cpu import ligar
        for part in e['appearance']['geometry']['parts']:construir_parte(ligar(part,rig,e),rig,objects)
        for id,obj in registrar_puntos(rig,e.get('points',[]),objects).items():objects[e['id']+'.'+id]=obj
        from perfiles_catalogo import aplicar_puntos
        aplicar_puntos(e,rig,objects)
    etapa(5,{'entities_with_dna_geometry':len(rigs),'part_count':sum(len(e.get('appearance',{}).get('geometry',{}).get('parts',[])) for e in d['entities'])});etapa(8,{'rigs':{k:len(v.pose.bones) for k,v in rigs.items()}})
    inicio(7)
    # 7: objetos existentes enlazados; bisagras locales y puntos sobre mallas reales.
    for p in d.get('props',[]):
        from objetos_finales import obtener_raiz
        root=obtener_raiz(p,objects,sc)
        for part in p.get('geometry',[]):construir_parte(part,root,objects)
        for id,obj in registrar_puntos(root,p.get('points',[]),objects).items():objects[p['id']+'.'+id]=obj
        for eje_id in p.get('axis_ids') or []:
            if eje_id in objects:continue
            from eje_objetos import alias_vacio
            spec_alias=alias_vacio(p,eje_id)
            empty=bpy.data.objects.new(eje_id,None);sc.collection.objects.link(empty)
            empty.matrix_world=root.matrix_world.copy();world=root.matrix_world.copy();root.parent=empty;root.matrix_world=world
            empty['axis_of']=p['id'];empty['source']=spec_alias['source'];objects[eje_id]=empty
        for h in p.get('hinges',[]):
            pivot=bpy.data.objects.new(h['id'],None);sc.collection.objects.link(pivot);pivot.parent=root;pivot.location=h['pivot_m'];pivot.rotation_mode='AXIS_ANGLE';axis=Vector(h['axis']).normalized();objects[h['id']]=pivot
            for name in h['parts']:
                obj=objects[name];bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=pivot;obj.matrix_world=world
            for key in h['keys']:
                if not 0<=key['c']<=1 or key['curve'] not in eventos.CURVAS:raise ValueError('Control/curva de bisagra inválido')
            controls=[{'t':k['t'],'value':k['c'],'curve':k['curve']} for k in h['keys']]
            for f in range(n+1):
                angle=h['min_deg']+(h['max_deg']-h['min_deg'])*eventos.valor(controls,f/fps);pivot.rotation_axis_angle=(math.radians(angle),*axis);pivot.keyframe_insert('rotation_axis_angle',frame=f+1)
    from anatomia_perfiles import aplicar_anclas
    inicio('anclas');etapa('anclas',aplicar_anclas(d['entities'],rigs,objects))
    etapa(7,{'props':len(d.get('props',[])),'named_points':sum(len(e.get('points',[])) for e in d['entities'])+sum(len(p.get('points',[])) for p in d.get('props',[]))})
    inicio(9)
    # 9: escalera semántica, sin candidatos incompatibles ni selección por nombre de persona.
    selections=[]
    for req in d['motion'].get('requests',[]):
        pool=[c for c in d['motion']['candidates'] if c['entity']==req['entity']]
        if req.get('execution')=='legacy_kernel':
            pool=[c for c in pool if c.get('request_id')==req['id']]
            def prepare_legacy(c):
                if c.get('execution')!='legacy_kernel' or not c.get('validated'):raise ValueError('Catálogo real no validado')
                if any(v is None for v in c['poses'].values()):raise ValueError('Falta pose referenciada')
                return c['movement'],{'type':'already_baked_by_same_kernel','source':c['source'],'assignment':c['assignment']}
            def review_legacy(track,request):
                # El revisor final vuelve a medir la geometría y física; no se rehace el bake.
                return {'passed':True,'scope':'source_integrity_only; physics mandatory afterwards'}
            chosen,log=seleccionar(req,pool,prepare_legacy,review_legacy)
            if chosen is None:raise ValueError('No hay asignación aprobada para solicitud real '+req['id'])
            selections.append({'request':req,'candidate':chosen['candidate']['id'],'log':log,'no_second_writer':True});continue
        def prepare(c):
            rig=rigs[c['entity']]
            if any(t['bone'] not in rig.pose.bones for t in c['tracks']):raise ValueError('Mapa angular no coincide con esqueleto')
            return c['tracks'],{'type':'angular_same_rig','candidate':c['id']}
        def review(track,r):
            rig=rigs[req['entity']];bone_specs={b['id']:b for b in next(e for e in d['entities'] if e['id']==req['entity'])['rig']['bones']};passed=True
            for t in track:
                for k in t['keys']:
                    for v,bounds in zip(k['value'],bone_specs[t['bone']]['limits_deg']):passed &= bounds[0]<=v<=bounds[1]
            return {'passed':bool(passed),'kind':'preliminar_angular; revisión física posterior obligatoria'}
        chosen,log=seleccionar(req,pool,prepare,review)
        if chosen is None:raise ValueError('Ningún candidato equivalente pasó: '+req['action'])
        # seleccionar devuelve tracks + candidato; usar el candidato por recibo inequívoco.
        c=chosen['candidate'];rig=rigs[c['entity']]
        for t in c['tracks']:
            bone=rig.pose.bones[t['bone']];bone.rotation_mode='XYZ'
            for f in range(n+1):
                bone.rotation_euler=[math.radians(x) for x in eventos.valor(t['keys'],f/fps)];bone.keyframe_insert('rotation_euler',frame=f+1)
        selections.append({'request':req,'candidate':c['id'],'log':log})
    etapa(9,selections)
    inicio(10)
    # 10: BVH ya pulido en el box, importación y retarget por mapa explícito; luego IK.
    rt=[]
    for job in d['motion'].get('retarget_jobs',[]):
        bpy.ops.import_anim.bvh(filepath=str(ruta(pk,job['bvh'])),global_scale=1,axis_forward='-Z',axis_up='Y',frame_start=1);src=bpy.context.object
        rec=transferir(src,rigs[job['entity']],job['mapping'],list(range(1,n+1)),job['unit_scale'],job['axis_quaternion'],job['root_source'],job['root_target']);src.hide_render=True;rt.append(rec)
    cons=[]
    for contact in d['contacts']:
        con=ik_punto(rigs[contact['entity']],contact['bone'],objects[contact['target_point']],contact['chain_length'],contact['iterations']);con.influence=0
        for f in range(n):con.influence=1 if contact['t0']<=f/fps<contact['t1'] else 0;con.keyframe_insert('influence',frame=f+1)
        cons.append(contact)
    etapa(10,{'retarget':rt,'contacts':cons,'legacy_solver_preserved':bool(d.get('legacy'))})
    inicio(12)
    # Recompilar presencia desde 01 en cada corrida: evita eventos hide_render obsoletos (p. ej. onset en t[1]).
    from narrativa_estructurada import compilar_presencia
    compilar_presencia(d)
    generated_events=[event for ob in objects.values() if not ob.get('motor_preserve_hidden') and ob.get('motor_events') for event in json.loads(ob['motor_events'])]
    all_events=d['environment']['events']+d.get('fx_events',[])+d['lighting']['events']+generated_events;conflicts=eventos.validar_eventos(all_events,dur)
    if conflicts:raise ValueError(str(conflicts))
    light_ids={p['id'] for p in d['lighting'].get('base',[])}|{ob.name for ob in sc.objects if ob.type=='LIGHT'}
    before,after=eventos.separar_por_dependencias(all_events,light_ids)
    applied=eventos.aplicar(sc,before,fps,dur);sc.frame_set(1);bpy.context.view_layer.update()
    from luces_blender import configurar as configurar_luces
    configurar_luces(sc,d['lighting'],objects)
    if d['lighting'].get('world'):
        profile=d['lighting']['world'];world=bpy.data.worlds.get(profile['id']) or bpy.data.worlds.new(profile['id']);world.use_nodes=True;nodes=[x for x in world.node_tree.nodes if x.type=='BACKGROUND']
        if len(nodes)!=1:raise ValueError('Perfil World necesita un Background inequívoco')
        nodes[0].inputs['Color'].default_value=profile['color_rgba'];nodes[0].inputs['Strength'].default_value=profile['strength'];sc.world=world
    sc.view_settings.exposure=d['lighting']['exposure'];sc.view_settings.view_transform=d['lighting']['view_transform']
    if 'gamma' in d['lighting']:sc.view_settings.gamma=d['lighting']['gamma']
    if 'look' in d['lighting']:sc.view_settings.look=d['lighting']['look']
    applied+=eventos.aplicar(sc,after,fps,dur)
    etapa(12,{'events':applied,'global_frames':n,'single_writer_graph':True,'environment_events_before_lights':True,'environment_tracks_before':len(before),'light_global_tracks_after':len(after)})
    auditoria_post12 = out / 'auditoria_post_etapa12.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(auditoria_post12))
    guardar(out / 'auditoria_post_etapa12.json', {'blend': str(auditoria_post12), 'nota': 'Estado tras eventos etapa 12; permite sonda si etapa 11 falla.'})
    inicio(11)
    # 11: trayectorias geométricas completas y controlador 4g, sin cámara técnica sustitutiva.
    if d['camera'].get('resolver')=='SB_4G':
        from puente_sb4g import construir as construir_4g
        cams,camera_review_4g=construir_4g(sc,d,pk,out,objects)
    else:cams=camara_final.construir(sc,d['camera']['shots'],fps,objects);camera_review_4g=None
    etapa(11,{'cameras':list(cams),'frames':n})
    inicio(13)
    # 13: medir de verdad todos los cuadros. Perfiles/tolerancias los da el paquete.
    state_review=eventos.verificar_estados(sc,d['environment'].get('expected_states',[]),fps);errors+=state_review['errors']
    cr=camera_review_4g if camera_review_4g is not None else camara_final.revisar(sc,d['camera']['shots'],cams,fps,objects);errors+=cr['errors'];trace=[];prev={};length0={id:{b.name:b.length for b in r.data.bones} for id,r in rigs.items()};rules=d['rules'];max_len=0;max_contact=0;max_velocity=0;max_accel=0
    for f in range(1,n+1):
        sc.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();row={'frame':f,'entities':{}}
        for id,rig in rigs.items():
            rig=rig.evaluated_get(dg);root=rig.matrix_world.translation.copy();lengtherr=max(abs((b.tail-b.head).length-length0[id][b.name]) for b in rig.pose.bones);max_len=max(max_len,lengtherr);row['entities'][id]={'root':list(root),'bones':{b.name:[list(rig.matrix_world@b.head),list(rig.matrix_world@b.tail)] for b in rig.pose.bones}}
            if lengtherr>rules['bone_length_error_m']:errors.append({'type':'LARGO','frame':f,'entity':id})
            if id in prev:
                vel=(root-prev[id][0])*fps;max_velocity=max(max_velocity,vel.length)
                if vel.length>rules['root_speed_max_m_s']:errors.append({'type':'VELOCIDAD','frame':f,'entity':id})
                if prev[id][1] is not None:
                    accel=(vel-prev[id][1])*fps;max_accel=max(max_accel,accel.length)
                    if accel.length>rules['root_accel_max_m_s2']:errors.append({'type':'ACELERACION','frame':f,'entity':id})
            else:vel=None
            prev[id]=(root,vel)
        for c in d['contacts']:
            if c['t0']<=(f-1)/fps<c['t1']:
                rig=rigs[c['entity']].evaluated_get(dg);p=rig.matrix_world@rig.pose.bones[c['bone']].tail;t=objects[c['target_point']].matrix_world.translation;err=(p-t).length;max_contact=max(max_contact,err)
                if err>c['tolerance_m']:errors.append({'type':'CONTACTO','frame':f,'entity':c['entity'],'error_m':err})
        trace.append(row)
    import fisica_final
    physical=fisica_final.revisar(sc,d,rigs,objects);errors+=physical['errors']
    report={'frames':n,'entities':list(rigs),'camera':cr,'environment_states':state_review,'physics':physical,'max_bone_length_error_m':max_len,'max_contact_error_m':max_contact,'root_speed_max_m_s':max_velocity,'root_accel_max_m_s2':max_accel,'errors':errors,'all_passed':not errors};guardar(out/'revision_final.json',report);guardar(out/'trazas_finales.json',trace);etapa(13,report)
    if errors:raise ValueError('La compuerta física/cámara rechazó la escena; no se genera video')
    from catalogos_crecimiento import registrar as registrar_movimiento
    from pathlib import Path
    library=Path(__file__).resolve().parents[1]/'bibliotecas/movimientos_aprobados';catalog_receipts=[]
    for job in d['motion'].get('retarget_jobs',[]):
        ent=next(e for e in d['entities'] if e['id']==job['entity'])
        catalog_receipts.append(registrar_movimiento(library,ruta(pk,job['bvh']),origin=job.get('origin','retarget'),source={'input_sha256':sha(ruta(pk,job.get('raw_bvh',job['bvh']))),'file_sha256':sha(ruta(pk,job['bvh'])),'source':job.get('source'),'job_configuration':__import__('catalogos_crecimiento').configuracion_job(job,d['clock'])},skeleton=job.get('skeleton') or {'bones':[b.name for b in rigs[ent['id']].data.bones]},profile=ent['physics'],metrics={'all_passed':True,'errors':[],'max_bone_length_error_m':max_len,'max_contact_error_m':max_contact,'physics':physical},request=job.get('request'),prompt=job.get('prompt'),tracks=job.get('tracks')))
    for selection in selections:
        selected=next(c for c in d['motion']['candidates'] if c['id']==selection['candidate'])
        if selected.get('provider') not in ['kimodo','cmu','retarget','video','mixamo'] or selected.get('catalog_cache'):continue
        import hashlib
        req=selection['request'];ent=next(e for e in d['entities'] if e['id']==req['entity']);rig=rigs[ent['id']];export=out/('movimiento_'+hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()[:16]+'.bvh')
        if export.exists():archivar(export)
        for obj in bpy.context.selected_objects:obj.select_set(False)
        rig.select_set(True);bpy.context.view_layer.objects.active=rig
        bpy.ops.export_anim.bvh(filepath=str(export),frame_start=1,frame_end=n,root_transform_only=False)
        catalog_receipts.append(registrar_movimiento(library,export,origin=selected['provider'],source={'provider_ref':selected.get('source'),'scene_validation':'fixture' if d.get('fixture_only') else 'real','BVH':'exportado de rig revisado'},skeleton=ent.get('rig') or {'bones':[b.name for b in rig.data.bones]},profile=ent['physics'],metrics={'all_passed':True,'errors':[],'max_bone_length_error_m':max_len,'max_contact_error_m':max_contact,'physics':physical},request=req,prompt=selected.get('prompt') or req.get('action'),tracks=selected.get('tracks')))
    guardar(out/'catalogo_registro.json',catalog_receipts)
    inicio(14)
    sc.frame_set(1);sc.camera=cams[d['camera']['shots'][0]['id']];bpy.ops.file.pack_all();blend=out/'escena.blend'
    if blend.exists():archivar(blend)
    parcial=out/'escena_parcial_guardando.blend' # un corte a mitad de escritura no deja un escena.blend truncado
    bpy.ops.wm.save_as_mainfile(filepath=str(parcial));os.replace(parcial,blend);_progreso(estado='TERMINADO',ultima_terminada='14')
    guardar(out/'worker_resultado.json',{'estado':'CONSTRUIDO_REVISADO','frames':n,'rigs':len(rigs),'blend_sha256':sha(blend),'blend_bytes':blend.stat().st_size})
except (Exception,Interrupcion) as exc:
    guardar(out/'worker_resultado.json',{'estado':'BLOQUEADO','codigo':getattr(exc,'codigo','CONSTRUCTOR_O_REVISION'),'etapa_en_curso':EN_CURSO.get('etapa'),'mensaje':str(exc),'tipo':type(exc).__name__,'traceback':traceback.format_exc(),'errores':errors,'faltantes_datos':getattr(exc,'faltantes',[])})
    _progreso(estado='BLOQUEADO');raise
