"""formas_biblioteca.py — BIBLIOTECA DE FORMAS paramétricas y compuestas (generadas por código; US$0, sin red, sin IA).

Universal: es un catálogo genérico (como un catálogo de mobiliario), no conoce ningún canal, guion ni lugar.
Cada forma = una función que devuelve PARTES de formas_detalle.py (caja, tramo, cilindro, esfera, toro, tubo,
placa, poliedro, cono) en coordenadas LOCALES: origen en el centro de la base, x = ancho, y = fondo
(el frente mira a -y; en vehículos el frente mira a +x), z = alto. Todas las medidas son parámetros: la ficha
da las típicas y quien la use (la respuesta de Argon o la ficha del canal) puede pasar otras.
Licencia: código propio de Star; sin activos externos descargados.
"""
import math, os, random, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import formas_detalle as FD

# colores guía (solo para ver las formas; NO son colores de molde)
MAD = [0.55, 0.38, 0.22]; MAD2 = [0.42, 0.28, 0.16]; OSC = [0.12, 0.12, 0.14]; MET = [0.6, 0.62, 0.65]
BLA = [0.9, 0.9, 0.88]; TEL = [0.45, 0.5, 0.6]; VER = [0.3, 0.55, 0.3]; VER2 = [0.2, 0.42, 0.22]; PIE = [0.55, 0.55, 0.52]
VID = [0.7, 0.85, 0.92]; ROJ = [0.75, 0.15, 0.12]; AMA = [0.9, 0.75, 0.15]; NAR = [0.95, 0.5, 0.1]; AZU = [0.2, 0.35, 0.7]
CAF = [0.4, 0.28, 0.18]; GRI = [0.5, 0.5, 0.52]; CEM = [0.66, 0.65, 0.62]; LUZ = [1.0, 0.95, 0.7]; CAR = [0.7, 0.55, 0.35]
NEG = [0.05, 0.05, 0.06]; LAD = [0.65, 0.3, 0.2]; AGU = [0.25, 0.45, 0.6]; VIO = [0.6, 0.2, 0.85]; VIO2 = [0.45, 0.15, 0.7]

def _c(p, col, n):
    if col: p['color_guia_rgb'] = list(col)
    if n: p['nombre'] = n
    return p
def B(cx, cy, cz, sx, sy, sz, col=None, rot=None, n=None):
    p = {'tipo': 'caja', 'centro_m': [cx, cy, cz], 'tam_m': [max(sx, 1e-3), max(sy, 1e-3), max(sz, 1e-3)]}
    if rot: p['rot_grados'] = list(rot)
    return _c(p, col, n)
def BZ(x0, x1, y0, y1, z0, z1, col=None, n=None):
    return B((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0, col, None, n)
def T(a, b, r, col=None, n=None): return _c({'tipo': 'tramo', 'a_m': list(a), 'b_m': list(b), 'radio_m': r}, col, n)
def C(cx, cy, z0, h, r, col=None, n=None, rot=None):
    """cilindro vertical apoyado en z0; con rot: cilindro girado con centro (cx, cy, z0)."""
    if rot: return _c({'tipo': 'cilindro', 'centro_m': [cx, cy, z0], 'radio_m': r, 'alto_m': h, 'rot_grados': list(rot)}, col, n)
    return _c({'tipo': 'cilindro', 'centro_m': [cx, cy, z0 + h / 2], 'radio_m': r, 'alto_m': h}, col, n)
def S(c, r, col=None, n=None): return _c({'tipo': 'esfera', 'centro_m': list(c), 'radio_m': r}, col, n)
def K(a, b, ra, rb, col=None, n=None): return _c({'tipo': 'cono', 'a_m': list(a), 'b_m': list(b), 'radio_a_m': ra, 'radio_b_m': rb}, col, n)
def TO(c, R, r, rot=None, col=None, n=None):
    p = {'tipo': 'toro', 'centro_m': list(c), 'radio_mayor_m': R, 'radio_menor_m': r}
    if rot: p['rot_grados'] = list(rot)
    return _c(p, col, n)
def TU(c0, re_, ri, h, seg=12, col=None, n=None):
    return _c({'tipo': 'tubo', 'centro_m': list(c0), 'radio_ext_m': re_, 'radio_int_m': ri, 'alto_m': h, 'segmentos': seg}, col, n)
def PL(c, r, e, rot=None, col=None, n=None):
    p = {'tipo': 'placa', 'centro_m': list(c), 'radio_m': r, 'espesor_m': e}
    if rot: p['rot_grados'] = list(rot)
    return _c(p, col, n)
def PO(vs, col=None, n=None): return _c({'tipo': 'poliedro', 'vertices_m': [list(v) for v in vs]}, col, n)

ESQ = ((-1, -1), (1, -1), (1, 1), (-1, 1))
def patas4(w, d, h, r, ins=0.04, col=None):
    return [T([sx * (w / 2 - ins - r), sy * (d / 2 - ins - r), 0], [sx * (w / 2 - ins - r), sy * (d / 2 - ins - r), h], r, col, 'pata') for sx, sy in ESQ]
def patas4c(w, d, h, s, ins=0.0, col=None):
    out = []
    for sx, sy in ESQ:
        x = sx * (w / 2 - ins - s / 2); y = sy * (d / 2 - ins - s / 2)
        out.append(B(x, y, h / 2, s, s, h, col, None, 'pata'))
    return out
def postes4(w, d, h, s, col=None, z0=0.0):
    return [B(sx * (w / 2 - s / 2), sy * (d / 2 - s / 2), z0 + (h - z0) / 2, s, s, h - z0, col, None, 'poste') for sx, sy in ESQ]
def roca_vs(w, d, h, semilla, n=14, z0=0.0, cx=0.0, cy=0.0):
    rnd = random.Random(semilla); vs = []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.2, 0.2); k = rnd.uniform(0.75, 1.0)
        z = z0 + rnd.choice([0.0, rnd.uniform(0.1, 0.6) * h])
        vs.append([cx + k * w / 2 * math.cos(a), cy + k * d / 2 * math.sin(a), z])
    for i in range(5):
        a = rnd.uniform(0, 2 * math.pi); k = rnd.uniform(0.1, 0.5)
        vs.append([cx + k * w / 2 * math.cos(a), cy + k * d / 2 * math.sin(a), z0 + h * rnd.uniform(0.8, 1.0)])
    vs += [[cx, cy, z0 + h], [cx + w / 2, cy, z0], [cx - w / 2, cy, z0], [cx, cy + d / 2, z0], [cx, cy - d / 2, z0]]
    return vs
def ruedas(xs, ancho, r, e, col=OSC):
    return [C(x, sy * (ancho / 2 - e / 2), r, e, r, col, 'rueda', rot=[90, 0, 0]) for x in xs for sy in (-1, 1)]
def prisma(w, d, z0, h, col, n, cumbre_y=0.0):
    return PO([[sx * w / 2, sy * d / 2, z0] for sx in (-1, 1) for sy in (-1, 1)] + [[sx * w / 2, cumbre_y, z0 + h] for sx in (-1, 1)], col, n)
def tronco_pir(w, d, w2, d2, z0, h, col, n, dy=0.0):
    return PO([[sx * w / 2, sy * d / 2, z0] for sx in (-1, 1) for sy in (-1, 1)] + [[sx * w2 / 2, dy + sy * d2 / 2, z0 + h] for sx in (-1, 1) for sy in (-1, 1)], col, n)
def poli_linea(pts, r, col, n): return [T(pts[i], pts[i + 1], r, col, n) for i in range(len(pts) - 1)]

G = {}
def gen(nombre):
    def f(fn): G[nombre] = fn; return fn
    return f

# ======================= muebles =======================
@gen('mesa_patas')
def _(w, d, h, col=MAD, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.04, h, col, 'tablero')] + patas4(w, d, h-0.04, 0.025, 0.04, MAD2)
@gen('mesa_redonda')
def _(w, d, h, col=MAD, **k): return [C(0, 0, h-0.04, 0.04, w/2, col, 'tablero'), C(0, 0, 0, 0.03, w*0.25, MAD2, 'pie_base'), T([0, 0, 0.03], [0, 0, h-0.04], 0.04, MAD2, 'poste')]
@gen('escritorio')
def _(w, d, h, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, h-0.03, h, MAD, 'tablero'), BZ(-w/2, -w/2+0.03, -d/2+0.03, d/2, 0, h-0.03, MAD2, 'lado'),
           BZ(w/2-0.42, w/2, -d/2+0.03, d/2, 0, h-0.03, MAD2, 'cajonera'), BZ(-w/2+0.03, w/2-0.42, d/2-0.02, d/2, 0.3, h-0.03, MAD2, 'faldon')]
    return out + [BZ(w/2-0.40, w/2-0.02, -d/2, -d/2+0.03, z, z+0.18, MAD, 'cajon') for z in (0.06, 0.28, 0.5) if z+0.18 < h-0.05]
@gen('escritorio_L')
def _(w, d, h, prof=0.6, **k):
    return [BZ(-w/2, w/2, d/2-prof, d/2, h-0.03, h, MAD, 'tablero'), BZ(w/2-prof, w/2, -d/2, d/2-prof, h-0.03, h, MAD, 'tablero'),
            BZ(-w/2, -w/2+0.03, d/2-prof, d/2, 0, h-0.03, MAD2, 'lado'), BZ(w/2-prof, w/2, -d/2, -d/2+0.03, 0, h-0.03, MAD2, 'lado'), BZ(w/2-0.03, w/2, d/2-prof, d/2, 0, h-0.03, MAD2, 'esquina')]
@gen('silla')
def _(w, d, h, asiento=0.45, col=MAD, **k):
    return [BZ(-w/2, w/2, -d/2, d/2, asiento-0.04, asiento, col, 'asiento'), BZ(-w/2, w/2, d/2-0.04, d/2, asiento, h, col, 'respaldo')] + patas4(w, d, asiento-0.04, 0.02, 0.02, MAD2)
@gen('taburete')
def _(w, d, h, **k):
    return [C(0, 0, h-0.04, 0.04, w/2, MAD, 'asiento'), TO([0, 0, h*0.35], w*0.3, 0.012, None, MAD2, 'aro')] + \
           [T([0.9*w/2*math.cos(a), 0.9*w/2*math.sin(a), 0], [0.5*w/2*math.cos(a), 0.5*w/2*math.sin(a), h-0.04], 0.018, MAD2, 'pata') for a in (0.5, 2.6, 4.7)]
@gen('silla_oficina')
def _(w, d, h, asiento=0.48, **k):
    out = [B(0, 0, asiento-0.04, w*0.85, d*0.8, 0.08, OSC, n='asiento'), B(0, d/2-0.06, (asiento+h)/2+0.05, w*0.8, 0.06, h-asiento-0.1, OSC, n='respaldo'),
           T([0, 0, 0.1], [0, 0, asiento-0.08], 0.03, MET, 'piston'), BZ(-w*0.45, -w*0.40, -0.1, 0.1, asiento+0.1, asiento+0.14, OSC, 'brazo'), BZ(w*0.40, w*0.45, -0.1, 0.1, asiento+0.1, asiento+0.14, OSC, 'brazo')]
    for i in range(5):
        a = 2*math.pi*i/5 + math.pi/2; R = min(w, d)/2 - 0.03
        out += [T([0, 0, 0.08], [R*math.cos(a), R*math.sin(a), 0.06], 0.018, OSC, 'rayo'), S([R*math.cos(a), R*math.sin(a), 0.03], 0.03, OSC, 'rueda')]
    return out
@gen('sofa')
def _(w, d, h, asiento=0.42, brazo=0.2, col=TEL, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, 0.1, asiento, col, 'base'), BZ(-w/2, w/2, d/2-0.22, d/2, asiento, h, col, 'respaldo'),
           BZ(-w/2, -w/2+brazo, -d/2, d/2-0.22, asiento, asiento+0.22, col, 'brazo'), BZ(w/2-brazo, w/2, -d/2, d/2-0.22, asiento, asiento+0.22, col, 'brazo')]
    m = (w-2*brazo)/2
    out += [BZ(-w/2+brazo+i*m+0.01, -w/2+brazo+(i+1)*m-0.01, -d/2+0.02, d/2-0.24, asiento, asiento+0.12, [0.52, 0.57, 0.67], 'cojin') for i in range(2)]
    return out + patas4c(w, d, 0.1, 0.06, 0.03, MAD2)
@gen('sillon')
def _(w, d, h, **k): return G['sofa'](w, d, h, brazo=0.16)
@gen('cama')
def _(w, d, h, colchon=0.55, **k):
    return [BZ(-w/2, w/2, -d/2, d/2-0.05, 0.1, 0.32, MAD, 'base'), BZ(-w/2+0.02, w/2-0.02, -d/2+0.02, d/2-0.06, 0.32, colchon, BLA, 'colchon'),
            BZ(-w/2, w/2, d/2-0.05, d/2, 0, h, MAD2, 'cabecero'), B(0, d/2-0.3, colchon+0.06, w*0.7, 0.35, 0.12, BLA, n='almohada'),
            BZ(-w/2+0.01, w/2-0.01, -d/2+0.01, d*0.15, colchon, colchon+0.03, TEL, 'cobija')] + patas4c(w, d-0.05, 0.1, 0.06, 0.0, MAD2)
@gen('litera')
def _(w, d, h, **k):
    out = [BZ(-w/2+0.05, w/2-0.05, -d/2+0.05, d/2-0.05, z-0.05, z, MAD, 'somier') for z in (0.25, 1.25)]
    out += [BZ(-w/2+0.05, w/2-0.05, -d/2+0.05, d/2-0.05, z, z+0.18, c, 'colchon') for z, c in ((0.25, TEL), (1.25, BLA))]
    out += postes4(w, d, h, 0.05, MAD2) + [BZ(-w/2, w/2, d/2-0.05, d/2, 1.5, 1.7, MAD2, 'baranda')]
    return out + [T([w/2-0.03, -d/2+0.15, z], [w/2-0.03, -d/2+0.45, z], 0.015, MAD2, 'peldano') for z in (0.5, 0.8, 1.1)]
@gen('armario')
def _(w, d, h, puertas=2, col=MAD, **k):
    out = [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, col, 'cuerpo')]
    for i in range(puertas):
        x0 = -w/2 + i*w/puertas
        out += [BZ(x0+0.005, x0+w/puertas-0.005, -d/2, -d/2+0.02, 0.05, h-0.05, MAD2, 'puerta'), B(x0 + w/puertas*(0.85 if i % 2 == 0 else 0.15), -d/2+0.01, h*0.5, 0.02, 0.02, 0.15, MET, n='tirador')]
    return out
@gen('estanteria')
def _(w, d, h, baldas=5, col=MAD, libros=True, **k):
    out = [BZ(-w/2, -w/2+0.02, -d/2, d/2, 0, h, col, 'lado'), BZ(w/2-0.02, w/2, -d/2, d/2, 0, h, col, 'lado'), BZ(-w/2+0.02, w/2-0.02, d/2-0.01, d/2, 0, h, MAD2, 'fondo')]
    rnd = random.Random(3); paso = (h-0.02)/(baldas-1)
    for i in range(baldas):
        z = i*paso; out.append(BZ(-w/2+0.02, w/2-0.02, -d/2, d/2-0.01, z, z+0.02, col, 'balda'))
        if libros and i < baldas-1:
            x = -w/2+0.04
            while x < w/2-0.1:
                bw = rnd.uniform(0.02, 0.05); bh = (paso-0.04)*rnd.uniform(0.6, 0.9)
                out.append(BZ(x, x+bw, -d/2+0.04, d/2-0.04, z+0.02, z+0.02+bh, rnd.choice([ROJ, AZU, VER, AMA, CAF]), 'libro')); x += bw+0.005
    return out
@gen('comoda')
def _(w, d, h, cajones=4, col=MAD, **k):
    out = [BZ(-w/2, w/2, -d/2+0.02, d/2, 0.06, h, col, 'cuerpo')] + patas4c(w, d, 0.06, 0.05, 0.02, MAD2); hc = (h-0.1)/cajones
    for i in range(cajones):
        z0 = 0.08 + i*hc; out += [BZ(-w/2+0.02, w/2-0.02, -d/2, -d/2+0.02, z0+0.01, z0+hc-0.01, MAD2, 'cajon'), B(0, -d/2+0.01, z0+hc/2, 0.15, 0.02, 0.02, MET, n='tirador')]
    return out
