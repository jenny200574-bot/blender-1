#!/usr/bin/env python3
"""MYIA · Taller n8n · llamada_segura (orden 68, Ricardo). GRATIS: nada aquí llama a la red ni toca el ledger.
PISTA INMI (2026-10-29): piezas comunes de 4a1/4b1/4c1/4a4 (Argon) y 4a5/4b2/4c2 (Nano Banana) — orden 72: + revisar_ids:

- leer_json / validar_esquema: la respuesta se lee como JSON y se revisa contra el esquema del taller (subconjunto de
  JSON Schema: type, properties, required, items, enum, minItems, maxItems, minLength, pattern; sin dependencias).
- reparar_json: arreglo LOCAL y determinista de JSON roto por un signo de estructura (falta un «]», «}» o «,», o sobra
  una «,»). Solo mete o quita esos signos FUERA de los textos, como mucho N cambios, y nunca inventa contenido. Si la
  respuesta está cortada (truncada) NO se repara: hay que volver a pedirla.
- clasificar_error / espera_reintento / intentar: intentos ACOTADOS. Cada intento lo hace quien llama con SU línea de ledger
  ANTES de la llamada. 429 = no_cobrado (Google no cobra el 429), se espera Retry-After / retryDelay o 20-40-80 s con
  azar; error definitivo (400/403/404) no se repite; otros errores se marcan error_posible_cobro y se repiten como mucho 1 vez
  y solo si el presupuesto aprobado alcanza (lo decide quien llama con puede_otro).
- Ritmo: separación mínima entre llamadas al mismo modelo, también entre procesos (candado de archivo, fcntl).
- Orden 81: TOPE DE TIEMPO por llamada (llamadas_config.json: imagen / texto). timeout_ms(tipo) para HttpOptions,
  transporte_texto() = la llamada de texto de Argon con ese tope, es_timeout() / clase «timeout»: la línea del ledger queda
  «timeout» (cuenta el peor caso) y intentar() la repite sola al menos reintentos_por_timeout veces si el --ok alcanza.
"""
import os, re, json, time, random, fcntl, email.utils
from pathlib import Path

# ------------------------------------------------------------------ JSON
_FENCE = re.compile(r'^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$', re.S)


def limpiar(texto):
    """Quita la cerca ```json … ``` si la trae (igual que myia_paso00._json)."""
    t = (texto or '').strip()
    m = _FENCE.match(t)
    return m.group(1).strip() if m else t


def leer_json(texto):
    """(obj, None) si es JSON válido; (None, {'msg','pos','linea','col'}) si no."""
    t = limpiar(texto)
    try:
        return json.loads(t), None
    except json.JSONDecodeError as e:
        return None, {'msg': e.msg, 'pos': e.pos, 'linea': e.lineno, 'col': e.colno}


def _tipo_ok(v, t):
    if isinstance(t, list): return any(_tipo_ok(v, z) for z in t)
    return {'object': isinstance(v, dict), 'array': isinstance(v, list), 'string': isinstance(v, str),
            'number': isinstance(v, (int, float)) and not isinstance(v, bool), 'integer': isinstance(v, int) and not isinstance(v, bool),
            'boolean': isinstance(v, bool), 'null': v is None}.get(t, True)


def validar_esquema(obj, esq, ruta='$', max_errores=40, _err=None):
    """Lista de errores (vacía = válido) contra un subconjunto de JSON Schema."""
    err = [] if _err is None else _err
    if len(err) >= max_errores or not isinstance(esq, dict): return err
    if 'anyOf' in esq:
        if not any(not validar_esquema(obj, s, ruta, max_errores) for s in esq['anyOf']): err.append(f'{ruta}: no cumple ninguna opción de anyOf')
        return err
    t = esq.get('type')
    if t is not None and not _tipo_ok(obj, t):
        err.append(f'{ruta}: se esperaba {t}, vino {type(obj).__name__}'); return err
    if 'enum' in esq and obj not in esq['enum']: err.append(f'{ruta}: {str(obj)[:40]!r} no está en {esq["enum"]}')
    if isinstance(obj, str):
        if 'minLength' in esq and len(obj) < esq['minLength']: err.append(f'{ruta}: texto más corto que {esq["minLength"]}')
        if 'pattern' in esq and not re.search(esq['pattern'], obj): err.append(f'{ruta}: {obj[:40]!r} no cumple {esq["pattern"]}')
    if isinstance(obj, dict):
        for k in esq.get('required') or []:
            if k not in obj: err.append(f'{ruta}: falta «{k}»')
        for k, s in (esq.get('properties') or {}).items():
            if k in obj: validar_esquema(obj[k], s, f'{ruta}.{k}', max_errores, err)
    if isinstance(obj, list):
        if 'minItems' in esq and len(obj) < esq['minItems']: err.append(f'{ruta}: menos de {esq["minItems"]} elementos')
        if 'maxItems' in esq and len(obj) > esq['maxItems']: err.append(f'{ruta}: más de {esq["maxItems"]} elementos')
        if isinstance(esq.get('items'), dict):
            for i, v in enumerate(obj): validar_esquema(v, esq['items'], f'{ruta}[{i}]', max_errores, err)
    return err[:max_errores]


