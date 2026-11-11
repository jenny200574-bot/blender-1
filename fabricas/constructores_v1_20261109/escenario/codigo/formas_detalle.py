"""formas_detalle.py — biblioteca de formas y de OPERACIONES geométricas para el escenario detallado (US$0, sin red).

Universal: no conoce ningún lugar, canal ni guion. Trabaja con piezas en metros absolutos
(x este, y norte, z arriba) y las entrega en el formato de blender_auto.py v6:
  caja (x_m/y_m/z_m, o centro_m + tam_m + rot_grados), cilindro_eje (a_m, b_m, radio_m),
  esfera (centro_m, radio_m), toro (centro_m, radio_mayor_m, radio_menor_m, rot_grados), poliedro (vertices_m).

Partes que puede pedir la respuesta (coordenadas LOCALES del objeto: origen en el centro de su base,
x a la derecha, y hacia atrás, z arriba; luego se gira rot_z_grados y se lleva a pos_m):
  caja      {centro_m, tam_m, rot_grados?}
  tramo     {a_m, b_m, radio_m}                    cilindro entre dos puntos (patas, cables, tubos)
  cilindro  {centro_m, radio_m, alto_m, rot_grados?}
  esfera    {centro_m, radio_m}
  toro      {centro_m, radio_mayor_m, radio_menor_m, rot_grados?}
  tubo      {centro_m, radio_ext_m, radio_int_m, alto_m, segmentos?, ancla?}   anillo hueco hecho de bloques.
            CONVENCIÓN: ancla 'base' (por defecto) = centro_m es el CENTRO DE LA BASE (el tubo va de z a z+alto_m);
            ancla 'centro' = centro_m es el centro del volumen (va de z−alto_m/2 a z+alto_m/2), igual que cilindro.
  placa     {centro_m, radio_m, espesor_m, rot_grados?}               disco fino
  cono      {a_m, b_m, radio_a_m, radio_b_m}        cono o tronco de cono entre dos puntos (radio_b_m 0 = punta)
  poliedro  {vertices_m}                            trozo convexo libre

OPERACIONES (cambios entre estados; lista cerrada y neutra; el QUÉ pasa lo describe la respuesta en texto):
  retirar, desplazar, girar, fragmentar, deformar, abrir_hueco, agregar, cambiar_color_guia
"""
import math, random

OPERACIONES = {
    'retirar': 'el objetivo deja de estar en el lugar desde este estado. parametros: {}',
    'desplazar': 'mueve el objetivo entero. parametros: {"d_m": [dx, dy, dz], "al_piso": true|false} '
                 '(dz > 0 lo separa del apoyo; al_piso true = después de mover, lo baja hasta tocar el piso)',
    'girar': 'gira el objetivo entero sobre su centro. parametros: {"grados": [rx, ry, rz], "mantener_base": true|false} '
             '(mantener_base true = tras girar, su punto más bajo queda a la misma altura que antes)',
    'fragmentar': 'parte el objetivo en trozos irregulares. parametros: {"trozos": n>=2, "separacion_m": s, '
                  '"angulo_max_grados": a, "caida": "en_sitio"|"al_piso", "semilla": entero}',
    'deformar': 'dobla el objetivo sin partirlo. parametros: {"modo": "curvar"|"inclinar", "amplitud_m": a, '
                '"segmentos": n>=3, "direccion": [dx, dy] (opcional; en un límite, por defecto hacia el centro del piso)}',
    'abrir_hueco': 'abre un hueco en un límite. parametros: {"u_m": centro a lo largo del límite desde su centro, '
                   '"z0_m": borde de abajo, "ancho_m": w, "alto_m": h, "restos": n trozos, "lado_restos": "dentro"|"fuera", '
                   '"borde_irregular": true|false, "semilla": entero}',
    'agregar': 'aparece un objeto nuevo desde este estado. parametros: {"objeto": <objeto con el mismo formato de capa3>}',
    'cambiar_color_guia': 'cambia el color guía de render. parametros: {"color_guia_rgb": [r, g, b]}',
}
PARTES = ('caja', 'tramo', 'cilindro', 'esfera', 'toro', 'tubo', 'placa', 'poliedro', 'cono')

