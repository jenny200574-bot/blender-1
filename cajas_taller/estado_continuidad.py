"""Arreglo 1 de continuidad (Ricardo, respuesta a t371s1296, 3-nov-2026; respuesta de Argon v2). GRATIS: sin red ni IA.
«Foto» del estado de cada toma: cómo están los objetos y los personajes en el SEGUNDO EN QUE EMPIEZA la toma.
- Entrada: lo que la escena trae de la anterior (cubos/SB/memoria_continuidad.json: «entrada» de la escena, o la «salida»
  de la escena anterior del plan).
- Cambios: los beats del 01 con «objeto» + «cambio» (datos, no texto libre). Si un objeto cambia dos veces, queda el ÚLTIMO.
- Hechos del 01 (texto) vigentes hasta ese segundo; un hecho sin segundo NO se adivina: va como aviso.
- Si un cambio ocurre DENTRO de la toma: nota «cambios_durante_toma» (empieza con…; cambia a… en el segundo…).
Genérico (regla 6): ningún canal, capítulo, objeto ni personaje escrito aquí. Lo usan el 05 y, más adelante, el 03."""
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATOS = AQUI / 'paso01_datos' / 'estados_cambio.json'


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def _leer(f, d=None):
    try: return json.loads(Path(f).read_text(encoding='utf-8'))
    except Exception: return d


def vocabulario(en=False):
    v = _leer(DATOS, {}) or {}
    if en: return v.get('estados_en') or {}, v.get('inicial_en') or 'as at the start'
    return v.get('estados') or {}, v.get('inicial') or 'como al inicio'


def cambios_de_escena(C, avisos=None, escena=''):
    """Lista ordenada [{objeto, estado, t, beat}] desde C['acciones'] (objeto + cambio). Cambio sin objeto o sin segundo → aviso."""
    avisos = avisos if avisos is not None else []
    est, _ = vocabulario(); est_en, _ = vocabulario(True); out = []
    for b in (C or {}).get('acciones') or []:
        cam = str(b.get('cambio') or '').strip(); obj = str(b.get('objeto') or '').strip()
        if not cam: continue
        t = b.get('t'); t0 = _num(t[0]) if isinstance(t, (list, tuple)) and t else _num(t)
        if not obj: avisos.append(f"escena {escena}: beat {b.get('id')} cambia «{cam}» sin objeto (no se usa)"); continue
        if t0 is None: avisos.append(f"escena {escena}: beat {b.get('id')} ({obj}: {cam}) sin segundo (no se adivina)"); continue
        if cam not in est: avisos.append(f"escena {escena}: cambio «{cam}» sin palabra de estado en estados_cambio.json (se usa tal cual)")
        out.append({'objeto': obj, 'estado': est.get(cam, cam), 'estado_en': est_en.get(cam, cam), 'cambio': cam, 't': t0, 'beat': b.get('id')})
    return sorted(out, key=lambda x: x['t'])


def hechos_de_escena(C, avisos=None, escena=''):
    avisos = avisos if avisos is not None else []; out = []
    for h in (C or {}).get('hechos') or []:
        if not isinstance(h, dict) or not str(h.get('hecho') or '').strip(): continue
        t = _num(h.get('t'))
        if t is None: avisos.append(f"escena {escena}: hecho «{h.get('hecho')}» sin segundo (no se adivina en qué toma va)"); continue
        out.append({'hecho': str(h['hecho']), 'personaje': h.get('personaje') or '', 't': t})
    return sorted(out, key=lambda x: x['t'])


def entrada_de_escena(memoria, escena, orden=None):
    """Lo que la escena trae: «entrada» guardada en la memoria, o la «salida» de la escena anterior según «orden»."""
    E = (memoria or {}).get('escenas') or {}; n = str(escena)
    e = (E.get(n) or {}).get('entrada')
    if e: return e, (E.get(n) or {}).get('entrada', {}).get('fuente') or 'memoria (entrada)'
    o = [str(x) for x in (orden or [])]
    if n in o and o.index(n) > 0:
        prev = o[o.index(n) - 1]; s = (E.get(prev) or {}).get('salida')
        if s: return s, f'salida de la escena {prev}'
    return {}, 'sin memoria (inicio)'


