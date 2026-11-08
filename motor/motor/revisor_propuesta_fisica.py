"""Revisa los valores físicos que Argon propone por escena.

No certifica la escena ni el render. El recibo deja approved,
production_approved, scene_physics_approved y physics_validated en False.
Cualquier marca de aprobación escrita por el modelo rechaza la propuesta.
Tres reglas fijas, no negociables y no importadas de T317:
aceleración del COM 20 m/s², velocidad articular 600 °/s,
deslizamiento de pie 0.05 m/cuadro.
La sensatez del resto es la de ingeniería AV08; no son tolerancias del oro.
Producción sigue apagada con config/revisor_propuesta_fisica.off.
"""
import copy
from pathlib import Path
from seguridad import error, numero

MOD = 'revisor_propuesta_fisica'
NOTA = 'Sensatez numérica no aprueba la física de la escena ni autoriza render.'
FIJAS = {'com_accel_max_m_s2': 20, 'joint_speed_max_deg_s': 600, 'slip_max_m_per_frame': .05}
# Topes de sensatez de ingeniería AV08. No modifican las tolerancias del oro.
SENSATEZ = {
    'bone_length_error_m': (1e-7, .001),
    'root_speed_max_m_s': (.01, 10),
    'root_accel_max_m_s2': (.1, 100),
    'penetration_tolerance_m': (1e-6, .01),
}
FISICAS = set(FIJAS) | set(SENSATEZ) | {'reject_surface_intersections', 'colliders', 'allowed_collision_pairs', 'contact_pairs'}
MARCAS = {'approved', 'production_approved', 'scene_physics_approved', 'physics_validated', 'certified', 'validado', 'technical_approved'}
ESTADOS_APROBACION = {'APPROVED', 'VALIDADO', 'CERTIFIED', 'APROBADO', 'TRUE', 'YES'}
ESCENA_MARCAS = ('approved', 'production_approved', 'scene_physics_approved', 'physics_validated', 'certified', 'validado')
UNIDADES = {
    'com_accel_max_m_s2': '20 m/s²',
    'joint_speed_max_deg_s': '600 °/s',
    'slip_max_m_per_frame': '0.05 m/cuadro',
}

def _falta(campo, mensaje, codigo='DATO_FALTANTE', **ctx):
    return error(campo, MOD, mensaje, codigo, tipo='completar dato', **ctx)

def _rechazo(campo, mensaje, codigo, **ctx):
    return error(campo, MOD, mensaje, codigo, tipo='rechazo', **ctx)

def _apagado():
    return (Path(__file__).resolve().parents[1] / 'config' / 'revisor_propuesta_fisica.off').exists()

def _marcas(obj, path='$'):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = path + '.' + str(k)
            if k in MARCAS and v is not False and v is not None:
                found.append(here)
            elif k == 'proposal_status' and isinstance(v, str) and v.strip().upper() in ESTADOS_APROBACION:
                found.append(here)
            else:
                found.extend(_marcas(v, here))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_marcas(v, path + '[' + str(i) + ']'))
    return found

def _recibo(estado, reglas, errores, faltantes):
    return {
        'estado': estado,
        'approved': False,
        'production_approved': False,
        'scene_physics_approved': False,
        'physics_validated': False,
        'reglas': reglas,
        'errores': errores,
        'faltantes': faltantes,
        'nota': NOTA,
    }

def _pares(pairs, campo, colliders, errores):
    if not isinstance(pairs, list):
        errores.append(_rechazo(campo, 'Los pares deben ser una lista explícita', 'PAR_INVALIDO'))
        return False
    ok = True
    cset = set(colliders)
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1] or any(not isinstance(x, str) or x not in cset for x in pair):
            errores.append(_rechazo(campo, 'Par inválido: ' + str(pair), 'PAR_INVALIDO'))
            ok = False
    return ok

