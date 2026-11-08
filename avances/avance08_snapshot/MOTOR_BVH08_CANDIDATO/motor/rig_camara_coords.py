"""Rig de cámara por COORDENADAS (fase 4g, Ricardo t281u/t284u). Puerto a Python/Blender del rig del «Estudio de cámara de mano»
(r2.txt: updateRig, órbita/acimut, filtro One Euro, applyShake, mirada), cambiando la entrada del teléfono por valores calculados.
Genérico: no sabe de canales, escenas ni personajes. Eje vertical = Z (Blender); en r2 era Y.
Entrada por toma: lista de tramos {f0,f1,modo,ini,fin,curva,rig}, función objetivo(f) -> Vector, límites del set real.
  ini/fin = {az (rad, alrededor del objetivo), dist (m horizontal), altura (m sobre el punto mirado), lente (mm), roll (rad),
             yaw (rad, giro extra de mirada = paneo), pitch (rad, = tilt), lateral (m, truck), mira_fija (bool)}
  modo: 'fijo' (cámara y mirada quietas: trípode), 'seguir' (pos = objetivo + acimut·dist + altura: dolly/órbita/grúa/travelling),
        'paneo' (pos quieta, gira la mirada).
Salida: por cuadro {f, loc, quat, lente, roll} ya suavizados. No se escriben keyframes a mano: el .blend recibe esta trayectoria."""
import math
from mathutils import Vector, Quaternion, Matrix

def _lerp(a, b, u): return a + (b - a) * u
def _wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi
CURVAS = {
    'lineal': lambda u: u,
    'suave_entrada': lambda u: u * u,
    'suave_salida': lambda u: 1 - (1 - u) * (1 - u),
    'suave_entrada_salida': lambda u: u * u * (3 - 2 * u),
}
def one_euro_alpha(dt, cutoff):   # r2: oneEuroAlpha
    return 1 / (1 + 1 / (2 * math.pi * cutoff * dt))
class OneEuro:
    """r2 filterQ/filterP: suavizado fuerte cuando casi no se mueve, ligero en movimientos rápidos."""
    def __init__(s, suavidad): s.s = suavidad; s.q = s.qp = s.p = s.pp = None; s.qv = s.pv = 0.0
    def Q(s, q, dt):
        if s.q is None: s.q = q.copy(); s.qp = q.copy(); return s.q.copy()
        v = s.qp.rotation_difference(q).angle / dt; s.qp = q.copy()
        s.qv += (v - s.qv) * one_euro_alpha(dt, 1.2)
        mc = _lerp(8, 0.35, s.s); s.q = s.q.slerp(q, one_euro_alpha(dt, mc + 1.6 * s.qv)); return s.q.copy()
    def P(s, p, dt):
        if s.p is None: s.p = p.copy(); s.pp = p.copy(); return s.p.copy()
        v = (p - s.pp).length / dt; s.pp = p.copy()
        s.pv += (v - s.pv) * one_euro_alpha(dt, 1.2)
        mc = _lerp(8, 0.35, s.s); s.p = s.p.lerp(p, one_euro_alpha(dt, mc + 3 * s.pv)); return s.p.copy()
def sacudida(t, amt):   # r2 applyShake (determinista, depende solo del tiempo)
    n = lambda f1, f2, f3, o: math.sin(t * f1 + o) + 0.55 * math.sin(t * f2 + o * 2.1) + 0.28 * math.sin(t * f3 + o * 3.7)
    rot = Vector((n(1.1, 2.7, 6.3, 0.4) * 0.0045 * amt, n(0.9, 2.3, 5.9, 1.9) * 0.0055 * amt, n(0.7, 1.9, 4.7, 3.1) * 0.004 * amt))
    pos = Vector((n(0.8, 2.1, 5.1, 2.5), n(1.3, 2.9, 6.7, 0.7), n(0.6, 1.7, 4.3, 4.2))) * (0.006 * amt)
    return rot, pos
def mirar(loc, punto, roll=0.0):
    q = (punto - loc).to_track_quat('-Z', 'Y')
    if roll: q = q @ Quaternion((0, 0, 1), roll)
    return q