# ---------------- álgebra mínima 3x3 ----------------
def mmul(A, B): return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mv(A, v): return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]
def add(a, b): return [x + y for x, y in zip(a, b)]
def sub(a, b): return [x - y for x, y in zip(a, b)]
def esc(a, k): return [x * k for x in a]
def norma(a): return math.sqrt(sum(x * x for x in a))
def unit(a):
    n = norma(a); return [x / n for x in a] if n > 1e-12 else [0.0, 0.0, 1.0]
def cruz(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
I3 = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
def rx(a): c, s = math.cos(a), math.sin(a); return [[1, 0, 0], [0, c, -s], [0, s, c]]
def ry(a): c, s = math.cos(a), math.sin(a); return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
def rz(a): c, s = math.cos(a), math.sin(a); return [[c, -s, 0], [s, c, 0], [0, 0, 1]]
def euler_a_m(g):
    """Euler XYZ de Blender (grados) -> matriz R = Rz·Ry·Rx"""
    a, b, c = [math.radians(float(x)) for x in (g or [0, 0, 0])]
    return mmul(rz(c), mmul(ry(b), rx(a)))
def m_a_euler(R):
    """matriz -> Euler XYZ (grados) de Blender"""
    sy = -R[2][0]; sy = max(-1.0, min(1.0, sy)); b = math.asin(sy)
    if abs(math.cos(b)) > 1e-6:
        a = math.atan2(R[2][1], R[2][2]); c = math.atan2(R[1][0], R[0][0])
    else:
        a = math.atan2(-R[1][2], R[1][1]); c = 0.0
    return [round(math.degrees(x), 4) for x in (a, b, c)]
def eje_angulo(eje, ang):
    x, y, z = unit(eje); c, s = math.cos(ang), math.sin(ang); C = 1 - c
    return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C]]

# ---------------- pieza interna (absoluta) ----------------
# {'t': 'caja', 'c', 's', 'R'} | {'t': 'cil', 'a', 'b', 'r'} | {'t': 'esf', 'c', 'r'} | {'t': 'toro', 'c', 'R_', 'r', 'R'} | {'t': 'pol', 'v'}

def parte_a_piezas(p, T):
    """parte local -> piezas internas absolutas; T(v) lleva un punto local a absoluto, Rg es su giro"""
    t = p['tipo']; fx, Rg = T; nom = p.get('nombre')
    base = {'nombre': nom, 'color': p.get('color_guia_rgb')}
    if t == 'caja':
        return [dict(base, t='caja', c=fx(p['centro_m']), s=[float(v) for v in p['tam_m']], R=mmul(Rg, euler_a_m(p.get('rot_grados'))))]
    if t == 'tramo':
        return [dict(base, t='cil', a=fx(p['a_m']), b=fx(p['b_m']), r=float(p['radio_m']))]
    if t in ('cilindro', 'placa'):
        h = float(p['alto_m'] if t == 'cilindro' else p['espesor_m']); R = euler_a_m(p.get('rot_grados'))
        d = mv(R, [0, 0, h / 2]); c = p['centro_m']
        return [dict(base, t='cil', a=fx(sub(c, d)), b=fx(add(c, d)), r=float(p['radio_m']))]
    if t == 'esfera':
        return [dict(base, t='esf', c=fx(p['centro_m']), r=float(p['radio_m']))]
    if t == 'toro':
        return [dict(base, t='toro', c=fx(p['centro_m']), R_=float(p['radio_mayor_m']), r=float(p['radio_menor_m']),
                     R=mmul(Rg, euler_a_m(p.get('rot_grados'))))]
    if t == 'tubo':
        n = int(p.get('segmentos') or 12); re_, ri = float(p['radio_ext_m']), float(p['radio_int_m']); h = float(p['alto_m'])
        rm = (re_ + ri) / 2; grosor = re_ - ri; largo = 2 * re_ * math.tan(math.pi / n)
        c0 = list(p['centro_m']); out = []
        anc = p.get('ancla', 'base')
        if anc not in ('base', 'centro'): raise ValueError(f"tubo {nom}: ancla debe ser 'base' o 'centro', no {anc!r}")
        if anc == 'centro': c0[2] -= h / 2          # a centro de la base
        for k in range(n):
            a = 2 * math.pi * k / n
            cl = [c0[0] + rm * math.cos(a), c0[1] + rm * math.sin(a), c0[2] + h / 2]
            out.append(dict(base, t='caja', c=fx(cl), s=[grosor, largo, h], R=mmul(Rg, rz(a)), nombre=f'{nom or "tubo"}_{k:02d}'))
        return out
    if t == 'poliedro':
        return [dict(base, t='pol', v=[fx(v) for v in p['vertices_m']])]
    if t == 'cono':
        return [dict(base, t='cono', a=fx(p['a_m']), b=fx(p['b_m']), ra=float(p['radio_a_m']), rb=float(p['radio_b_m']))]
    raise ValueError(f'parte desconocida: {t}')

