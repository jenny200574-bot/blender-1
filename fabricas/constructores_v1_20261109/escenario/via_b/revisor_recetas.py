# -*- coding: utf-8 -*-
"""Revisor SIN IA de recetas de objetos (recetas_objetos/v1) que devuelva Argon. US$0, sin red.
Comprueba, por receta: (1) esquema JSON; (2) que sean los objetos pedidos, en orden, con la caja y el apoyo de la ficha;
(3) que cada parte se pueda armar con formas_detalle (las mismas partes que usa Star); (4) que nada salga de la caja y que la
silueta llene la caja (1 cm o 5 % por eje); (5) apoyo: toca el piso / la pared / el techo según la ficha; (6) que no haya
partes flotando (grafo de contacto de cajas límite, tolerancia 2 mm; `conjunto` permite piezas sueltas si cada una apoya);
(7) colores dentro de la paleta de la ficha; (8) evidencia: cita LITERAL en el corpus (verificador_citas), campo de hoja
existente, deducciones con claves de la misma receta.
Uso: python3 revisor_recetas.py RESPUESTA.json FICHAS_<grupo>.json corpus_<grupo>.json  → sale 0 si APTA, 1 si RECHAZADA."""
from __future__ import annotations
import json, math, re, sys
from pathlib import Path
B = Path(__file__).resolve().parent
sys.path[:0] = [str(B.parent / 'codigo'), str(B)]   # [constructores_v1_20261109] verificador_citas.py copiado al lado (antes ruta del box)
import formas_detalle as FD
from verificador_citas import verificar as verificar_citas
import datos_via_b as DV
ESQUEMA = DV.inyectar_enum_apoyo(json.loads((B / 'esquemas/recetas_objetos_v1.schema.json').read_text(encoding='utf-8')))
TOL_CAJA, TOL_TOQUE, TOL_COLOR = 0.003, 0.002, 0.05
CAMPOS = {'caja': ['centro_m', 'tam_m'], 'tramo': ['a_m', 'b_m', 'radio_m'], 'cilindro': ['centro_m', 'radio_m', 'alto_m'],
          'esfera': ['centro_m', 'radio_m'], 'toro': ['centro_m', 'radio_mayor_m', 'radio_menor_m'],
          'tubo': ['centro_m', 'radio_ext_m', 'radio_int_m', 'alto_m'], 'placa': ['centro_m', 'radio_m', 'espesor_m'],
          'cono': ['a_m', 'b_m', 'radio_a_m', 'radio_b_m'], 'poliedro': ['vertices_m']}

# ---------------- esquema (subconjunto de JSON Schema que usa recetas_objetos/v1; sin dependencias) ----------------
_T = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'integer': int, 'number': (int, float), 'null': type(None)}
def _tipo_ok(v, t):
    if isinstance(t, list): return any(_tipo_ok(v, x) for x in t)
    if t in ('number', 'integer') and isinstance(v, bool): return False
    return isinstance(v, _T[t])
def esquema(v, s=ESQUEMA, ruta='$'):
    e = []
    if 'const' in s and v != s['const']: return [f'{ruta}: debe ser {s["const"]!r}']
    if 'enum' in s and v not in s['enum']: return [f'{ruta}: {v!r} no está en {s["enum"]}']
    if 'type' in s and not _tipo_ok(v, s['type']): return [f'{ruta}: tipo {type(v).__name__}, se espera {s["type"]}']
    if isinstance(v, dict):
        for k in s.get('required', []):
            if k not in v: e.append(f'{ruta}: falta {k}')
        pr = s.get('properties', {})
        for k, x in v.items():
            if k in pr: e += esquema(x, pr[k], f'{ruta}.{k}')
            elif s.get('additionalProperties') is False: e.append(f'{ruta}: campo no permitido {k}')
    if isinstance(v, list):
        if len(v) < s.get('minItems', 0): e.append(f'{ruta}: menos de {s["minItems"]} elementos')
        if 'maxItems' in s and len(v) > s['maxItems']: e.append(f'{ruta}: más de {s["maxItems"]} elementos')
        if 'items' in s: [e.extend(esquema(x, s['items'], f'{ruta}[{i}]')) for i, x in enumerate(v)]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if 'minimum' in s and v < s['minimum']: e.append(f'{ruta}: {v} < {s["minimum"]}')
        if 'maximum' in s and v > s['maximum']: e.append(f'{ruta}: {v} > {s["maximum"]}')
        if 'exclusiveMinimum' in s and v <= s['exclusiveMinimum']: e.append(f'{ruta}: {v} ≤ {s["exclusiveMinimum"]}')
        if not math.isfinite(v): e.append(f'{ruta}: no finito')
    if isinstance(v, str) and 'pattern' in s and not re.search(s['pattern'], v): e.append(f'{ruta}: {v!r} no cumple {s["pattern"]}')
    return e

