"""Emisores independientes por datos; marcos explícitos para luces parentadas.
Una fórmula no autoriza su iluminación de ejemplo como luz final de la escena.
"""
def configurar(scene,profile,objects):
    import bpy,math
    from mathutils import Matrix,Euler,Vector
    from objetos_star import FaltaDatos
    declared={light['id'] for light in profile['base']}
    for ob in objects.values():
        if ob.type=='LIGHT' and ob.get('source_recipe_sha256') and ob.name not in declared:
            raise FaltaDatos('lighting/base/'+ob.name,'Emisor de receta sin perfil individual: tipo, energía, color y marco/transformación. No publicar luz técnica heredada como acabado.')
    for light in profile['base']:
        required={'id','type','position_m','rotation_deg','energy','color'}
        if not required<=set(light):raise FaltaDatos('lighting/base/'+light.get('id','?'),'Perfil de emisor incompleto')
        if light['energy']<0 or len(light['color'])!=3 or any(not 0<=v<=1 for v in light['color']):raise FaltaDatos('lighting/base/'+light['id'],'Energía/color fuera de rango')
        obj=objects.get(light['id'])
        if obj is not None and (obj.type!='LIGHT' or obj.data.type!=light['type']):raise FaltaDatos('lighting/base/'+light['id'],'ID/tipo de emisor no coincide con objeto real')
        if obj is None:
            data=bpy.data.lights.new(light['id'],light['type']);obj=bpy.data.objects.new(light['id'],data);scene.collection.objects.link(obj);objects[obj.name]=obj
        frame=light.get('frame','WORLD' if obj.parent is None else None)
        if frame not in ['WORLD','LOCAL']:raise FaltaDatos('lighting/base/'+light['id']+'/frame','Luz parentada: declarar WORLD o LOCAL; no reinterpretar una posición world como local')
        transform=Matrix.LocRotScale(Vector(light['position_m']),Euler([math.radians(x) for x in light['rotation_deg']]).to_quaternion(),Vector([1,1,1]))
        if frame=='WORLD':obj.matrix_world=transform
        else:obj.matrix_basis=transform
        obj.data.energy=light['energy'];obj.data.color=light['color'];obj['lighting_profile_source']=str(light.get('source',profile.get('source','entrada_escena.json#/lighting')))
    bpy.context.view_layer.update()