def transformador(pos_m, rot_z, base_z):
    R = rz(math.radians(float(rot_z or 0)))
    def fx(v):
        w = mv(R, [float(v[0]), float(v[1]), float(v[2])])
        return [w[0] + float(pos_m[0]), w[1] + float(pos_m[1]), w[2] + float(base_z)]
    return fx, R

# ---------------- cajas límite (bbox) ----------------
def esquinas_caja(p):
    out = []
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                out.append(add(p['c'], mv(p['R'], [i * p['s'][0] / 2, j * p['s'][1] / 2, k * p['s'][2] / 2])))
    return out

def bbox_pieza(p):
    t = p['t']
    if t == 'caja':
        vs = esquinas_caja(p)
    elif t == 'pol':
        vs = p['v']
    elif t == 'cil':
        d = sub(p['b'], p['a']); L = norma(d); n = unit(d); r = p['r']
        e = [r * math.sqrt(max(0.0, 1 - n[i] ** 2)) for i in range(3)]
        mn = [min(p['a'][i], p['b'][i]) - e[i] for i in range(3)]; mx = [max(p['a'][i], p['b'][i]) + e[i] for i in range(3)]
        return mn, mx
    elif t == 'esf':
        return [x - p['r'] for x in p['c']], [x + p['r'] for x in p['c']]
    elif t == 'cono':
        n = unit(sub(p['b'], p['a'])); e = [math.sqrt(max(0.0, 1 - n[i] ** 2)) for i in range(3)]
        mn = [min(p['a'][i] - p['ra'] * e[i], p['b'][i] - p['rb'] * e[i]) for i in range(3)]
        mx = [max(p['a'][i] + p['ra'] * e[i], p['b'][i] + p['rb'] * e[i]) for i in range(3)]
        return mn, mx
    elif t == 'toro':
        n = mv(p['R'], [0, 0, 1]); e = [p['R_'] * math.sqrt(max(0.0, 1 - n[i] ** 2)) + p['r'] for i in range(3)]
        return [p['c'][i] - e[i] for i in range(3)], [p['c'][i] + e[i] for i in range(3)]
    return [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]

def bbox(piezas):
    bs = [bbox_pieza(p) for p in piezas]
    return [min(b[0][i] for b in bs) for i in range(3)], [max(b[1][i] for b in bs) for i in range(3)]

def centro_de(piezas):
    mn, mx = bbox(piezas); return [(a + b) / 2 for a, b in zip(mn, mx)]

# ---------------- transformaciones rígidas ----------------
def mover_pieza(p, R, piv, d):
    """gira con R alrededor de piv y luego desplaza d"""
    f = lambda v: add(add(piv, mv(R, sub(v, piv))), d)
    q = dict(p); t = p['t']
    if t in ('caja', 'esf', 'toro'): q['c'] = f(p['c'])
    if t in ('caja', 'toro'): q['R'] = mmul(R, p['R'])
    if t in ('cil', 'cono'): q['a'] = f(p['a']); q['b'] = f(p['b'])
    if t == 'pol': q['v'] = [f(v) for v in p['v']]
    return q

def desplazar(piezas, d): return [mover_pieza(p, I3, [0, 0, 0], [float(x) for x in d]) for p in piezas]
def girar(piezas, grados, piv=None):
    piv = piv or centro_de(piezas); R = euler_a_m(grados)
    return [mover_pieza(p, R, piv, [0, 0, 0]) for p in piezas]

