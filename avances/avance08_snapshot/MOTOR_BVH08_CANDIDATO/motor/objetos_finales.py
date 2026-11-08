"""Reemplazo reversible de moldes: medidas finales en metros, nunca doble escala."""
def obtener_raiz(spec,objects,scene):
    import bpy,math
    from mathutils import Matrix,Vector,Euler
    old=objects.get(spec['id'])
    if old is not None and not spec.get('geometry') and spec.get('reference_kind')!='POINT':return old
    if old is not None and old.type=='ARMATURE':raise ValueError('Un PROP no puede reemplazar un rig de personaje por coincidencia de ID')
    world=old.matrix_world.copy() if old is not None else None;parent=old.parent if old is not None else None
    if old is not None:
        old.name=spec['id']+'__molde_archivado';objects[old.name]=old
        for obj in [old]+list(old.children_recursive):obj.hide_render=True;obj['motor_preserve_hidden']=True
    root=bpy.data.objects.new(spec['id'],None);scene.collection.objects.link(root);root.parent=parent
    if old is None:position=spec['position_m'];quaternion=Euler([math.radians(v) for v in spec.get('rotation_deg',[0,0,0])]).to_quaternion()
    else:
        position=spec.get('position_m',list(world.translation));quaternion=Euler([math.radians(v) for v in spec['rotation_deg']]).to_quaternion() if 'rotation_deg' in spec else world.to_quaternion()
        root['archived_mold_id']=old.name
    root.matrix_world=Matrix.LocRotScale(Vector(position),quaternion,Vector([1,1,1]));objects[spec['id']]=root
    return root