def _fuera_de_texto(t, pos):
    """True si la posición pos de t queda fuera de un texto JSON ("…")."""
    dentro = esc = False
    for c in t[:pos]:
        if esc: esc = False; continue
        if c == '\\' and dentro: esc = True; continue
        if c == '"': dentro = not dentro
    return not dentro


def _token_anterior(t, pos):
    """Inicio del token anterior a pos (salta espacios; un texto "…" cuenta entero) y la coma antes de él, si hay."""
    i = pos - 1
    while i >= 0 and t[i] in ' \t\r\n': i -= 1
    if i >= 0 and t[i] == '"':
        j = i - 1
        while j >= 0:
            if t[j] == '"' and (j == 0 or t[j - 1] != '\\'): break
            j -= 1
        i = j
    ini = max(i, 0)
    k = ini - 1
    while k >= 0 and t[k] in ' \t\r\n': k -= 1
    return ini, (k if k >= 0 and t[k] == ',' else None)


def _avance(t):
    try:
        json.loads(t); return None
    except json.JSONDecodeError as e:
        return e


_NO_REPARABLE = ('Unterminated string', 'Invalid control character', 'Invalid \\escape', 'Invalid \\uXXXX escape')


def reparar_json(texto, max_ediciones=3):
    """Arreglo local determinista. Devuelve dict(ok, obj, texto, ediciones=[...], motivo).
    ok=False con motivo 'truncado' si el error está al final (respuesta cortada): eso NO se repara aquí."""
    t = limpiar(texto)
    ed = []
    for _ in range(max_ediciones + 1):
        e = _avance(t)
        if e is None:
            return {'ok': True, 'obj': json.loads(t), 'texto': t, 'ediciones': ed, 'motivo': 'sin_cambios' if not ed else 'reparado'}
        if len(ed) >= max_ediciones:
            return {'ok': False, 'obj': None, 'texto': None, 'ediciones': ed, 'motivo': f'más de {max_ediciones} arreglos: {e.msg} en {e.pos}'}
        if any(e.msg.startswith(m) for m in _NO_REPARABLE):
            return {'ok': False, 'obj': None, 'texto': None, 'ediciones': ed, 'motivo': f'no reparable: {e.msg} en {e.pos}'}
        if len(t[e.pos:].strip()) == 0:
            return {'ok': False, 'obj': None, 'texto': None, 'ediciones': ed, 'motivo': f'truncado: la respuesta termina antes de cerrar ({e.msg} en {e.pos})'}
        ini, coma = _token_anterior(t, e.pos)
        cands = []
        for p in dict.fromkeys(x for x in (coma, ini, e.pos) if x is not None):
            if not _fuera_de_texto(t, p): continue
            for c in (']', '}', ','):
                cands.append((t[:p] + c + t[p:], {'accion': 'meter', 'signo': c, 'pos': p}))
        for q in (e.pos - 1, e.pos):   # coma de más (Python 3.13 marca la coma misma: «Illegal trailing comma»)
            if 0 <= q < len(t) and t[q] == ',' and _fuera_de_texto(t, q):
                cands.append((t[:q] + t[q + 1:], {'accion': 'quitar', 'signo': ',', 'pos': q}))
        mejor = None
        for nt, d in cands:   # orden fijo → mismo resultado siempre; gana lo que deja leer más lejos (o todo)
            e2 = _avance(nt)
            lejos = len(nt) + 1 if e2 is None else e2.pos
            if lejos > e.pos + 1 and (mejor is None or lejos > mejor[0]): mejor = (lejos, nt, d)
        if mejor is None:
            return {'ok': False, 'obj': None, 'texto': None, 'ediciones': ed, 'motivo': f'sin arreglo de estructura que sirva: {e.msg} en {e.pos}'}
        d = dict(mejor[2], error=e.msg, error_pos=e.pos, contexto=t[max(0, mejor[2]['pos'] - 40):mejor[2]['pos'] + 40])
        ed.append(d); t = mejor[1]
    return {'ok': False, 'obj': None, 'texto': None, 'ediciones': ed, 'motivo': 'sin terminar'}


