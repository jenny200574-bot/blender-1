"""Rechaza mallas vacías y cabezas sin hueso. No inventa geometría ni huesos."""

def desplazar_cabeza(vertices, largo):
    """Desplaza la cápsula de cabeza a lo largo del hueso. El largo sale del rig, no se inventa."""
    if isinstance(largo, bool) or not isinstance(largo, (int, float)):
        raise ValueError('Largo de cabeza ausente; no se desplaza la malla')
    return [(v[0], v[1] + largo * 0.5, v[2]) for v in vertices]

def error_malla_vacia(spec):
    if not isinstance(spec, dict) or spec.get('shape') != 'MESH':
        return None
    verts = spec.get('vertices_m')
    faces = spec.get('faces')
    if verts and faces:
        return None
    return 'Malla vacía ' + str(spec.get('id')) + ': sin vértices o caras. No se construye ni se inventa geometría.'

def error_hueso_cabeza(entity_id, bind_role, bone_name, bones):
    """None si el hueso declarado está en el rig. Si no, el mensaje nombra al personaje."""
    if bone_name and bone_name in set(bones or []):
        return None
    esperado = bone_name or 'un hueso de ' + str(bind_role) + ' declarado en el rig'
    return str(entity_id) + ': el rig no tiene hueso ni malla de ' + str(bind_role) + ' asignados (se esperaba ' + str(esperado) + '). No se inventa el hueso.'

def partes_cabeza(parts):
    return [p for p in parts or [] if isinstance(p, dict) and (p.get('bind_role') == 'head' or p.get('role') in ('head', 'face'))]

def region_desde_hueso(cabeza, cola):
    """Región medida de un hueso ya existente. None si falta un extremo o el largo es cero."""
    puntos = []
    for punto in (cabeza, cola):
        if isinstance(punto, bool) or not isinstance(punto, (list, tuple)) or len(punto) != 3:
            return None
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in punto):
            return None
        if any(x != x or x in (float('inf'), float('-inf')) for x in punto):
            return None
        puntos.append((float(punto[0]), float(punto[1]), float(punto[2])))
    a, b = puntos
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    largo = (dx * dx + dy * dy + dz * dz) ** 0.5
    if largo <= 0:
        return None
    centro = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    alto = abs(b[2] - a[2]) or largo
    return {
        'centro': centro,
        'alto': alto,
        'top': max(a[2], b[2]),
        'puntos': [a, b, centro],
        'puntos_cara': [a, b, centro],
        'origen': 'hueso',
    }


def validar_cabeza(entity):
    """Bloquea si la cabeza compilada no tiene malla con vértices, o el rig trae huesos y ninguno es la cabeza."""
    ident = entity.get('id', '?')
    parts = ((entity.get('appearance') or {}).get('geometry') or {}).get('parts') or []
    heads = partes_cabeza(parts)
    vacias = [p.get('id') for p in heads if error_malla_vacia(p)]
    if vacias:
        return ident + ': malla de cabeza sin vértices: ' + ', '.join(str(x) for x in vacias) + '. No se inventa la cabeza.'
    utiles = [p for p in heads if not error_malla_vacia(p)]
    if not utiles:
        return ident + ': el rig no tiene hueso ni malla de cabeza asignados. No se inventa la cabeza.'
    huesos = (entity.get('rig') or {}).get('bones') or []
    if huesos:
        ids = {b.get('id') for b in huesos if isinstance(b, dict)}
        roles = {b.get('role'): b.get('id') for b in huesos if isinstance(b, dict)}
        esperado = roles.get('head') or 'cabeza'
        if esperado not in ids and 'cabeza' not in ids:
            return error_hueso_cabeza(ident, 'head', esperado, ids)
    return None
