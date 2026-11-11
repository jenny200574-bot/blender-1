"""PISTA INMI (2026-11-01) TRADUCTOR (BORRADOR, gratis) del DSL de cámara de cada viñeta → especificación de keyframes de cámara para el 02N.
NO toca Blender ni el 02N: solo escribe cubos/SB/blender/esc_N_camara.json para cuando el 02N lo quiera leer.
Distancia cámara-personaje = lente × (altura del personaje × fracción visible del plano) / alto del sensor. La ALTURA sale SIEMPRE del
diseño de Blender de la escena (alturas_blender.altura); si no hay diseño, queda «por medir en 02N» (nunca se inventa)."""
import sb_comun as S

ROT = {'PAN', 'TILT', 'ROLL', 'WHIPPAN', 'ORBIT'}


def _dist(alt, plano, mm, aj):
    fr = (aj['encuadre_fraccion_altura_visible'] or {}).get(plano)
    if alt is None or fr is None or not mm: return None
    sensor_h = float(aj['sensor_ancho_mm']) * 9 / 16
    return round(float(mm) * float(alt) * fr / sensor_h, 3)


def traducir(sb, altura_de, aj=None):
    """sb = storyboard validado; altura_de(pid) -> (metros|None, fuente|None). Devuelve la especificación."""
    aj = aj or S.ajustes(); out = []; faltan = set()
    for v in sb['vinetas']:
        di, dc = v['director_imagen'], v['director_camara']; t0 = float(v['t'][0])
        obj = next((c['id'] for c in di['en_cuadro'] if c.get('profundidad') == 'frente'), (di['en_cuadro'] or [{}])[0].get('id'))
        alt, fuente = altura_de(obj) if obj else (None, None)
        if obj and alt is None: faltan.add(obj)
        mm = float(di['lente_mm']); plano = di['plano']; d = _dist(alt, plano, mm, aj)
        keys =[REDACTED]
        segs = []
        for a0, a1, c, args in S.comandos(S.analizar(dc['dsl_movimiento'])):
            ta = [round(t0 + float(a0), 3), round(t0 + float(a1), 3)] if a0 is not None else [round(t0, 3), round(float(v['t'][1]), 3)]
            curva = (aj.get('velocidad_a_curva') or {}).get(args.get('speed') or dc.get('velocidad'), 'lineal')
            segs.append({'t_abs': ta, 'movimiento': c, 'args': args, 'curva': curva})
            sr = args.get('size_range'); k = dict(keys[-1]); k['t'] = ta[1]
            if sr:
                k['plano'] = sr[1]
                if c in ('ZOOMIN', 'ZOOMOUT', 'CRASHZOOM'):
                    f0, f1 = aj['encuadre_fraccion_altura_visible'][sr[0]], aj['encuadre_fraccion_altura_visible'][sr[1]]
                    k['lente_mm'] = round(float(keys[-1]['lente_mm']) * f0 / f1, 1)
                else: k['distancia_m'] = _dist(alt, sr[1], k['lente_mm'], aj) if alt is not None else 'por medir en 02N'
            if c in ROT: k['giro_grados'] = float(args.get('degrees') or 0) or 'por decidir en 02N (el DSL no dio grados)'
            if c not in ('STATIC',) and (sr or c in ROT or c not in ('HANDHELD', 'STEADICAM')): keys.append(k)
        out.append({'vineta': v['id'], 't_abs': v['t'], 'objetivo': obj, 'altura_m': alt, 'altura_fuente': fuente or ('por medir en 02N' if obj else None),
                    'angulo': di['angulo'], 'lado_objetivo': next((c['lado'] for c in di['en_cuadro'] if c['id'] == obj), None),
                    'segmentos': segs, 'keyframes': keys, 'transicion_salida': v['transicion_salida']['tipo']})
    return {'version': 'sb_dsl_a_blender_borrador_v1', 'dsl_commit': S.DSL_COMMIT, 'sensor_mm': [aj['sensor_ancho_mm'], round(float(aj['sensor_ancho_mm']) * 9 / 16, 2)],
            'pista': 'BORRADOR: el 02N aún no lee este archivo. Distancias solo con alturas medidas del diseño de Blender.',
            'alturas_por_medir': sorted(faltan), 'vinetas': out}
