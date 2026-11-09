"""Helpers del modo directa SB (sin bpy): diagnóstico y opciones experimentales."""
import re

# Solo geometría de escenario (no props de historia tipo obj-* ni personajes).
_PREFIJOS_DESPEJE = ('muro_', 'amb-esc-', 'pared_', 'techo_', 'suelo_', 'cortina_', 'ventana_')


def es_geometria_escenario_auto(nombre):
    if not nombre:
        return False
    low = nombre.lower()
    return any(low.startswith(p) for p in _PREFIJOS_DESPEJE) or low.startswith('muro') or 'cortinas' in low


def es_entidad_historia(nombre, act_ids, act_mesh_names):
    if not nombre:
        return False
    act_ids = act_ids or ()
    if nombre in act_ids or nombre in (act_mesh_names or ()):
        return True
    return any(nombre == pid or nombre.startswith(pid + '.') or nombre.startswith(pid + '_') for pid in act_ids)


def tapadores_escenario_desde_malos(malos, act_ids=(), act_mesh_names=()):
    out = set()
    for row in malos or []:
        msg = row[1] if len(row) > 1 else ''
        if 'otro personaje' in msg:
            continue
        for m in re.finditer(r'\(([^)]+)\)', msg):
            nombre = m.group(1).strip()
            if nombre.startswith('escenario:'):
                nombre = nombre.split('escenario:', 1)[1].strip()
            if nombre and not es_entidad_historia(nombre, act_ids, act_mesh_names) and es_geometria_escenario_auto(nombre):
                if any(x in msg for x in ('escenario', 'pegada', 'dentro de geometría')):
                    out.add(nombre)
                elif 'tapado' in msg and msg.startswith('cámara'):
                    out.add(nombre)
    return frozenset(out)


def clasificar_motivos_directa(malos):
    cats = {'encuadre': 0, 'oclusion_escenario': 0, 'holgura_escenario': 0, 'eje_180': 0, 'inclinacion_roll': 0, 'cara_espalda': 0, 'otros': 0}
    for row in malos or []:
        msg = row[1] if len(row) > 1 else ''
        if 'fuera de cuadro' in msg:
            cats['encuadre'] += 1
        elif 'tapado' in msg and 'escenario' in msg:
            cats['oclusion_escenario'] += 1
        elif 'pegada' in msg or 'dentro de geometría' in msg:
            cats['holgura_escenario'] += 1
        elif '180' in msg:
            cats['eje_180'] += 1
        elif 'inclinación' in msg or 'roll' in msg:
            cats['inclinacion_roll'] += 1
        elif 'espaldas' in msg:
            cats['cara_espalda'] += 1
        else:
            cats['otros'] += 1
    return cats


def informe_conflicto_toma(vineta, S, motivos, clasificacion, vin=None):
    """Qué pide el SB, qué viola la revisión; sin ocultar props ni cambiar plan."""
    vin = vin or {}
    segs = vin.get('segmentos') or []
    mov = [{k: s.get(k) for k in ('movimiento', 'args')} for s in segs[:6]]
    ops = []
    if clasificacion.get('eje_180') or clasificacion.get('inclinacion_roll'):
        ops.append('Conflicto geométrico con eje/inclinación pedidos: decidir en SB o habilitar reparación (quitar camara_busqueda_reparacion.off).')
    if any('tapado' in m and 'obj-' in m for m in (motivos or [])):
        ops.append('Oclusión de prop de historia (obj-*): no se oculta automáticamente; mover prop, encuadre o aceptar bloqueo.')
    if clasificacion.get('encuadre'):
        ops.append('Encuadre: verificar medición con malla de cabeza visible (no cápsula legacy); pose directa sin factor distancia.')
    if not ops:
        ops.append('Revisión bloqueada: exportar muestras_malas y decidir sin relajar tolerancias.')
    clases = []
    if clasificacion.get('holgura_escenario'):
        clases.append('arreglable_motor')
    if clasificacion.get('oclusion_escenario'):
        clases.append('arreglable_motor' if any('escenario' in (m or '') for m in (motivos or [])) else 'escena_o_layout')
    if clasificacion.get('encuadre'):
        clases.append('conflicto_storyboard')
    if clasificacion.get('eje_180') or clasificacion.get('inclinacion_roll'):
        clases.append('conflicto_storyboard')
    if clasificacion.get('cara_espalda'):
        clases.append('conflicto_storyboard')
    if not clases:
        clases.append('revisar_manual')
    return {
        'vineta': vineta,
        'plano_inicial': S.get('plano0'),
        'elevacion_pedida_deg': S.get('elev'),
        'orientacion_sb_deg': S.get('orient'),
        'roll_pedido_deg': S.get('roll_deg'),
        'lente_mm': S.get('lens'),
        'movimientos_sb': mov,
        'motivos_revision': list(motivos or []),
        'clasificacion': clasificacion,
        'opciones_sin_cambiar_storyboard': ops,
        'props_historia': 'No se ocultan obj-* (p. ej. obj-cama.*).',
        'clase_conflicto': clases,
        'nota_ricardo': 'No recalcular plan SB; pared invisible o acercamiento solo para esa cámara si clase incluye arreglable_motor.',
    }


def retroceder_tray_holgura(tray, frac):
    if not frac or frac <= 0:
        return tray
    salida = []
    for x in tray:
        y = dict(x)
        mira = y.get('mira')
        if mira is not None:
            d = y['loc'] - mira
            if hasattr(d, 'length') and d.length > 1e-6:
                y['loc'] = y['loc'] + d.normalized() * (d.length * float(frac))
        salida.append(y)
    return salida