def _colliders(physics, inventario, errores, faltantes):
    if 'colliders' not in physics:
        faltantes.append('physics/colliders')
        errores.append(_falta('physics/colliders', 'Falta la lista de colliders; no se interpreta la ausencia como autorización', 'REGLAS_DATOS_FALTANTES'))
        return None
    cs = physics['colliders']
    if not isinstance(cs, list) or not cs or len(cs) != len(set(cs)) or any(not isinstance(x, str) or not x for x in cs):
        errores.append(_rechazo('physics/colliders', 'Colliders vacíos, duplicados o con IDs no textuales', 'COLLIDERS_INVALIDOS'))
        return None
    if not isinstance(inventario, dict) or not isinstance(inventario.get('meshes'), list) or not inventario['meshes'] or any(not isinstance(x, str) or not x for x in inventario['meshes']):
        faltantes.append('inventario_fisico.meshes')
        errores.append(_falta('inventario_fisico/meshes', 'Falta el inventario medido de mallas; no se aceptan colliders a ciegas', 'INVENTARIO_AUSENTE'))
        return None
    meshes = set(inventario['meshes'])
    markers = set(inventario.get('markers') or [])
    empty = set(inventario.get('empty_roots') or [])
    for x in cs:
        if x not in meshes or x in markers or x in empty:
            errores.append(_rechazo('physics/colliders', 'No es malla física medida: ' + x, 'NOT_ACTUAL_PHYSICAL_MESH'))
    primary = inventario.get('character_primary')
    if isinstance(primary, dict):
        for who, parts in primary.items():
            if isinstance(parts, list) and parts and not any(x in cs for x in parts):
                errores.append(_rechazo('physics/colliders', 'Sin collider del cuerpo declarado: ' + str(who), 'CHARACTER_COLLISION_OMITTED'))
    if 'allowed_collision_pairs' not in physics:
        faltantes.append('physics/allowed_collision_pairs')
        errores.append(_falta('physics/allowed_collision_pairs', 'Falta la lista explícita de pares permitidos; no se inventa vacía', 'REGLAS_DATOS_FALTANTES'))
        return None
    if not _pares(physics['allowed_collision_pairs'], 'physics/allowed_collision_pairs', cs, errores):
        return None
    if 'contact_pairs' in physics and not _pares(physics['contact_pairs'], 'physics/contact_pairs', cs, errores):
        return None
    if any(e['codigo'] in {'NOT_ACTUAL_PHYSICAL_MESH', 'CHARACTER_COLLISION_OMITTED', 'PAR_INVALIDO'} for e in errores):
        return None
    return cs

def _avian(avian, physics, inventario, errores):
    if not isinstance(avian, dict):
        errores.append(_rechazo('avian', 'El bloque aviar propuesto no es un objeto', 'AVIAN_INVALIDO'))
        return
    margin = avian.get('balance_margin_m')
    if not numero(margin) or not 0 <= margin <= .01:
        errores.append(_rechazo('avian/balance_margin_m', 'Margen de equilibrio fuera de 0 a 0.01 m', 'AVIAN_MARGIN', dato_encontrado=margin, dato_esperado='0..0.01 m'))
    offset = avian.get('shoulder_offset_m')
    if not isinstance(offset, list) or len(offset) != 3 or any(not numero(v) or abs(v) > .04 for v in offset):
        errores.append(_rechazo('avian/shoulder_offset_m', 'Offset de hombro fuera del sobre de 0.04 m', 'ANCLA_ABSURDA'))
    poly = avian.get('support_polygon_offsets_m')
    if not isinstance(poly, list) or len(poly) < 4 or any(not isinstance(x, list) or len(x) != 3 or any(not numero(v) or abs(v) > .04 for v in x) for x in poly):
        errores.append(_rechazo('avian/support_polygon_offsets_m', 'Polígono de apoyo ausente o fuera del hombro (0.04 m)', 'SOPORTE_ABSURDO'))
    elif isinstance(offset, list) and len(offset) == 3 and numero(offset[2]) and numero(physics.get('penetration_tolerance_m')):
        tol = physics['penetration_tolerance_m']
        if any(abs(x[2] - offset[2]) > tol for x in poly):
            errores.append(_rechazo('avian/support_polygon_offsets_m', 'El apoyo del ave queda separado del ancla más que la tolerancia de penetración', 'FLOATING_SUPPORT_GAP'))
    intervals = avian.get('support_intervals')
    if intervals is not None:
        if not isinstance(intervals, list) or not intervals:
            errores.append(_rechazo('avian/support_intervals', 'Intervalos de apoyo mal formados', 'APOYO_INVALIDO'))
        else:
            for i, row in enumerate(intervals):
                if not isinstance(row, dict) or not numero(row.get('t0')) or not numero(row.get('t1')) or row['t0'] >= row['t1']:
                    errores.append(_rechazo('avian/support_intervals/' + str(i), 'Intervalo de apoyo inválido', 'APOYO_INVALIDO'))
                    continue
                if row.get('mode') not in {'supported', 'airborne', 'flight', 'suspended'}:
                    errores.append(_rechazo('avian/support_intervals/' + str(i), 'Modo de apoyo desconocido', 'APOYO_INVALIDO'))
                elif row.get('mode') != 'supported' and not row.get('action_ref'):
                    errores.append(_rechazo('avian/support_intervals/' + str(i), 'Vuelo o cuelgue sin acción fuente', 'APOYO_SIN_FUENTE'))
    esperado = inventario.get('intervalos_apoyo_fuente') if isinstance(inventario, dict) else None
    if esperado is not None:
        got = [(x.get('t0'), x.get('t1')) for x in intervals or [] if isinstance(x, dict)]
        if got != [tuple(x) for x in esperado]:
            errores.append(_rechazo('avian/support_intervals', 'Los intervalos no coinciden con la fuente de la escena', 'INTERVALOS_NO_COINCIDEN', dato_encontrado=got, dato_esperado=esperado))
    hombro = inventario.get('punto_hombro') if isinstance(inventario, dict) else None
    if hombro is not None:
        target = (avian.get('attachment') or {}).get('target_point') if isinstance(avian.get('attachment'), dict) else None
        if target != hombro:
            errores.append(_rechazo('avian/attachment/target_point', 'El ancla no es el punto medido de la escena', 'HOMBRO_NO_COINCIDE', dato_encontrado=target, dato_esperado=hombro))