# ---------------- fragmentar ----------------
def _trozos_caja(p, n, rnd):
    """corta una caja en n trozos convexos con cortes inclinados (planos), a lo largo de su eje más largo"""
    s = p['s']; k = max(range(3), key=lambda i: s[i]); u, v = [i for i in range(3) if i != k]
    L = s[k]; cortes = [-L / 2]
    for j in range(1, n):
        cortes.append(-L / 2 + L * j / n + rnd.uniform(-0.12, 0.12) * L / n)
    cortes.append(L / 2)
    incl = [(0.0, 0.0)] + [(rnd.uniform(-0.35, 0.35) * L / n / max(s[u], 1e-3), rnd.uniform(-0.35, 0.35) * L / n / max(s[v], 1e-3)) for _ in range(n - 1)] + [(0.0, 0.0)]
    out = []
    for j in range(n):
        vs = []
        for jj in (j, j + 1):
            for su in (-1, 1):
                for sv in (-1, 1):
                    loc = [0.0, 0.0, 0.0]; loc[u] = su * s[u] / 2; loc[v] = sv * s[v] / 2
                    loc[k] = max(-L / 2, min(L / 2, cortes[jj] + incl[jj][0] * loc[u] + incl[jj][1] * loc[v]))
                    vs.append(add(p['c'], mv(p['R'], loc)))
        out.append({'t': 'pol', 'v': vs, 'nombre': f"{p.get('nombre') or 'pieza'}_t{j + 1}", 'color': p.get('color'),
                    '_eje': mv(p['R'], [1.0 if i == k else 0.0 for i in range(3)]), '_j': j - (n - 1) / 2})
    return out

def fragmentar(piezas, prm, z_piso=0.0):
    n = max(2, int(prm.get('trozos') or 3)); sep = float(prm.get('separacion_m') or 0.05)
    amax = float(prm.get('angulo_max_grados') or 15); rnd = random.Random(int(prm.get('semilla') or 1))
    caida = prm.get('caida') or 'en_sitio'; out = []
    zmin0, zmax0 = bbox(piezas)[0][2], bbox(piezas)[1][2]
    for p in piezas:
        if p['t'] == 'caja':
            tr = _trozos_caja(p, n, rnd)
        elif p['t'] == 'pol':                                    # un trozo se vuelve a partir por su caja envolvente
            mn, mx = bbox_pieza(p)
            tr = _trozos_caja({'c': [(a + b) / 2 for a, b in zip(mn, mx)], 's': sub(mx, mn), 'R': I3, 'nombre': p.get('nombre'), 'color': p.get('color')}, n, rnd)
        elif p['t'] in ('cil', 'cono'):                          # tramo o cono: dos mitades
            m = esc(add(p['a'], p['b']), 0.5); d = unit(sub(p['b'], p['a']))
            tr = [dict(p, b=sub(m, esc(d, 0.01)), nombre=f"{p.get('nombre') or 'tramo'}_t1", _eje=d, _j=-0.5),
                  dict(p, a=add(m, esc(d, 0.01)), nombre=f"{p.get('nombre') or 'tramo'}_t2", _eje=d, _j=0.5)]
            if p['t'] == 'cono':
                rm = (p['ra'] + p['rb']) / 2; tr[0]['rb'] = rm; tr[1]['ra'] = rm
        else:
            out.append(p); continue
        for q in tr:
            cq = centro_de([q])
            g = [rnd.uniform(-amax, amax) for _ in range(3)]
            q2 = mover_pieza(q, euler_a_m(g), cq, esc(q.pop('_eje'), q.pop('_j') * sep * 2))
            if caida == 'al_piso':
                mn, _ = bbox_pieza(q2); q2 = mover_pieza(q2, I3, [0, 0, 0], [0, 0, z_piso - mn[2]])
            else:                                                # en_sitio: cada trozo se queda dentro de la altura que tenía el objeto
                mn, mx = bbox_pieza(q2); dz = 0.0
                if mx[2] > zmax0: dz = zmax0 - mx[2]
                if mn[2] + dz < zmin0: dz = zmin0 - mn[2]
                if dz: q2 = mover_pieza(q2, I3, [0, 0, 0], [0, 0, dz])
            out.append(q2)
    return out

