"""Lectura GENÉRICA (solo lectura, US$0) de lo que deja el motor de Ako (Argon→Blender v5, caja 02N) para cualquier canal y capítulo.
2026-11-01 (Ricardo t304u): el 03 revisa los renders de la 02N en vez de los videos del 02 viejo.

Dónde mira (paso01_datos/motor_02n.json → «raiz», por defecto /opt/myia-argon-blender):
  tramos/<canal>/<cap>/<tramo>.json        → a qué escena pertenece cada tramo (campo «escena»), fps, ledger del 01 usado
  historial/<canal>/<cap>/<tramo>_<fecha>/  → corrida REAL (estado_escena.json, render_fNNN.png, revision_movimiento.json, log)
  historial/<canal>/<cap>-seco/…           → corrida EN SECO (Argon falso): sirve para probar la conexión, no la dirección
Nunca escribe en el motor de Ako ni llama a nada pago."""
import json, os, re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RX_CORRIDA = re.compile(r'^(?P<tramo>.+)_(?P<fecha>\d{8}_\d{6})$')
RX_RENDER = re.compile(r'^render_f(\d+)\.png$')


def ajustes():
    try: x = json.loads((AQUI / 'paso01_datos' / 'motor_02n.json').read_text(encoding='utf-8'))
    except Exception: x = {}
    return {'raiz': os.environ.get('MYIA_AB_RAIZ') or x.get('raiz') or '/opt/myia-argon-blender',
            'modos': x.get('modos') or ['real', 'seco'], 'usar_si_hay': x.get('usar_si_hay', True)}


def _leer(f, d=None):
    try: return json.loads(Path(f).read_text(encoding='utf-8'))
    except Exception: return d


def _seguro(x): return bool(re.fullmatch(r'[A-Za-z0-9._-]+', str(x or '')))


def _caps(capitulo):
    """El motor guarda el capítulo tal como se lo pasaron (n8n manda «1»); acepto también «01»."""
    c = str(capitulo); out = [c]
    if c.isdigit(): out += [str(int(c)), f'{int(c):02d}']
    return list(dict.fromkeys(out))


def corridas(canal, capitulo, escena=None, cfg=None):
    """Corridas del motor para el capítulo (las más nuevas primero). escena=None → todas. Cada una:
    {id, tramo, modo, carpeta, escena, fps, frames, renders[(frame, ruta)], estado, revision, validacion, costo_usd, tramo_json}"""
    cfg = cfg or ajustes(); R = Path(cfg['raiz'])
    if not (_seguro(canal) and all(_seguro(c) for c in _caps(capitulo))): return []
    out = []
    for cap in _caps(capitulo):
        for modo in cfg['modos']:
            h = R / 'historial' / canal / (cap if modo == 'real' else f'{cap}-seco')
            if not h.is_dir(): continue
            for d in h.iterdir():
                m = RX_CORRIDA.match(d.name)
                if not (d.is_dir() and m and (d / 'estado_escena.json').is_file()): continue
                tj = _leer(R / 'tramos' / canal / cap / f"{m['tramo']}.json", {}) or {}
                n = str(tj.get('escena') or '')
                if escena is not None and n != str(escena): continue
                est = _leer(d / 'estado_escena.json', {}) or {}
                rev = _leer(d / 'revision_movimiento.json', {}) or {}
                rend = sorted((int(RX_RENDER.match(f.name).group(1)), str(f)) for f in d.glob('render_f*.png') if RX_RENDER.match(f.name))
                costo = None
                for ln in (d / 'log_herramientas.jsonl').read_text(encoding='utf-8', errors='replace').splitlines() if (d / 'log_herramientas.jsonl').is_file() else []:
                    if '"costo_total_usd"' in ln:
                        try: costo = float(json.loads(ln)['costo_total_usd'])
                        except Exception: pass
                out.append({'id': d.name, 'tramo': m['tramo'], 'fecha': m['fecha'], 'modo': modo, 'carpeta': str(d), 'escena': n or None,
                            'fps': float(tj.get('fps') or est.get('fps') or 24), 'frames': est.get('frames') or [1, tj.get('frames') or 1],
                            'renders': rend, 'estado': est, 'revision': rev, 'validacion': (est.get('validacion') or {}),
                            'costo_usd': 0.0 if modo == 'seco' else costo, 'tramo_json': tj})
    # orden: primero el modo preferido (real), dentro de cada modo la más nueva primero
    return sorted(out, key=lambda c: (cfg['modos'].index(c['modo']), -int(c['fecha'].replace('_', ''))))