@gen('mesa_noche')
def _(w, d, h, **k): return G['comoda'](w, d, h, cajones=2)
@gen('mueble_tv')
def _(w, d, h, **k):
    return [BZ(-w/2, w/2, -d/2, d/2, h-0.03, h, MAD, 'tapa'), BZ(-w/2, w/2, -d/2, d/2, 0.05, 0.08, MAD, 'fondo'), BZ(-w/2, -w/2+0.03, -d/2, d/2, 0.08, h-0.03, MAD2, 'lado'),
            BZ(w/2-0.03, w/2, -d/2, d/2, 0.08, h-0.03, MAD2, 'lado'), BZ(-0.015, 0.015, -d/2, d/2, 0.08, h-0.03, MAD2, 'division')] + patas4c(w, d, 0.05, 0.04, 0.02, OSC)
@gen('baul')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.7, MAD, 'caja'), tronco_pir(w, d, w, d*0.6, h*0.7, h*0.3, MAD2, 'tapa'), B(0, -d/2+0.01, h*0.6, 0.08, 0.02, 0.1, MET, n='cerradura')]
@gen('alfombra')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.8, ROJ, 'alfombra'), BZ(-w/2+0.1, w/2-0.1, -d/2+0.1, d/2-0.1, h*0.8, h, AMA, 'guarda')]
@gen('cuadro')
def _(w, d, h, col=AZU, **k): return [BZ(-w/2, w/2, -d/2+0.004, d/2, 0, h, MAD2, 'marco'), BZ(-w/2+0.05, w/2-0.05, -d/2, -d/2+0.004, 0.05, h-0.05, col, 'lienzo')]
@gen('espejo')
def _(w, d, h, **k): return G['cuadro'](w, d, h, col=VID)
@gen('reloj_pared')
def _(w, d, h, **k): return [C(0, 0, h/2, d*0.8, w/2, BLA, 'esfera_reloj', rot=[90, 0, 0]), T([0, -d/2+0.004, h/2], [0, -d/2+0.004, h/2+w*0.35], 0.004, NEG, 'aguja'), T([0, -d/2+0.004, h/2], [w*0.25, -d/2+0.004, h/2], 0.004, NEG, 'aguja')]
@gen('perchero')
def _(w, d, h, **k): return [C(0, 0, 0, 0.03, w*0.3, MAD2, 'base'), T([0, 0, 0.03], [0, 0, h-0.2], 0.02, MAD, 'poste')] + [T([0, 0, h-0.2], [0.85*w/2*math.cos(a), 0.85*w/2*math.sin(a), h-0.02], 0.012, MAD, 'gancho') for a in (0, 1.57, 3.14, 4.71)]
@gen('biombo')
def _(w, d, h, hojas=3, **k):
    L = w/hojas; return [B(-w/2 + L*(i+0.5), (d/2-0.02)*(1 if i % 2 else -1), h/2, L*0.97, 0.03, h, MAD if i % 2 else CAR, n='hoja') for i in range(hojas)]
@gen('puf')
def _(w, d, h, **k): return [C(0, 0, 0, h-0.01, w/2, NAR, 'cuerpo'), C(0, 0, h-0.01, 0.01, w/2*0.9, [0.8, 0.4, 0.08], 'tapa')]
@gen('cojin')
def _(w, d, h, **k): return [B(0, 0, h/2, w, d, h, AMA, n='cojin')]
@gen('cuna')
def _(w, d, h, **k):
    out = [BZ(-w/2+0.02, w/2-0.02, -d/2+0.02, d/2-0.02, 0.3, 0.42, BLA, 'colchon')] + [T([sx*(w/2-0.02), sy*(d/2-0.02), 0], [sx*(w/2-0.02), sy*(d/2-0.02), h], 0.02, MAD, 'poste') for sx, sy in ESQ]
    xs = [-w/2+0.1 + i*0.1 for i in range(int((w-0.2)/0.1)+1)]
    out += [T([x, sy*(d/2-0.02), 0.3], [x, sy*(d/2-0.02), h], 0.008, MAD, 'barrote') for sy in (-1, 1) for x in xs]
    return out + [T([-w/2+0.02, sy*(d/2-0.02), h-0.015], [w/2-0.02, sy*(d/2-0.02), h-0.015], 0.015, MAD, 'baranda') for sy in (-1, 1)]
@gen('hamaca')
def _(w, d, h, **k):
    out = [T([sx*(w/2-0.05), 0, 0], [sx*(w/2-0.05), 0, h], 0.05, MAD2, 'poste') for sx in (-1, 1)]; L = w*0.85; n = 10
    pts = [[-L/2 + L*i/n, 0, h*0.75 - 0.6*(1 - (2*i/n - 1)**2)] for i in range(n+1)]
    return out + poli_linea(pts, d/2*0.7, ROJ, 'tela')
@gen('mesa_centro')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.04, h, MAD, 'tablero'), BZ(-w/2+0.05, w/2-0.05, -d/2+0.05, d/2-0.05, 0.08, 0.1, MAD2, 'repisa')] + patas4c(w, d, h-0.04, 0.05, 0.02, MAD2)
@gen('mesa_reuniones')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.05, h, MAD2, 'tablero')] + [BZ(x-0.06, x+0.06, -d*0.3, d*0.3, 0, h-0.05, OSC, 'pie') for x in (-w*0.3, w*0.3)]
@gen('banco_madera')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.05, h, MAD, 'asiento')] + patas4c(w, d, h-0.05, 0.05, 0.03, MAD2)

# ======================= lámparas y luz =======================
@gen('lampara_pie')
def _(w, d, h, **k): return [C(0, 0, 0, 0.03, w*0.4, OSC, 'base'), T([0, 0, 0.03], [0, 0, h-0.3], 0.012, MET, 'poste'), K([0, 0, h-0.3], [0, 0, h], w/2, w*0.3, LUZ, 'pantalla')]
@gen('lampara_escritorio')
def _(w, d, h, **k): return [C(0, 0, 0, 0.02, w/2, OSC, 'base'), T([0, 0, 0.02], [0, d*0.2, h*0.65], 0.008, MET, 'brazo'), T([0, d*0.2, h*0.65], [0, -d*0.2, h-0.06], 0.008, MET, 'brazo'), K([0, -d*0.2, h-0.04], [0, -d/2+0.07, h-0.12], 0.02, 0.07, OSC, 'cabeza')]
@gen('lampara_colgante')
def _(w, d, h, **k): return [C(0, 0, h-0.02, 0.02, 0.05, BLA, 'roseton'), T([0, 0, 0.25], [0, 0, h-0.02], 0.004, NEG, 'cable'), K([0, 0, 0.25], [0, 0, 0], 0.06, w/2, LUZ, 'pantalla')]
@gen('aplique_pared')
def _(w, d, h, **k): return [BZ(-w*0.2, w*0.2, d/2-0.02, d/2, h*0.3, h*0.7, MET, 'placa_pared'), K([0, d/2-0.02, h/2], [0, -d/2, h/2], 0.03, min(w, h)/2, LUZ, 'difusor')]
@gen('reflector')
def _(w, d, h, **k):
    r = min(w*0.35, h*0.4)
    return [T([-w*0.4, 0, 0], [-w*0.4, 0, h*0.55], 0.015, OSC, 'pata'), T([w*0.4, 0, 0], [w*0.4, 0, h*0.55], 0.015, OSC, 'pata'), T([-w*0.4, 0, h*0.55], [w*0.4, 0, h*0.55], 0.015, OSC, 'horquilla'),
            C(0, 0, h*0.55, d, r, OSC, 'cuerpo', rot=[90, 0, 0]), PL([0, -d/2+0.005, h*0.55], r*0.9, 0.01, [90, 0, 0], LUZ, 'cristal')]
@gen('candelabro')
def _(w, d, h, **k): return [C(0, 0, 0, 0.02, d/2, AMA, 'base'), T([0, 0, 0.02], [0, 0, h*0.6], 0.01, AMA, 'poste'), T([-w/2+0.012, 0, h*0.6], [w/2-0.012, 0, h*0.6], 0.008, AMA, 'brazo')] + [C(x, 0, h*0.6, h*0.4, 0.012, BLA, 'vela') for x in (-w/2+0.012, 0, w/2-0.012)]
@gen('vela')
def _(w, d, h, **k): return [C(0, 0, 0, h*0.85, w/2, BLA, 'vela'), K([0, 0, h*0.85], [0, 0, h], w*0.2, 0.0, LUZ, 'llama')]
@gen('farol')
def _(w, d, h, **k): return [B(0, 0, h*0.45, w*0.8, d*0.8, h*0.6, LUZ, n='vidrio'), K([0, 0, h*0.75], [0, 0, h*0.9], w/2, 0.02, OSC, 'tapa'), TO([0, 0, h*0.94], 0.03, 0.008, [90, 0, 0], OSC, 'aro'), BZ(-w/2, w/2, -d/2, d/2, 0, h*0.15, OSC, 'base')]
@gen('foco_techo')
def _(w, d, h, **k): return [C(0, 0, h-0.03, 0.03, w/2, BLA, 'aro'), C(0, 0, 0, h-0.03, w*0.35, LUZ, 'difusor')]
@gen('tubo_fluorescente')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h*0.4, h, BLA, 'regleta'), T([-w/2+0.03, 0, h*0.25], [w/2-0.03, 0, h*0.25], h*0.25, LUZ, 'tubo')]

# ======================= plantas y árboles =======================
@gen('arbol_frondoso')
def _(w, d, h, tronco=0.4, semilla=1, ramas=8, **k):
    rnd = random.Random(semilla); R = min(w, d)/2; rc = R*0.55; r = R*0.42
    out = [K([0, 0, 0], [0, 0, h*0.5], tronco/2, tronco*0.3, CAF, 'tronco'), S([0, 0, h - rc], rc, VER, 'copa')]
    for i in range(ramas):
        a = 2*math.pi*i/ramas; cz = h - rc - rnd.uniform(0.05, 0.3)*rc
        out.append(S([(w/2-r)*math.cos(a), (d/2-r)*math.sin(a), cz], r, VER2 if i % 2 else VER, 'copa'))
    return out
@gen('conifera')
def _(w, d, h, **k): return [C(0, 0, 0, h*0.15, w*0.06, CAF, 'tronco')] + [K([0, 0, h*0.12 + i*h*0.22], [0, 0, h*0.12 + i*h*0.22 + h*(0.66 - i*0.11)], w/2*(1-i*0.25), 0.0, VER2, 'copa') for i in range(3)]
@gen('palmera')
def _(w, d, h, hojas=8, **k):
    n = 6; out = [K([0, 0, i*h*0.85/n], [0, 0, (i+1)*h*0.85/n], 0.15-0.01*i, 0.14-0.01*i, CAF, 'tronco') for i in range(n)]
    top = [0, 0, h*0.85]
    out += [T(top, [(w/2-0.06)*math.cos(a), (d/2-0.06)*math.sin(a), h*0.68 + (i % 2)*0.12], 0.06, VER, 'hoja') for i, a in enumerate([2*math.pi*j/hojas for j in range(hojas)])]
    return out + [S([0, 0, h-0.15], 0.15, VER2, 'copa')]
@gen('arbusto')
def _(w, d, h, semilla=2, **k):
    rnd = random.Random(semilla); r = min(w, d, 2*h)/2*0.6; out = []
    for i in range(5):
        a = 2*math.pi*i/5; out.append(S([(w/2-r)*math.cos(a)*rnd.uniform(0.6, 1), (d/2-r)*math.sin(a)*rnd.uniform(0.6, 1), r], r*rnd.uniform(0.85, 1.0), VER if i % 2 else VER2, 'mata'))
    return out + [S([0, 0, h-r], r, VER, 'mata')]
@gen('seto')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, VER2, 'seto')]
@gen('maceta_planta')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h*0.35], w*0.3, w*0.4, LAD, 'maceta'), T([0, 0, h*0.35], [0, 0, h*0.6], 0.015, VER2, 'tallo'), S([0, 0, h - w/2*0.9], w/2*0.9, VER, 'follaje')]
@gen('maceta_flores')
def _(w, d, h, **k):
    return [K([0, 0, 0], [0, 0, h*0.4], w*0.35, w/2, LAD, 'maceta')] + [T([0, 0, h*0.4], [0.12*w*math.cos(a), 0.12*w*math.sin(a), h-0.04], 0.005, VER, 'tallo') for a in (0, 2.1, 4.2)] + \
           [S([0.12*w*math.cos(a), 0.12*w*math.sin(a), h-0.04], 0.04, c, 'flor') for a, c in ((0, ROJ), (2.1, AMA), (4.2, NAR))]
@gen('cactus')
def _(w, d, h, **k):
    r = w*0.15; return [C(0, 0, 0, h-r, r, VER2, 'tallo'), S([0, 0, h-r], r, VER2, 'punta'), T([0, 0, h*0.35], [w*0.35, 0, h*0.35], 0.06, VER2, 'brazo'), T([w*0.35, 0, h*0.35], [w*0.35, 0, h*0.6], 0.06, VER2, 'brazo'),
                         T([0, 0, h*0.5], [-w*0.35, 0, h*0.5], 0.05, VER2, 'brazo'), T([-w*0.35, 0, h*0.5], [-w*0.35, 0, h*0.72], 0.05, VER2, 'brazo')]
@gen('tronco_caido')
def _(w, d, h, **k): return [C(0, 0, h/2, w*0.98, h/2, CAF, 'tronco', rot=[0, 90, 0]), PL([w*0.49, 0, h/2], h/2*0.9, 0.01, [0, 90, 0], CAR, 'corte')]
@gen('tocon')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h-0.005], w/2, w*0.4, CAF, 'tocon'), PL([0, 0, h-0.005], w*0.38, 0.01, None, CAR, 'corte')]
@gen('matas_hierba')
def _(w, d, h, semilla=4, **k):
    rnd = random.Random(semilla); out = []
    for _ in range(14):
        x, y = rnd.uniform(-w/2+0.03, w/2-0.03), rnd.uniform(-d/2+0.03, d/2-0.03); out.append(K([x, y, 0], [x, y, h*rnd.uniform(0.6, 1)], 0.03, 0.0, VER, 'brizna'))
    return out
@gen('flor')
def _(w, d, h, **k): return [T([0, 0, 0], [0, 0, h-w/2], 0.006, VER, 'tallo'), S([0, 0, h-w/2], w/2, ROJ, 'flor'), B(0.03, 0, h*0.4, 0.05, 0.02, 0.005, VER, rot=[0, -20, 0], n='hoja')]
@gen('arbol_seco')
def _(w, d, h, ramas=4, **k):
    out = [K([0, 0, 0], [0, 0, h*0.6], 0.15, 0.08, CAF, 'tronco')]
    return out + [T([0, 0, min(h*0.45 + i*0.12*h, h*0.6)], [(w/2-0.04)*math.cos(a), (d/2-0.04)*math.sin(a), min(h, h*0.45 + i*0.12*h + h*0.35) - 0.04], 0.04, CAF, 'rama') for i, a in enumerate([2*math.pi*j/ramas for j in range(ramas)])]
@gen('bambu')
def _(w, d, h, **k):
    out = []
    for i, (x, y) in enumerate(((-w*0.3, 0), (0, d*0.2), (w*0.3, -d*0.1), (0.05, -d*0.3))):
        hh = h*(0.75 + 0.08*i); out += [T([x, y, 0], [x, y, hh], 0.025, [0.55, 0.65, 0.3], 'cana'), S([x, y, hh], 0.08, VER, 'hojas')]
    return out
@gen('enredadera')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, VER2, 'masa')] + [S([x, -d/2+0.05, z], 0.05, VER, 'hojas') for x in (-w/3, 0, w/3) for z in (h*0.3, h*0.7)]