# ---------------- geometría ----------------
def receta_a_piezas(r):
    T = FD.transformador([0, 0], 0, 0); out = []
    for p in r['partes']:
        for q in FD.parte_a_piezas(p, T):
            q['parte'] = p['nombre']; out.append(q)
    return out
def _toca(a, b, t=TOL_TOQUE):
    return all(a[0][k] <= b[1][k] + t and b[0][k] <= a[1][k] + t for k in range(3))
def componentes(cajas):
    n = len(cajas); padre = list(range(n))
    def f(i):
        while padre[i] != i: padre[i] = padre[padre[i]]; i = padre[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if _toca(cajas[i], cajas[j]): padre[f(i)] = f(j)
    g = {}
    for i in range(n): g.setdefault(f(i), []).append(i)
    return list(g.values())

def _hex_rgb(h): h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
def paleta(ficha):
    """(colores, estricta). Estricta si hay hex de 4a1 (dato del canal); si solo hay texto del ADN, avisa en vez de rechazar."""
    hx = re.findall(r'#[0-9A-Fa-f]{6}', ficha.get('color_4a1') or '')
    estricta = bool(hx)
    hx += [v for v in (ficha.get('colores_usados') or {}).values()]
    return [_hex_rgb(h) for h in hx], estricta

def campo(ficha, ruta):
    v = ficha
    for k in ruta.split('.'):
        if isinstance(v, dict) and k in v: v = v[k]
        elif isinstance(v, list) and k.isdigit() and int(k) < len(v): v = v[int(k)]
        else: return False
    return True

def revisar_receta(r, ficha, corpus):
    err, av = [], []
    oid = r['objeto_id']
    c = r['caja_m']; cf = ficha['caja_m']
    for k in ('ancho', 'fondo', 'alto'):
        if abs(c[k] - cf[k]) > 1e-4: err.append(f'E_CAJA {oid}: caja_m.{k} = {c[k]} y la ficha dice {cf[k]}')
    if DV.norma_apoyo(r['apoyo']) != DV.norma_apoyo(ficha['apoyo']): err.append(f'E_APOYO_FICHA {oid}: apoyo {r["apoyo"]!r}, la ficha dice {ficha["apoyo"]!r}')
    nombres = [p['nombre'] for p in r['partes']]
    if len(set(nombres)) != len(nombres): err.append(f'E_NOMBRES {oid}: nombres de parte repetidos')
    for p in r['partes']:
        falta = [k for k in CAMPOS[p['tipo']] if k not in p]
        if falta: err.append(f'E_PARTE {oid}.{p["nombre"]}: {p["tipo"]} sin {falta}')
        if p['tipo'] == 'tubo' and p.get('radio_int_m', 0) >= p.get('radio_ext_m', 0): err.append(f'E_PARTE {oid}.{p["nombre"]}: radio_int ≥ radio_ext')
    if err: return err, av, None
    try:
        pz = receta_a_piezas(r)
    except Exception as e:
        return err + [f'E_ARMAR {oid}: {type(e).__name__}: {e}'], av, None
    w, d, h = c['ancho'], c['fondo'], c['alto']
    lo, hi = [-w / 2, -d / 2, 0.0], [w / 2, d / 2, h]
    cajas = [FD.bbox_pieza(q) for q in pz]
    for q, (mn, mx) in zip(pz, cajas):
        fuera = max(max(lo[k] - mn[k], mx[k] - hi[k]) for k in range(3))
        if fuera > TOL_CAJA: err.append(f'E_FUERA {oid}.{q["parte"]}: sale {fuera * 100:.1f} cm de la caja')
    mn, mx = FD.bbox(pz)
    for k, (eje, L) in enumerate((('x/ancho', w), ('y/fondo', d), ('z/alto', h))):
        if (mx[k] - mn[k]) < L - max(0.01, 0.05 * L): err.append(f'E_NO_LLENA {oid}: en {eje} mide {mx[k] - mn[k]:.3f} m de {L} m')
    ap = DV.norma_apoyo(r['apoyo'])
    caja = {'ancho': w, 'fondo': d, 'alto': h}
    if ap not in DV.apoyos():
        err.append(f'E_APOYO {oid}: apoyo {ap!r} no está en apoyos.json')
        def toca(a, b): return False
    else:
        if not DV.toca_apoyo(ap, mn, mx, caja, TOL_CAJA):
            err.append(f'E_APOYO {oid}: no toca su apoyo ({ap})')
        def toca(a, b):
            return DV.toca_apoyo(ap, a, b, caja, TOL_CAJA)
    comp = componentes(cajas)
    if len(comp) > 1:
        if not r['conjunto']:
            sueltas = sorted({pz[i]['parte'] for g in sorted(comp, key=len)[:-1] for i in g})
            err.append(f'E_FLOTA {oid}: {len(comp)} grupos sin contacto; sueltas: {sueltas[:8]}')
        else:
            for g in comp:
                gm = [min(cajas[i][0][k] for i in g) for k in range(3)]; gx = [max(cajas[i][1][k] for i in g) for k in range(3)]
                if not toca(gm, gx): err.append(f'E_FLOTA {oid}: pieza suelta {pz[g[0]]["parte"]} no toca su apoyo ({ap})')
    pal, estricta = paleta(ficha)
    for p in r['partes']:
        if pal and min(math.dist(p['color_guia_rgb'], q) for q in pal) > TOL_COLOR:
            (err if estricta else av).append(f'{"E" if estricta else "A"}_COLOR {oid}.{p["nombre"]}: color fuera de la paleta de la ficha')
    cv = verificar_citas({'tipo': 'objeto', 'datos': r['datos']}, corpus, adn=None)
    err += [f'{x} ({oid})' for x in cv['errores'] if not x.startswith('E_HOJA')]
    for dd in r['datos']:
        if dd.get('origen') == 'hoja' and not campo(ficha, dd.get('campo_hoja') or ''):
            err.append(f'E_HOJA {oid} {dd.get("clave")}: campo {dd.get("campo_hoja")!r} no está en la ficha')
    if cv['con_fuente'] == 0: av.append(f'A_SIN_FUENTE {oid}: ningún dato con cita del corpus')
    return err, av, {'partes': len(r['partes']), 'piezas': len(pz), 'bbox_m': [round(mx[k] - mn[k], 4) for k in range(3)],
                     'grupos': len(comp), 'datos': cv['datos'], 'con_fuente': cv['con_fuente']}

def revisar(resp, fichas, corpus):
    e = esquema(resp)
    if e: return {'apta': False, 'errores': ['E_ESQUEMA ' + x for x in e[:40]], 'avisos': [], 'recetas': {}}
    err, av, info = [], [], {}
    pedidos = [f['objeto_id'] for f in fichas]; recibidos = [r['objeto_id'] for r in resp['recetas']]
    if recibidos != pedidos: err.append(f'E_OBJETOS: pedí {pedidos} y llegaron {recibidos}')
    fx = {f['objeto_id']: f for f in fichas}
    for r in resp['recetas']:
        if r['objeto_id'] not in fx: continue
        e1, a1, i1 = revisar_receta(r, fx[r['objeto_id']], corpus); err += e1; av += a1; info[r['objeto_id']] = i1
    return {'apta': not err, 'errores': err, 'avisos': av, 'recetas': info}

if __name__ == '__main__':
    resp, fichas, corpus = (json.loads(Path(a).read_text(encoding='utf-8')) for a in sys.argv[1:4])
    r = revisar(resp, fichas, corpus); print(json.dumps(r, ensure_ascii=False, indent=1)); sys.exit(0 if r['apta'] else 1)
