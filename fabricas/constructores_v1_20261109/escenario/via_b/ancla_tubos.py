# -*- coding: utf-8 -*-
"""ancla_tubos.py — conversión DETERMINISTA del ancla de los tubos en recetas de Argon (US$0, sin red).

En la biblioteca de Star, tubo.centro_m es el CENTRO DE LA BASE (ancla 'base'); cilindro.centro_m es el centro del volumen.
El prompt no lo decía explícito y Argon a veces usó tubo.centro_m como centro del volumen. Aquí NO se adivina:
solo se convierte cuando la receta DECLARA literalmente una altura (dato de la propia receta) que coincide con la
lectura 'centro' y NO con la lectura 'base'. Entonces se pone "ancla": "centro" en una COPIA de la parte (la posición
z queda tal cual la escribió Argon; formas_detalle la lleva a la base). El original no se toca.
"""
import copy, json, re
from pathlib import Path

TOL = 0.002   # m
# objeto_id -> clave del dato que declara la altura del borde superior del cuerpo tubular. Ya NO está en el código:
#  1) la receta puede traer "ancla_dato": "<clave>" (la declara Argon/el pedido);
#  2) si no, ancla_tubos_declara.json (datos revisados, por objeto; ahí quedaron las 2 de la habitación de Guardianes);
#  si el valor es una lista se lee el primer número (igual que antes).
_DATOS = Path(__file__).with_name('ancla_tubos_declara.json')
def _leer(v): return v[0] if isinstance(v, list) else v
DECLARA = {k: (c, _leer) for k, c in (json.loads(_DATOS.read_text(encoding='utf-8')).get('declara') or {}).items()} if _DATOS.is_file() else {}
def _declaracion(r):
    if r.get('ancla_dato'): return r['ancla_dato'], _leer
    return DECLARA.get(r.get('objeto_id'), (None, None))

def tope(p, ancla):
    z, h = float(p['centro_m'][2]), float(p['alto_m'])
    return z + h / 2 if ancla == 'centro' else z + h

def decidir(r):
    """-> (ancla | None, detalle). ancla='centro' solo si el dato declarado cuadra con 'centro' y no con 'base'."""
    tubos = [p for p in r.get('partes', []) if p.get('tipo') == 'tubo' and 'ancla' not in p]
    if not tubos: return None, 'sin tubos sin ancla'
    clave, leer = _declaracion(r)
    if not clave: return None, 'sin declaración registrada para este objeto'
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
            if _declaracion(r)[0]: inf[r['objeto_id']] = {'convertido': False, 'detalle': det}
            continue
        for p in r['partes']:
            if p.get('tipo') == 'tubo' and 'ancla' not in p:
                p['ancla'] = anc
                p['ancla_añadida_por'] = 'programa ancla_tubos.py (Argon no escribió ancla)'
        inf[r['objeto_id']] = {'convertido': anc == 'centro', 'ancla': anc, 'detalle': det}
    return out, inf