def mirada_relativa(frente, desde, hacia):
    """r2 «Mirada»: vector desde→hacia en el sistema del sujeto (frente horizontal): guiñada = atan2(lateral, frontal), cabeceo = −atan2(dz, horizontal)."""
    d = hacia - desde; fh = Vector((frente.x, frente.y, 0)).normalized(); der = fh.cross(Vector((0, 0, 1)))
    lx, lz = d.dot(der), d.dot(fh)
    return math.atan2(lx, lz), -math.atan2(-d.z, math.hypot(lx, lz))
def trayectoria(tramos, fps, objetivo, limites, suavidad=0.35, sacudir=0.0, t_base=0.0):
    """Recorre la toma cuadro a cuadro. limites = {'minZ','maxZ', 'max_dist': fn(origen, dir)->m|None}. Devuelve lista y avisos de límite."""
    dt = 1.0 / fps; filt = OneEuro(suavidad); out = []; avisos = []; pos = None
    k = 1 - math.exp(-dt * _lerp(30, 2.5, suavidad))
    for tr in tramos:
        a, b = tr['ini'], tr['fin']; cur = CURVAS.get(tr.get('curva') or 'lineal', CURVAS['lineal']); f0, f1 = tr['f0'], tr['f1']
        ancla0 = objetivo(f0)
        for f in range(f0, f1 + 1):
            u = cur(0.0 if f1 == f0 else (f - f0) / (f1 - f0)); g = {x: _lerp(a[x], b[x], u) for x in ('dist', 'altura', 'lente', 'roll', 'yaw', 'pitch', 'lateral')}
            g['az'] = a['az'] + _wrap(b['az'] - a['az']) * u if abs(b['az'] - a['az']) <= math.pi else _lerp(a['az'], b['az'], u)   # órbitas > 180° se recorren enteras
            mz = Vector((0, 0, 0)); g['mira'] = a.get('mira', mz).lerp(b.get('mira', mz), u)   # reencuadre del punto mirado (zoom/dolly)
            modo = tr['modo']; obj = objetivo(f) if modo == 'seguir' else ancla0
            centro = obj + (g['mira'] if modo == 'seguir' else a.get('mira', mz))   # la cámara orbita el punto mirado; en fijo/paneo no se mueve por el reencuadre
            base = centro + Vector((math.cos(g['az']) * g['dist'], math.sin(g['az']) * g['dist'], g['altura']))
            if modo in ('fijo', 'paneo') and tr.get('pos_fija') is not None: base = tr['pos_fija'].copy()
            # truck: desplazamiento lateral respecto de la mirada
            if g['lateral']:
                fwd = (obj - base); fwd.z = 0
                if fwd.length > 1e-9: base += fwd.normalized().cross(Vector((0, 0, 1))) * g['lateral']
            # límites del set real (r2: clamp minY/maxY y maxDistance)
            if limites.get('minZ') is not None and base.z < limites['minZ']: avisos.append((f, 'altura limitada por el piso', round(base.z, 3))); base.z = limites['minZ']
            if limites.get('maxZ') is not None and base.z > limites['maxZ']: avisos.append((f, 'altura limitada por el techo', round(base.z, 3))); base.z = limites['maxZ']
            if limites.get('max_dist'):
                d = base - centro; md = limites['max_dist'](centro, d.normalized()) if d.length > 1e-9 else None
                if md is not None and d.length > md: avisos.append((f, 'distancia limitada por pared/objeto', round(md, 3))); base = centro + d.normalized() * md
            pos = base.copy() if pos is None or tr.get('corte_ini') and f == f0 else pos.lerp(base, 1.0 if modo == 'seguir' else k)
            q = mirar(pos, obj + g['mira'], g['roll'])
            if g['yaw'] or g['pitch']: q = Quaternion((0, 0, 1), g['yaw']) @ q @ Quaternion((1, 0, 0), g['pitch'])
            qf = filt.Q(q, dt); pf = filt.P(pos, dt)
            if sacudir:
                rr, pp = sacudida(t_base + f * dt, sacudir); qf = qf @ Quaternion(Vector((1, 0, 0)), rr.x) @ Quaternion(Vector((0, 1, 0)), rr.y) @ Quaternion(Vector((0, 0, 1)), rr.z)
                pf = pf + qf @ pp
            out.append({'f': f, 'loc': pf, 'quat': qf, 'lente': g['lente'], 'roll': g['roll'], 'mira': obj + g['mira'], 'modo': modo})
    return out, avisos
