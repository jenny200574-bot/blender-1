# -*- coding: utf-8 -*-
"""ancla_tubos.py — conversión DETERMINISTA del ancla de los tubos en recetas de Argon (US$0, sin red).

En la biblioteca de Star, tubo.centro_m es el CENTRO DE LA BASE (ancla 'base'); cilindro.centro_m es el centro del volumen.
El prompt no lo decía explícito y Argon a veces usó tubo.centro_m como centro del volumen. Aquí NO se adivina:
solo se convierte cuando la receta DECLARA literalmente una altura (dato de la propia receta) que coincide con la
lectura 'centro' y NO con la lectura 'base'. Entonces se pone "ancla": "centro" en una COPIA de la parte (la posición
z queda tal cual la escribió Argon; formas_detalle la lleva a la base). El original no se toca.
"""
import copy, re

TOL = 0.002   # m
# objeto_id -> clave del dato que declara la altura del borde superior del cuerpo tubular (y cómo leer el número).
DECLARA = {
    'amb-esc-habitacion-cesta-tela': ('receta.altura_cuerpo_y_asas_m', lambda v: v[0] if isinstance(v, list) else v),
    'amb-esc-habitacion-bote-crayones': ('receta.cubilete.alto_m', lambda v: v),
}

def tope(p, ancla):
    z, h = float(p['centro_m'][2]), float(p['alto_m'])
    return z + h / 2 if ancla == 'centro' else z + h

def decidir(r):
    """-> (ancla | None, detalle). ancla='centro' solo si el dato declarado cuadra con 'centro' y no con 'base'."""
    tubos = [p for p in r.get('partes', []) if p.get('tipo') == 'tubo' and 'ancla' not in p]
    if not tubos: return None, 'sin tubos sin ancla'
    if r.get('objeto_id') not in DECLARA: return None, 'sin declaración registrada para este objeto'
    clave, leer = DECLARA[r['objeto_id']]
    d = next((x for x in r.get('datos', []) if x.get('clave') == clave), None)
    if d is None: return None, f'no está el dato {clave}'
    try: decl = float(leer(d['valor']))
    except Exception: return None, f'dato {clave} no numérico'
    t_c, t_b = max(tope(p, 'centro') for p in tubos), max(tope(p, 'base') for p in tubos)
    det = {'dato': clave, 'valor_declarado_m': decl, 'razon_argon': d.get('razon'), 'tope_si_centro_m': round(t_c, 4), 'tope_si_base_m': round(t_b, 4)}
    if abs(t_c - decl) <= TOL and abs(t_b - decl) > TOL: return 'centro', det
    if abs(t_b - decl) <= TOL: return 'base', det
    return None, dict(det, nota='ninguna lectura cuadra; no se convierte')

def aplicar(resp):
    """Devuelve (copia_convertida, informe). No modifica resp."""
    out = copy.deepcopy(resp); inf = {}
    for r in out.get('recetas', []) if isinstance(out, dict) else []:
        anc, det = decidir(r)
        if anc is None: 
            if r.get('objeto_id') in DECLARA: inf[r['objeto_id']] = {'convertido': False, 'detalle': det}
            continue
        for p in r['partes']:
            if p.get('tipo') == 'tubo' and 'ancla' not in p:
                p['ancla'] = anc
                p['ancla_añadida_por'] = 'programa ancla_tubos.py (Argon no escribió ancla)'
        inf[r['objeto_id']] = {'convertido': anc == 'centro', 'ancla': anc, 'detalle': det}
    return out, inf
