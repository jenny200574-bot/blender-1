"""Helpers del modo directa SB (sin bpy): diagnóstico y opciones experimentales."""
from camara_oclusion_sb import nombres_obstaculo_en_malos


def tapadores_escenario_desde_malos(malos, act_ids=(), act_mesh_names=()):
    """Compat: nombres citados en malos (la reparación R14 usa además rayos BVH)."""
    return frozenset(nombres_obstaculo_en_malos(malos).keys())


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


def opcion_ricardo(clasificacion, motivos):
    """Reparación motor R14: visible_camera, retroceso, espejo eje 180°."""
    ops = []
    if clasificacion.get('holgura_escenario') or clasificacion.get('oclusion_escenario'):
        ops.append({'accion': 'visible_camera_por_toma', 'detalle': 'visible_camera=False en rango de toma (CONSTANT); obstáculos entre cámara y sujeto SB.', 'interruptor': 'camara_escenario_despeje_por_toma.off'})
    if clasificacion.get('holgura_escenario') or clasificacion.get('encuadre'):
        ops.append({'accion': 'retroceso_holgura', 'detalle': 'Alejar cámara a lo largo del eje sin recalcular trayectoria SB.', 'interruptor': 'camara_retroceso_holgura_directa.off'})
    if clasificacion.get('eje_180'):
        ops.append({'accion': 'espejo_eje_180', 'detalle': 'Reflejar posición de cámara al lado correcto del eje (salvo CROSSAXIS en SB).'})
    if clasificacion.get('inclinacion_roll'):
        ops.append({'accion': 'conflicto_storyboard', 'detalle': 'Inclinación/roll fuera de tolerancia: revisar SB o pose.'})
    return ops


def informe_conflicto_toma(vineta, S, motivos, clasificacion, vin=None):
    """Qué pide el SB, qué viola la revisión tras intento de reparación R14."""
    vin = vin or {}
    segs = vin.get('segmentos') or []
    mov = [{k: s.get(k) for k in ('movimiento', 'args')} for s in segs[:6]]
    ops = []
    if clasificacion.get('eje_180'):
        ops.append('Eje 180°: el motor puede espejar la cámara si no hay CROSSAXIS en el SB.')
    if clasificacion.get('oclusion_escenario') or any('tapado' in (m or '') for m in (motivos or [])):
        ops.append('Oclusión: visible_camera por rayos sujeto-cámara (props, paredes o no-sujetos); sujetos SB protegidos.')
    if clasificacion.get('encuadre'):
        ops.append('Encuadre: retroceso acotado + oclusión; medir con malla de cabeza visible.')
    if clasificacion.get('inclinacion_roll'):
        ops.append('Inclinación/roll: sin reparación automática; revisar SB.')
    if not ops:
        ops.append('Revisión bloqueada: ver reparacion_toma en experimental_directa y muestras_malas.')
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
        'props_historia': 'obj-* y ch-* no sujeto pueden ocultarse con visible_camera si tapan al sujeto SB (R14).',
        'clase_conflicto': clases,
        'opciones_ricardo': opcion_ricardo(clasificacion, motivos),
        'nota_ricardo': 'R14: reparación automática (visible_camera, retroceso, eje 180°) sin recalcular plan SB.',
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