# ======================= rocas y terreno =======================
@gen('roca')
def _(w, d, h, semilla=5, **k): return [PO(roca_vs(w, d, h, semilla), PIE, 'roca')]
@gen('grupo_piedras')
def _(w, d, h, semilla=6, **k):
    rnd = random.Random(semilla); out = [PO(roca_vs(w*0.5, d*0.5, h, semilla, cx=-w*0.2), PIE, 'piedra')]
    for i in range(4):
        s = rnd.uniform(0.2, 0.35); cx = rnd.uniform(-w/2+s*w/2, w/2-s*w/2); cy = rnd.uniform(-d/2+s*d/2, d/2-s*d/2)
        out.append(PO(roca_vs(w*s, d*s, h*rnd.uniform(0.3, 0.6), semilla+i+1, cx=cx, cy=cy), GRI, 'piedra'))
    return out
@gen('monton_grava')
def _(w, d, h, **k): return [PO([[w/2*math.cos(a), d/2*math.sin(a), 0] for a in [i*math.pi/6 for i in range(12)]] + [[w*0.1, 0, h], [-w*0.1, d*0.1, h*0.95]], CEM, 'monton')]
@gen('penasco')
def _(w, d, h, semilla=8, **k): return [PO(roca_vs(w, d, h*0.7, semilla), PIE, 'base'), PO(roca_vs(w*0.6, d*0.6, h*0.4, semilla+1, z0=h*0.6, cx=w*0.05), GRI, 'cima')]
@gen('canto_rodado')
def _(w, d, h, semilla=9, **k): return [PO(roca_vs(w, d, h, semilla, n=20), [0.6, 0.58, 0.55], 'canto')]
@gen('monticulo_tierra')
def _(w, d, h, **k): return [PO([[w/2*math.cos(a), d/2*math.sin(a), 0] for a in [i*math.pi/8 for i in range(16)]] + [[w/4*math.cos(a), d/4*math.sin(a), h*0.8] for a in [i*math.pi/4 for i in range(8)]] + [[0, 0, h]], CAF, 'tierra')]

# ======================= electrónica y oficina =======================
@gen('monitor')
def _(w, d, h, **k):
    return [B(0, 0, 0.01, w*0.4, d, 0.02, OSC, n='base'), T([0, d*0.2, 0.02], [0, d*0.2, h*0.4], 0.02, OSC, 'cuello'), BZ(-w/2, w/2, -0.02, 0.02, h*0.3, h, OSC, 'marco'), BZ(-w/2+0.015, w/2-0.015, -0.025, -0.02, h*0.3+0.015, h-0.015, AZU, 'pantalla')]
@gen('torre_pc')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0.01, h, OSC, 'caja'), BZ(-w/2+0.02, w/2-0.02, -d/2-0.002, -d/2+0.002, h*0.75, h*0.95, GRI, 'bahia'), S([0, -d/2, h*0.65], 0.01, LUZ, 'boton')] + patas4c(w, d, 0.01, 0.02, 0.0, NEG)
@gen('portatil')
def _(w, d, h, abierto=True, **k):
    out = [BZ(-w/2, w/2, -d/2, d*0.1, 0, 0.02, GRI, 'base'), BZ(-w/2+0.02, w/2-0.02, -d/2+0.04, d*0.05, 0.02, 0.022, OSC, 'teclado')]
    if abierto: return out + [B(0, d*0.1 + (d/2-d*0.1)/2, h/2+0.005, w, (h-0.01)*math.sin(math.radians(20))+0.01, h-0.01, GRI, [-20, 0, 0], 'tapa')]
    return out
@gen('teclado')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.6, OSC, 'cuerpo')] + [BZ(-w/2+0.01, w/2-0.01, -d/2+0.01 + i*(d-0.02)/5, -d/2+0.01 + (i+0.8)*(d-0.02)/5, h*0.6, h, GRI, 'teclas') for i in range(5)]
@gen('raton')
def _(w, d, h, **k): return [PO([[sx*w/2, sy*d/2, 0] for sx in (-1, 1) for sy in (-1, 1)] + [[sx*w*0.3, sy*d*0.3, h] for sx in (-1, 1) for sy in (-1, 1)], OSC, 'raton')]
@gen('rack_servidores')
def _(w, d, h, unidades=10, **k):
    out = [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, NEG, 'armazon')]; hu = (h-0.2)/unidades
    for i in range(unidades):
        z = 0.1 + i*hu; out += [BZ(-w/2+0.03, w/2-0.03, -d/2, -d/2+0.02, z+0.005, z+hu-0.005, OSC, 'servidor'), S([-w/2+0.08, -d/2, z+hu/2], 0.006, VER if i % 3 else NAR, 'led')]
    return out
@gen('router')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.25, OSC, 'cuerpo')] + [T([x, d/2-0.01, h*0.25], [x, d/2-0.01, h], 0.005, OSC, 'antena') for x in (-w*0.35, 0, w*0.35)]
@gen('altavoz')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.005, d/2, 0, h, OSC, 'caja'), PL([0, -d/2+0.0025, h*0.3], w*0.38, 0.005, [90, 0, 0], GRI, 'woofer'), PL([0, -d/2+0.0025, h*0.75], w*0.15, 0.005, [90, 0, 0], GRI, 'tweeter')]
@gen('ventilador_pie')
def _(w, d, h, **k):
    r = w/2; cz = h - r
    return [C(0, 0, 0, 0.03, d/2, OSC, 'base'), T([0, 0, 0.03], [0, 0, cz], 0.015, BLA, 'poste'), TO([0, 0, cz], r-0.01, 0.01, [90, 0, 0], BLA, 'rejilla'),
            C(0, 0.02, cz, 0.08, 0.06, BLA, 'motor', rot=[90, 0, 0])] + [B(0.4*r*math.cos(a), -0.02, cz + 0.4*r*math.sin(a), 0.6*r, 0.01, 0.1, BLA, [0, -math.degrees(a), 0], 'aspa') for a in (0.3, 2.4, 4.5)]
@gen('ventilador_techo')
def _(w, d, h, aspas=4, **k):
    L = w/2 - 0.1
    return [C(0, 0, h-0.03, 0.03, 0.06, BLA, 'roseton'), T([0, 0, 0.15], [0, 0, h-0.03], 0.012, BLA, 'barra'), C(0, 0, 0.05, 0.1, 0.09, BLA, 'motor')] + \
           [B((0.1 + L/2)*math.cos(a), (0.1 + L/2)*math.sin(a), 0.08, L, 0.12, 0.01, MAD, [0, 0, math.degrees(a)], 'aspa') for a in [2*math.pi*i/aspas for i in range(aspas)]]
@gen('televisor')
def _(w, d, h, **k): return [BZ(-w*0.2, w*0.2, -d/2, d/2, 0, 0.02, OSC, 'base'), T([0, 0, 0.02], [0, 0, h*0.2], 0.02, OSC, 'cuello'), BZ(-w/2, w/2, -0.03, 0.03, h*0.15, h, NEG, 'marco'), BZ(-w/2+0.01, w/2-0.01, -0.035, -0.03, h*0.15+0.01, h-0.01, AZU, 'pantalla')]
@gen('consola_juegos')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, BLA, 'cuerpo'), BZ(-w/2, w/2, -d/2, d/2, h*0.45, h*0.55, NEG, 'franja')]
@gen('telefono_movil')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.6, OSC, 'cuerpo'), BZ(-w/2+0.004, w/2-0.004, -d/2+0.008, d/2-0.008, h*0.6, h, AZU, 'pantalla')]
@gen('tableta')
def _(w, d, h, **k): return G['telefono_movil'](w, d, h)
@gen('camara_seguridad')
def _(w, d, h, **k): return [BZ(-w*0.3, w*0.3, d/2-0.02, d/2, h*0.3, h, BLA, 'soporte_pared'), T([0, d/2-0.02, h*0.7], [0, d*0.1, h*0.7], 0.012, BLA, 'brazo'), B(0, -d*0.1, h*0.6, w*0.6, d*0.5, h*0.35, BLA, [15, 0, 0], 'cuerpo'), PL([0, -d/2+0.01, h*0.52], w*0.12, 0.01, [90, 0, 0], NEG, 'lente')]
@gen('auriculares')
def _(w, d, h, **k): return [TO([0, 0, h*0.45], w/2-0.03, 0.012, [90, 0, 0], OSC, 'diadema')] + [C(sx*(w/2-0.03), 0, h*0.18, 0.04, 0.045, OSC, 'auricular', rot=[0, 90, 0]) for sx in (-1, 1)]
@gen('regleta')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, BLA, 'cuerpo')] + [B(-w/2+0.06 + i*0.06, 0, h, 0.03, 0.02, 0.002, NEG, n='enchufe') for i in range(int((w-0.08)/0.06))]
@gen('ups_bateria')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, OSC, 'cuerpo'), BZ(-w*0.3, w*0.3, -d/2-0.002, -d/2, h*0.7, h*0.85, VER, 'pantalla')]
@gen('proyector')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, BLA, 'cuerpo'), C(w*0.25, -d/2, h/2, 0.03, h*0.3, NEG, 'lente', rot=[90, 0, 0])]
@gen('impresora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.05, d/2, 0, h*0.8, GRI, 'cuerpo'), prisma(w*0.9, d*0.3, h*0.8, h*0.2, GRI, 'bandeja_sup', cumbre_y=d*0.15), BZ(-w*0.35, w*0.35, -d/2, -d/2+0.05, h*0.2, h*0.25, BLA, 'bandeja_papel')]
@gen('fotocopiadora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0.05, h*0.85, GRI, 'cuerpo'), BZ(-w/2, w/2, -d/2, d/2, h*0.85, h, BLA, 'tapa'), BZ(-w*0.4, w*0.4, -d/2-0.002, -d/2, 0.1, h*0.6, BLA, 'cajones')] + patas4c(w, d, 0.05, 0.05, 0.02, NEG)
@gen('pizarra')
def _(w, d, h, base=0.9, col=BLA, **k):
    pts = [[-w/2+0.05, 0, 0], [-w/2+0.05, 0, base], [w/2-0.05, 0, 0], [w/2-0.05, 0, base]]
    return [BZ(-w/2, w/2, -0.02, 0.02, base, h, MET, 'marco'), BZ(-w/2+0.02, w/2-0.02, -0.025, -0.02, base+0.02, h-0.02, col, 'superficie'), T(pts[0], pts[1], 0.02, MET, 'pata'), T(pts[2], pts[3], 0.02, MET, 'pata'),
            T([-w/2+0.05, -d/2+0.02, 0.02], [-w/2+0.05, d/2-0.02, 0.02], 0.02, MET, 'pie'), T([w/2-0.05, -d/2+0.02, 0.02], [w/2-0.05, d/2-0.02, 0.02], 0.02, MET, 'pie')]
@gen('pantalla_proyeccion')
def _(w, d, h, **k): return [T([-w/2, 0, h-0.05], [w/2, 0, h-0.05], 0.05, OSC, 'rodillo'), BZ(-w/2+0.05, w/2-0.05, -0.005, 0.005, h*0.25, h-0.1, BLA, 'tela'), T([0, 0, 0], [0, 0, h*0.25], 0.02, OSC, 'poste'), T([0, -d/2+0.01, 0.01], [0, d/2-0.01, 0.01], 0.01, OSC, 'pie'), T([-d/2*0.6, 0, 0.01], [d/2*0.6, 0, 0.01], 0.01, OSC, 'pie')]
@gen('dispensador_agua')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.62, BLA, 'cuerpo'), C(0, 0, h*0.62, h*0.38-w*0.38, w*0.38, AGU, 'botellon'), S([0, 0, h-w*0.38], w*0.38, AGU, 'botellon_tope'), B(0, -d/2-0.0, h*0.45, 0.12, 0.04, 0.06, AZU, n='grifo')]
@gen('archivador')
def _(w, d, h, cajones=4, **k):
    out = [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, GRI, 'cuerpo')]; hc = h/cajones
    for i in range(cajones): out += [BZ(-w/2+0.01, w/2-0.01, -d/2, -d/2+0.02, i*hc+0.01, (i+1)*hc-0.01, GRI, 'cajon'), B(0, -d/2+0.01, i*hc+hc*0.75, 0.12, 0.02, 0.02, MET, n='tirador')]
    return out
@gen('caja_carton')
def _(w, d, h, abierta=False, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, 0, h, CAR, 'caja'), BZ(-0.03, 0.03, -d/2, d/2, h, h+0.001, [0.8, 0.75, 0.6], 'cinta')]
    return out if not abierta else out[:1]
@gen('papelera')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h], w*0.38, w/2, GRI, 'cubo'), TO([0, 0, h-0.008], w/2-0.008, 0.008, None, OSC, 'borde')]
@gen('lapiz_tablero_pared')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, CAR, 'corcho'), BZ(-w/2, w/2, -d/2, d/2, 0, 0.02, MAD, 'marco'), BZ(-w/2, w/2, -d/2, d/2, h-0.02, h, MAD, 'marco')]
@gen('microscopio')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.03, OSC, 'base'), T([0, d*0.3, 0.03], [0, d*0.3, h*0.8], 0.02, OSC, 'brazo'), T([0, d*0.25, h*0.85], [0, -d*0.1, h*0.5], 0.025, BLA, 'tubo'), K([0, d*0.3, h*0.8], [0, d*0.35, h], 0.012, 0.015, NEG, 'ocular'), BZ(-w*0.3, w*0.3, -d*0.3, d*0.1, h*0.35, h*0.37, OSC, 'platina')]
@gen('panel_control')
def _(w, d, h, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.6, GRI, 'cuerpo'), tronco_pir(w, d, w, d*0.4, h*0.6, h*0.4, OSC, 'consola', dy=d*0.3)]
    return out + [S([-w/2 + w*(i+1)/7, -d*0.05, h*0.82], 0.015, (ROJ, VER, AMA)[i % 3], 'boton') for i in range(6)]
@gen('pantalla_gigante')
def _(w, d, h, base=1.0, **k): return [BZ(-w/2, w/2, -d/2+0.02, d/2, base, h, NEG, 'marco'), BZ(-w/2+0.05, w/2-0.05, -d/2, -d/2+0.02, base+0.05, h-0.05, AZU, 'pantalla')] + [B(x, d*0.25, base/2, 0.1, 0.1, base, MET, n='poste') for x in (-w*0.3, w*0.3)]

# ======================= cocina y baño =======================
@gen('nevera')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.03, d/2, 0, h, BLA, 'cuerpo'), BZ(-w/2, w/2, -d/2, -d/2+0.03, h*0.36, h-0.01, BLA, 'puerta'), BZ(-w/2, w/2, -d/2, -d/2+0.03, 0.01, h*0.35, BLA, 'congelador'),
                             T([w/2-0.06, -d/2-0.0, h*0.45], [w/2-0.06, -d/2, h*0.75], 0.012, MET, 'tirador'), T([w/2-0.06, -d/2, h*0.15], [w/2-0.06, -d/2, h*0.3], 0.012, MET, 'tirador')]
@gen('estufa')
def _(w, d, h, **k):
    out = [BZ(-w/2, w/2, -d/2+0.02, d/2-0.05, 0, h*0.92, BLA, 'cuerpo'), BZ(-w/2, w/2, d/2-0.05, d/2, 0, h, BLA, 'panel'), BZ(-w/2+0.05, w/2-0.05, -d/2, -d/2+0.02, 0.1, h*0.7, NEG, 'puerta_horno')]
    return out + [PL([sx*w/4, sy*d/5, h*0.92+0.005], 0.08, 0.01, None, NEG, 'hornilla') for sx in (-1, 1) for sy in (-1, 1)]
@gen('campana_extractora')
def _(w, d, h, **k): return [tronco_pir(w, d, w*0.3, d*0.4, 0, h*0.3, MET, 'campana', dy=d*0.3), BZ(-w*0.15, w*0.15, d/2-d*0.4, d/2, h*0.3, h, MET, 'chimenea')]
@gen('meson_cocina')
def _(w, d, h, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, h-0.04, h, GRI, 'encimera'), BZ(-w/2, w/2, -d/2+0.05, d/2, 0, 0.1, NEG, 'zocalo'), BZ(-w/2, w/2, -d/2+0.02, d/2, 0.1, h-0.04, BLA, 'cuerpo')]
    n = max(1, int(w/0.6)); out += [BZ(-w/2 + i*w/n + 0.005, -w/2 + (i+1)*w/n - 0.005, -d/2, -d/2+0.02, 0.11, h-0.06, BLA, 'puerta') for i in range(n)]
    return out