# ---------------- deformar ----------------
def deformar(piezas, prm, hacia=None):
    modo = prm.get('modo') or 'curvar'; A = float(prm.get('amplitud_m') or 0.1); m = max(3, int(prm.get('segmentos') or 7))
    out = []
    for p in piezas:
        if p['t'] != 'caja':
            out.append(p); continue
        s = p['s']
        if modo == 'inclinar':                                  # capas en z que se corren cada vez más
            d = unit([*(prm.get('direccion') or hacia or [1, 0])[:2], 0.0]); h = s[2]
            for i in range(m):
                z = -h / 2 + h * (i + 0.5) / m; off = A * (i + 0.5) / m
                out.append(dict(p, c=add(add(p['c'], mv(p['R'], [0, 0, z])), esc(d, off)), s=[s[0], s[1], h / m * 1.02],
                                nombre=f"{p.get('nombre') or 'pieza'}_c{i + 1}"))
            continue
        hor = [0, 1]; k = max(hor, key=lambda i: s[i])           # curvar: tramos a lo largo del eje horizontal más largo
        ek = mv(p['R'], [1.0 if i == k else 0.0 for i in range(3)])
        d = prm.get('direccion') or hacia
        if d is None: d = mv(p['R'], [1.0 if i == (1 - k) else 0.0 for i in range(3)])
        d = unit([float(d[0]), float(d[1]), 0.0]); L = s[k]
        eje_giro = cruz(ek, d)
        for i in range(m):
            t = (i + 0.5) / m; x = -L / 2 + L * t
            off = A * math.sin(math.pi * t); der = A * math.pi / L * math.cos(math.pi * t)
            R = mmul(eje_angulo(eje_giro, math.atan(der)), p['R']) if norma(eje_giro) > 1e-9 else p['R']
            sz = list(s); sz[k] = L / m * 1.04
            c = add(add(p['c'], esc(ek, x)), esc(d, off))
            if i in (0, m - 1):                                  # los tramos de las puntas no salen del largo original
                fuera = L / m * 0.02 + s[1 - k] / 2 * abs(math.sin(math.atan(der))) + 1e-4
                sz[k] -= fuera; c = add(c, esc(ek, fuera / 2 if i == 0 else -fuera / 2))
            out.append(dict(p, c=c, s=sz, R=R, nombre=f"{p.get('nombre') or 'pieza'}_s{i + 1}"))
    return out

# ---------------- hueco en un límite (caja alineada) ----------------
def abrir_hueco(lim, prm):
    """lim: {'x_m','y_m','z_m'} alineado. Devuelve (lista de cajas que quedan, info del hueco en absoluto)"""
    (x0, x1), (y0, y1), (z0, z1) = lim['x_m'], lim['y_m'], lim['z_m']
    largo_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if largo_x else (y0, y1); cm = (a0 + a1) / 2
    u = cm + float(prm.get('u_m') or 0); w = float(prm['ancho_m']); h = float(prm['alto_m']); hz0 = float(prm.get('z0_m') or 0)
    h0, h1 = max(a0, u - w / 2), min(a1, u + w / 2); v0, v1 = max(z0, hz0), min(z1, hz0 + h)
    trozos = []
    def caja_a(b0, b1, c0, c1):
        if b1 - b0 > 1e-3 and c1 - c0 > 1e-3:
            trozos.append({'x_m': [b0, b1] if largo_x else [x0, x1], 'y_m': [y0, y1] if largo_x else [b0, b1], 'z_m': [c0, c1]})
    caja_a(a0, h0, z0, z1); caja_a(h1, a1, z0, z1); caja_a(h0, h1, z0, v0); caja_a(h0, h1, v1, z1)
    info = {'largo_x': largo_x, 'h0': h0, 'h1': h1, 'v0': v0, 'v1': v1, 'grueso': (y0, y1) if largo_x else (x0, x1)}
    return trozos, info

