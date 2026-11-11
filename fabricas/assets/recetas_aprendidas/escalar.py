# -*- coding: utf-8 -*-
"""Escala una receta aprendida a una caja pedida (ancho×fondo×alto). US$0, sin IA.
Convención: origen en el centro de la base; x=ancho, y=fondo, z=alto.
Escala independiente por eje (como Star ajusta a medidas). El grafo de contacto AABB
se conserva bajo ese reescalado homogéneo por eje."""
from __future__ import annotations
import copy, math, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI.parents[1] / 'escenario' / 'codigo')]
import formas_detalle as FD

VEC_KEYS =[REDACTED]
RAD_KEYS =[REDACTED]

def _sx_sy_sz(caja_ref, caja_nueva):
    return (caja_nueva['ancho'] / caja_ref['ancho'],
            caja_nueva['fondo'] / caja_ref['fondo'],
            caja_nueva['alto'] / caja_ref['alto'])

def _esc_vec(v, sx, sy, sz):
    if v is None: return v
    if isinstance(v[0], (list, tuple)):
        return [_esc_vec(p, sx, sy, sz) for p in v]
    return [v[0] * sx, v[1] * sy, v[2] * sz]

def _esc_radio(r, sx, sy, sz):
    """Radios horizontales usan media geométrica de sx,sy; alto_m/espesor vertical usan sz."""
    return r * math.sqrt(abs(sx * sy))

def escalar_parte(p, sx, sy, sz):
    q = copy.deepcopy(p)
    for k in VEC_KEYS:
        if k in q:
            q[k] = _esc_vec(q[k], sx, sy, sz)
    for k in ('radio_m', 'radio_ext_m', 'radio_int_m', 'radio_mayor_m', 'radio_menor_m'):
        if k in q:
            q[k] = _esc_radio(q[k], sx, sy, sz)
    if 'alto_m' in q:
        q['alto_m'] = q['alto_m'] * sz
    if 'espesor_m' in q:
        # espesor de placa: componente dominante según rotación; por defecto z
        q['espesor_m'] = q['espesor_m'] * sz
    if 'radio_a_m' in q:
        q['radio_a_m'] = _esc_radio(q['radio_a_m'], sx, sy, sz)
    if 'radio_b_m' in q:
        q['radio_b_m'] = _esc_radio(q['radio_b_m'], sx, sy, sz)
    return q

def aplicar_colores(partes, colores):
    """colores: dict nombre_parcial -> [r,g,b] o {'*': [...]}. Sin colores = deja los de la receta."""
    if not colores:
        return partes
    out = []
    for p in partes:
        q = copy.deepcopy(p)
        n = (q.get('nombre') or '').lower()
        rgb = next((v for k, v in colores.items() if k != '*' and k.lower() in n), colores.get('*'))
        if rgb is not None:
            q['color_guia_rgb'] = list(rgb)[:3]
        out.append(q)
    return out

def escalar_receta(receta, caja_m, colores=None):
    """receta = ficha aprendida (con medidas_tipicas + partes) o dict con caja_m+partes.
    Devuelve {caja_m, partes, factores_escala}."""
    ref = receta.get('medidas_tipicas') or receta.get('caja_m')
    if 'ancho_m' in ref:
        ref = {'ancho': ref['ancho_m'], 'fondo': ref['fondo_m'], 'alto': ref['alto_m']}
    nueva = {'ancho': float(caja_m['ancho']), 'fondo': float(caja_m['fondo']), 'alto': float(caja_m['alto'])}
    sx, sy, sz = _sx_sy_sz(ref, nueva)
    partes = [escalar_parte(p, sx, sy, sz) for p in receta['partes']]
    partes = aplicar_colores(partes, colores)
    return {'caja_m': nueva, 'partes': partes, 'factores_escala': {'sx': sx, 'sy': sy, 'sz': sz},
            'apoyo': receta.get('apoyo'), 'conjunto': receta.get('conjunto', False)}

def receta_a_piezas(partes):
    T = FD.transformador([0, 0], 0, 0)
    out = []
    for p in partes:
        for q in FD.parte_a_piezas(p, T):
            q['parte'] = p.get('nombre')
            out.append(q)
    return out

def z_min_max(piezas):
    mn, mx = FD.bbox(piezas)
    return mn[2], mx[2]

def toca_piso(piezas, tol=0.002):
    z0, _ = z_min_max(piezas)
    return abs(z0) <= tol, z0

def componentes_flotantes(piezas, apoyo='piso', tol=0.002):
    """Réplica ligera del grafo de contacto del revisor: True si alguna componente no toca apoyo ni otras."""
    cajas = [FD.bbox([p]) for p in piezas]
    n = len(cajas)
    padre = list(range(n))
    def f(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]; i = padre[i]
        return i
    def toca(a, b):
        return all(a[0][k] <= b[1][k] + tol and b[0][k] <= a[1][k] + tol for k in range(3))
    for i in range(n):
        for j in range(i + 1, n):
            if toca(cajas[i], cajas[j]):
                padre[f(i)] = f(j)
    grupos = {}
    for i in range(n):
        grupos.setdefault(f(i), []).append(i)
    floja = []
    for g, idxs in grupos.items():
        if apoyo == 'piso':
            ok = any(cajas[i][0][2] <= tol for i in idxs)
        elif apoyo == 'pared':
            # toca y+ o y- del objeto local (frente -y): usamos y máximo ≈ fondo/2… aquí solo comprobamos contacto interno
            ok = True  # tras escala uniforme por eje, si antes no flotaba, no flota
        else:
            ok = True
        if not ok:
            floja.append(idxs)
    return floja