@gen('fregadero')
def _(w, d, h, **k): return G['meson_cocina'](w, d, h-0.25) + [BZ(-w*0.3, w*0.3, -d*0.3, d*0.3, h-0.29, h-0.25, MET, 'poceta'), T([0, d*0.4, h-0.25], [0, d*0.4, h], 0.015, MET, 'grifo'), T([0, d*0.4, h], [0, d*0.1, h-0.05], 0.012, MET, 'cano')]
@gen('microondas')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.01, d/2, 0, h, BLA, 'cuerpo'), BZ(-w/2+0.02, w*0.2, -d/2, -d/2+0.01, 0.03, h-0.03, NEG, 'puerta'), BZ(w*0.25, w/2-0.03, -d/2, -d/2+0.01, h*0.5, h-0.04, GRI, 'panel')]
@gen('horno')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, MET, 'cuerpo'), BZ(-w/2+0.03, w/2-0.03, -d/2, -d/2+0.02, 0.03, h*0.8, NEG, 'puerta'), T([-w*0.35, -d/2, h*0.85], [w*0.35, -d/2, h*0.85], 0.012, MET, 'tirador')]
@gen('lavavajillas')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, MET, 'cuerpo'), BZ(-w/2, w/2, -d/2, -d/2+0.02, 0.1, h-0.08, MET, 'puerta'), BZ(-w/2, w/2, -d/2, -d/2+0.02, h-0.07, h, OSC, 'panel')]
@gen('lavadora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, BLA, 'cuerpo'), TO([0, -d/2+0.01, h*0.45], w*0.28, 0.03, [90, 0, 0], GRI, 'aro_puerta'), PL([0, -d/2+0.01, h*0.45], w*0.25, 0.01, [90, 0, 0], VID, 'vidrio'), BZ(-w/2+0.02, w/2-0.02, -d/2, -d/2+0.02, h*0.85, h-0.02, GRI, 'panel')]
@gen('secadora')
def _(w, d, h, **k): return G['lavadora'](w, d, h)
@gen('inodoro')
def _(w, d, h, **k):
    return [K([0, -d*0.05, 0], [0, -d*0.05, h*0.5], w*0.3, w*0.4, BLA, 'taza'), B(0, -d*0.05, h*0.5+0.02, w*0.85, d*0.6, 0.04, BLA, n='asiento'),
            BZ(-w/2, w/2, d/2-0.2, d/2, h*0.5, h, BLA, 'tanque'), BZ(-w*0.2, w*0.2, d/2-0.25, d/2-0.2, h*0.3, h*0.55, BLA, 'union')]
@gen('banera')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.08, BLA, 'fondo'), BZ(-w/2, -w/2+0.08, -d/2, d/2, 0.08, h, BLA, 'pared'), BZ(w/2-0.08, w/2, -d/2, d/2, 0.08, h, BLA, 'pared'),
                             BZ(-w/2+0.08, w/2-0.08, -d/2, -d/2+0.08, 0.08, h, BLA, 'pared'), BZ(-w/2+0.08, w/2-0.08, d/2-0.08, d/2, 0.08, h, BLA, 'pared')]
@gen('ducha')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.08, BLA, 'plato'), BZ(-w/2, -w/2+0.01, -d/2, d/2, 0.08, h*0.9, VID, 'mampara'), BZ(-w/2+0.01, w/2, -d/2, -d/2+0.01, 0.08, h*0.9, VID, 'mampara'),
                            T([w/2-0.05, d/2-0.05, 0.8], [w/2-0.05, d/2-0.05, h], 0.012, MET, 'barra'), T([w/2-0.05, d/2-0.05, h], [w/2-0.15, d/2-0.15, h-0.05], 0.012, MET, 'brazo'), PL([w/2-0.15, d/2-0.15, h-0.06], 0.08, 0.02, None, MET, 'regadera')]
@gen('lavamanos')
def _(w, d, h, **k): return [T([0, d*0.2, 0], [0, d*0.2, h-0.15], 0.07, BLA, 'pedestal'), BZ(-w/2, w/2, -d/2, d/2, h-0.15, h-0.05, BLA, 'lavabo'), T([0, d*0.38, h-0.05], [0, d*0.38, h], 0.012, MET, 'grifo')]
@gen('olla')
def _(w, d, h, **k): return [C(0, 0, 0, h*0.85, w*0.4, MET, 'cuerpo'), C(0, 0, h*0.85, h*0.05, w*0.42, MET, 'tapa'), S([0, 0, h*0.95], h*0.05, OSC, 'pomo')] + [T([sx*w*0.4, 0, h*0.7], [sx*w/2, 0, h*0.7], 0.012, OSC, 'asa') for sx in (-1, 1)]
@gen('cafetera')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.03, OSC, 'base'), BZ(-w/2, w/2, d*0.1, d/2, 0.03, h, OSC, 'columna'), BZ(-w/2, w/2, -d/2, d/2, h*0.8, h, OSC, 'cabezal'), C(0, -d*0.15, 0.03, h*0.45, w*0.35, VID, 'jarra')]
@gen('licuadora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.3, OSC, 'motor'), K([0, 0, h*0.3], [0, 0, h*0.95], w*0.3, w*0.45, VID, 'vaso'), C(0, 0, h*0.95, h*0.05, w*0.45, OSC, 'tapa')]
@gen('tostadora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, MET, 'cuerpo')] + [BZ(-w*0.35, w*0.35, y-0.015, y+0.015, h-0.002, h, NEG, 'ranura') for y in (-d*0.15, d*0.15)]
@gen('taza')
def _(w, d, h, **k): return [C(0, 0, 0, h, d/2, BLA, 'cuerpo'), TO([d/2, 0, h/2], h*0.25, 0.008, [90, 0, 0], BLA, 'asa')]
@gen('vaso')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h], w*0.4, w/2, VID, 'vaso')]
@gen('botella')
def _(w, d, h, **k): return [C(0, 0, 0, h*0.6, w/2, VER, 'cuerpo'), K([0, 0, h*0.6], [0, 0, h*0.78], w/2, w*0.18, VER, 'hombro'), C(0, 0, h*0.78, h*0.22, w*0.15, VER, 'cuello')]
@gen('plato')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h], w*0.3, w/2, BLA, 'plato')]
@gen('jarra')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h], d/2, d*0.4, VID, 'cuerpo'), TO([d*0.45, 0, h*0.55], h*0.25, 0.01, [90, 0, 0], VID, 'asa')]
@gen('sarten')
def _(w, d, h, **k): return [K([w/2-d/2, 0, 0], [w/2-d/2, 0, h], d*0.42, d/2, OSC, 'sarten'), T([w/2-d, 0, h*0.8], [-w/2+0.02, 0, h*0.8], 0.015, NEG, 'mango')]
@gen('mesa_cocina_isla')
def _(w, d, h, **k): return G['meson_cocina'](w, d, h)
@gen('alacena_pared')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.02, d/2, 0, h, MAD, 'cuerpo')] + [BZ(-w/2 + i*w/2 + 0.005, -w/2 + (i+1)*w/2 - 0.005, -d/2, -d/2+0.02, 0.01, h-0.01, MAD2, 'puerta') for i in range(2)]
@gen('toallero')
def _(w, d, h, **k): return [T([-w/2+0.02, d/2-0.02, h*0.8], [-w/2+0.02, -d/2+0.02, h*0.8], 0.01, MET, 'soporte'), T([w/2-0.02, d/2-0.02, h*0.8], [w/2-0.02, -d/2+0.02, h*0.8], 0.01, MET, 'soporte'),
                             T([-w/2+0.02, -d/2+0.02, h*0.8], [w/2-0.02, -d/2+0.02, h*0.8], 0.01, MET, 'barra'), BZ(-w*0.35, w*0.35, -d/2+0.005, -d/2+0.035, 0, h*0.8, AZU, 'toalla')]

# ======================= puertas, ventanas y vanos =======================
@gen('puerta')
def _(w, d, h, abierta_grados=0, **k):
    m = 0.06; out = [BZ(-w/2, -w/2+m, -d/2, d/2, 0, h, MAD2, 'marco'), BZ(w/2-m, w/2, -d/2, d/2, 0, h, MAD2, 'marco'), BZ(-w/2, w/2, -d/2, d/2, h-m, h, MAD2, 'marco')]
    hw = w - 2*m; a = math.radians(abierta_grados); cx = -w/2+m + hw/2*math.cos(a); cy = -hw/2*math.sin(a)
    out += [B(cx, cy, (h-m)/2, hw, 0.04, h-m-0.01, MAD, [0, 0, -abierta_grados], 'hoja'), S([-w/2+m + (hw-0.08)*math.cos(a), -(hw-0.08)*math.sin(a) - 0.03, 1.0], 0.03, MET, 'pomo')]
    return out
@gen('puerta_garaje')
def _(w, d, h, **k):
    out = [BZ(-w/2, -w/2+0.1, -d/2, d/2, 0, h, CEM, 'jamba'), BZ(w/2-0.1, w/2, -d/2, d/2, 0, h, CEM, 'jamba'), BZ(-w/2, w/2, -d/2, d/2, h-0.15, h, CEM, 'dintel')]
    n = 5; return out + [BZ(-w/2+0.1, w/2-0.1, -0.02, 0.02, i*(h-0.15)/n + 0.005, (i+1)*(h-0.15)/n - 0.005, BLA, 'panel') for i in range(n)]
@gen('ventana')
def _(w, d, h, alfeizar=0.9, hojas=2, **k):
    m = 0.05; out = [BZ(-w/2, w/2, -d/2, d/2, alfeizar, alfeizar+m, BLA, 'marco'), BZ(-w/2, w/2, -d/2, d/2, h-m, h, BLA, 'marco'),
                     BZ(-w/2, -w/2+m, -d/2, d/2, alfeizar, h, BLA, 'marco'), BZ(w/2-m, w/2, -d/2, d/2, alfeizar, h, BLA, 'marco'), BZ(-w/2-0.03, w/2+0.03, -d/2-0.04, d/2, alfeizar-0.03, alfeizar, BLA, 'alfeizar')]
    out += [BZ(-w/2+m + i*(w-2*m)/hojas, -w/2+m + (i+1)*(w-2*m)/hojas, -0.005, 0.005, alfeizar+m, h-m, VID, 'vidrio') for i in range(hojas)]
    return out + [BZ(-0.015, 0.015, -d/2, d/2, alfeizar+m, h-m, BLA, 'parteluz')] if hojas == 2 else out
@gen('ventana_persiana')
def _(w, d, h, alfeizar=0.9, **k):
    out = G['ventana'](w, d, h, alfeizar=alfeizar, hojas=1); n = 12; hh = (h-alfeizar)/n
    return out + [B(0, -d/2-0.02, alfeizar + (i+0.5)*hh, w-0.1, 0.01, hh*0.6, GRI, [-30, 0, 0], 'lama') for i in range(n)]
@gen('ventanal')
def _(w, d, h, **k): return G['ventana'](w, d, h, alfeizar=0.03, hojas=3)
@gen('vano')
def _(w, d, h, **k): return [BZ(-w/2, -w/2+0.05, -d/2, d/2, 0, h, CEM, 'jamba'), BZ(w/2-0.05, w/2, -d/2, d/2, 0, h, CEM, 'jamba'), BZ(-w/2, w/2, -d/2, d/2, h-0.08, h, CEM, 'dintel')]
@gen('porton_reja')
def _(w, d, h, **k):
    out = [B(sx*(w/2-0.07), 0, h/2, 0.14, d, h, CEM, n='pilar') for sx in (-1, 1)] + [T([-w/2+0.14, 0, z], [w/2-0.14, 0, z], 0.02, NEG, 'travesano') for z in (0.15, h*0.5, h-0.15)]
    n = int((w-0.28)/0.12); return out + [T([-w/2+0.14+0.12*(i+0.5), 0, 0.05], [-w/2+0.14+0.12*(i+0.5), 0, h-0.08], 0.012, NEG, 'barrote') for i in range(n)]
@gen('arco')
def _(w, d, h, grosor=0.4, **k):
    R = w/2 - grosor/2; hp = h - w/2; out = [BZ(-w/2, -w/2+grosor, -d/2, d/2, 0, hp, CEM, 'pilar'), BZ(w/2-grosor, w/2, -d/2, d/2, 0, hp, CEM, 'pilar')]
    n = 9
    for i in range(n):
        a = math.pi*(i+0.5)/n; out.append(B(R*math.cos(a), 0, hp + R*math.sin(a), grosor, d, R*math.pi/n*1.1, CEM, [0, 90-math.degrees(a), 0], 'dovela'))
    return out
@gen('puerta_corredera_vidrio')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.06, h, MET, 'riel'), BZ(-w/2, w/2, -d/2, d/2, 0, 0.03, MET, 'riel'), BZ(-w/2+0.02, 0.02, -0.04, -0.01, 0.03, h-0.06, VID, 'hoja'), BZ(-0.02, w/2-0.02, 0.01, 0.04, 0.03, h-0.06, VID, 'hoja')]
@gen('escotilla_suelo')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.5, MET, 'marco'), BZ(-w/2+0.04, w/2-0.04, -d/2+0.04, d/2-0.04, h*0.5, h, GRI, 'tapa'), TO([0, 0, h], 0.04, 0.008, None, MET, 'argolla')]

# ======================= escaleras y rampas =======================
@gen('escalera_recta')
def _(w, d, h, peldanos=None, **k):
    n = peldanos or max(2, round(h/0.175)); hz = h/n; dy = d/n
    return [BZ(-w/2, w/2, -d/2 + i*dy, d/2, i*hz, (i+1)*hz, CEM, 'peldano') for i in range(n)]
@gen('escalera_caracol')
def _(w, d, h, **k):
    n = max(6, round(h/0.19)); R = min(w, d)/2; out = [C(0, 0, 0, h, 0.06, MET, 'eje')]
    for i in range(n):
        a = 2*math.pi*i/12; out.append(B((R/2)*math.cos(a), (R/2)*math.sin(a), (i+1)*h/n - 0.02, R*0.95, 0.28, 0.04, MAD, [0, 0, math.degrees(a)], 'peldano'))
    return out
@gen('escalera_mano')
def _(w, d, h, **k):
    inc = d; out = [T([sx*(w/2-0.02), -inc/2, 0], [sx*(w/2-0.02), inc/2, h], 0.02, MAD, 'larguero') for sx in (-1, 1)]; n = int(h/0.3)
    return out + [T([-w/2+0.02, -inc/2 + inc*(i+1)/(n+1), h*(i+1)/(n+1)], [w/2-0.02, -inc/2 + inc*(i+1)/(n+1), h*(i+1)/(n+1)], 0.015, MAD, 'peldano') for i in range(n)]
@gen('escalera_tijera')
def _(w, d, h, **k):
    out = [T([sx*(w/2-0.02), sy*(d/2-0.02), 0], [sx*(w/2-0.04), 0, h-0.03], 0.018, MET, 'pata') for sx in (-1, 1) for sy in (-1, 1)] + [BZ(-w/2+0.02, w/2-0.02, -0.08, 0.08, h-0.03, h, GRI, 'tope')]
    return out + [BZ(-w/2+0.04, w/2-0.04, -(d/2-0.02)*(1-z/h)-0.04, -(d/2-0.02)*(1-z/h)+0.04, z-0.015, z+0.015, GRI, 'peldano') for z in (h*0.25, h*0.5, h*0.75)]
@gen('rampa')
def _(w, d, h, **k): return [PO([[-w/2, -d/2, 0], [w/2, -d/2, 0], [-w/2, d/2, 0], [w/2, d/2, 0], [-w/2, d/2, h], [w/2, d/2, h]], CEM, 'rampa')]
@gen('escalinata_exterior')
def _(w, d, h, **k): return G['escalera_recta'](w, d, h, peldanos=max(2, round(h/0.15))) + [BZ(-w/2-0.2, -w/2, -d/2, d/2, 0, h+0.3, PIE, 'murete'), BZ(w/2, w/2+0.2, -d/2, d/2, 0, h+0.3, PIE, 'murete')]
@gen('escalera_mecanica')
def _(w, d, h, **k): return [PO([[sx*w/2, -d/2, 0] for sx in (-1, 1)] + [[sx*w/2, -d/2+1, 0] for sx in (-1, 1)] + [[sx*w/2, d/2, h-0.9] for sx in (-1, 1)] + [[sx*w/2, d/2-1, h-0.9] for sx in (-1, 1)] + [[sx*w/2, d/2, h-1.4] for sx in (-1, 1)], GRI, 'cuerpo')] + \
                                        [PO([[sx*(w/2), -d/2+0.3, 1.0], [sx*(w/2), -d/2+0.3, 0.0], [sx*(w/2-0.1), -d/2+0.3, 1.0], [sx*(w/2), d/2-0.2, h], [sx*(w/2-0.1), d/2-0.2, h], [sx*(w/2), d/2-0.2, h-1.0]], NEG, 'pasamanos') for sx in (-1, 1)]