def _fmt_t(t): return f'{t:g}'


def estado_toma(entrada, cambios, hechos, t_ini, t_fin=None):
    """«Foto» al empezar la toma (t_ini) + nota de lo que cambia dentro (t_ini < t < t_fin)."""
    _, inicial = vocabulario(); t_ini = _num(t_ini) or 0.0; t_fin = _num(t_fin)
    objetos = {}
    for o in (entrada or {}).get('objetos_escena') or []:
        objetos[str(o) if not isinstance(o, dict) else str(o.get('id') or o.get('nombre'))] = (o.get('estado') if isinstance(o, dict) else None) or 'como quedó en la escena anterior'
    objetos_en = {k: ('as left by the previous scene' if v == 'como quedó en la escena anterior' else v) for k, v in objetos.items()}
    for c in cambios:
        if c['t'] <= t_ini + 1e-9: objetos[c['objeto']] = c['estado']; objetos_en[c['objeto']] = c.get('estado_en') or c['estado']   # el último gana
    durante = []
    if t_fin is not None:
        _, inicial_en = vocabulario(True); prev = dict(objetos); prev_en = dict(objetos_en)
        for c in cambios:
            if t_ini + 1e-9 < c['t'] < t_fin - 1e-9:
                en = c.get('estado_en') or c['estado']
                durante.append({'objeto': c['objeto'], 'empieza': prev.get(c['objeto'], inicial), 'termina': c['estado'], 't': c['t'],
                                'empieza_en': prev_en.get(c['objeto'], inicial_en), 'termina_en': en})
                prev[c['objeto']] = c['estado']; prev_en[c['objeto']] = en
    personajes = {k: {x: v.get(x) for x in ('vestuario', 'danos', 'objetos') if v.get(x)} for k, v in ((entrada or {}).get('personajes') or {}).items() if isinstance(v, dict)}
    vig = [h for h in hechos if h['t'] <= t_ini + 1e-9]
    texto = ', '.join(f'{k}: {v}' for k, v in objetos.items())
    nota = '; '.join(f"{d['objeto']}: empieza {d['empieza']}, queda {d['termina']} en el segundo {_fmt_t(d['t'])} (a mitad de toma)" for d in durante)
    texto_en = ', '.join(f'{k}: {v}' for k, v in objetos_en.items())
    nota_en = '; '.join(f"{d['objeto']}: starts {d['empieza_en']}, becomes {d['termina_en']} at second {_fmt_t(d['t'])} (mid-shot)" for d in durante)
    return {'t_inicio': t_ini, 't_fin': t_fin, 'objetos': objetos, 'personajes': personajes, 'hechos_vigentes': vig,
            'texto': texto or 'sin cambios de objetos', 'cambios_durante_toma': durante, 'nota_cambios': nota,
            'objetos_en': objetos_en, 'texto_en': texto_en or 'no object changes', 'nota_en': nota_en}


def _fin_de_toma(t, siguientes, dur):
    if _num(t.get('t_fin')) is not None: return _num(t['t_fin'])
    t0 = _num(t.get('t')) or 0.0
    nx = [(_num(s.get('t')) or 0.0) for s in siguientes if (_num(s.get('t')) or 0.0) > t0 + 1e-9]
    return min(nx) if nx else _num(dur)