def restos_de_hueco(info, prm, lado_signo, color=None):
    """trozos (poliedros) en el piso junto al hueco y, si borde_irregular, dientes en el borde del hueco"""
    rnd = random.Random(int(prm.get('semilla') or 7)); n = int(prm.get('restos') or 0); out = []
    g0, g1 = info['grueso']; gm = (g0 + g1) / 2; e = g1 - g0
    def punto(a, g, z): return [a, g, z] if info['largo_x'] else [g, a, z]
    for i in range(n):
        a = rnd.uniform(info['h0'], info['h1']); g = gm + lado_signo * rnd.uniform(e + 0.15, e + 1.0)
        tam = rnd.uniform(0.12, 0.3)
        vs = [punto(a + rnd.uniform(-tam, tam) / 2, g + rnd.uniform(-tam, tam) / 2, rnd.uniform(0, tam * 0.6)) for _ in range(7)]
        vs.append(punto(a, g, 0.0))
        out.append({'t': 'pol', 'v': vs, 'nombre': f'resto_{i + 1:02d}', 'color': color})
    if prm.get('borde_irregular'):
        for i in range(10):                                   # dientes sobre los cuatro bordes del hueco
            lado = i % 4; tam = rnd.uniform(0.08, 0.18)
            if lado < 2:
                a = info['h0'] if lado == 0 else info['h1']; z = rnd.uniform(info['v0'] + 0.1, info['v1'] - 0.1)
                da = tam if lado == 0 else -tam
                vs = [punto(a, g0, z - tam), punto(a, g1, z - tam), punto(a, g0, z + tam), punto(a, g1, z + tam), punto(a + da, gm, z + rnd.uniform(-tam, tam) / 2)]
            else:
                z = info['v0'] if lado == 2 else info['v1']; a = rnd.uniform(info['h0'] + 0.1, info['h1'] - 0.1)
                dz = tam if lado == 2 else -tam
                if z <= 1e-3 and lado == 2: continue
                vs = [punto(a - tam, g0, z), punto(a + tam, g0, z), punto(a - tam, g1, z), punto(a + tam, g1, z), punto(a + rnd.uniform(-tam, tam) / 2, gm, z + dz)]
            out.append({'t': 'pol', 'v': vs, 'nombre': f'borde_{i + 1:02d}', 'color': color})
    return out

# ---------------- salida al formato de blender_auto ----------------
def a_blender(p, nombre, color_def):
    r = lambda v: [round(float(x), 4) for x in v]
    col = p.get('color') or color_def
    t = p['t']
    if t == 'caja':
        e = m_a_euler(p['R'])
        if all(abs(x) < 1e-6 for x in e):
            c, s = p['c'], p['s']
            q = {'tipo': 'caja', 'x_m': r([c[0] - s[0] / 2, c[0] + s[0] / 2]), 'y_m': r([c[1] - s[1] / 2, c[1] + s[1] / 2]), 'z_m': r([c[2] - s[2] / 2, c[2] + s[2] / 2])}
        else:
            q = {'tipo': 'caja', 'centro_m': r(p['c']), 'tam_m': r(p['s']), 'rot_grados': e}
    elif t == 'cil':
        q = {'tipo': 'cilindro_eje', 'a_m': r(p['a']), 'b_m': r(p['b']), 'radio_m': round(p['r'], 4)}
    elif t == 'esf':
        q = {'tipo': 'esfera', 'centro_m': r(p['c']), 'radio_m': round(p['r'], 4)}
    elif t == 'toro':
        q = {'tipo': 'toro', 'centro_m': r(p['c']), 'radio_mayor_m': round(p['R_'], 4), 'radio_menor_m': round(p['r'], 4), 'rot_grados': m_a_euler(p['R'])}
    elif t == 'cono':
        q = {'tipo': 'cono_eje', 'a_m': r(p['a']), 'b_m': r(p['b']), 'radio1_m': round(p['ra'], 4), 'radio2_m': round(p['rb'], 4)}
    else:
        q = {'tipo': 'poliedro', 'vertices_m': [r(v) for v in p['v']]}
    q['nombre'] = nombre
    if col is not None and col != color_def: q['color_rgb'] = col
    return q