# ======================= vehículos (largo en x, frente a +x) =======================
def _auto(L, W, H, r, cab, col):
    return [BZ(-L/2, L/2, -W/2, W/2, r*0.6, H*0.55, col, 'carroceria'), tronco_pir(L*cab, W*0.94, L*cab*0.6, W*0.84, H*0.55, H*0.45, VID, 'cabina'),
            BZ(L/2-0.01, L/2, -W*0.4, -W*0.25, H*0.4, H*0.5, LUZ, 'faro'), BZ(L/2-0.01, L/2, W*0.25, W*0.4, H*0.4, H*0.5, LUZ, 'faro')] + ruedas([-L*0.32, L*0.32], W, r, 0.2)
@gen('auto_sedan')
def _(w, d, h, col=ROJ, **k): return _auto(w, d, h, 0.32, 0.55, col)
@gen('auto_suv')
def _(w, d, h, col=AZU, **k): return _auto(w, d, h, 0.38, 0.7, col)
@gen('camioneta_pickup')
def _(w, d, h, col=BLA, **k):
    r = 0.38; return [BZ(-w/2, w/2, -d/2, d/2, r*0.6, h*0.5, col, 'chasis'), BZ(-w*0.05, w*0.3, -d/2+0.05, d/2-0.05, h*0.5, h, VID, 'cabina'),
                      BZ(-w/2, -w*0.05, -d/2, -d/2+0.05, h*0.5, h*0.65, col, 'borde_caja'), BZ(-w/2, -w*0.05, d/2-0.05, d/2, h*0.5, h*0.65, col, 'borde_caja'), BZ(-w/2, -w/2+0.05, -d/2, d/2, h*0.5, h*0.65, col, 'compuerta')] + ruedas([-w*0.32, w*0.32], d, r, 0.25)
@gen('furgoneta')
def _(w, d, h, col=BLA, **k): return [BZ(-w/2, w/2-0.8, -d/2, d/2, 0.25, h, col, 'caja'), tronco_pir(0.8, d, 0.3, d*0.9, 0.25, h*0.9, col, 'morro')] + [B(w/2-0.4, 0, h*0.6, 0.3, d*0.9, h*0.35, VID, [0, 30, 0], 'parabrisas')] + ruedas([-w*0.33, w*0.32], d, 0.35, 0.22)
@gen('autobus')
def _(w, d, h, col=AMA, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, 0.3, h, col, 'carroceria')] + [BZ(-w/2+0.5 + i*1.2, -w/2+1.5 + i*1.2, -d/2-0.01, -d/2, h*0.55, h*0.88, VID, 'ventana') for i in range(int((w-1.5)/1.2))]
    return out + [BZ(w/2-0.01, w/2, -d/2+0.1, d/2-0.1, h*0.45, h*0.9, VID, 'parabrisas')] + ruedas([-w*0.32, w*0.3], d, 0.5, 0.3)
@gen('camion')
def _(w, d, h, **k): return [BZ(-w/2, w/2-2.2, -d/2, d/2, 0.9, h, BLA, 'caja'), BZ(w/2-2.1, w/2, -d/2+0.05, d/2-0.05, 0.6, h*0.75, ROJ, 'cabina'), BZ(-w/2, w/2, -d*0.3, d*0.3, 0.45, 0.9, OSC, 'chasis')] + ruedas([-w*0.38, -w*0.22, w*0.36], d, 0.5, 0.3)
@gen('motocicleta')
def _(w, d, h, **k):
    r = 0.32; out = [C(sx*(w/2-r), 0, r, 0.12, r, NEG, 'rueda', rot=[90, 0, 0]) for sx in (-1, 1)]
    return out + [B(0, 0, r+0.25, w*0.45, 0.3, 0.35, ROJ, n='motor'), B(-w*0.1, 0, r+0.45, w*0.35, 0.28, 0.12, NEG, n='asiento'), T([w/2-r, 0, r], [w*0.25, 0, h-0.1], 0.03, MET, 'horquilla'), T([w*0.25, -d/2, h-0.05], [w*0.25, d/2, h-0.05], 0.02, MET, 'manillar'), T([-w/2+r, 0, r], [-w*0.1, 0, r+0.35], 0.03, MET, 'basculante')]
@gen('bicicleta')
def _(w, d, h, **k):
    r = 0.34; a = [-w/2+r, 0, r]; b = [w/2-r, 0, r]; p = [0, 0, r]; s = [-0.12, 0, h-0.2]; t = [w*0.22, 0, h-0.15]
    return [TO(a, r-0.02, 0.02, [90, 0, 0], NEG, 'rueda'), TO(b, r-0.02, 0.02, [90, 0, 0], NEG, 'rueda'), T(a, p, 0.015, ROJ, 'cuadro'), T(p, s, 0.015, ROJ, 'cuadro'), T(s, t, 0.015, ROJ, 'cuadro'), T(p, t, 0.015, ROJ, 'cuadro'),
            T(a, s, 0.012, ROJ, 'cuadro'), T(t, b, 0.015, MET, 'horquilla'), T([t[0], -d/2, h-0.03], [t[0], d/2, h-0.03], 0.012, NEG, 'manillar'), T(t, [t[0], 0, h-0.03], 0.012, MET, 'potencia'), B(-0.14, 0, h-0.18, 0.25, 0.1, 0.05, NEG, n='sillin')]
@gen('patinete')
def _(w, d, h, **k): return [BZ(-w/2+0.08, w/2-0.08, -0.07, 0.07, 0.08, 0.12, OSC, 'tabla'), C(-w/2+0.08, 0, 0.08, 0.04, 0.08, NEG, 'rueda', rot=[90, 0, 0]), C(w/2-0.08, 0, 0.08, 0.04, 0.08, NEG, 'rueda', rot=[90, 0, 0]),
                                T([w/2-0.08, 0, 0.12], [w/2-0.12, 0, h-0.02], 0.016, MET, 'manubrio'), T([w/2-0.12, -d/2, h-0.02], [w/2-0.12, d/2, h-0.02], 0.016, NEG, 'puno')]
@gen('vagon_tren')
def _(w, d, h, **k):
    out = [BZ(-w/2, w/2, -d/2, d/2, 0.9, h-0.2, GRI, 'caja'), BZ(-w/2+0.2, w/2-0.2, -d/2+0.2, d/2-0.2, h-0.2, h, GRI, 'techo')] + [BZ(-w/2+0.8 + i*1.6, -w/2+1.9 + i*1.6, -d/2-0.01, -d/2, 1.7, 2.5, VID, 'ventana') for i in range(int((w-1.6)/1.6))]
    return out + [C(x, sy*(d/2-0.4), 0.45, 0.1, 0.45, NEG, 'rueda', rot=[90, 0, 0]) for x in (-w*0.4, -w*0.3, w*0.3, w*0.4) for sy in (-1, 1)]
@gen('bote')
def _(w, d, h, **k): return [PO([[-w/2, -d/2, h*0.6], [-w/2, d/2, h*0.6], [w/2, 0, h*0.7], [-w/2+0.2, -d*0.35, 0], [-w/2+0.2, d*0.35, 0], [w*0.3, 0, 0]], MAD, 'casco'), BZ(-w*0.1, w*0.05, -d/2+0.05, d/2-0.05, h*0.4, h*0.47, MAD2, 'banco'), T([-w*0.1, 0, h*0.6], [-w*0.1, 0, h], 0.03, MAD2, 'mastil')]
@gen('carrito_compras')
def _(w, d, h, **k):
    out = [tronco_pir(w*0.75, d*0.85, w*0.95, d, 0.45, h*0.55, MET, 'cesta'), BZ(-w/2, -w/2+0.04, -d/2, d/2, 0.95, h, NEG, 'empunadura')] + [T([sx*w*0.35, sy*d*0.38, 0.07], [sx*w*0.35, sy*d*0.38, 0.45], 0.012, MET, 'pata') for sx in (-1, 1) for sy in (-1, 1)]
    return out + [S([sx*w*0.35, sy*d*0.38, 0.06], 0.06, NEG, 'rueda') for sx in (-1, 1) for sy in (-1, 1)]
@gen('carretilla')
def _(w, d, h, **k): return [tronco_pir(w*0.45, d*0.5, w*0.65, d, 0.3, h-0.3, VER, 'batea', dy=0.0), C(w/2-0.2, 0, 0.2, 0.08, 0.2, NEG, 'rueda', rot=[90, 0, 0])] + [T([w*0.2, sy*0.15, 0.25], [-w/2, sy*0.25, 0.6], 0.02, MAD, 'brazo') for sy in (-1, 1)] + [T([-w*0.15, sy*0.15, 0.3], [-w*0.15, sy*0.15, 0], 0.015, MET, 'pata') for sy in (-1, 1)]
@gen('helicoptero')
def _(w, d, h, **k):
    return [S([w*0.2, 0, h*0.5], h*0.35, BLA, 'cabina'), BZ(-w*0.1, w*0.3, -d*0.12, d*0.12, h*0.25, h*0.75, BLA, 'cuerpo'), T([-w*0.1, 0, h*0.6], [-w/2, 0, h*0.65], 0.08, BLA, 'cola'),
            T([0.1, -d/2, h*0.97], [0.1, d/2, h*0.97], 0.02, NEG, 'aspa'), T([-w*0.3, 0, h*0.97], [w/2, 0, h*0.97], 0.02, NEG, 'aspa'), T([0.1, 0, h*0.78], [0.1, 0, h*0.97], 0.04, MET, 'rotor')] + [T([-w*0.15, sy*d*0.12, 0.02], [w*0.35, sy*d*0.12, 0.02], 0.02, MET, 'patin') for sy in (-1, 1)]
@gen('avioneta')
def _(w, d, h, **k): return [T([-w/2, 0, h*0.5], [w/2-0.3, 0, h*0.5], h*0.18, BLA, 'fuselaje'), K([w/2-0.3, 0, h*0.5], [w/2, 0, h*0.5], h*0.18, 0.05, ROJ, 'morro'), BZ(-w*0.05, w*0.15, -d/2, d/2, h*0.62, h*0.68, BLA, 'ala'), BZ(-w/2, -w/2+0.6, -d*0.18, d*0.18, h*0.55, h*0.6, BLA, 'estabilizador'), BZ(-w/2, -w/2+0.5, -0.03, 0.03, h*0.6, h, BLA, 'deriva')] + [C(w*0.05, sy*0.6, 0.15, 0.08, 0.15, NEG, 'rueda', rot=[90, 0, 0]) for sy in (-1, 1)]
@gen('tanque_militar')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0.3, h*0.5, VER2, 'casco')] + [BZ(-w/2+0.1, w/2-0.1, sy*(d/2-0.25)-0.25, sy*(d/2-0.25)+0.25, 0, 0.6, NEG, 'oruga') for sy in (-1, 1)] + [C(-w*0.05, 0, h*0.5, h*0.3, d*0.3, VER2, 'torreta'), T([0, 0, h*0.68], [w/2+0.0, 0, h*0.7], 0.07, VER2, 'canon')]

# ======================= mobiliario urbano =======================
@gen('banco_calle')
def _(w, d, h, **k):
    out = [BZ(-w/2, w/2, -d/2 + i*0.1, -d/2 + i*0.1 + 0.08, 0.42, 0.45, MAD, 'listón') for i in range(int(d/0.1))] + [B(0, d/2-0.03, 0.65, w, 0.03, 0.3, MAD, [-10, 0, 0], 'respaldo')]
    return out + [BZ(sx*(w/2-0.15)-0.03, sx*(w/2-0.15)+0.03, -d/2, d/2, 0, 0.42, NEG, 'pata') for sx in (-1, 1)] + [T([sx*(w/2-0.15), d/2-0.05, 0.42], [sx*(w/2-0.15), d/2-0.03, h-0.02], 0.02, NEG, 'soporte') for sx in (-1, 1)]
@gen('farola')
def _(w, d, h, **k):
    lw = min(0.45, w*0.35); px = -w/2 + 0.12
    return [C(px, 0, 0, 0.3, 0.12, OSC, 'base'), K([px, 0, 0.3], [px, 0, h-0.3], 0.08, 0.05, OSC, 'poste'), T([px, 0, h-0.3], [w/2-lw/2, 0, h-0.1], 0.04, OSC, 'brazo'),
            B(w/2-lw/2, 0, h-0.125, lw, d, 0.25, LUZ, n='luminaria')]
@gen('semaforo')
def _(w, d, h, **k): return [T([0, 0, 0], [0, 0, h-0.95], 0.06, OSC, 'poste'), BZ(-w/2, w/2, -d/2, d/2, h-0.95, h, NEG, 'caja')] + [PL([0, -d/2-0.005, h-0.95 + 0.17 + i*0.31], w*0.35, 0.01, [90, 0, 0], c, 'luz') for i, c in enumerate((VER, AMA, ROJ))]
@gen('hidrante')
def _(w, d, h, **k): return [C(0, 0, 0, 0.05, w*0.4, ROJ, 'base'), C(0, 0, 0.05, h*0.7, w*0.28, ROJ, 'cuerpo'), S([0, 0, h*0.78], w*0.28, ROJ, 'cupula'), T([-w/2, 0, h*0.55], [w/2, 0, h*0.55], 0.05, ROJ, 'boca'), T([0, -d/2, h*0.55], [0, 0, h*0.55], 0.06, ROJ, 'boca')]
@gen('parada_bus')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.08, h, MET, 'techo'), BZ(-w/2+0.05, w/2-0.05, d/2-0.05, d/2-0.02, 0.15, h-0.1, VID, 'panel_fondo'), BZ(-w/2, -w/2+0.03, -d/2+0.1, d/2-0.05, 0.15, h-0.1, VID, 'panel_lado'), BZ(-w*0.3, w*0.3, d/2-0.45, d/2-0.1, 0.42, 0.46, MAD, 'banco')] + postes4(w, d, h-0.08, 0.06, MET)
@gen('kiosco')
def _(w, d, h, **k): return [BZ(-w/2+0.1, w/2-0.1, -d/2+0.1, d/2-0.1, 0, h-0.4, VER, 'cuerpo'), BZ(-w/2+0.12, w/2-0.12, -d/2+0.09, -d/2+0.1, 0.9, h-0.6, VID, 'ventanilla'), BZ(-w/2+0.1, w/2-0.1, -d/2, -d/2+0.1, 0.85, 0.9, MAD, 'mostrador'), tronco_pir(w, d, w*0.2, d*0.2, h-0.4, 0.4, ROJ, 'techo')]
@gen('buzon')
def _(w, d, h, **k): return [T([0, 0, 0], [0, 0, h*0.5], 0.04, AZU, 'poste'), BZ(-w/2, w/2, -d/2, d/2, h*0.5, h - w/2, AZU, 'cuerpo'), C(0, 0, h - w/2, d, w/2, AZU, 'tapa', rot=[90, 0, 0])]
@gen('senal_trafico')
def _(w, d, h, **k): return [T([0, 0, 0], [0, 0, h-w/2], 0.03, MET, 'poste'), PL([0, -0.04, h-w/2], w/2, 0.02, [90, 0, 0], ROJ, 'placa')]
@gen('contenedor_basura')
def _(w, d, h, **k): return [tronco_pir(w*0.95, d*0.9, w, d, 0.15, h-0.2, VER2, 'cuerpo'), BZ(-w/2, w/2, -d/2, d/2, h-0.05, h, VER, 'tapa')] + [S([sx*(w/2-0.15), sy*(d/2-0.12), 0.08], 0.08, NEG, 'rueda') for sx, sy in ESQ]
@gen('papelera_calle')
def _(w, d, h, **k):
    r = w/2; cy = -d/2 + r
    return [T([0, d/2-0.03, 0], [0, d/2-0.03, h], 0.03, OSC, 'poste'), BZ(-0.03, 0.03, cy, d/2-0.03, h*0.7, h*0.75, OSC, 'soporte'), C(0, cy, h*0.35, h*0.55, r, GRI, 'cubo')]