def revisar_respuesta(texto, esquema=None, fin=None, max_ediciones=3):
    """Revisión completa de una respuesta de texto JSON. estado: ok | reparable | json_roto | truncado."""
    obj, err = leer_json(texto)
    corto = 'MAX_TOKENS' in str(fin or '')
    if obj is not None:
        return {'estado': 'ok', 'obj': obj, 'json_valido': True, 'esquema_errores': validar_esquema(obj, esquema) if esquema else [], 'truncado': False}
    r = reparar_json(texto, max_ediciones)
    if r['ok'] and not corto:
        return {'estado': 'reparable', 'obj': r['obj'], 'texto_reparado': r['texto'], 'ediciones': r['ediciones'], 'json_valido': False, 'error_json': err,
                'esquema_errores': validar_esquema(r['obj'], esquema) if esquema else [], 'truncado': False}
    trunc = corto or str(r.get('motivo', '')).startswith('truncado')
    return {'estado': 'truncado' if trunc else 'json_roto', 'obj': None, 'json_valido': False, 'error_json': err, 'motivo': r.get('motivo'), 'truncado': trunc}


# ------------------------------------------------------------------ una imagen por cámara (orden 69)
def revisar_camaras(escenario, camaras):
    """PISTA INMI (2026-10-29): orden 69 (Ricardo: «exige una vista por cámara») — revisión LOCAL y GRATIS de un escenario 4a4.
    camaras = renders de las cámaras del molde de Blender de ESE escenario (lista que arma el código desde molde.json; nunca la
    del modelo). Regla genérica: la base usa UNA cámara del molde y CADA otra cámara tiene SU vista (base + vistas = una imagen
    por cámara). Falta una cámara, dos imágenes con la misma cámara (vistas juntadas o repetidas) o una cámara que no es del
    molde → completo=False. Sin cámaras (sin molde) → completo=True (no hay nada que exigir)."""
    cams = [str(c) for c in (camaras or []) if c]
    x = escenario if isinstance(escenario, dict) else {}
    b = x.get('base') if isinstance(x.get('base'), dict) else {}
    usadas = [('base', str(((b.get('camara') or {}) if isinstance(b.get('camara'), dict) else {}).get('render') or ''))]
    for k, v in enumerate(x.get('vistas') or [], 1):
        if not isinstance(v, dict): usadas.append((f'vista {k}', '')); continue
        c = v.get('camara') if isinstance(v.get('camara'), dict) else {}
        usadas.append((str(v.get('vista_id') or f'vista {k}'), str(c.get('render') or '')))
    out = {'escenario_id': x.get('escenario_id'), 'camaras_del_molde': cams, 'imagenes_esperadas': len(cams), 'vistas_esperadas': max(0, len(cams) - 1),
           'vistas_recibidas': len(usadas) - 1, 'base': usadas[0][1], 'faltan': [], 'repetidas': [], 'ajenas': [], 'completo': True, 'sin_molde': not cams}
    if not cams: return out
    cuenta = {}
    for _, r in usadas:
        if r: cuenta[r] = cuenta.get(r, 0) + 1
    out['faltan'] = [c for c in cams if not cuenta.get(c)]
    out['repetidas'] = [c for c in cams if cuenta.get(c, 0) > 1]
    out['ajenas'] = [f'{q}: {r or "sin cámara"}' for q, r in usadas if r not in cams and not (q == 'base' and not r)]
    if not usadas[0][1]: out['ajenas'].insert(0, 'base: sin cámara')
    out['completo'] = not (out['faltan'] or out['repetidas'] or out['ajenas'])
    return out


def texto_camaras(rv):
    """Frase corta en español para el equipo (n8n, bitácora)."""
    if not rv or rv.get('completo'): return ''
    p = []
    if rv.get('faltan'): p.append('faltan vistas para las cámaras ' + ', '.join(c.rsplit('.', 1)[0] for c in rv['faltan']))
    if rv.get('repetidas'): p.append('cámaras usadas dos veces ' + ', '.join(c.rsplit('.', 1)[0] for c in rv['repetidas']))
    if rv.get('ajenas'): p.append('imágenes sin una cámara del molde: ' + '; '.join(rv['ajenas']))
    return (f"{rv.get('escenario_id')}: INCOMPLETO — " + '; '.join(p) +
            f" (el molde tiene {rv.get('imagenes_esperadas')} cámaras = base + {rv.get('vistas_esperadas')} vistas; llegaron base + {rv.get('vistas_recibidas')})")


