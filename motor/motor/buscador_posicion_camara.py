"""Buscador de posición de cámara dentro de los límites que el storyboard ya pidió.

No elige otro plano, otra lente, otra elevación ni otro roll. No abre el abanico
de acimut ni de distancia más allá de las listas ya escritas en la config: recorre
el intervalo cerrado de esas listas, porque la rejilla de puntos sueltos se salta
el único factor que a la vez encuadra y respeta la holgura. No importa bibliotecas numéricas externas.
No aprueba apariencia, física ni producción.
"""
import math
from fractions import Fraction

RESTRICCIONES = ('encuadre', 'holgura', 'eje_180', 'cara', 'inclinacion', 'roll')
SENSOR_MM = 36.0


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def xyz(v):
    if v is None:
        return None
    if hasattr(v, 'x'):
        return (float(v.x), float(v.y), float(v.z))
    if not isinstance(v, (list, tuple)) or len(v) < 3:
        return None
    if not all(_num(x) for x in v[:3]):
        return None
    return (float(v[0]), float(v[1]), float(v[2]))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v):
    n = math.sqrt(_dot(v, v))
    if n < 1e-12:
        return None
    return (v[0] / n, v[1] / n, v[2] / n)


def _horizontal(v):
    p = xyz(v)
    if p is None:
        return None
    n = math.hypot(p[0], p[1])
    if n < 1e-8:
        return None
    return (p[0] / n, p[1] / n, 0.0)


def _rotar_z(v, rad):
    c, s = math.cos(rad), math.sin(rad)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1], v[2])


def cuadro(t, fps):
    """Misma cuantización HALF_UP que seguridad.cuadro. El buscador no importa el motor entero."""
    v = Fraction(str(t)) * Fraction(str(fps))
    return (2 * v.numerator + v.denominator) // (2 * v.denominator)


def direccion(frente, az_deg, elev_deg):
    """Misma composición que emplazar: frente girado en acimut y luego elevado."""
    fv = _horizontal(frente)
    if fv is None:
        return None, None
    a = math.radians(az_deg)
    e = math.radians(elev_deg)
    rx, ry = fv[1], -fv[0]
    dh = _horizontal((fv[0] * math.cos(a) + rx * math.sin(a), fv[1] * math.cos(a) + ry * math.sin(a), 0.0))
    if dh is None:
        return None, None
    return dh, (dh[0] * math.cos(e), dh[1] * math.cos(e), math.sin(e))


def acimut_mundo(frente, az_deg):
    """Acimut mundo del offset cámara−mira. Lo usa el TRACK para no congelar el frente del primer cuadro."""
    dh, _ = direccion(frente, az_deg, 0.0)
    if dh is None:
        return None
    return math.atan2(dh[1], dh[0])


def colocar(mira, dh, elev_deg, distancia, altura_extra):
    e = math.radians(elev_deg)
    horizontal = distancia * math.cos(e)
    altura = distancia * math.sin(e) + altura_extra
    return (mira[0] + dh[0] * horizontal, mira[1] + dh[1] * horizontal, mira[2] + altura)


def ejes_camara(loc, look, roll, yaw):
    """-Z hacia el objetivo. El Y local, arriba de la imagen, se apoya en el Z mundo."""
    forward = _norm(_sub(look, loc))
    if forward is None:
        return None
    if yaw:
        forward = _norm(_rotar_z(forward, yaw))
        if forward is None:
            return None
    z_axis = _mul(forward, -1.0)
    # El Y local de la cámara es el «arriba» de la imagen y se apoya en el Z mundo.
    x_axis = _norm(_cruz((0.0, 0.0, 1.0), z_axis))
    if x_axis is None:
        x_axis = (1.0, 0.0, 0.0)
    y_axis = _norm(_cruz(z_axis, x_axis))
    if y_axis is None:
        return None
    if roll:
        c, s = math.cos(roll), math.sin(roll)
        x2 = _norm(_add(_mul(x_axis, c), _mul(y_axis, s)))
        y2 = _norm(_add(_mul(x_axis, -s), _mul(y_axis, c)))
        if x2 is None or y2 is None:
            return None
        x_axis, y_axis = x2, y2
    return x_axis, y_axis, z_axis


