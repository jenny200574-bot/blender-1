"""Mapa cuadro↔toma (camera/shots). Universal: no excluye límites cinemáticos salvo regla explícita."""
from seguridad import cuadro, numero


def indice_tomas(d):
    """Devuelve lista ordenada {id, f0, f1, t0, t1, transicion_entrada}."""
    fps = float(d['clock']['fps'])
    shots = list((d.get('camera') or {}).get('shots') or [])
    if not shots:
        return []
    out = []
    for i, s in enumerate(shots):
        t0, t1 = s.get('t0'), s.get('t1')
        if not numero(t0) or not numero(t1) or t1 <= t0:
            continue
        f0, f1 = cuadro(t0, fps), cuadro(t1, fps)
        tr = s.get('transition')
        kind = tr.get('type') if isinstance(tr, dict) else tr
        out.append({
            'id': s.get('id'),
            'f0': f0,
            'f1': f1,
            't0': float(t0),
            't1': float(t1),
            'transicion_entrada': kind,
            'es_corte_seco_entrada': kind in {'CORTE', 'CORTE_SECO', 'CUT', 'FIN_ESCENA'} or (isinstance(kind, str) and kind.startswith('CORTE')),
        })
    return out


def cuadro_a_toma(d, frame, fps=None):
    fps = fps or float(d['clock']['fps'])
    matches = []
    for t in indice_tomas(d):
        if t['f0'] <= frame <= t['f1']:
            matches.append(t)
    if not matches:
        return None
    # En el borde compartido (f1==f0 siguiente) cuenta la toma entrante.
    t = matches[-1]
    return dict(t, frame=frame, frame_inicio=frame == t['f0'])


def cuadros_inicio_toma(d):
    return {t['f0'] for t in indice_tomas(d)}


def exclusion_cinematica_contrato(rules):
    """El contrato vigente no define exclusión automática en cortes (solo montaje/video)."""
    if rules.get('cinematic_skip_shot_first_frame') is True:
        return True, 'rules/cinematic_skip_shot_first_frame'
    if rules.get('cinematic_skip_shot_boundaries') is True:
        return True, 'rules/cinematic_skip_shot_boundaries'
    return False, None


def anotar_error_toma(error, d, frame, fps, rules):
    info = cuadro_a_toma(d, frame, fps)
    if info:
        error['toma'] = info['id']
        if info['frame_inicio']:
            error['inicio_toma'] = True
            error['transicion_entrada'] = info.get('transicion_entrada')
    excl, fuente = exclusion_cinematica_contrato(rules)
    if excl and info and info['frame_inicio']:
        error['cinematica_omitida_por_regla'] = fuente
    elif info and info['frame_inicio'] and error.get('type') in ('ACELERACION_COM', 'VELOCIDAD_ANGULAR', 'ACELERACION', 'VELOCIDAD'):
        error['nota_continuidad'] = (
            'Picos en cuadro 1 de toma: el montaje usa corte exacto (montaje_cpu, camara_v2 MATCHCUT); '
            'fisica_final mide continuidad frame-a-frame; el contrato único no excluye cortes en cinemática.'
        )
    return error