# ------------------------------------------------------------------ un registro por id pedido (orden 72)
def revisar_ids(obj, clave, idk, ids, requeridos=()):
    """PISTA INMI (2026-10-29): orden 72 (Ricardo, pt251u) — revisión LOCAL y GRATIS de una respuesta 4a1/4b1/4c1 (genérica: sirve
    para cualquier lista de registros con id). No se confía en lo que dice el modelo: el CÓDIGO cuenta.
    - buenos: ids pedidos que vinieron UNA vez y con todos los campos obligatorios del registro (requeridos = required del item);
    - faltan: ids pedidos que no vinieron; ajenos: ids que no se pidieron; repetidos: ids que vinieron más de una vez;
    - sin_campos: {id: [campos que faltan]} (el registro está, pero le falta algo obligatorio → no sirve).
    completo = todos los pedidos son buenos y no hay ajenos ni repetidos. Errores más hondos del esquema solo se informan aparte."""
    pedidos = [str(i) for i in (ids or [])]
    regs = (obj or {}).get(clave) if isinstance(obj, dict) else None
    regs = regs if isinstance(regs, list) else []
    cuenta, sin_campos, no_dict = {}, {}, 0
    for v in regs:
        if not isinstance(v, dict) or not v.get(idk): no_dict += 1; continue
        i = str(v[idk]); cuenta[i] = cuenta.get(i, 0) + 1
        fal = [k for k in (requeridos or ()) if k not in v]
        if fal: sin_campos.setdefault(i, fal)
    out = {'pedidos': pedidos, 'recibidos': len(regs), 'faltan': [i for i in pedidos if not cuenta.get(i)],
           'ajenos': sorted(i for i in cuenta if i not in pedidos), 'repetidos': sorted(i for i, n in cuenta.items() if n > 1),
           'sin_campos': sin_campos, 'sin_id': no_dict, 'lista_ok': isinstance((obj or {}).get(clave) if isinstance(obj, dict) else None, list)}
    out['buenos'] = [i for i in pedidos if cuenta.get(i) == 1 and i not in sin_campos]
    out['completo'] = bool(out['lista_ok']) and len(out['buenos']) == len(pedidos) and not out['ajenos'] and not out['repetidos'] and not no_dict
    return out


def texto_ids(rv, quien=''):
    """Frase corta en español (n8n, bitácora). '' si está completo."""
    if not rv or rv.get('completo'): return ''
    p = []
    if not rv.get('lista_ok'): p.append('la respuesta no trae la lista de registros')
    if rv.get('faltan'): p.append('faltan ' + ', '.join(rv['faltan']))
    if rv.get('sin_campos'): p.append('registros a medias: ' + '; '.join(f"{i} (sin {', '.join(c[:4])}{'…' if len(c) > 4 else ''})" for i, c in rv['sin_campos'].items()))
    if rv.get('repetidos'): p.append('repetidos ' + ', '.join(rv['repetidos']))
    if rv.get('ajenos'): p.append('no pedidos ' + ', '.join(rv['ajenos']))
    if rv.get('sin_id'): p.append(f"{rv['sin_id']} registro(s) sin id")
    return (f'{quien}: ' if quien else '') + 'INCOMPLETO — ' + '; '.join(p) + f" (pedidos {len(rv.get('pedidos') or [])}, buenos {len(rv.get('buenos') or [])})"


# ------------------------------------------------------------------ errores e intentos
class SinPresupuesto(RuntimeError):
    """No hay presupuesto aprobado para OTRO intento: no se anota ni se llama."""


class NoLlamado(RuntimeError):
    """Falló ANTES de la llamada (fijo, precio, credencial, tope…): no hay línea de ledger; repetir no sirve."""


class LlamadaVencida(TimeoutError):
    """Orden 81: la llamada pasó su tope de tiempo (llamadas_config.json) y se cortó."""


CONFIG_LLAMADAS = Path(__file__).resolve().parent / 'llamadas_config.json'


def config_llamadas():
    try: return json.loads(CONFIG_LLAMADAS.read_text(encoding='utf-8'))
    except Exception: return {'timeout_s': {'imagen': 120, 'texto': 900}, 'reintentos_por_timeout': 1, 'espera_tras_timeout_s': 10}