@gen('bolardo')
def _(w, d, h, **k): return [C(0, 0, 0, h-w/2, w/2, GRI, 'cuerpo'), S([0, 0, h-w/2], w/2, GRI, 'tope'), TO([0, 0, h*0.75], w/2, 0.01, None, AMA, 'franja')]
@gen('valla_metalica')
def _(w, d, h, **k):
    out = [T([sx*(w/2-0.03), 0, 0.05], [sx*(w/2-0.03), 0, h], 0.025, MET, 'marco') for sx in (-1, 1)] + [T([-w/2+0.03, 0, z], [w/2-0.03, 0, z], 0.02, MET, 'marco') for z in (0.1, h-0.02)]
    out += [T([-w/2+0.1*(i+1), 0, 0.1], [-w/2+0.1*(i+1), 0, h-0.02], 0.006, MET, 'barra') for i in range(int((w-0.1)/0.1))]
    return out + [BZ(sx*(w/2-0.03)-0.3, sx*(w/2-0.03)+0.3, -d/2, d/2, 0, 0.05, CEM, 'pie') for sx in (-1, 1)]
@gen('cerca_madera')
def _(w, d, h, **k):
    n = max(2, int(w/0.15)); out = [BZ(-w/2 + i*w/n + 0.01, -w/2 + (i+1)*w/n - 0.01, -d/2+0.04, d/2, 0, h, MAD, 'tabla') for i in range(n)]
    return out + [BZ(-w/2, w/2, -d/2, -d/2+0.04, z, z+0.08, MAD2, 'travesano') for z in (h*0.2, h*0.75)]
@gen('barandilla')
def _(w, d, h, **k): return [T([-w/2, 0, h-0.03], [w/2, 0, h-0.03], 0.03, MET, 'pasamanos')] + [T([-w/2+0.03 + i*(w-0.06)/max(1, int(w/0.12)), 0, 0], [-w/2+0.03 + i*(w-0.06)/max(1, int(w/0.12)), 0, h-0.03], 0.01, MET, 'balaustre') for i in range(int(w/0.12)+1)]
@gen('cono_trafico')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.03, NAR, 'base'), K([0, 0, 0.03], [0, 0, h], w*0.35, 0.02, NAR, 'cono'), TO([0, 0, h*0.55], w*0.17, 0.012, None, BLA, 'franja')]
@gen('barrera_obra')
def _(w, d, h, **k): return [B(0, 0, h-0.1, w, 0.03, 0.18, ROJ, n='tablero'), B(0, 0, h*0.45, w, 0.03, 0.15, BLA, n='tablero')] + [T([sx*(w/2-0.1), sy*(d/2-0.02), 0], [sx*(w/2-0.1), 0, h], 0.02, MET, 'pata') for sx in (-1, 1) for sy in (-1, 1)]
@gen('fuente')
def _(w, d, h, **k):
    R = w/2; return [TU([0, 0, 0], R, R-0.25, 0.5, 16, PIE, 'pileta'), C(0, 0, 0, 0.35, R-0.2, AGU, 'agua'), T([0, 0, 0.35], [0, 0, h*0.6], 0.15, PIE, 'columna'), K([0, 0, h*0.6], [0, 0, h*0.7], 0.2, R*0.4, PIE, 'taza'), T([0, 0, h*0.7], [0, 0, h], 0.06, AGU, 'chorro')]
@gen('poste_electrico')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, h], 0.15, 0.1, MAD2, 'poste'), T([-w/2, 0, h-0.4], [w/2, 0, h-0.4], 0.06, MAD2, 'cruceta')] + [C(x, 0, h-0.35, 0.12, 0.04, BLA, 'aislador') for x in (-w/2+0.1, 0.25, w/2-0.1)] + [C(0, -0.25, h-1.5, 0.5, 0.2, GRI, 'transformador')]
@gen('parquimetro')
def _(w, d, h, **k): return [T([0, 0, 0], [0, 0, h-0.35], 0.04, OSC, 'poste'), BZ(-w/2, w/2, -d/2, d/2, h-0.35, h, GRI, 'cabeza'), BZ(-w*0.3, w*0.3, -d/2-0.002, -d/2, h-0.15, h-0.05, VID, 'pantalla')]
@gen('cabina_telefonica')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.1, ROJ, 'base'), BZ(-w/2, w/2, -d/2, d/2, h-0.25, h, ROJ, 'techo')] + postes4(w, d, h-0.25, 0.08, ROJ, 0.1) + [BZ(-w/2+0.08, w/2-0.08, -d/2+0.02, -d/2+0.04, 0.4, h-0.35, VID, 'vidrio'), BZ(-w/2+0.08, w/2-0.08, d/2-0.04, d/2-0.02, 0.4, h-0.35, VID, 'vidrio')]
@gen('bebedero')
def _(w, d, h, **k): return [C(0, 0, 0, h-0.1, 0.12, GRI, 'columna'), C(0, 0, h-0.1, 0.1, w/2, GRI, 'taza')] + [S([0, 0, h-0.03], 0.03, MET, 'grifo')]
@gen('jardinera')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.6, CEM, 'jardinera')] + [S([x, 0, h*0.6+0.001 + (h*0.4)/2 - 0.001], h*0.2, VER, 'planta') for x in (-w/3, 0, w/3)]
@gen('marquesina')
def _(w, d, h, **k): return [B(0, 0, h-0.15, w, d, 0.05, ROJ, [-12, 0, 0], 'lona')] + [T([sx*(w/2-0.02), d/2-0.02, h-0.6], [sx*(w/2-0.02), -d/2+0.05, h-0.24], 0.015, MET, 'brazo') for sx in (-1, 1)]
@gen('mesa_terraza_sombrilla')
def _(w, d, h, **k): return [C(0, 0, 0.72, 0.03, 0.4, BLA, 'mesa'), T([0, 0, 0], [0, 0, 0.72], 0.03, MET, 'pie'), C(0, 0, 0, 0.02, 0.25, MET, 'base'), T([0, 0, 0.75], [0, 0, h-0.35], 0.02, MET, 'mastil'), K([0, 0, h-0.35], [0, 0, h], w/2, 0.03, AMA, 'sombrilla')]
@gen('portabicicletas')
def _(w, d, h, **k):
    R = h/2 - 0.01; n = max(2, int((w - 0.1)/(2*R + 0.15)) + 1); xs = [-w/2 + R + 0.02 + i*(w - 2*R - 0.04)/(n - 1) for i in range(n)]
    return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.02, MET, 'riel')] + [TO([x, 0, h/2], R - 0.01, 0.01, [90, 0, 0], MET, 'aro') for x in xs]
# ======================= estructuras y arquitectura =======================
@gen('columna_cuadrada')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.1, CEM, 'basa'), BZ(-w/2+0.05, w/2-0.05, -d/2+0.05, d/2-0.05, 0.1, h-0.1, CEM, 'fuste'), BZ(-w/2, w/2, -d/2, d/2, h-0.1, h, CEM, 'capitel')]
@gen('columna_redonda')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.08, PIE, 'basa'), C(0, 0, 0.08, h-0.16, w/2*0.8, PIE, 'fuste'), BZ(-w/2, w/2, -d/2, d/2, h-0.08, h, PIE, 'capitel')]
@gen('viga')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.15, MET, 'ala'), BZ(-w/2, w/2, -d/2, d/2, h*0.85, h, MET, 'ala'), BZ(-w/2, w/2, -d*0.1, d*0.1, h*0.15, h*0.85, MET, 'alma')]
@gen('muro')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, CEM, 'muro')]
@gen('muro_ladrillo')
def _(w, d, h, **k):
    out = []; hl = 0.075; L = 0.25; filas = max(1, int(h/hl))
    for f in range(filas):
        x = -w/2 - (L/2 if f % 2 else 0)
        while x < w/2:
            x0, x1 = max(x, -w/2), min(x+L-0.01, w/2)
            if x1 - x0 > 0.02: out.append(BZ(x0, x1, -d/2, d/2, f*hl, f*hl+hl-0.01, LAD, 'ladrillo'))
            x += L
    return out
@gen('portico')
def _(w, d, h, **k): return [BZ(-w/2, -w/2+d, -d/2, d/2, 0, h-d, MAD2, 'pilar'), BZ(w/2-d, w/2, -d/2, d/2, 0, h-d, MAD2, 'pilar'), BZ(-w/2, w/2, -d/2, d/2, h-d, h, MAD2, 'dintel')]
@gen('andamio')
def _(w, d, h, niveles=3, **k):
    out = [T([sx*(w/2-0.03), sy*(d/2-0.03), 0], [sx*(w/2-0.03), sy*(d/2-0.03), h], 0.025, MET, 'tubo') for sx, sy in ESQ]
    for i in range(1, niveles+1):
        z = h*i/niveles - 0.05; out.append(BZ(-w/2+0.03, w/2-0.03, -d/2+0.03, d/2-0.03, z, z+0.04, MAD, 'plataforma'))
        out.append(T([-w/2+0.03, -d/2+0.03, z - h/niveles + 0.05], [w/2-0.03, -d/2+0.03, z], 0.015, MET, 'diagonal'))
    return out
@gen('valla_publicitaria')
def _(w, d, h, **k): return [T([0, d*0.3, 0], [0, d*0.3, h*0.55], 0.15, MET, 'poste'), BZ(-w/2, w/2, -d/2, -d/2+0.2, h*0.55, h, BLA, 'cartel'), BZ(-w/2+0.1, w/2-0.1, -d/2-0.002, -d/2, h*0.58, h-0.05, AZU, 'imagen'), BZ(-w/2, w/2, -d/2+0.2, d/2, h*0.55, h*0.58, MET, 'pasarela')]
@gen('tanque_agua')
def _(w, d, h, **k): return [C(0, 0, h*0.35, h*0.55, w/2, AZU, 'tanque'), K([0, 0, h*0.9], [0, 0, h], w/2, 0.05, AZU, 'tapa')] + [T([sx*w*0.35, sy*d*0.35, 0], [sx*w*0.3, sy*d*0.3, h*0.35], 0.04, MET, 'pata') for sx, sy in ESQ]
@gen('torre_antena')
def _(w, d, h, **k):
    out = [T([sx*w/2*(1-0.0)*0.95, sy*d/2*0.95, 0], [sx*0.1, sy*0.1, h-1], 0.04, ROJ if i % 2 else BLA, 'montante') for i, (sx, sy) in enumerate(ESQ)]
    return out + [T([0, 0, h-1], [0, 0, h], 0.03, MET, 'antena')] + [TO([0, 0, z], (w/2)*(1 - z/h)*0.95, 0.015, None, MET, 'anillo') for z in (h*0.25, h*0.5, h*0.75)]
@gen('silo')
def _(w, d, h, **k): return [C(0, 0, 0, h-w/2, w/2, MET, 'cuerpo'), K([0, 0, h-w/2], [0, 0, h], w/2, 0.1, MET, 'techo')]
@gen('puente_peatonal')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-1.3, h-1.1, CEM, 'tablero')] + [BZ(x-0.2, x+0.2, -0.2, 0.2, 0, h-1.3, CEM, 'pila') for x in (-w*0.35, w*0.35)] + \
                                     [T([-w/2, sy*(d/2-0.03), h-0.05], [w/2, sy*(d/2-0.03), h-0.05], 0.03, MET, 'baranda') for sy in (-1, 1)] + [T([x, sy*(d/2-0.03), h-1.1], [x, sy*(d/2-0.03), h-0.05], 0.02, MET, 'poste') for x in (-w/2+0.1, 0, w/2-0.1) for sy in (-1, 1)]
@gen('tejado_dos_aguas')
def _(w, d, h, **k): return [prisma(w, d, 0, h, LAD, 'tejado')]
@gen('casa_simple')
def _(w, d, h, **k):
    hp = h*0.62; return [BZ(-w/2, w/2, -d/2, d/2, 0, hp, CEM, 'muros'), prisma(w+0.0, d, hp, h-hp, LAD, 'tejado'), BZ(-0.45, 0.45, -d/2-0.01, -d/2, 0, 2.05, MAD, 'puerta'),
                         BZ(-w/2+0.5, -w/2+1.5, -d/2-0.01, -d/2, 1.0, 2.0, VID, 'ventana'), BZ(w/2-1.5, w/2-0.5, -d/2-0.01, -d/2, 1.0, 2.0, VID, 'ventana')]
@gen('edificio_bloque')
def _(w, d, h, pisos=None, **k):
    n = pisos or max(1, int(h/3)); out = [BZ(-w/2, w/2, -d/2, d/2, 0, h, CEM, 'bloque')]; nv = max(1, int(w/2.5))
    for p in range(n):
        for i in range(nv): out.append(BZ(-w/2 + (i+0.2)*w/nv, -w/2 + (i+0.8)*w/nv, -d/2-0.01, -d/2, p*h/n + h/n*0.3, p*h/n + h/n*0.8, VID, 'ventana'))
    return out
@gen('caseta')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.8, MAD, 'cuerpo'), tronco_pir(w, d, w, 0.02, h*0.8, h*0.2, MAD2, 'techo'), BZ(-0.4, 0.4, -d/2-0.01, -d/2, 0, h*0.75, MAD2, 'puerta')]
@gen('pergola')
def _(w, d, h, **k): return postes4(w, d, h-0.15, 0.12, MAD) + [BZ(-w/2, w/2, sy*(d/2-0.06)-0.04, sy*(d/2-0.06)+0.04, h-0.15, h-0.05, MAD2, 'viga') for sy in (-1, 1)] + \
                              [BZ(x-0.03, x+0.03, -d/2, d/2, h-0.05, h, MAD2, 'liston') for x in [-w/2+0.1 + i*(w-0.2)/7 for i in range(8)]]
@gen('chimenea_hogar')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.55, LAD, 'cuerpo'), BZ(-w*0.3, w*0.3, -d/2-0.01, -d/2+0.25, 0.1, h*0.4, NEG, 'boca'), BZ(-w/2-0.05, w/2+0.05, -d/2-0.05, d/2, h*0.55, h*0.6, PIE, 'repisa'), BZ(-w*0.3, w*0.3, -d/2+0.1, d/2, h*0.6, h, LAD, 'tiro')]
@gen('pozo_agua')
def _(w, d, h, **k):
    R = min(w, d)/2*0.75; return [TU([0, 0, 0], R, R-0.2, 0.8, 16, PIE, 'brocal'), C(0, 0, 0, 0.6, R-0.2, NEG, 'boca'), T([-R, 0, 0.8], [-R, 0, h-0.1], 0.06, MAD, 'poste'), T([R, 0, 0.8], [R, 0, h-0.1], 0.06, MAD, 'poste'),
                                  T([-R, 0, h-0.25], [R, 0, h-0.25], 0.05, MAD2, 'torno'), prisma(w, d, h-0.15, 0.15, LAD, 'tejadillo'), T([0, 0, h-0.3], [0, 0, 1.0], 0.006, CAF, 'cuerda'), K([0, 0, 0.8], [0, 0, 1.0], 0.1, 0.13, MAD2, 'balde')]
@gen('contenedor_maritimo')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, ROJ, 'caja')] + [BZ(-w/2 + i*w/16, -w/2 + i*w/16 + 0.04, -d/2-0.02, -d/2, 0.05, h-0.05, [0.62, 0.12, 0.1], 'acanalado') for i in range(1, 16)]
@gen('escenario_tarima')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, MAD2, 'tarima')] + [BZ(-w/2+0.02, w/2-0.02, -d/2-0.0, -d/2+0.02, 0.02, h-0.02, NEG, 'faldon')]
@gen('cupula')
def _(w, d, h, **k):
    out = []; n = 6; R = w/2
    for i in range(n):
        z0 = h*i/n; z1 = h*(i+1)/n; r0 = R*math.sqrt(max(0.0, 1-(z0/h)**2)); r1 = R*math.sqrt(max(0.0, 1-(z1/h)**2))
        out.append(K([0, 0, z0], [0, 0, z1], r0, max(r1, 0.01), CEM, 'anillo'))
    return out
