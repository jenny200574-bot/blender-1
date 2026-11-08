"""Biblioteca de fórmulas Star dentro del mismo constructor. Nunca llama main/clear_scene.
Transformación/ancla/material por entrada; puntos móviles y c→eventos comunes/IK.
Las recetas congeladas mantienen su hash; no se publica bbox como acabado.
"""
import importlib.util,json,math
from pathlib import Path
from seguridad import sha
class FaltaDatos(ValueError):
    def __init__(self,field,message,producer='4a2/escenario vivo'):
        self.faltantes=[{'campo':field,'modulo':producer,'mensaje':message,'codigo':'STAR_DATO_FALTANTE','tipo':'completar dato'}];super().__init__(message)

def verificar(spec):
    missing=[]
    for key in ['id','formula','dimensions_m','position_m','rotation_deg','ancla_z','material','source']:
        if key not in spec:missing.append((key,'Campo necesario para construir sin inferir'))
    if missing:return missing
    if not isinstance(spec['formula'],str):missing.append(('formula','Fórmula ausente o tipo desconocido; no llamar startswith sobre None'))
    if spec['formula'] in ['bbox','caja']:missing.append(('formula','Caja de ubicación rechazada como acabado final; hace falta despiece o receta detallada'))
    if spec['ancla_z'] not in ['base','centro','plano','habitacion_piso']:missing.append(('ancla_z','Convención desconocida'))
    if len(spec['dimensions_m'])!=3 or min(spec['dimensions_m'])<=0:missing.append(('dimensions_m','Tres dimensiones positivas requeridas'))
    for point in spec.get('points',[]):
        if 'frame' not in point:missing.append(('points/'+point['id']+'/frame','Declarar WORLD o LOCAL'))
        if 'pieza_movil' not in point:missing.append(('points/'+point['id']+'/pieza_movil','Declarar ID de pieza padre, o null explícito para el root'))
    if spec['formula']=='cables_haz' and not spec.get('polyline'):missing.append(('polyline','Faltan puntos/ruta exacta de cables; no usar haz genérico como equivalente'))
    return missing