def tope_s(tipo):
    """Segundos máximos de UNA llamada pagada ('imagen' | 'texto'). Se puede bajar/subir con TALLER_TIMEOUT_<TIPO>_S."""
    return num_env(f'TALLER_TIMEOUT_{str(tipo).upper()}_S', (config_llamadas().get('timeout_s') or {}).get(tipo, 900))


def timeout_ms(tipo): return int(tope_s(tipo) * 1000)


def reintentos_por_timeout(): return max(1, int(config_llamadas().get('reintentos_por_timeout', 1)))   # Ricardo: «por lo menos 1 vez más»


def es_timeout(exc):
    """¿El error es un tope de tiempo (nuestro o de la red: httpx ReadTimeout/ConnectTimeout, socket timeout, «timed out»)?"""
    if isinstance(exc, (TimeoutError, LlamadaVencida)): return True
    for k in type(exc).__mro__:
        if 'timeout' in k.__name__.lower(): return True
    s = str(exc)[:300].lower()
    return 'timed out' in s or 'deadline exceeded' in s or 'deadline_exceeded' in s


def estado_fallo(exc):
    """Estado del ledger para un intento que falló: «timeout» si se venció el tope de tiempo; si no, no_cobrado / error_posible_cobro."""
    c = clasificar_error(exc)
    return 'timeout' if c['clase'] == 'timeout' else (c['cobro'] or 'error_posible_cobro')


def cuenta_peor_caso(cobro):
    """¿Ese intento fallido suma su peor caso a lo gastado? (todo menos no_cobrado)."""
    return bool(cobro) and cobro != 'no_cobrado'


def transporte_texto(AR, segundos=None, pensamientos=False, silencio_s=None):
    """Orden 81 + t419u (2026-11-05): tope de tiempo REAL aunque el stream no entregue chunks.
    - HttpOptions(timeout) en el pedido.
    - AFC desactivado (el SDK lo prende por defecto y con generate_content_stream puede colgarse sin texto).
    - Watchdog en hilo: si no termina en `seg` s, LlamadaVencida aunque el iterador esté bloqueado.
    Se pasa como transporte= a AR.llamar (ledger ANTES igual)."""
    seg = float(segundos if segundos is not None else tope_s('texto'))
    if pensamientos and not PENSAMIENTOS_OFF.exists(): return _transporte_pensando(AR, seg, silencio_s)   # Fase 4: solo si el cubo lo pide
    def vertex(prompt, modelo, nivel, max_out, json_out, adjuntos=None, esquema=None, reloj=time.monotonic):
        from google.genai import types
        import concurrent.futures
        c = AR._cliente()
        extra = {'response_mime_type': 'application/json'} if json_out else {}
        if esquema is not None: extra.update(response_mime_type='application/json', response_json_schema=AR.esquema_para_api(esquema))
        afc = types.AutomaticFunctionCallingConfig(disable=True)
        cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=nivel), max_output_tokens=max_out,
                                          automatic_function_calling=afc,
                                          http_options=types.HttpOptions(timeout=int(seg * 1000)), **extra)
        t0 = reloj()
        def _consumir():
            txt, u, fin = '', None, None
            for ch in c.models.generate_content_stream(model=modelo, contents=AR.contenidos(prompt, types, adjuntos), config=cfg):
                if reloj() - t0 > seg:
                    raise LlamadaVencida(f'la llamada de texto pasó {seg:.0f} s (tope de llamadas_config.json)')
                if ch.text: txt += ch.text
                if ch.usage_metadata: u = ch.usage_metadata
                if ch.candidates and ch.candidates[0].finish_reason: fin = str(ch.candidates[0].finish_reason)
            tin = (u.prompt_token_count or 0) if u else 0
            tout = ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) if u else 0
            return {'texto': txt, 'tokens_entrada': tin, 'tokens_salida': tout, 'fin': fin}
        # tope duro: aunque el stream no entregue el primer chunk, salimos a los `seg` s
        with concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='argon_txt') as pool:
            fut = pool.submit(_consumir)
            try:
                return fut.result(timeout=max(1.0, seg + 2.0))
            except concurrent.futures.TimeoutError as e:
                raise LlamadaVencida(f'la llamada de texto pasó {seg:.0f} s sin terminar (watchdog t419u; stream bloqueado)') from e
    vertex.tope_s = seg
    return vertex