@gen('tienda_campana')
def _(w, d, h, **k): return [prisma(w, d, 0, h, NAR, 'lona'), BZ(-0.25, 0.25, -d/2-0.005, -d/2, 0, h*0.6, OSC, 'entrada')]
@gen('torre_agua_elevada')
def _(w, d, h, **k): return G['tanque_agua'](w, d, h)

# ======================= industrial =======================
@gen('barril')
def _(w, d, h, **k): return [C(0, 0, 0, h, w/2*0.97, AZU, 'cuerpo')] + [TO([0, 0, z], w/2*0.97, w*0.015, None, MET, 'aro') for z in (h*0.1, h*0.5, h*0.9)]
@gen('caja_madera')
def _(w, d, h, **k):
    out = [BZ(-w/2+0.02, w/2-0.02, -d/2+0.02, d/2-0.02, 0.02, h-0.02, CAR, 'caja')]
    for sx, sy in ESQ: out.append(B(sx*(w/2-0.03), sy*(d/2-0.03), h/2, 0.06, 0.06, h, MAD, n='canto'))
    return out + [B(0, -d/2+0.02, h/2, math.hypot(w, h)-0.12, 0.04, 0.06, MAD, [0, -math.degrees(math.atan2(h, w)), 0], 'diagonal')]
@gen('pale')
def _(w, d, h, **k): return [BZ(-w/2 + i*(w/7), -w/2 + i*(w/7) + w/7*0.75, -d/2, d/2, h-0.02, h, MAD, 'tabla') for i in range(7)] + [BZ(-w/2, w/2, y-0.05, y+0.05, 0, h-0.02, MAD2, 'taco') for y in (-d/2+0.05, 0, d/2-0.05)]
@gen('estanteria_metalica')
def _(w, d, h, **k): return postes4(w, d, h, 0.04, AZU) + [BZ(-w/2, w/2, -d/2, d/2, z, z+0.05, NAR, 'balda') for z in (0.1, h*0.35, h*0.65, h-0.05)]
@gen('aire_acondicionado')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, BLA, 'cuerpo'), C(-w*0.12, -d/2-0.0, h/2, 0.02, h*0.38, GRI, 'rejilla', rot=[90, 0, 0])]
@gen('tuberia')
def _(w, d, h, **k): return [T([-w/2, 0, h/2], [w/2, 0, h/2], h/2, MET, 'tubo')] + [T([x-0.03, 0, h/2], [x+0.03, 0, h/2], h/2, GRI, 'brida') for x in (-w/2+0.03, 0, w/2-0.03)]
@gen('valvula')
def _(w, d, h, **k):
    Rv = min(w, d)/2 - 0.015
    return [T([-w/2, 0, d/2], [w/2, 0, d/2], d/2*0.8, MET, 'tubo'), S([0, 0, d/2], d/2, MET, 'cuerpo'), T([0, 0, d/2], [0, 0, h-0.015], 0.02, MET, 'vastago'), TO([0, 0, h-0.015], Rv, 0.015, None, ROJ, 'volante')]
@gen('generador')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, 0.1, NEG, 'patin'), BZ(-w/2+0.05, w/2-0.05, -d/2+0.05, d/2-0.05, 0.1, h, AMA, 'carcasa')] + [BZ(-w*0.3, -w*0.1, -d/2+0.03, -d/2+0.05, h*0.5, h*0.8, GRI, 'panel')]
@gen('carrete_cable')
def _(w, d, h, **k): return [PL([0, sy*(d/2-0.025), h/2], h/2, 0.05, [90, 0, 0], MAD, 'disco') for sy in (-1, 1)] + [C(0, 0, h/2, d-0.1, h*0.3, NEG, 'cable', rot=[90, 0, 0])]
@gen('bidon')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.85, BLA, 'cuerpo'), C(w*0.25, 0, h*0.85, h*0.15, 0.03, AZU, 'tapon'), T([-w*0.3, 0, h*0.85], [0, 0, h*0.95], 0.015, BLA, 'asa')]
@gen('extintor')
def _(w, d, h, **k): return [C(0, 0, 0, h*0.8, w*0.35, ROJ, 'cilindro'), S([0, 0, h*0.8], w*0.35, ROJ, 'hombro'), BZ(-0.02, 0.02, -0.02, 0.02, h*0.8, h, NEG, 'valvula'), T([0.02, 0, h*0.95], [w/2, -d/2+0.01, h*0.4], 0.01, NEG, 'manguera')]
@gen('tanque_gas')
def _(w, d, h, **k): return [C(0, 0, 0.1, h-0.1-w/2, w/2, BLA, 'cuerpo'), S([0, 0, h-w/2], w/2*0.999, BLA, 'cupula'), TU([0, 0, 0], w/2*0.8, w/2*0.7, 0.1, 10, BLA, 'aro_base')]
@gen('banda_transportadora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.15, h, NEG, 'banda')] + [T([x, -d/2+0.05, 0], [x, -d/2+0.05, h-0.15], 0.03, MET, 'pata') for x in (-w/2+0.1, w/2-0.1)] + [T([x, d/2-0.05, 0], [x, d/2-0.05, h-0.15], 0.03, MET, 'pata') for x in (-w/2+0.1, w/2-0.1)]
@gen('maquina_industrial')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.6, GRI, 'cuerpo'), BZ(-w*0.3, w/2, -d/2+0.1, d/2-0.1, h*0.6, h, GRI, 'cabezal'), C(-w*0.3, 0, h*0.6, h*0.25, d*0.25, MET, 'husillo'), BZ(-w/2+0.05, -w*0.2, -d/2-0.01, -d/2, h*0.3, h*0.55, AMA, 'panel')]
@gen('grua_torre')
def _(w, d, h, **k): return [BZ(-0.8, 0.8, -d/2, d/2, 0, 0.5, CEM, 'base'), BZ(-0.6, 0.6, -0.6, 0.6, 0.5, h-1.5, AMA, 'mastil'), BZ(-w*0.25, w/2, -0.4, 0.4, h-1.5, h-0.8, AMA, 'pluma'), BZ(-w/2, -w*0.25, -0.5, 0.5, h-1.5, h-0.8, AMA, 'contrapluma'),
                                BZ(-w/2, -w/2+1.5, -0.6, 0.6, h-2.5, h-1.5, CEM, 'contrapeso'), K([0, 0, h-0.8], [0, 0, h], 0.6, 0.05, AMA, 'punta'), T([w*0.35, 0, h-1.5], [w*0.35, 0, h*0.5], 0.01, NEG, 'cable')]

# ======================= cables =======================
@gen('cable_colgante')
def _(w, d, h, flecha=0.6, **k):
    n = 10; return poli_linea([[-w/2 + w*i/n, 0, h - flecha*(1 - (2*i/n - 1)**2)] for i in range(n+1)], max(d/2, 0.005), NEG, 'cable')
@gen('cable_suelo')
def _(w, d, h, semilla=11, **k):
    rnd = random.Random(semilla); n = 10; return poli_linea([[-w/2 + w*i/n, rnd.uniform(-d/2+h/2, d/2-h/2) if 0 < i < n else 0, h/2] for i in range(n+1)], h/2, NEG, 'cable')
@gen('haz_cables')
def _(w, d, h, **k): return [T([-w/2, y, h/2], [w/2, y*0.5, h/2], h/2*0.8, c, 'cable') for y, c in ((-d/2+h/2, NEG), (0, ROJ), (d/2-h/2, AZU))]
@gen('cable_entre_postes')
def _(w, d, h, **k): return [K([sx*(w/2-0.12), 0, 0], [sx*(w/2-0.12), 0, h], 0.12, 0.08, MAD2, 'poste') for sx in (-1, 1)] + G['cable_colgante'](w-0.24, 0.02, h-0.3, flecha=1.0) + [T([-w/2+0.12, d/2-0.01, h-0.3], [w/2-0.12, d/2-0.01, h-0.3], 0.008, NEG, 'cable')]
@gen('cable_vertical_colgando')
def _(w, d, h, **k): return poli_linea([[0, 0, h], [0.02, 0, h*0.6], [-0.03, 0.02, h*0.3], [w/2-0.02, 0, 0.02]], 0.01, NEG, 'cable') + [BZ(w/2-0.06, w/2, -0.02, 0.02, 0, 0.04, GRI, 'enchufe')]

# ======================= escombros y daño =======================
@gen('escombros')
def _(w, d, h, semilla=12, **k):
    rnd = random.Random(semilla); out = [PO(roca_vs(w*0.6, d*0.6, h, semilla), CEM, 'monton')]
    for i in range(10):
        s = rnd.uniform(0.08, 0.2); x = rnd.uniform(-w/2+s, w/2-s); y = rnd.uniform(-d/2+s, d/2-s)
        out.append(B(x, y, s*0.25, s, s*0.7, s*0.5, rnd.choice([CEM, LAD, GRI]), [rnd.uniform(-15, 15), rnd.uniform(-15, 15), rnd.uniform(0, 90)], 'trozo'))
    return out
@gen('losa_rota')
def _(w, d, h, trozos=4, semilla=13, **k):
    """una losa partida de verdad con formas_detalle.fragmentar (no cajas sueltas inventadas)."""
    fx = FD.transformador([0, 0], 0, 0); piezas = FD.parte_a_piezas(BZ(-w/2, w/2, -d/2, d/2, 0, h, CEM, 'losa'), fx)
    frag = FD.fragmentar(piezas, {'trozos': trozos, 'separacion_m': 0.06, 'angulo_max_grados': 8, 'caida': 'en_sitio', 'semilla': semilla})
    return [{'tipo': '_pieza_interna', 'pieza': p} for p in frag]
@gen('ladrillos_sueltos')
def _(w, d, h, semilla=14, **k):
    rnd = random.Random(semilla); return [B(rnd.uniform(-w/2+0.13, w/2-0.13), rnd.uniform(-d/2+0.13, d/2-0.13), 0.04 + 0.075*(i % 2 if i < 4 else 0), 0.24, 0.115, 0.07, LAD, [0, 0, rnd.uniform(0, 180)], 'ladrillo') for i in range(9)]
@gen('tablones')
def _(w, d, h, **k): return [B(0, -d/2+0.12, 0.015, w*0.9, 0.2, 0.03, MAD, [0, 0, 4], 'tablon'), B(0.1, 0.0, 0.045, w*0.85, 0.2, 0.03, MAD2, [0, 0, -6], 'tablon'), B(-0.05, d/2-0.12, 0.015, w*0.8, 0.2, 0.03, MAD, [0, 0, 2], 'tablon')]
@gen('vidrios_rotos')
def _(w, d, h, semilla=15, **k):
    rnd = random.Random(semilla); out = []
    for i in range(12):
        x, y = rnd.uniform(-w/2+0.06, w/2-0.06), rnd.uniform(-d/2+0.06, d/2-0.06); s = rnd.uniform(0.04, 0.1)
        out.append(PO([[x, y, 0], [x+s*0.9, y+s*0.2, 0], [x+s*0.3, y+s*0.8, 0], [x+s*0.4, y+s*0.3, h]], VID, 'vidrio'))
    return out
@gen('viga_caida')
def _(w, d, h, **k):
    ang = math.degrees(math.atan2(h-0.15, w-0.2)); return [B(0, 0, h/2, math.hypot(w-0.2, h-0.15), d, 0.15, MAD2, [0, -ang, 0], 'viga')]
@gen('varillas')
def _(w, d, h, **k): return [T([-w/2, -d/2 + i*d/5, 0.02], [w/2 - 0.1*i, -d/2 + i*d/5 + 0.05, 0.02 + h*0.2*(i % 3)], 0.01, [0.45, 0.25, 0.15], 'varilla') for i in range(6)]
@gen('crater')
def _(w, d, h, **k): return [TU([0, 0, 0], w/2, w/2*0.6, h, 16, CAF, 'borde'), C(0, 0, 0, 0.01, w/2*0.6, NEG, 'fondo')]
@gen('grieta_suelo')
def _(w, d, h, semilla=16, **k):
    rnd = random.Random(semilla); n = 8; pts = [[-w/2 + w*i/n, rnd.uniform(-d/2+0.04, d/2-0.04) if 0 < i < n else 0, h/2] for i in range(n+1)]
    return [B((a[0]+b[0])/2, (a[1]+b[1])/2, h/2, math.hypot(b[0]-a[0], b[1]-a[1]), 0.04, h, NEG, [0, 0, math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))], 'grieta') for a, b in zip(pts, pts[1:])]
@gen('mueble_volcado')
def _(w, d, h, **k): return [B(0, 0, h/2, w, d, h, MAD, [0, 0, 0], 'cuerpo'), BZ(-w/2, w/2, -d/2-0.0, -d/2+0.02, h*0.1, h*0.9, MAD2, 'frente')]
@gen('pared_agujero')
def _(w, d, h, hueco_ancho=1.0, hueco_alto=1.2, hueco_z=0.6, **k):
    """muro con hueco hecho con formas_detalle.abrir_hueco + restos_de_hueco (lo mismo que usará el motor)."""
    trozos, info = FD.abrir_hueco({'x_m': [-w/2, w/2], 'y_m': [-d/2, d/2], 'z_m': [0, h]}, {'ancho_m': hueco_ancho, 'alto_m': hueco_alto, 'z0_m': hueco_z})
    out = [BZ(t['x_m'][0], t['x_m'][1], t['y_m'][0], t['y_m'][1], t['z_m'][0], t['z_m'][1], CEM, 'muro') for t in trozos]
    return out + [{'tipo': '_pieza_interna', 'pieza': q} for q in FD.restos_de_hueco(info, {'restos': 0, 'borde_irregular': True, 'semilla': 3}, -1, CEM)]

# ======================= objetos de mano =======================
@gen('mochila')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.05, d/2, 0, h*0.9, AZU, 'cuerpo'), BZ(-w*0.35, w*0.35, -d/2, -d/2+0.05, h*0.1, h*0.5, [0.15, 0.28, 0.55], 'bolsillo'), TO([0, d*0.1, h*0.9], w*0.15, 0.015, [0, 90, 0], NEG, 'asa')]
@gen('bolso')
def _(w, d, h, **k): return [tronco_pir(w, d, w*0.85, d*0.8, 0, h*0.6, CAF, 'cuerpo'), TO([0, 0, h*0.6], w*0.3, 0.012, [90, 0, 0], CAF, 'asa')]
@gen('maleta')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0.04, h*0.8, NEG, 'cuerpo'), T([-w*0.2, 0, h*0.8], [-w*0.2, 0, h], 0.01, MET, 'barra'), T([w*0.2, 0, h*0.8], [w*0.2, 0, h], 0.01, MET, 'barra'), T([-w*0.2, 0, h-0.01], [w*0.2, 0, h-0.01], 0.012, NEG, 'mango')] + [S([sx*(w/2-0.04), d/2-0.04, 0.04], 0.04, NEG, 'rueda') for sx in (-1, 1)]
@gen('paraguas')
def _(w, d, h, abierto=True, **k): return [T([0, 0, 0.05], [0, 0, h], 0.008, NEG, 'baston'), TO([0.03, 0, 0.05], 0.03, 0.008, [90, 0, 0], NEG, 'mango')] + ([K([0, 0, h*0.75], [0, 0, h], w/2, 0.01, NEG, 'tela')] if abierto else [K([0, 0, h*0.3], [0, 0, h], 0.03, 0.005, NEG, 'tela')])
@gen('espada')
def _(w, d, h, **k): return [PO([[-0.02, -0.003, 0.22], [0.02, -0.003, 0.22], [-0.02, 0.003, 0.22], [0.02, 0.003, 0.22], [0, 0, h]], MET, 'hoja'), BZ(-w/2, w/2, -d/2, d/2, 0.18, 0.22, AMA, 'guarda'), T([0, 0, 0.02], [0, 0, 0.18], 0.015, CAF, 'empunadura'), S([0, 0, 0.02], 0.02, AMA, 'pomo')]
@gen('escudo')
def _(w, d, h, **k): return [B(0, 0, h/2, w, d*0.6, h, AZU, n='cuerpo'), PL([0, -d/2+0.005, h/2], min(w, h)*0.2, 0.01, [90, 0, 0], AMA, 'umbo')]
@gen('cuchillo')
def _(w, d, h, **k): return [BZ(-w/2, -w/2+0.1, -d/2, d/2, 0, h, NEG, 'mango'), PO([[-w/2+0.1, -d/2, 0], [-w/2+0.1, d/2, 0], [-w/2+0.1, -d/2, h*0.4], [-w/2+0.1, d/2, h*0.4], [w/2, 0, 0], [w/2, 0, h*0.2]], MET, 'hoja')]
@gen('pistola')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h*0.65, h, NEG, 'corredera'), B(-w/2+0.035, 0, h*0.35, 0.05, d, h*0.7, NEG, [0, -15, 0], 'empunadura'), TO([-w*0.05, 0, h*0.55], 0.02, 0.004, [90, 0, 0], NEG, 'guardamonte')]
@gen('libro')
def _(w, d, h, abierto=False, **k):
    if abierto: return [B(sx*w/4, 0, h/2, w/2, d, h, BLA, [0, sx*5, 0], 'pagina') for sx in (-1, 1)]
    return [BZ(-w/2, w/2, -d/2, d/2, 0, h, ROJ, 'tapa'), BZ(-w/2+0.005, w/2, -d/2+0.003, d/2-0.003, 0.003, h-0.003, BLA, 'hojas')]