def _contactos(proposal, inventario, errores, faltantes):
    if 'contacts' not in proposal:
        faltantes.append('contacts')
        errores.append(_falta('contacts', 'Falta la lista explícita de contactos; no se convierte la ausencia en lista vacía', 'CONTACTOS_DATOS_FALTANTES'))
        return
    rows = proposal['contacts']
    if not isinstance(rows, list):
        errores.append(_rechazo('contacts', 'Los contactos deben ser una lista', 'CONTACTOS_INVALIDOS'))
        return
    if not rows:
        return
    duration = inventario.get('duration_s') if isinstance(inventario, dict) else None
    if not numero(duration) or duration <= 0:
        faltantes.append('inventario_fisico.duration_s')
        errores.append(_falta('inventario_fisico/duration_s', 'Falta la duración de la escena para revisar contactos', 'DATO_FALTANTE'))
        return
    from puentes_fisicos import contactos
    _result, extra = contactos(rows, duration)
    errores.extend(extra)

def revisar(proposal, inventario=None):
    """Devuelve el recibo. Nunca trae approved=true. No muta la propuesta."""
    errores = []
    faltantes = []
    if not isinstance(proposal, dict):
        faltantes.append('argon_physics_proposal')
        errores.append(_falta('argon_physics_proposal', 'La propuesta de Argon debe ser un objeto JSON'))
        return _recibo('BLOQUEADO', None, errores, faltantes)
    marcas = _marcas(proposal)
    if marcas:
        errores.append(_rechazo('argon_physics_proposal/approved', 'El modelo no aprueba la física: ' + ', '.join(marcas), 'MODELO_NO_APRUEBA'))
    if not isinstance(proposal.get('scene_id'), str) or not proposal.get('scene_id'):
        faltantes.append('scene_id')
        errores.append(_falta('scene_id', 'Cada propuesta física pertenece a una escena; falta scene_id'))
    status = proposal.get('proposal_status')
    if not isinstance(status, str) or not status:
        faltantes.append('proposal_status')
        errores.append(_falta('proposal_status', 'Falta proposal_status PROPOSED_FOR_DETERMINISTIC_VALIDATION'))
    elif status != 'PROPOSED_FOR_DETERMINISTIC_VALIDATION':
        errores.append(_rechazo('proposal_status', 'Estado no admisible: la propuesta no puede declararse aprobada ni validada', 'ESTADO_PROPUESTA_INVALIDO', dato_encontrado=status, dato_esperado='PROPOSED_FOR_DETERMINISTIC_VALIDATION'))
    physics = proposal.get('physics')
    out = {}
    if not isinstance(physics, dict):
        faltantes.append('physics')
        errores.append(_falta('physics', 'Falta el objeto physics con los valores propuestos'))
        physics = {}
    else:
        desconocidos = sorted(set(physics) - FISICAS - MARCAS)
        for key in desconocidos:
            errores.append(_rechazo('physics/' + key, 'Límite no reconocido; no se copia ni se afloja', 'LIMITE_NO_RECONOCIDO'))
    for key, esperado in FIJAS.items():
        if key not in physics:
            faltantes.append('physics/' + key)
            errores.append(_falta('physics/' + key, 'Falta la regla fija ' + UNIDADES[key], 'REGLA_FIJA_AUSENTE', dato_esperado=esperado))
        elif not numero(physics[key]) or physics[key] != esperado:
            errores.append(_rechazo('physics/' + key, 'Regla fija alterada. Se exige ' + UNIDADES[key] + '. No se importa el valor de T317.', 'REGLA_FIJA_ALTERADA', dato_encontrado=physics.get(key), dato_esperado=esperado))
        else:
            out[key] = esperado
    for key, (lo, hi) in SENSATEZ.items():
        if key not in physics:
            faltantes.append('physics/' + key)
            errores.append(_falta('physics/' + key, 'Falta el tope propuesto ' + key, 'REGLAS_DATOS_FALTANTES', dato_esperado=[lo, hi]))
        elif not numero(physics[key]) or not lo <= physics[key] <= hi:
            errores.append(_rechazo('physics/' + key, 'Valor fuera de sensatez', 'FUERA_DE_SENSATEZ', dato_encontrado=physics.get(key), dato_esperado=[lo, hi]))
        else:
            out[key] = physics[key]
    if 'reject_surface_intersections' not in physics:
        faltantes.append('physics/reject_surface_intersections')
        errores.append(_falta('physics/reject_surface_intersections', 'Falta reject_surface_intersections; debe ser true', 'REGLAS_DATOS_FALTANTES'))
    elif physics.get('reject_surface_intersections') is not True:
        errores.append(_rechazo('physics/reject_surface_intersections', 'El rechazo de intersección de superficies no se puede apagar', 'INTERSECCION_NO_RECHAZADA', dato_encontrado=physics.get('reject_surface_intersections'), dato_esperado=True))
    else:
        out['reject_surface_intersections'] = True
    cs = _colliders(physics, inventario, errores, faltantes) if isinstance(proposal.get('physics'), dict) else None
    if cs is not None:
        out['colliders'] = list(cs)
        out['allowed_collision_pairs'] = copy.deepcopy(physics['allowed_collision_pairs'])
        if 'contact_pairs' in physics:
            out['contact_pairs'] = copy.deepcopy(physics['contact_pairs'])
    if 'avian' in proposal:
        _avian(proposal['avian'], physics, inventario, errores)
    _contactos(proposal, inventario, errores, faltantes)
    if marcas or (errores and not faltantes):
        estado = 'RECHAZADO'
    elif faltantes:
        estado = 'BLOQUEADO'
    elif errores:
        estado = 'RECHAZADO'
    else:
        estado = 'PROPUESTA_EN_LIMITE'
    return _recibo(estado, out if estado == 'PROPUESTA_EN_LIMITE' else None, errores, faltantes)