class IntentosAgotados(RuntimeError):
    def __init__(self, ultimo, intentos):
        super().__init__(f'{type(ultimo).__name__}: {str(ultimo)[:300]}')
        self.ultimo, self.intentos = ultimo, intentos


def _codigo(exc):
    c = getattr(exc, 'code', None)
    if isinstance(c, int): return c
    m = re.match(r'\s*(\d{3})\b', str(exc))
    return int(m.group(1)) if m else None


def clasificar_error(exc):
    """clase: '429' | 'transitorio' | 'definitivo'; cobro: lo que va al ledger (no_cobrado | error_posible_cobro)."""
    if isinstance(exc, (SinPresupuesto, NoLlamado)): return {'clase': 'definitivo', 'codigo': None, 'cobro': None}
    if es_timeout(exc): return {'clase': 'timeout', 'codigo': None, 'cobro': 'error_posible_cobro'}   # orden 81: cuenta el peor caso; en el ledger se anota «timeout» (estado_fallo)
    cod = _codigo(exc); st = str(getattr(exc, 'status', '') or ''); s = str(exc)[:400]
    if cod == 429 or st == 'RESOURCE_EXHAUSTED' or (cod is None and ('429' in s[:60] or 'RESOURCE_EXHAUSTED' in s)):
        return {'clase': '429', 'codigo': 429, 'cobro': 'no_cobrado'}
    if cod in (400, 401, 403, 404) or st in ('INVALID_ARGUMENT', 'PERMISSION_DENIED', 'NOT_FOUND', 'UNAUTHENTICATED'):
        return {'clase': 'definitivo', 'codigo': cod, 'cobro': 'no_cobrado'}
    return {'clase': 'transitorio', 'codigo': cod, 'cobro': 'error_posible_cobro'}