@gen('cuaderno')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, AZU, 'tapa')] + [TO([-w/2, -d/2 + d*(i+0.5)/8, h/2], h, 0.001, [90, 0, 0], MET, 'espiral') for i in range(8)]
@gen('linterna')
def _(w, d, h, **k): return [C(0, 0, 0, h*0.7, w*0.35, NEG, 'mango'), K([0, 0, h*0.7], [0, 0, h], w*0.35, w/2, NEG, 'cabeza'), PL([0, 0, h], w/2*0.9, 0.002, None, LUZ, 'lente')]
@gen('llave_inglesa')
def _(w, d, h, **k): return [BZ(-w/2+0.03, w/2-0.05, -d/2*0.4, d/2*0.4, 0, h, MET, 'mango'), BZ(w/2-0.06, w/2, -d/2, -d*0.1, 0, h, MET, 'boca'), BZ(w/2-0.06, w/2, d*0.1, d/2, 0, h, MET, 'boca'), C(-w/2+0.03, 0, 0, h, d*0.3, MET, 'ojo')]
@gen('martillo')
def _(w, d, h, **k): return [T([0, 0, 0], [0, 0, h-0.03], 0.015, MAD, 'mango'), BZ(-w/2, w/2, -d/2, d/2, h-0.035, h, MET, 'cabeza')]
@gen('caja_herramientas')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.75, ROJ, 'cuerpo'), BZ(-w/2, w/2, -d/2, d/2, h*0.75, h*0.82, [0.6, 0.12, 0.1], 'tapa'), T([-w*0.3, 0, h*0.82], [-w*0.3, 0, h], 0.01, NEG, 'asa'), T([w*0.3, 0, h*0.82], [w*0.3, 0, h], 0.01, NEG, 'asa'), T([-w*0.3, 0, h-0.01], [w*0.3, 0, h-0.01], 0.012, NEG, 'asa')]
@gen('comida_plato')
def _(w, d, h, **k): return [K([0, 0, 0], [0, 0, 0.02], w*0.3, w/2, BLA, 'plato'), S([-w*0.12, 0, 0.04], 0.04, CAF, 'comida'), BZ(0, w*0.25, -0.05, 0.05, 0.02, h, VER, 'ensalada')]
@gen('foto_marco')
def _(w, d, h, **k): return [B(0, 0, h/2, w, 0.015, h, MAD2, [-12, 0, 0], 'marco'), B(0, -0.009, h/2, w*0.8, 0.002, h*0.8, AZU, [-12, 0, 0], 'foto'), T([0, 0.01, h*0.5], [0, d/2-0.005, 0.005], 0.005, MAD2, 'apoyo')]
@gen('llave')
def _(w, d, h, **k): return [TO([-w/2+d/2, 0, h/2], d/2-h/2, h/2, None, MET, 'cabeza'), BZ(-w/2+d, w/2, -0.004, 0.004, 0, h, MET, 'pala')]
@gen('tarjeta')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h, BLA, 'tarjeta'), BZ(-w/2+0.005, -w/2+0.02, -0.006, 0.006, h, h+0.0005, AMA, 'chip')]
@gen('memoria_usb')
def _(w, d, h, **k): return [BZ(-w/2, w/2-0.012, -d/2, d/2, 0, h, NEG, 'cuerpo'), BZ(w/2-0.012, w/2, -d/2*0.7, d/2*0.7, h*0.2, h*0.8, MET, 'conector')]
@gen('jeringa')
def _(w, d, h, **k): return [T([-w/2+0.02, 0, d/2], [w/2-0.02, 0, d/2], d/2*0.9, VID, 'cuerpo'), T([w/2-0.02, 0, d/2], [w/2, 0, d/2], 0.002, MET, 'aguja'), BZ(-w/2, -w/2+0.005, -d/2, d/2, 0, d, BLA, 'embolo')]

# ======================= comercio, escuela y ocio =======================
@gen('mostrador')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2-0.05, 0, h-0.04, MAD, 'cuerpo'), BZ(-w/2, w/2, -d/2, d/2, h-0.04, h, MAD2, 'tapa'), BZ(-w/2+0.03, w/2-0.03, -d/2-0.0, -d/2+0.01, 0.1, h-0.1, MAD2, 'panel')]
@gen('estante_tienda')
def _(w, d, h, **k): return G['estanteria'](w, d, h, baldas=5, col=BLA, libros=False) + [BZ(x, x+0.12, -d/2+0.03, -d/2+0.2, z+0.02, z+0.2, c, 'producto') for z in (0.0, (h-0.02)/4, (h-0.02)/2) for x, c in ((-w/2+0.1, ROJ), (-0.06, AMA), (w/2-0.22, AZU))]
@gen('caja_registradora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.35, GRI, 'cajon'), tronco_pir(w, d*0.8, w, d*0.3, h*0.35, h*0.25, GRI, 'teclado', dy=d*0.1), BZ(-w*0.3, w*0.3, d*0.2, d*0.3, h*0.6, h, OSC, 'pantalla')]
@gen('pupitre')
def _(w, d, h, **k): return [B(0, 0, h-0.02, w, d, 0.03, MAD, [-6, 0, 0], 'tablero'), BZ(-w/2+0.03, w/2-0.03, -d/2+0.05, d/2-0.05, h-0.2, h-0.18, MET, 'bandeja')] + patas4(w, d, h-0.06, 0.015, 0.04, MET)
@gen('vitrina')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0, h*0.5, MAD, 'base'), BZ(-w/2, w/2, -d/2, d/2, h*0.5, h, VID, 'vidrio'), BZ(-w/2+0.03, w/2-0.03, -d/2+0.03, d/2-0.03, h*0.75, h*0.76, VID, 'balda')]
@gen('nevera_bebidas')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.04, d/2, 0, h, ROJ, 'cuerpo'), BZ(-w/2+0.05, w/2-0.05, -d/2, -d/2+0.04, 0.15, h-0.25, VID, 'puerta'), BZ(-w/2, w/2, -d/2, -d/2+0.04, h-0.22, h-0.02, BLA, 'cartel')]
@gen('pizarra_tiza')
def _(w, d, h, **k): return G['pizarra'](w, d, h, col=VER2)
@gen('atril')
def _(w, d, h, **k): return [C(0, 0, 0, 0.03, w*0.35, MAD2, 'base'), T([0, 0, 0.03], [0, 0, h-0.1], 0.03, MAD2, 'poste'), B(0, 0, h-0.06, w, d*0.8, 0.03, MAD, [-25, 0, 0], 'atril')]
@gen('mesa_billar')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.12, h, MAD2, 'banda'), BZ(-w/2+0.08, w/2-0.08, -d/2+0.08, d/2-0.08, h-0.1, h-0.04, VER2, 'pano')] + patas4c(w, d, h-0.12, 0.12, 0.1, MAD2)
@gen('maquina_expendedora')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2+0.03, d/2, 0, h, AZU, 'cuerpo'), BZ(-w/2+0.05, w*0.15, -d/2, -d/2+0.03, 0.5, h-0.1, VID, 'vidrio'), BZ(w*0.2, w/2-0.05, -d/2, -d/2+0.03, h*0.55, h*0.75, NEG, 'panel'), BZ(-w/2+0.05, w*0.15, -d/2, -d/2+0.03, 0.15, 0.35, NEG, 'boca')]
@gen('columpio')
def _(w, d, h, **k):
    out = [T([sx*(w/2-0.05), sy*(d/2-0.05), 0], [sx*(w/2-0.05), 0, h-0.05], 0.04, ROJ, 'pata') for sx in (-1, 1) for sy in (-1, 1)] + [T([-w/2+0.05, 0, h-0.05], [w/2-0.05, 0, h-0.05], 0.05, ROJ, 'travesano')]
    return out + [T([x, 0, h-0.1], [x, 0, 0.45], 0.005, MET, 'cadena') for x in (-0.25, 0.25)] + [BZ(-0.27, 0.27, -0.1, 0.1, 0.42, 0.45, NEG, 'asiento')]
@gen('tobogan')
def _(w, d, h, **k): return [B(0, d*0.05, h*0.5, w*0.8, math.hypot(d*0.8, h)*0.98, 0.04, AMA, [-math.degrees(math.atan2(h*0.95, d*0.8)), 0, 0], 'rampa')] + [T([sx*w*0.4, d/2-0.05, 0], [sx*w*0.4, d/2-0.05, h], 0.03, AZU, 'poste') for sx in (-1, 1)]
@gen('cama_hospital')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, 0.5, 0.65, BLA, 'colchon'), BZ(-w/2, w/2, -d/2, d/2, 0.35, 0.5, MET, 'base'), BZ(-w/2, w/2, d/2-0.04, d/2, 0.35, h, MET, 'cabecero'), BZ(-w/2-0.0, -w/2+0.03, -d*0.3, d*0.3, 0.65, 0.85, MET, 'baranda')] + [T([sx*(w/2-0.05), sy*(d/2-0.05), 0.08], [sx*(w/2-0.05), sy*(d/2-0.05), 0.35], 0.02, MET, 'pata') for sx, sy in ESQ] + [S([sx*(w/2-0.05), sy*(d/2-0.05), 0.04], 0.04, NEG, 'rueda') for sx, sy in ESQ]
@gen('camilla')
def _(w, d, h, **k): return [BZ(-w/2, w/2, -d/2, d/2, h-0.08, h, BLA, 'colchon')] + patas4(w, d, h-0.08, 0.02, 0.05, MET)
@gen('soporte_suero')
def _(w, d, h, **k): return [T([0, 0, 0.05], [0, 0, h], 0.012, MET, 'poste'), T([-w/2+0.02, 0, h-0.05], [w/2-0.02, 0, h-0.05], 0.008, MET, 'gancho'), B(w/2-0.06, 0, h-0.2, 0.08, 0.03, 0.15, VID, n='bolsa')] + [T([0, 0, 0.05], [w/2*math.cos(a), d/2*math.sin(a), 0.02], 0.012, MET, 'pata') for a in (0, 1.257, 2.513, 3.77, 5.027)]

# ======================= efectos y formas genéricas (neutras; el canal dice qué son) =======================
@gen('anillo_vertical')
def _(w, d, h, **k): return [TO([0, 0, h/2], w/2 - d/2, d/2, [90, 0, 0], VIO, 'anillo')]
@gen('anillo_horizontal')
def _(w, d, h, **k): return [TO([0, 0, h/2], w/2 - h/2, h/2, None, VIO, 'anillo')]
@gen('esfera_envolvente')
def _(w, d, h, **k): return [S([0, 0, h/2], h/2, VIO, 'esfera')]
@gen('domo')
def _(w, d, h, **k): return G['cupula'](w, d, h)
@gen('columna_luz')
def _(w, d, h, **k): return [C(0, 0, 0, h, w/2, LUZ, 'haz'), PL([0, 0, 0.01], w/2*1.3, 0.02, None, AMA, 'aro_suelo')]
@gen('cristal_prisma')
def _(w, d, h, **k):
    n = 6; return [PO([[w/2*math.cos(2*math.pi*i/n), d/2*math.sin(2*math.pi*i/n), 0] for i in range(n)] + [[w/2*math.cos(2*math.pi*i/n), d/2*math.sin(2*math.pi*i/n), h*0.75] for i in range(n)] + [[0, 0, h]], VIO, 'cristal')]
@gen('racimo_cristales')
def _(w, d, h, semilla=17, **k):
    rnd = random.Random(semilla); out = [PO(roca_vs(w*0.6, d*0.6, h*0.2, semilla), PIE, 'base')]
    for i in range(6):
        a = 2*math.pi*i/6; x, y = w*0.25*math.cos(a), d*0.25*math.sin(a); hh = h*rnd.uniform(0.5, 1.0); r = min(w, d)*0.08
        out.append(PO([[x + r*math.cos(b), y + r*math.sin(b), 0.05] for b in [j*math.pi/3 for j in range(6)]] + [[x*1.6, y*1.6, hh]], VIO if i % 2 else VIO2, 'cristal'))
    return out
@gen('portal_rectangular')
def _(w, d, h, **k): return [BZ(-w/2, -w/2+0.15, -d/2, d/2, 0, h, OSC, 'marco'), BZ(w/2-0.15, w/2, -d/2, d/2, 0, h, OSC, 'marco'), BZ(-w/2, w/2, -d/2, d/2, h-0.15, h, OSC, 'marco'), BZ(-w/2+0.15, w/2-0.15, -0.01, 0.01, 0, h-0.15, VIO, 'superficie')]
@gen('portal_circular')
def _(w, d, h, **k): return [TO([0, 0, h/2], w/2-0.1, 0.1, [90, 0, 0], OSC, 'aro'), PL([0, 0, h/2], w/2-0.15, 0.02, [90, 0, 0], VIO, 'superficie')]
@gen('nube_particulas')
def _(w, d, h, semilla=18, **k):
    rnd = random.Random(semilla); r = min(w, d, h)*0.06
    return [S([rnd.uniform(-w/2+r, w/2-r), rnd.uniform(-d/2+r, d/2-r), rnd.uniform(r, h-r)], r*rnd.uniform(0.5, 1), LUZ, 'particula') for _ in range(20)]
@gen('charco')
def _(w, d, h, **k): return [PO([[w/2*math.cos(a)*(0.85 + 0.15*math.sin(3*a)), d/2*math.sin(a)*(0.85 + 0.15*math.cos(2*a)), z] for a in [i*math.pi/8 for i in range(16)] for z in (0, h)], AGU, 'agua')]
@gen('llamas')
def _(w, d, h, **k): return [K([x, y, 0], [x, y, h*s], w*0.18, 0.0, c, 'llama') for x, y, s, c in ((0, 0, 1.0, NAR), (-w*0.28, d*0.1, 0.7, AMA), (w*0.28, -d*0.1, 0.75, ROJ), (0.05, d*0.28, 0.6, AMA), (-0.05, -d*0.28, 0.6, NAR))]
@gen('humo_columna')
def _(w, d, h, **k):
    R = min(w, d)/2; rs = [R*(0.5 + 0.125*i) for i in range(5)]; z0, z1 = rs[0], h - rs[4]
    return [S([(w/2 - r)*0.5*(1 if i % 2 else -1), (d/2 - r)*0.5*(-1 if i % 2 else 1), z0 + (z1 - z0)*i/4], r, GRI, 'bocanada') for i, r in enumerate(rs)]
@gen('holograma')
def _(w, d, h, **k): return [C(0, 0, 0, 0.05, w/2, OSC, 'emisor'), K([0, 0, 0.05], [0, 0, h], w/2*0.8, w/2, [0.4, 0.8, 1.0], 'haz')]
@gen('escudo_energia')
def _(w, d, h, **k): return [PO([[w/2*math.cos(a), d/2*math.sin(a) - d/2 + d*0.5, z] for a in [math.pi*i/8 for i in range(9)] for z in (0, h)], [0.4, 0.8, 1.0], 'barrera')]
@gen('objeto_flotante_generico')
def _(w, d, h, **k): return [S([0, 0, h/2], min(w, d, h)/2, VIO, 'cuerpo'), TO([0, 0, h/2], min(w, d)/2*0.95, 0.01, [20, 0, 0], LUZ, 'halo')]