def aplicar(d, proposal, inventario=None, prueba_cpu=False):
    """Copia reglas solo si la propuesta pasa. No escribe approved=true. Apagado por .off."""
    if not isinstance(d, dict):
        raise ValueError('Escena debe ser objeto')
    if _apagado() and not prueba_cpu:
        err = _falta('config/revisor_propuesta_fisica.off', 'Revisor de propuestas Argon apagado; la propuesta no se acepta', 'CAPACIDAD_APAGADA')
        return _recibo('OFF', None, [err], ['revisor_propuesta_fisica.off']), [err]
    recibo = revisar(proposal, inventario)
    scene_flags = [k for k in ESCENA_MARCAS if d.get(k) is True]
    if scene_flags:
        recibo['errores'].append(_rechazo('entrada/' + ','.join(scene_flags), 'La escena trae aprobación escrita por el modelo; no se acepta', 'MODELO_NO_APRUEBA'))
        recibo['estado'] = 'RECHAZADO'
        recibo['reglas'] = None
        for k in scene_flags:
            d[k] = False
    if recibo['estado'] == 'PROPUESTA_EN_LIMITE' and not d.get('rules'):
        d['rules'] = copy.deepcopy(recibo['reglas'])
    for k in ESCENA_MARCAS:
        if d.get(k) is True:
            d[k] = False
    return recibo, list(recibo['errores'])