def proyectar(p, loc, ejes, lens, sensor, aspecto):
    d = _sub(p, loc)
    cx, cy, cz = _dot(d, ejes[0]), _dot(d, ejes[1]), _dot(d, ejes[2])
    if cz >= -1e-6:
        return None
    k = lens / sensor
    return (0.5 + k * cx / -cz, 0.5 + k * aspecto * cy / -cz, -cz)


def _pitch_roll(ejes):
    forward = _mul(ejes[2], -1.0)
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, forward[2]))))
    roll = math.degrees(math.atan2(ejes[0][2], ejes[1][2]))
    return pitch, roll


def _yaw_cara(frente, desde, hacia):
    fh = _horizontal(frente)
    if fh is None:
        return None
    d = _sub(hacia, desde)
    der = (fh[1], -fh[0], 0.0)
    lx = d[0] * der[0] + d[1] * der[1]
    lz = d[0] * fh[0] + d[1] * fh[1]
    return math.degrees(math.atan2(lx, lz))


def _signo_eje(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _holgura(dist, altura, ped):
    return min(ped['holgura_max_m'], ped['holgura_frac_distancia'] * dist, ped['holgura_frac_altura'] * altura)


def _ajustar(mira, dh, elev, distancia, altura_extra, puntos, ped, yaw, roll):
    look = mira
    sensor, lens, aspecto = ped['sensor_mm'], ped['lens_mm'], ped['aspecto']
    for _ in range(6):
        loc = colocar(look, dh, elev, distancia, altura_extra)
        ejes = ejes_camara(loc, look, roll, yaw)
        if ejes is None or not puntos:
            break
        qs = [q for q in (proyectar(p, loc, ejes, lens, sensor, aspecto) for p in puntos) if q]
        if not qs:
            break
        uc = sum(q[0] for q in qs) / len(qs)
        vt = max(q[1] for q in qs)
        sensor_h = sensor / aspecto
        look = (look[0], look[1], look[2] + (vt - (1.0 - ped['aire'])) * (distancia * sensor_h / lens))
        loc = colocar(look, dh, elev, distancia, altura_extra)
        ejes = ejes_camara(loc, look, roll, yaw)
        if ejes is None:
            break
        paso = (ped['xlado'] - uc) * (distancia * sensor / lens)
        right = ejes[0]
        look = (look[0] - right[0] * paso, look[1] - right[1] * paso, look[2] - right[2] * paso)
    loc = colocar(look, dh, elev, distancia, altura_extra)
    return look, loc, ejes_camara(loc, look, roll, yaw)


def fallos_muestra(daz, factor, muestra, ped, lado_visto):
    """Conjunto de restricciones que este cuadro no cumple. No relaja tolerancias."""
    mal = []
    if not muestra.get('modelado', True):
        return {'modelo'}, lado_visto
    frente = muestra.get('frente')
    mira = xyz(muestra.get('mira'))
    hf = muestra.get('hf')
    if frente is None or mira is None or not _num(hf) or hf <= 0 or not _num(ped['lens_mm']) or ped['lens_mm'] <= 0:
        return {'pedido'}, lado_visto
    dh, _ = direccion(frente, (ped['orient_deg'] or 0) + daz, ped['elev_deg'])
    if dh is None:
        return {'pedido'}, lado_visto
    sensor_h = ped['sensor_mm'] / ped['aspecto']
    distancia = hf * ped['lens_mm'] / sensor_h * factor * muestra.get('dist_mul', 1.0)
    if distancia <= 1e-4:
        return {'pedido'}, lado_visto
    roll = muestra.get('roll', 0.0) or 0.0
    yaw = muestra.get('yaw', 0.0) or 0.0
    altura_extra = muestra.get('altura_extra', 0.0) or 0.0
    _, loc, ejes = _ajustar(mira, dh, ped['elev_deg'], distancia, altura_extra, muestra.get('puntos') or [], ped, yaw, roll)
    if ejes is None:
        return {'pedido'}, lado_visto
    if not muestra.get('libre_inclin'):
        pitch, roll_med = _pitch_roll(ejes)
        if abs(pitch - (-ped['elev_deg'])) > ped['inclinacion_tol_deg']:
            mal.append('inclinacion')
        if abs(roll_med - math.degrees(roll)) > ped['roll_tol_deg'] and abs(abs(pitch) - 90) > 10:
            mal.append('roll')
    centro = xyz(muestra.get('centro')) or mira
    dist_centro = math.sqrt(_dot(_sub(centro, loc), _sub(centro, loc)))
    hol = _holgura(dist_centro, muestra.get('altura') or hf, ped)
    obs = muestra.get('obstaculo')
    if obs is not None:
        adentro, cerca, _nombre = obs(loc)
        if adentro or (cerca is not None and cerca < hol):
            mal.append('holgura')
    eje = muestra.get('eje')
    if eje and eje[0] and eje[1]:
        s = _signo_eje(eje[0], eje[1], loc)
        ref = ped.get('lado')
        if ref is None:
            ref = lado_visto
        if ref is None:
            lado_visto = s
        elif (s > 0) != (ref > 0):
            mal.append('eje_180')
    if not muestra.get('libre_encuadre'):
        puntos = muestra.get('puntos') or []
        if not puntos:
            mal.append('encuadre')
        else:
            pr = [proyectar(p, loc, ejes, ped['lens_mm'], ped['sensor_mm'], ped['aspecto']) for p in puntos]
            dentro = sum(1 for q in pr if q and 0 <= q[0] <= 1 and 0 <= q[1] <= 1)
            if dentro / len(pr) < ped['region_min']:
                mal.append('encuadre')
        if ped.get('cara_exigida', True):
            yaw_c = _yaw_cara(muestra.get('frente_cara') or frente, xyz(muestra.get('cabeza')) or mira, loc)
            if yaw_c is None or abs(yaw_c) > ped['max_cara_deg']:
                mal.append('cara')
    return set(mal), lado_visto


def fallos_de(daz, factor, ped):
    tot = {k: 0 for k in RESTRICCIONES}
    lado = ped.get('lado')
    for muestra in ped['muestras']:
        mal, lado = fallos_muestra(daz, factor, muestra, ped, lado if ped.get('lado') is not None else lado)
        if ped.get('lado') is None:
            # el lado de este candidato queda fijado por su primer cuadro, como el resolutor actual
            pass
        for k in mal:
            if k in tot:
                tot[k] += 1
            elif k == 'pedido':
                tot['encuadre'] += 1
    return tot


def _lista(valores):
    limpios = []
    for v in valores or []:
        if _num(v):
            limpios.append(float(v))
    if not limpios:
        raise ValueError('La lista de búsqueda está vacía; no se inventa un margen')
    return limpios


def _azimuts(lista):
    lo, hi = min(lista), max(lista)
    vals = list(lista)
    x = lo
    while x < hi - 1e-9:
        vals.append(x)
        x += 5.0
    vals.append(hi)
    if lo <= 0 <= hi:
        vals.append(0.0)
    return lo, hi, sorted(set(round(v, 4) for v in vals))


def _factores(lista):
    lo, hi = min(lista), max(lista)
    vals = list(lista)
    n = 21
    for i in range(n):
        vals.append(lo + (hi - lo) * i / (n - 1))
    return lo, hi, sorted(set(round(v, 4) for v in vals))


def _pasa(fallos):
    return sum(fallos.values()) == 0


def _refinar(daz, a, b, pasa_a, ped):
    hallados = []
    for _ in range(8):
        medio = (a + b) / 2
        ok = _pasa(fallos_de(daz, medio, ped))
        if ok:
            hallados.append(medio)
        if ok == pasa_a:
            a = medio
        else:
            b = medio
    return hallados


def efectos_de_segmentos(segmentos, f0, f1, fps, fracciones):
    """Traduce las órdenes ya pedidas a guiñada, grúa y factor de distancia por cuadro.

    Si una orden no está modelada, ese cuadro queda modelado=False y el buscador
    no declara imposible la toma: la deja en la rejilla existente.
    """
    fracciones = fracciones or {}

    def fr(t):
        return 1 + cuadro(t, fps)

    def fr_fin(t):
        return cuadro(t, fps)

    if not segmentos:
        segmentos = [{'t0': 0.0, 't1': 0.0, 'movimiento': 'STATIC', 'args': {}}]
    completo = True
    yaw = 0.0
    altura_extra = 0.0
    dist_mul = 1.0
    out = {f: None for f in range(f0, f1 + 1)}
    for i, s in enumerate(segmentos):
        g0 = max(f0, fr(float(s['t0'])))
        g1 = f1 if i == len(segmentos) - 1 else min(f1, max(g0, fr_fin(float(s['t1']))))
        mv = s.get('movimiento') or 'STATIC'
        ar = s.get('args') or {}
        mira_sigue = True
        seguir_frente = False
        libre_e = False
        libre_i = False
        modelado = True
        yaw1, alt1, mul1 = yaw, altura_extra, dist_mul
        if mv in ('STATIC', 'TRIPOD'):
            mira_sigue = False
        elif mv in ('TRACK', 'TRACKSIDE'):
            seguir_frente = True
        elif mv in ('FOLLOW', 'LEAD'):
            modelado = False
        elif mv in ('PAN', 'WHIPPAN'):
            mira_sigue = False
            libre_e = True
            libre_i = True
            g = ar.get('degrees')
            if isinstance(g, (int, float)) and not isinstance(g, bool):
                sgn = -1.0 if str(ar.get('dir_lr') or '').upper() == 'R' else 1.0
                yaw1 = yaw + math.radians(float(g)) * sgn
            else:
                modelado = False
        elif mv in ('TILT', 'ROLL'):
            mira_sigue = False
            libre_e = True
            libre_i = True
            modelado = False
        elif mv in ('CRANE', 'PEDESTAL', 'BOOM'):
            dd = ar.get('distance')
            if isinstance(dd, (int, float)) and not isinstance(dd, bool):
                sgn = 1.0 if str(ar.get('dir_ud') or '').upper() == 'UP' else -1.0
                alt1 = altura_extra + float(dd) * sgn
            else:
                modelado = False
        elif mv in ('DOLLYIN', 'DOLLYOUT', 'PUSH', 'PULL'):
            sr = ar.get('size_range')
            if isinstance(sr, (list, tuple)) and len(sr) == 2 and sr[0] in fracciones and sr[1] in fracciones and fracciones[sr[0]]:
                mul1 = dist_mul * (float(fracciones[sr[1]]) / float(fracciones[sr[0]]))
            elif isinstance(ar.get('percent'), (int, float)) and not isinstance(ar.get('percent'), bool):
                sgn = -1.0 if mv in ('DOLLYIN', 'PUSH') else 1.0
                mul1 = dist_mul * (1.0 + sgn * float(ar['percent']) / 100.0)
            else:
                modelado = False
        elif mv in ('HANDHELD', 'SHOULDER', 'STEADICAM', 'GIMBAL', 'SLIDER'):
            mira_sigue = False
        else:
            modelado = False
            mira_sigue = False
        if not modelado:
            completo = False
        for f in range(g0, g1 + 1):
            if f < f0 or f > f1:
                continue
            u = 0.0 if g1 == g0 else (f - g0) / (g1 - g0)
            out[f] = {
                'seguir_frente': seguir_frente,
                'mira_sigue': mira_sigue,
                'nueva_ancla': f == g0,
                'yaw': yaw + (yaw1 - yaw) * u,
                'altura_extra': altura_extra + (alt1 - altura_extra) * u,
                'dist_mul': dist_mul + (mul1 - dist_mul) * u,
                'libre_encuadre': libre_e,
                'libre_inclin': libre_i,
                'modelado': modelado,
            }
        yaw, altura_extra, dist_mul = yaw1, alt1, mul1
    for f in range(f0, f1 + 1):
        if out[f] is None:
            completo = False
            out[f] = {
                'seguir_frente': False, 'mira_sigue': False, 'nueva_ancla': False, 'yaw': yaw,
                'altura_extra': altura_extra, 'dist_mul': dist_mul, 'libre_encuadre': False,
                'libre_inclin': False, 'modelado': False,
            }
    return out, completo


def _clave(daz, factor):
    return (round(float(daz), 4), round(float(factor), 4))


def _candidato(daz, factor):
    return {'az_extra_deg': float(daz), 'factor_distancia': float(factor)}


def sin_modelo(motivo):
    return {
        'modelo_completo': False,
        'resuelto_geometrico': False,
        'rejilla_discreta_resuelve': False,
        'examinados': 0,
        'restricciones': [{'nombre': 'modelo', 'estado': 'incompleto', 'detalle': motivo}],
        'incompatibles': [],
        'motivo': motivo,
        'candidato': None,
        'propuestas': [],
        'production_approved': False,
    }


def _resumen_restricciones(examinados):
    cuentas = {k: 0 for k in RESTRICCIONES}
    for item in examinados:
        for k in RESTRICCIONES:
            if item['fallos'][k] == 0:
                cuentas[k] += 1
    mejor = min(examinados, key=lambda item: (sum(item['fallos'].values()), abs(item['daz']), abs(item['factor'] - 1)))
    filas = []
    for k in RESTRICCIONES:
        if cuentas[k] == 0:
            estado = 'sin_solucion'
        elif mejor['fallos'][k]:
            estado = 'falla'
        else:
            estado = 'pasa'
        filas.append({
            'nombre': k,
            'estado': estado,
            'candidatos_que_la_cumplen': cuentas[k],
            'muestras_fallidas_en_el_mejor': mejor['fallos'][k],
        })
    incompatibles = []
    nombres = list(RESTRICCIONES)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            if cuentas[a] and cuentas[b] and not any(item['fallos'][a] == 0 and item['fallos'][b] == 0 for item in examinados):
                incompatibles.append([a, b])
    return filas, incompatibles, mejor


def buscar(pedido):
    """Devuelve un candidato dentro del intervalo ya autorizado, o el cruce vacío de restricciones."""
    if not isinstance(pedido, dict):
        raise ValueError('El pedido del buscador no es un objeto')
    if float(pedido.get('sensor_mm') or 0) != SENSOR_MM:
        raise ValueError('sensor_mm debe ser 36; no se inventa otro ancho')
    for clave in ('lens_mm', 'aspecto', 'elev_deg', 'orient_deg', 'aire', 'xlado', 'region_min', 'max_cara_deg', 'inclinacion_tol_deg', 'roll_tol_deg', 'holgura_max_m', 'holgura_frac_distancia', 'holgura_frac_altura'):
        if not _num(pedido.get(clave)):
            raise ValueError('Falta el número ya medido o ya configurado: ' + clave)
    if pedido['lens_mm'] <= 0 or pedido['aspecto'] <= 0 or pedido['holgura_max_m'] <= 0:
        raise ValueError('Lente, aspecto u holgura no son válidos; no se sustituyen')
    muestras = pedido.get('muestras') or []
    if not muestras:
        return sin_modelo('No hay cuadros medidos; no se coloca la cámara')
    if any(not m.get('modelado', True) for m in muestras):
        az = _lista(pedido.get('azimuts_deg'))
        fac = _lista(pedido.get('factores'))
        out = sin_modelo('Hay un movimiento sin modelo matemático. No se declara imposible ni se cambia la orden: sigue la rejilla ya existente.')
        out['propuestas'] = [_candidato(a, f) for a in az for f in fac]
        return out
    az_lista = _lista(pedido.get('azimuts_deg'))
    fac_lista = _lista(pedido.get('factores'))
    _lo_a, _hi_a, azimuts = _azimuts(az_lista)
    flo, fhi, factores = _factores(fac_lista)
    examinados = []
    vistos = set()
    buenos = []

    def anotar(daz, factor):
        clave = _clave(daz, factor)
        if clave in vistos or not (min(az_lista) - 1e-6 <= daz <= max(az_lista) + 1e-6 and flo - 1e-6 <= factor <= fhi + 1e-6):
            return None
        vistos.add(clave)
        fallos = fallos_de(daz, factor, pedido)
        fila = {'daz': clave[0], 'factor': clave[1], 'fallos': fallos}
        examinados.append(fila)
        if _pasa(fallos):
            buenos.append(fila)
        return fila

    discretos = [(a, f) for a in az_lista for f in fac_lista]
    pedido_directo = anotar(0.0, 1.0)
    if pedido_directo is not None and _pasa(pedido_directo['fallos']):
        propuestas = [_candidato(0.0, 1.0)]
        for daz, factor in discretos:
            if _clave(daz, factor) != (0.0, 1.0):
                propuestas.append(_candidato(daz, factor))
        return {
            'modelo_completo': True,
            'resuelto_geometrico': True,
            'rejilla_discreta_resuelve': True,
            'examinados': len(examinados),
            'restricciones': [{'nombre': k, 'estado': 'pasa', 'candidatos_que_la_cumplen': 1, 'muestras_fallidas_en_el_mejor': 0} for k in RESTRICCIONES],
            'incompatibles': [],
            'motivo': 'La posición pedida, sin acimut extra ni otro factor de distancia, ya cumple las restricciones.',
            'candidato': _candidato(0.0, 1.0),
            'propuestas': propuestas,
            'production_approved': False,
        }
    for daz, factor in discretos:
        anotar(daz, factor)
    rejilla_ok = any(_pasa(item['fallos']) for item in examinados)
    for daz in azimuts:
        muestras_f = []
        for factor in factores:
            fila = anotar(daz, factor)
            if fila is not None:
                muestras_f.append(fila)
        muestras_f.sort(key=lambda item: item['factor'])
        for i in range(len(muestras_f) - 1):
            a, b = muestras_f[i], muestras_f[i + 1]
            if _pasa(a['fallos']) == _pasa(b['fallos']):
                continue
            for medio in _refinar(daz, a['factor'], b['factor'], _pasa(a['fallos']), pedido):
                anotar(daz, medio)
    filas, incompatibles, mejor = _resumen_restricciones(examinados)
    buenos.sort(key=lambda item: (abs(item['daz']), abs(item['factor'] - 1.0), abs(item['daz']) + abs(item['factor'] - 1.0)))
    if buenos:
        elegido = buenos[0]
        motivo = 'Hay posición dentro del acimut y la distancia ya autorizados que cumple holgura, encuadre, eje, cara, inclinación y roll.'
        if not rejilla_ok:
            motivo += ' La rejilla discreta no la contenía.'
    else:
        elegido = None
        vacias = [f['nombre'] for f in filas if f['estado'] == 'sin_solucion']
        cruce = ['+'.join(par) for par in incompatibles]
        motivo = 'Sin solución dentro de los límites ya pedidos.'
        if vacias:
            motivo += ' Ningún candidato cumple: ' + ', '.join(vacias) + '.'
        if cruce:
            motivo += ' Cruces vacíos: ' + ', '.join(cruce) + '.'
    propuestas = []
    vistos_p = set()

    def meter(daz, factor):
        clave = _clave(daz, factor)
        if clave in vistos_p:
            return
        vistos_p.add(clave)
        propuestas.append(_candidato(clave[0], clave[1]))

    if elegido is not None:
        meter(elegido['daz'], elegido['factor'])
        for item in buenos[1:8]:
            meter(item['daz'], item['factor'])
    else:
        meter(mejor['daz'], mejor['factor'])
    for daz, factor in discretos:
        meter(daz, factor)
    return {
        'modelo_completo': True,
        'resuelto_geometrico': elegido is not None,
        'rejilla_discreta_resuelve': rejilla_ok,
        'examinados': len(examinados),
        'restricciones': filas,
        'incompatibles': incompatibles,
        'motivo': motivo,
        'candidato': None if elegido is None else _candidato(elegido['daz'], elegido['factor']),
        'propuestas': propuestas,
        'production_approved': False,
    }


def resumen(informe):
    """Copia serializable. No incluye geometría de la escena ni funciones."""
    if not isinstance(informe, dict):
        return {'modelo_completo': False, 'motivo': 'sin informe', 'production_approved': False}
    return {
        'modelo_completo': bool(informe.get('modelo_completo')),
        'resuelto_geometrico': bool(informe.get('resuelto_geometrico')),
        'rejilla_discreta_resuelve': bool(informe.get('rejilla_discreta_resuelve')),
        'examinados': informe.get('examinados') or 0,
        'restricciones': informe.get('restricciones') or [],
        'incompatibles': informe.get('incompatibles') or [],
        'motivo': informe.get('motivo'),
        'candidato': informe.get('candidato'),
        'production_approved': False,
    }
