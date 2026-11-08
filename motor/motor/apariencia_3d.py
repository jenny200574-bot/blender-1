"""Backend ADN geométrico: piezas, rasgos, ropa, malla y visemas verdaderos.
No deduce proporciones de adjetivos ni sustituye un ADN final por cápsulas.
"""
import math
from seguridad import exigir
RECIPE_RUNTIME=None

def material_por_datos(name,mat):
    import bpy
    required=['rgba','metallic','roughness']
    if any(k not in mat for k in required):raise ValueError('Material sin parámetros individuales obligatorios')
    if len(mat['rgba'])!=4 or any(not 0<=x<=1 for x in mat['rgba']):raise ValueError('RGBA fuera de rango')
    for key in ['metallic','roughness','transmission','alpha']:
        if key in mat and not 0<=mat[key]<=1:raise ValueError('Material fuera de rango: '+key)
    m=bpy.data.materials.new(name);m.use_nodes=True;bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=mat['rgba'];bsdf.inputs['Metallic'].default_value=mat['metallic'];bsdf.inputs['Roughness'].default_value=mat['roughness']
    bsdf.inputs['Alpha'].default_value=mat.get('alpha',mat['rgba'][3]);bsdf.inputs['Transmission Weight'].default_value=mat.get('transmission',0)
    if 'subsurface_weight' in mat:
        if not 0<=mat['subsurface_weight']<=1:raise ValueError('SSS fuera de rango')
        bsdf.inputs['Subsurface Weight'].default_value=mat['subsurface_weight']
    if 'ior' in mat:bsdf.inputs['IOR'].default_value=mat['ior']
    if bsdf.inputs['Alpha'].default_value<1:
        if hasattr(m,'surface_render_method'):m.surface_render_method='DITHERED'
        elif hasattr(m,'blend_method'):m.blend_method='BLEND'
        else:raise ValueError('Runtime no permite transparencia requerida')
    if 'emission_rgba' in mat:bsdf.inputs['Emission Color'].default_value=mat['emission_rgba'];bsdf.inputs['Emission Strength'].default_value=mat['emission_strength']
    if 'source' in mat:m['material_source']=str(mat['source'])
    return m

