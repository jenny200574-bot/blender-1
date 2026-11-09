"""Publicación de mallas de cabeza del ADN (no cápsulas legacy ocultas por constructor etapa 5/8)."""

DATAPATHS_VISIBILIDAD = ('hide_render', 'hide_viewport')


def es_capsula_legacy_auditoria(nombre, entity_id, motor_preserve_hidden):
    if motor_preserve_hidden:
        return True
    if not entity_id or not nombre:
        return False
    if nombre.startswith(entity_id + '_malla_') or nombre.startswith(entity_id + '_art_'):
        return True
    return False


def quitar_fcurves_visibilidad_objeto(obj):
    """Quita animación de hide_* que anula la propiedad en frame_set (p. ej. eventos etapa 12)."""
    anim = getattr(obj, 'animation_data', None)
    if anim is None or anim.action is None:
        return 0
    from curvas_accion import curvas_de_accion
    action = anim.action
    quitadas = 0
    for curva in list(curvas_de_accion(action)):
        if curva.data_path not in DATAPATHS_VISIBILIDAD:
            continue
        if hasattr(action, 'fcurves'):
            action.fcurves.remove(curva)
        quitadas += 1
    if quitadas and action and not list(curvas_de_accion(action)):
        if hasattr(obj, 'animation_data_clear'):
            obj.animation_data_clear()
        else:
            obj.animation_data = None
    return quitadas


def publicar_mallas_cabeza_adn(entity, rig, roles_cabeza):
    """Deja visibles para render/medición las piezas de cabeza del ADN; las cápsulas legacy siguen ocultas."""
    from malla_cabeza import malla_es_cabeza, partes_cabeza

    parts = ((entity.get('appearance') or {}).get('geometry') or {}).get('parts') or []
    ids_adn = {p['id'] for p in partes_cabeza(parts)}
    eid = entity.get('id')
    publicadas = []
    for ch in getattr(rig, 'children_recursive', []) or []:
        if getattr(ch, 'type', None) != 'MESH':
            continue
        if ch.get('motor_visibilidad_cabeza_fija'):
            publicadas.append(ch.name)
            continue
        preserve = bool(ch.get('motor_preserve_hidden')) if hasattr(ch, 'get') else False
        if es_capsula_legacy_auditoria(ch.name, eid, preserve):
            continue
        if ch.name in ids_adn or malla_es_cabeza(ch, roles_cabeza):
            nf = quitar_fcurves_visibilidad_objeto(ch)
            ch.hide_render = False
            ch.hide_viewport = False
            ch['motor_cabeza_canonica'] = True
            ch['motor_visibilidad_cabeza_fija'] = True
            if nf:
                ch['motor_visibilidad_cabeza_notas'] = f'Quitadas {nf} fcurve(s) hide_render/hide_viewport; origen típico: eventos etapa 12 (narrativa/entorno).'
            publicadas.append(ch.name)
    return publicadas