def _segundos(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    v = str(v).strip()
    m = re.fullmatch(r'(\d+(?:\.\d+)?)s?', v)
    if m: return float(m.group(1))
    try:
        d = email.utils.parsedate_to_datetime(v)
        return max(0.0, d.timestamp() - time.time())
    except Exception:
        return None


def retry_after(exc):
    """Segundos que pide Google: cabecera Retry-After de la respuesta, o RetryInfo.retryDelay del cuerpo. None si no dice."""
    resp = getattr(exc, 'response', None)
    hs = getattr(resp, 'headers', None)
    if hs is not None:
        try: v = hs.get('Retry-After') or hs.get('retry-after')
        except Exception: v = None
        s = _segundos(v)
        if s is not None: return s
    det = getattr(exc, 'details', None)
    pila = [det]
    while pila:
        x = pila.pop()
        if isinstance(x, dict):
            if 'retryDelay' in x:
                s = _segundos(x['retryDelay'])
                if s is not None: return s
            pila += list(x.values())
        elif isinstance(x, list): pila += x
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", str(exc))
    return float(m.group(1)) if m else None


def espera_reintento(exc, n, base=20.0, maximo=120.0, azar=random.random):
    """Espera antes del intento n+1: lo que pide Google (tope `maximo`), o base·2^(n-1) + hasta 25 % de azar."""
    ra = retry_after(exc)
    if ra is not None: return round(min(maximo, max(1.0, ra)), 1)
    return round(min(maximo, base * 2 ** (n - 1)) * (1 + 0.25 * azar()), 1)


def intentar(llamada, *, max_intentos=4, max_transitorios=1, espera_base=20.0, espera_max=120.0, espera_total_max=300.0,
             puede_otro=lambda n, c: True, dormir=time.sleep, azar=random.random, ritmo=None, ahora=lambda: time.strftime('%Y-%m-%dT%H:%M:%S%z'),
             max_timeouts=None):
    """Intentos ACOTADOS. llamada(n) hace UN intento (n = 1, 2, …) con su propia línea de ledger ANTES de llamar y la
    marca si falla. Devuelve (resultado, intentos). Si se acaban: IntentosAgotados(ultimo_error, intentos)."""
    intentos, esperado, trans, venc = [], 0.0, 0, 0
    max_timeouts = reintentos_por_timeout() if max_timeouts is None else max(1, int(max_timeouts))
    # t1036s3512: si el llamador no pasa ritmo, 20 s (configurable) entre llamadas Argon, candado compartido.
    if ritmo is None:
        try:
            iv = float((config_llamadas() or {}).get('intervalo_entre_llamadas_s', 20) or 20)
        except (TypeError, ValueError):
            iv = 20.0
        if iv > 0:
            ritmo = Ritmo(Path(__file__).resolve().parent / '.ritmo', 'argon', iv)
    n = 0
    while True:
        n += 1
        if ritmo is not None: ritmo.esperar()
        try:
            r = llamada(n)
            intentos.append({'n': n, 'ok': True, 'hora': ahora()})
            return r, intentos
        except Exception as exc:
            c = clasificar_error(exc)
            fila = {'n': n, 'ok': False, 'clase': c['clase'], 'codigo': c['codigo'], 'cobro': c['cobro'], 'error': f'{type(exc).__name__}: {str(exc)[:200]}', 'hora': ahora()}
            intentos.append(fila)
            if c['clase'] == 'definitivo': raise IntentosAgotados(exc, intentos) from exc
            if c['clase'] == 'timeout':   # orden 81: un timeout SIEMPRE deja al menos 1 reintento (aunque --max-intentos sea 1)
                venc += 1
                if venc > max_timeouts: fila['sin_otro'] = f'{venc} timeouts'; raise IntentosAgotados(exc, intentos) from exc
                if n >= max_intentos + max_timeouts: raise IntentosAgotados(exc, intentos) from exc
            elif n >= max_intentos: raise IntentosAgotados(exc, intentos) from exc
            if c['clase'] == 'transitorio':
                trans += 1
                if trans > max_transitorios: raise IntentosAgotados(exc, intentos) from exc
            if not puede_otro(n, c):
                fila['sin_otro'] = 'sin presupuesto para otro intento'; raise IntentosAgotados(exc, intentos) from exc
            w = (float(config_llamadas().get('espera_tras_timeout_s', 10)) if c['clase'] == 'timeout'
                 else espera_reintento(exc, n, espera_base, espera_max, azar))
            if esperado + w > espera_total_max:
                fila['sin_otro'] = f'la espera total pasaría {espera_total_max}s'; raise IntentosAgotados(exc, intentos) from exc
            fila['espera_s'] = w; dormir(w); esperado += w
    raise AssertionError('inalcanzable')


# ------------------------------------------------------------------ ritmo entre procesos
class Ritmo:
    """Separación mínima entre llamadas al mismo modelo, compartida entre procesos (candado de archivo)."""

    def __init__(self, carpeta, modelo, intervalo_s, dormir=time.sleep, reloj=time.time):
        self.f = Path(carpeta) / f"ritmo_{re.sub(r'[^A-Za-z0-9._-]', '_', str(modelo))}.txt"
        self.intervalo, self.dormir, self.reloj = float(intervalo_s), dormir, reloj

    def esperar(self):
        if self.intervalo <= 0: return 0.0
        self.f.parent.mkdir(parents=True, exist_ok=True)
        with open(self.f, 'a+') as h:
            fcntl.flock(h, fcntl.LOCK_EX)
            try:
                h.seek(0)
                try: ult = float(h.read().strip() or 0)
                except ValueError: ult = 0.0
                w = max(0.0, ult + self.intervalo - self.reloj())
                if w > 0: self.dormir(w)
                h.seek(0); h.truncate(); h.write(str(self.reloj())); h.flush()
                return w
            finally:
                fcntl.flock(h, fcntl.LOCK_UN)


def num_env(nombre, defecto):
    try: return float(os.environ.get(nombre, defecto))
    except ValueError: return float(defecto)


# ---------------- Fase 4 (Ricardo resp. t261s798): avances de razonamiento en streaming, SOLO si el cubo lo pide ----------------
REGISTRO_STREAM = Path(__file__).resolve().parent / 'registros_argon_stream'
PENSAMIENTOS_OFF = Path(__file__).resolve().parent / 'argon_pensamientos.off'


def _transporte_pensando(AR, seg, silencio_s=None):
    """Como transporte_texto, pero pide include_thoughts=True: el stream manda resúmenes del razonamiento mientras piensa
    (la conexión no queda muda). El vigilante cuenta cada trozo (pensamiento o texto) como VIDA: «stream bloqueado» solo si pasan
    silencio_s sin ningún trozo; el tope total `seg` sigue igual. Deja registro por llamada (registros_argon_stream/AAAAMMDD.jsonl):
    response_id, versión del modelo, tokens (entrada/salida/pensamiento), primer trozo, trozos, y si hubo respuesta parcial."""
    silencio = float(silencio_s or seg)
    def vertex(prompt, modelo, nivel, max_out, json_out, adjuntos=None, esquema=None, reloj=time.monotonic):
        from google.genai import types
        import concurrent.futures, datetime as _dt
        c = AR._cliente()
        extra = {'response_mime_type': 'application/json'} if json_out else {}
        if esquema is not None: extra.update(response_mime_type='application/json', response_json_schema=AR.esquema_para_api(esquema))
        afc = types.AutomaticFunctionCallingConfig(disable=True)
        cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=nivel, include_thoughts=True), max_output_tokens=max_out,
                                          automatic_function_calling=afc, http_options=types.HttpOptions(timeout=int(seg * 1000)), **extra)
        t0 = reloj(); vida = {'ultimo': t0}; parcial = {'txt': ''}
        reg = {'inicio': _dt.datetime.now().astimezone().isoformat(timespec='seconds'), 'modelo': modelo, 'nivel': nivel, 'max_out': max_out,
               'tope_s': seg, 'silencio_max_s': silencio, 'chars_prompt': len(prompt or ''), 'primer_trozo_s': None, 'trozos': 0,
               'trozos_pensamiento': 0, 'chars_pensamiento': 0, 'chars_texto': 0, 'response_id': None, 'model_version': None,
               'uso': None, 'fin': None, 'estado': 'en_curso'}
        def _consumir():
            txt, u, fin = '', None, None
            for ch in c.models.generate_content_stream(model=modelo, contents=AR.contenidos(prompt, types, adjuntos), config=cfg):
                ahora = reloj(); vida['ultimo'] = ahora; reg['trozos'] += 1
                if reg['primer_trozo_s'] is None: reg['primer_trozo_s'] = round(ahora - t0, 1)
                reg['response_id'] = getattr(ch, 'response_id', None) or reg['response_id']
                reg['model_version'] = getattr(ch, 'model_version', None) or reg['model_version']
                if ahora - t0 > seg: raise LlamadaVencida(f'la llamada de texto pasó {seg:.0f} s (tope total)')
                if getattr(ch, 'prompt_feedback', None): reg['prompt_feedback'] = str(ch.prompt_feedback)[:800]
                if not ch.candidates: reg['trozo_sin_candidatos'] = str(ch)[:1500]
                for cand in (ch.candidates or [])[:1]:
                    for p in ((cand.content.parts if cand.content else None) or []):
                        if getattr(p, 'thought', False): reg['trozos_pensamiento'] += 1; reg['chars_pensamiento'] += len(p.text or '')
                        elif p.text: txt += p.text
                    if cand.finish_reason: fin = str(cand.finish_reason)
                parcial['txt'] = txt; reg['chars_texto'] = len(txt)
                if ch.usage_metadata: u = ch.usage_metadata
            tin = (u.prompt_token_count or 0) if u else 0
            tout = ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) if u else 0
            reg['uso'] = {'entrada': tin, 'salida': (u.candidates_token_count or 0) if u else 0, 'pensamiento': (u.thoughts_token_count or 0) if u else 0}
            reg['fin'] = fin
            return {'texto': txt, 'tokens_entrada': tin, 'tokens_salida': tout, 'fin': fin}
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='argon_txt_p'); fut = pool.submit(_consumir)
        try:
            while True:
                try:
                    r = fut.result(timeout=5); reg['estado'] = 'ok'; return r
                except concurrent.futures.TimeoutError:
                    ahora = reloj()
                    if ahora - t0 > seg + 2: raise LlamadaVencida(f'la llamada de texto pasó {seg:.0f} s (tope total; con avances)')
                    if ahora - vida['ultimo'] > silencio:
                        raise LlamadaVencida(f'la llamada de texto pasó {silencio:.0f} s sin ningún avance (stream bloqueado)')
        except BaseException as e:
            reg['estado'] = 'error'; reg['error'] = f'{type(e).__name__}: {str(e)[:300]}'; raise
        finally:
            pool.shutdown(wait=False)
            reg['duracion_s'] = round(reloj() - t0, 1); reg['respuesta_parcial'] = bool(parcial['txt']) and reg['estado'] != 'ok'
            try:
                REGISTRO_STREAM.mkdir(exist_ok=True)
                if reg['respuesta_parcial']:
                    pf = REGISTRO_STREAM / f"parcial_{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}.txt"; pf.write_text(parcial['txt'], encoding='utf-8'); reg['archivo_parcial'] = str(pf)
                with (REGISTRO_STREAM / f"{time.strftime('%Y%m%d')}.jsonl").open('a', encoding='utf-8') as fh: fh.write(json.dumps(reg, ensure_ascii=False, default=str) + '\n')
            except Exception:
                pass
    vertex.tope_s = seg; vertex.pensamientos = True
    return vertex