def construir_parte(spec,root,objects):
    exigir('geometria')
    import bpy
    from mathutils import Matrix
    for k in ['id','shape','position_m','rotation_deg','material','source']:
        if k not in spec:raise ValueError('ADN/3D: falta '+k)
    kind=spec['shape'];loc=spec['position_m']
    if kind=='OBJECT_SEARCH':
        from buscador_formas import buscar
        from objetos_star import FaltaDatos
        from pathlib import Path
        result=buscar(spec['query'],spec['form_catalog'],spec['search_policy'],switch=Path(__file__).resolve().parents[1]/'config/argon_recetas.off',runtime=RECIPE_RUNTIME)
        if result['state']!='FOUND':raise FaltaDatos('objects/'+spec['id'],str(result['missing']),result['producer'])
        if result['step'] in [1,2] and not result['recipe'].get('parts'):
            resolved=dict(spec,shape='STAR_FORMULA',formula=result['recipe'].get('formula',result['recipe']['id']));obj=construir_parte(resolved,root,objects)
        else:
            import bpy
            from mathutils import Matrix
            obj=bpy.data.objects.new(spec['id'],None);bpy.context.scene.collection.objects.link(obj);obj.parent=root;obj.matrix_parent_inverse=Matrix.Identity(4);obj.location=loc;obj.rotation_euler=[math.radians(x) for x in spec['rotation_deg']];objects[obj.name]=obj
            for part in result['recipe']['parts']:construir_parte(part,obj,objects)
        obj['form_search_receipt']=__import__('json').dumps(result,ensure_ascii=False);return obj
    if kind=='STAR_FORMULA':
        from objetos_star import construir
        return construir(spec,root,objects)
    if kind=='MESH':
        from malla_cabeza import error_malla_vacia
        vacia=error_malla_vacia(spec)
        if vacia:raise ValueError(vacia)
        mesh=bpy.data.meshes.new(spec['id']);mesh.from_pydata(spec['vertices_m'],[],spec['faces']);mesh.update();obj=bpy.data.objects.new(spec['id'],mesh);bpy.context.scene.collection.objects.link(obj)
    elif kind=='CURVE':
        curve=bpy.data.curves.new(spec['id'],'CURVE');curve.dimensions='3D';curve.bevel_depth=spec['radius_m'];curve.bevel_resolution=spec['resolution'];s=curve.splines.new('POLY');s.points.add(len(spec['points_m'])-1)
        for p,c in zip(s.points,spec['points_m']):p.co=(*c,1)
        obj=bpy.data.objects.new(spec['id'],curve);bpy.context.scene.collection.objects.link(obj)
    else:
        dim=spec['dimensions_m']
        if len(dim)!=3 or min(dim)<=0:raise ValueError('Dimensiones no positivas')
        res=spec['resolution']
        if kind=='BOX':bpy.ops.mesh.primitive_cube_add(size=1)
        elif kind=='ELLIPSOID':bpy.ops.mesh.primitive_uv_sphere_add(segments=res,ring_count=max(4,res//2),radius=.5)
        elif kind=='CONE':bpy.ops.mesh.primitive_cone_add(vertices=res,radius1=.5,radius2=spec['tip_ratio']*.5,depth=1)
        elif kind=='CYLINDER':bpy.ops.mesh.primitive_cylinder_add(vertices=res,radius=.5,depth=1)
        elif kind=='TORUS':
            bpy.ops.mesh.primitive_torus_add(major_segments=res,minor_segments=max(4,res//2),major_radius=spec['major_radius_m'],minor_radius=spec['minor_radius_m'])
        else:raise ValueError('Operador ADN no implementado: '+kind)
        obj=bpy.context.object;obj.name=spec['id']
        # Incorporar escala al mesh para shape_keys en metros físicos.
        for v in obj.data.vertices:
            for i in range(3):v.co[i]*=dim[i]
    obj.name=spec['id'];obj.parent=root;obj.matrix_parent_inverse=Matrix.Identity(4);obj.location=loc;obj.rotation_euler=[math.radians(x) for x in spec['rotation_deg']]
    mat=spec['material'];m=material_por_datos(spec['id']+'_material',mat);obj.data.materials.append(m)
    if spec.get('bevel'):
        b=spec['bevel']
        if obj.type!='MESH' or b['width_m']<=0 or b['segments']<1:raise ValueError('Bisel inválido')
        mod=obj.modifiers.new('bevel_by_contract','BEVEL');mod.width=b['width_m'];mod.segments=b['segments'];mod.limit_method='ANGLE';mod.angle_limit=math.radians(b['angle_deg'])
    normals=spec.get('normals','FLAT')
    if normals not in ['FLAT','SMOOTH']:raise ValueError('Política de normales no soportada')
    if obj.type=='MESH':
        for polygon in obj.data.polygons:polygon.use_smooth=normals=='SMOOTH'
    if spec.get('bone'):
        if root.type!='ARMATURE' or spec['bone'] not in root.data.bones:raise ValueError('ADN: hueso de pieza ausente')
        obj.parent_type='BONE';obj.parent_bone=spec['bone']
        # En Blender parent_bone sitúa origen en cola del hueso; posición proviene del ADN.
    if 'visemes' in spec:
        if obj.type!='MESH':raise ValueError('Visemas requieren malla')
        obj.shape_key_add(name='Basis')
        for v in spec['visemes']:
            key=obj.shape_key_add(name=v['id'])
            if 'vertex_deltas_m' in v:
                for i,delta in v['vertex_deltas_m'].items():
                    for j,x in enumerate(delta):key.data[int(i)].co[j]+=x
            else:
                # Deformación afín local explícita: apertura/redondeo sin números de identidad.
                scale=v['scale'];offset=v['offset_m']
                for p in key.data:
                    for j in range(3):p.co[j]=p.co[j]*scale[j]+offset[j]
    if obj.name in objects:raise ValueError('ID 3D repetido '+obj.name)
    if spec.get('hidden_under_garment'):obj.hide_render=True;obj['motor_preserve_hidden']=True
    if spec.get('library_dimensions'):obj['library_dimensions']=__import__('json').dumps(spec['library_dimensions'],ensure_ascii=False)
    obj['dna_source']=spec['source'];obj['semantic_role']=spec.get('role','geometry');objects[obj.name]=obj;return obj

def validar_adn(adn):
    """Exportador de ADN acepta sólo despiece reproducible y trazable, nunca prosa como malla."""
    missing=[]
    for k in ['parts','source','final_appearance_ref']:
        if k not in adn:missing.append(k)
    roles={x.get('role') for x in adn.get('parts',[])}
    for role in adn.get('required_roles',[]):
        if role not in roles:missing.append('parts/role/'+role)
    return missing