def biblioteca():
    p=Path(__file__).parent/'heredado/star_src/src/motor_fondos.py';sp=importlib.util.spec_from_file_location('star_formulas_library',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
    # Portabilidad Blender y sin fallback de material desconocido.
    from apariencia_3d import material_por_datos
    def material(name,base=(.5,.5,.5),rough=.5,metal=0,emit=None,emit_strength=0,transmission=0,alpha=1):
        data={'rgba':[*base,alpha],'roughness':rough,'metallic':metal,'transmission':transmission,'alpha':alpha,'source':'receta Star SHA256 '+sha(p)}
        if emit is not None:data.update(emission_rgba=[*emit,1],emission_strength=emit_strength)
        return material_por_datos(name,data)
    m.mat_pbr=material
    def catalog(formula,cat,override_base=None,suffix=''):
        if formula not in cat:raise FaltaDatos('materials/'+formula,'Material de fórmula no suministrado; no cae a gris/bbox','catálogo de materiales / 4a2')
        d=cat[formula];return material((d.get('nombre') or formula)+suffix,base=override_base if override_base is not None else d['base'],rough=d['rough'],metal=d.get('metal',0),emit=d.get('emit'),emit_strength=d.get('emit_strength',0),transmission=d.get('transmission',0),alpha=d.get('alpha',1)),d
    m.mat_from_catalog=catalog;return m,sha(p)

def controles(spec):
    out=[]
    for c in spec.get('controls',[]):
        if 'target_piece' not in c or 'property' not in c:raise FaltaDatos('controls/'+c['id'],'Control sin ID de pieza y propiedad explícitos')
        a,b=c['range'];keys=[]
        for k in c['keys']:
            v=k['c']
            if not 0<=v<=1:raise FaltaDatos('controls/'+c['id']+'/c','Control fuera de [0,1]; no recortar en silencio')
            val=[x+(y-x)*v for x,y in zip(a,b)] if isinstance(a,list) else a+(b-a)*v
            if c.get('units')=='deg':val=[math.radians(x) for x in val] if isinstance(val,list) else math.radians(val)
            keys.append({'t':k['t'],'value':val,'curve':k['curve']})
        out.append({'object':c['target_piece'],'property':c['property'],'keys':keys,'material':c.get('material'),'source':c['source'],'control_id':c['id']})
    return out

def construir(spec,parent,objects):
    from seguridad import exigir_desarrollo
    exigir_desarrollo('star_unificado');exigir_desarrollo('catalogo_star_completo')
    import bpy
    from mathutils import Matrix,Vector,Euler
    from apariencia_3d import construir_parte,material_por_datos
    from geometria import registrar_puntos
    missing=verificar(spec)
    if missing:raise FaltaDatos('objects/'+spec.get('id','?')+'/'+missing[0][0],missing[0][1])
    if spec['id'] in objects:raise ValueError('ID de fórmula duplicado '+spec['id'])
    library,source_hash=biblioteca();formula=spec['formula']
    if formula not in library.REGISTRY:raise FaltaDatos('objects/'+spec['id']+'/formula','No existe constructor para fórmula '+formula,'catálogo de fórmulas / motor')
    root=bpy.data.objects.new(spec['id'],None);bpy.context.scene.collection.objects.link(root);root.parent=parent;root.matrix_parent_inverse=Matrix.Identity(4);root.location=spec['position_m'];root.rotation_euler=[math.radians(x) for x in spec['rotation_deg']];objects[root.name]=root
    before=set(bpy.data.objects);report={'falta':[],'dudas':[],'notas':[]}
    try:
        if formula=='muros_caja_con_huecos':
            from arquitectura_datos import paneles
            arch=spec.get('architecture')
            if arch is None:raise FaltaDatos('architecture','Falta lista explícita de paredes/orientaciones/huecos; no se presupone pared derecha ni noche')
            for wall in arch['walls']:
                wr=bpy.data.objects.new(wall['id'],None);bpy.context.scene.collection.objects.link(wr);wr.parent=root;wr.location=wall['position_m'];wr.rotation_euler=[math.radians(x) for x in wall['rotation_deg']];objects[wr.name]=wr
                for i,p in enumerate(paneles(wall)):
                    part=dict(p,id=wall['id']+'.panel_'+str(i),shape='BOX',rotation_deg=[0,0,0],material=wall['material'],source=wall['source'],resolution=wall['resolution'],bevel=wall.get('bevel'))
                    construir_parte(part,wr,objects)
            for part in arch.get('exterior_geometry',[]):construir_parte(part,root,objects)
            built=list(set(bpy.data.objects)-before)
        elif formula=='plano':
            # La receta original cambiaba color por nombre y podía dar espesor cero.
            # El contrato ya aporta material y espesor: ejecutarlos literalmente.
            height=spec['dimensions_m'][2];z=height/2 if spec['ancla_z'] in ['base','plano','habitacion_piso'] else 0
            part={'id':spec['id']+'.surface','shape':'BOX','dimensions_m':spec['dimensions_m'],'position_m':[0,0,z],'rotation_deg':[0,0,0],'material':spec['material'],'source':spec['source'],'resolution':spec.get('resolution',8)}
            if spec.get('bevel'):part['bevel']=spec['bevel']
            construir_parte(part,root,objects);built=[objects[part['id']]]
        elif formula=='cables_haz':
            poly=spec['polyline'];points={p['id']:p['position_m'] for p in spec.get('points',[]) if p.get('frame')=='LOCAL'}
            if any(k not in points for k in poly['point_ids']):raise FaltaDatos('polyline/point_ids','La ruta debe referirse a puntos locales existentes')
            part={'id':spec['id']+'.path','shape':'CURVE','position_m':[0,0,0],'rotation_deg':[0,0,0],'points_m':[points[k] for k in poly['point_ids']],'radius_m':poly['radius_m'],'resolution':poly['resolution'],'material':spec['material'],'source':spec['source']};construir_parte(part,root,objects);built=[objects[part['id']]]
        else:
            # Construir receta en un marco canónico aislado del nombre/posición del usuario.
            canonical={'id':'recipe','formula':formula,'tamano_m':spec['dimensions_m'],'pos_m':[0,0,0],'ancla_z':'base','cielo_nocturno':False}
            library.REGISTRY[formula](canonical,spec['materials_catalog'],report);built=list(set(bpy.data.objects)-before)
            if report['falta'] or report['dudas']:raise FaltaDatos('formula',str(report['falta']+report['dudas']))
            mesh=[x for x in built if x.type=='MESH']
            if not mesh:raise ValueError('Receta no produjo mallas')
            dg=bpy.context.evaluated_depsgraph_get();vertices=[]
            for ob in mesh:
                ev=ob.evaluated_get(dg);me=ev.to_mesh();vertices.extend(ob.matrix_world@v.co for v in me.vertices);ev.to_mesh_clear()
            lo=Vector([min(v[i] for v in vertices) for i in range(3)]);hi=Vector([max(v[i] for v in vertices) for i in range(3)]);extent=hi-lo
            if min(extent)<=0:raise ValueError('Receta degenerada')
            axes=spec.get('dimension_order',[0,1,2]);desired=Vector([spec['dimensions_m'][i] for i in axes]);scale=Vector([desired[i]/extent[i] for i in range(3)]);center=(lo+hi)/2;offset=center.copy()
            if spec['ancla_z'] in ['base','plano','habitacion_piso']:offset.z=lo.z
            transform=Matrix.Diagonal((*scale,1))@Matrix.Translation(-offset)
            primary=material_por_datos(spec['id']+'.entry_material',spec['material'])
            for ob in built:
                local=transform@ob.matrix_world;ob.parent=root;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=local;old_name=ob.name;role=old_name.removeprefix('recipe').lstrip('_') or 'body';ob.name=spec['id']+'.'+role;objects[ob.name]=ob;ob['formula_role']=role;ob['source_recipe_sha256']=source_hash
                if ob.type=='MESH':
                    overrides=spec.get('piece_materials',{});match=overrides.get(role)
                    if match:ob.data.materials.clear();ob.data.materials.append(material_por_datos(spec['id']+'.'+role+'.material',match))
                    else:
                        # Material individual sólo reemplaza el primario de la fórmula, no las piezas con acabado distinto.
                        for i,mat in enumerate(ob.data.materials):
                            if mat and mat.name.startswith(spec['materials_catalog'][formula].get('nombre',formula)):ob.data.materials[i]=primary
            root['actual_size_normalized_m']=list(desired);root['anchor_preserved']=spec['ancla_z'];root['rotation_applied_deg']=spec['rotation_deg']
        bpy.context.view_layer.update()
        descriptor_path=Path(__file__).resolve().parents[1]/'bibliotecas/formulas_star_estrictas.json'
        descriptor=spec.get('recipe_descriptor')
        if descriptor is None:
            descriptor=next((x for x in json.loads(descriptor_path.read_text())['recipes'] if x['formula']==formula),{})
            root['recipe_descriptor_sha256']=sha(descriptor_path)
        role_objects={ob.get('formula_role'):ob for ob in built if ob.get('formula_role')}
        for binding in descriptor.get('piece_parenting',[]):
            pivot=role_objects.get(binding['parent_role'])
            if pivot is None:raise FaltaDatos('recipe/piece_parenting','La receta no construyó el rol de pivote declarado','catálogo de fórmulas / motor')
            for role in binding['child_roles']:
                ob=role_objects.get(role)
                if ob is None:raise FaltaDatos('recipe/piece_parenting','La receta no construyó el rol móvil '+role,'catálogo de fórmulas / motor')
                world=ob.matrix_world.copy();ob.parent=pivot;ob.matrix_world=world
        for p in spec.get('pivots',[]):
            pivot=bpy.data.objects.new(p['id'],None);bpy.context.scene.collection.objects.link(pivot);pivot.parent=root;pivot.location=p['position_m'];pivot.rotation_euler=[math.radians(x) for x in p['rotation_deg']];objects[pivot.name]=pivot;bpy.context.view_layer.update()
            for child_id in p['pieces']:
                if child_id not in objects:raise FaltaDatos('pivots/'+p['id']+'/pieces','Pieza no registrada: '+child_id)
                ob=objects[child_id];world=ob.matrix_world.copy();ob.parent=pivot;ob.matrix_world=world
        for key,pt in registrar_puntos(root,spec.get('points',[]),objects).items():objects[root.name+'.'+key]=pt
        root['motor_events']=json.dumps(controles(spec),ensure_ascii=False);root['formula']=formula;root['source']=str(spec['source']);root['formula_receipt']=json.dumps(report,ensure_ascii=False)
        return root
    except Exception:
        # Preservar restos fallidos ocultos; nunca borrar ni publicarlos como acabado.
        for ob in set(bpy.data.objects)-before:ob.hide_render=True;ob['construction_failed']=True
        root.hide_render=True;root['construction_failed']=True;raise