def mejor(canal, capitulo, escena, cfg=None):
    cs = corridas(canal, capitulo, escena, cfg)
    return cs[0] if cs else None


def _seg(f, fps, f0=1): return round((int(f) - int(f0)) / float(fps), 3)


def _a_escena(c):
    """Segundos del tramo → segundos de la escena del 01, si el tramo dice qué ventana del 01 cubre (cubo01_ventana_s)."""
    v = (c['tramo_json'] or {}).get('cubo01_ventana_s'); fps = c['fps']; fr = c['frames'] or [1, 1]
    dur = (int(fr[-1]) - int(fr[0])) / float(fps) if len(fr) > 1 else 0
    if not (isinstance(v, list) and len(v) == 2 and dur > 0): return lambda s: s
    return lambda s: round(float(v[0]) + s * (float(v[1]) - float(v[0])) / dur, 3)


def tomas_y_fotos(c, camara=None):
    """Corrida del motor → (tomas, fotos) en el formato que ya usa el 03 (mismo que el 02 viejo).
    tomas: {toma, segundos_escena, tipo, camara_usada, figuras, accion, lineas, fuente}; fotos: {toma, segundo, archivo, frame}.
    segundos_escena = segundos del 01 (si el tramo trae su ventana); segundos_tramo = desde el cuadro 1 del tramo."""
    fps = c['fps']; f0 = int((c['frames'] or [1])[0] or 1); est = c['estado']; E = _a_escena(c)
    figs = [{'id_01': k, 'personaje': k, 'pos_final': (v or {}).get('pos')} for k, v in (est.get('actores') or {}).items()]
    tomas = []
    for i, t in enumerate(est.get('tomas') or []):
        fr = t.get('f') or [f0, f0]
        st = [_seg(fr[0], fps, f0), _seg(fr[-1], fps, f0)]
        tomas.append({'toma': str(t.get('id') or f'T{i + 1}'), 'segundos_escena': [E(st[0]), E(st[1])], 'segundos_tramo': st, 'frames': fr,
                      'tipo': t.get('plano'), 'camara_usada': camara or {}, 'figuras': figs, 'accion': t.get('accion'), 'lineas': t.get('lineas'),
                      'fuente': f"02N {c['modo']} {c['id']}"})
    if not tomas and c['renders']:
        fin = c['frames'][-1] if c['frames'] else c['renders'][-1][0]
        tomas = [{'toma': 'T1', 'segundos_escena': [E(0.0), E(_seg(fin, fps, f0))], 'segundos_tramo': [0.0, _seg(fin, fps, f0)], 'frames': [f0, fin], 'tipo': None, 'camara_usada': camara or {},
                  'figuras': figs, 'fuente': f"02N {c['modo']} {c['id']}"}]
    fotos = []
    for fr, ruta in c['renders']:
        t = next((x for x in tomas if x['frames'][0] <= fr <= x['frames'][-1]), tomas[-1] if tomas else None)
        fotos.append({'toma': t['toma'] if t else 'T1', 'segundo': E(_seg(fr, fps, f0)), 'segundo_tramo': _seg(fr, fps, f0), 'archivo': ruta, 'frame': fr})
    return tomas, fotos


def hallazgos_revisor(c):
    """Errores del revisor de movimiento del motor → hallazgos del código para el 03 (los avisos van aparte)."""
    h = []
    for x in (c['revision'] or {}).get('hallazgos') or []:
        if x.get('severidad') != 'error': continue
        fr = (x.get('frames') or [[None]])[0]
        h.append({'tipo': 'movimiento', 'figura': x.get('actor'), 'segundo': _a_escena(c)(_seg(fr[0], c['fps'], (c['frames'] or [1])[0])) if fr and fr[0] is not None else None,
                  'que': f"revisor del motor: {x.get('tipo')} · {x.get('detalle')}"})
    return h


def resumen(c):
    rev = c['revision'] or {}
    return {'id': c['id'], 'modo': c['modo'], 'carpeta': c['carpeta'], 'renders': [r for _, r in c['renders']], 'validacion_ok': bool(c['validacion'].get('ok')),
            'revisor_errores': int(rev.get('errores') or 0), 'revisor_avisos': sum(1 for x in rev.get('hallazgos') or [] if x.get('severidad') != 'error'),
            'costo_usd': c['costo_usd'], 'ledger_01': (c['tramo_json'] or {}).get('cubo01_ledger'), 'tramo': c['tramo'],
            'estado_escena': str(Path(c['carpeta']) / 'estado_escena.json')}