def anotar_plan(tomas, dirigida, memoria, orden=None):
    """Escribe t['estado'] en cada toma (in situ). dirigida(n) → dirección del 01 (o None). Devuelve avisos."""
    avisos, cache = [], {}
    orden = orden or list(dict.fromkeys(str(t.get('escena')) for t in tomas))
    for t in tomas:
        n = str(t.get('escena'))
        if n not in cache:
            C = dirigida(n); av = []
            if not C: av.append(f'escena {n}: sin dirección del 01 (estado solo con lo que trae de la escena anterior)')
            ent, fte = entrada_de_escena(memoria, n, orden)
            cache[n] = (C, cambios_de_escena(C, av, n), hechos_de_escena(C, av, n), ent, fte); avisos += av
        C, cam, hech, ent, fte = cache[n]
        mismas = [s for s in tomas if str(s.get('escena')) == n]
        e = estado_toma(ent, cam, hech, t.get('t'), _fin_de_toma(t, mismas, (C or {}).get('duracion_s')))
        e['entrada_fuente'] = fte; t['estado'] = e
        if e['nota_cambios']: t['cambios_durante_toma'] = e['nota_cambios']
    return avisos


# ---------------- Arreglo 4 (cubo 11): línea de estado por toma para el pedido de pintura ----------------
def linea_toma(toma):
    """«ESTADO EN ESTA TOMA <id>: …» + nota si algo cambia a mitad de toma. Toma sin estado → ''."""
    e = toma.get('estado') if isinstance(toma, dict) else None
    if not isinstance(e, dict): return ''
    partes = [e.get('texto_en') or e.get('texto') or 'no object changes']
    per = '; '.join(f"{k}: " + ', '.join(f"{x} {', '.join(map(str, v)) if isinstance(v, list) else v}" for x, v in d.items()) for k, d in (e.get('personajes') or {}).items() if d)
    if per: partes.append(per)
    s = f"STATE IN THIS SHOT {toma.get('id')}: " + '; '.join(partes) + '.'
    nota = e.get('nota_en') if 'nota_en' in e else e.get('nota_cambios')
    if nota: s += f" CHANGE MID-SHOT: {nota}."
    return s


def bloque_estados(ids_tomas, tomas_plan, dirigida=None, memoria=None):
    """Líneas de estado para las tomas pedidas (en su orden). Si el plan del 05 aún no trae «estado» (05 viejo),
    se calcula aquí sobre una COPIA (no se escribe nada). Toma que no está en el plan → se omite."""
    import copy
    tp = copy.deepcopy(tomas_plan or [])
    if dirigida is not None and any('estado' not in t for t in tp): anotar_plan(tp, dirigida, memoria or {})
    por_id = {str(t.get('id')): t for t in tp}
    return '\n'.join(x for x in (linea_toma(por_id[str(i)]) for i in ids_tomas if str(i) in por_id) if x)


# ---------------- Arreglo 2 (cubo 03): estado por toma y por fotograma para la revisión de coherencia ----------------
def estado_para_03(C, escena, memoria, orden, tomas_render):
    """El 03 corre ANTES del 05: el estado sale directo del 01 (C) + memoria, sobre los datos dados (no guarda nada).
    tomas_render = [{'shot', 'scene_seconds': [s0, s1], 'frames': [{'second'}]}]. Devuelve (lista STATE_PER_SHOT en inglés, avisos)."""
    av = []; n = str(escena)
    cam = cambios_de_escena(C, av, n); hech = hechos_de_escena(C, av, n); ent, fte = entrada_de_escena(memoria, n, orden)
    out = []
    for t in tomas_render or []:
        ss = t.get('scene_seconds') or [0, None]
        s0 = _num(ss[0]) if isinstance(ss, (list, tuple)) and ss else 0.0; s1 = _num(ss[1]) if isinstance(ss, (list, tuple)) and len(ss) > 1 else None
        e = estado_toma(ent, cam, hech, s0 or 0.0, s1)
        out.append({'shot': str(t.get('shot')), 'objects_at_start': e['objetos_en'], 'characters_carried_in': e['personajes'],
                    'facts_in_force': [h['hecho'] for h in e['hechos_vigentes']], 'changes_mid_shot': e['nota_en'],
                    'frames': [{'second': f.get('second'), 'objects': estado_toma(ent, cam, hech, f.get('second') or 0.0)['objetos_en']} for f in t.get('frames') or []]})
    return {'source_of_carry_in': fte, 'object_changes_in_scene': [{'object': c['objeto'], 'becomes': c.get('estado_en'), 'second': c['t']} for c in cam],
            'shots': out}, av
