"""Publicación de mallas de cabeza del ADN (no cápsulas legacy ocultas por constructor etapa 5/8)."""


def es_capsula_legacy_auditoria(nombre, entity_id, motor_preserve_hidden):
    if motor_preserve_hidden:
        return True
    if not entity_id or not nombre:
        return False
    if nombre.startswith(entity_id + '_malla_') or nombre.startswith(entity_id + '_art_'):
        return True
    return False


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
        preserve = bool(ch.get('motor_preserve_hidden')) if hasattr(ch, 'get') else False
        if es_capsula_legacy_auditoria(ch.name, eid, preserve):
            continue
        if ch.name in ids_adn or malla_es_cabeza(ch, roles_cabeza):
            ch.hide_render = False
            ch.hide_viewport = False
            ch['motor_cabeza_canonica'] = True
            publicadas.append(ch.name)
    return publicadas
