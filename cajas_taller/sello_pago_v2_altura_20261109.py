#!/usr/bin/env python3
"""[v2 altura 9-nov-2026 — fase 2 motor, OK Ricardo t987s3315. Copia versionada; sello_pago.py v1 NO se tocó.]
Cambios v2: Maestro 02 v2 (estatura en METROS obligatoria + cabezas), cubo_fijo_v2_altura, la estatura OFICIAL del ADN sale de
trabajo/biblioteca/<canal>/personajes/personajes.json (si falta → STOP sin llamar), 1 solo intento (sin reintento automático),
tope US$0,75 por llamada, salida en trabajo/sello_pago_prueba_fase2_20261109/ (no pisa el sello_pago real), compara la altura devuelta (±2%).
sello_pago.py — LLAMADAS PAGAS de los SELLOS FIJOS (genérico: sin nombres de canal ni personajes).
inmi 2-nov-2026 (orden de Ricardo 17:02 Bogotá «ok gasta», tope total US$1,00).
  estado                                   gratis: compuerta, monto, gastado, quedan
  hoja  b64.{id,canal,refs:[..],estilo_img,extra}  --ok USD --aprobado QUIEN   imagen: hoja Fase 1 (Maestro 02)
  adn   b64.{id,canal,clase,imagenes:[..],extra}   --ok USD --aprobado QUIEN   texto+visión: ADN 5 bloques (Maestro 02 F2 / 03 / 04 / 05)
Reglas: compuerta cajas/HABILITAR_PAGO_ADN con el monto TOTAL; lo gastado = filas del ledger con id «taller-sello-» desde que
se abrió la compuerta (no cuenta «no_cobrado»); gastado + peor caso > monto → no se llama. Línea de ledger ANTES de cada
llamada (AR.registrar / AR.llamar). Máximo 1 reintento por elemento. El ADN se valida con el MISMO parse_ako de cubo_fijo;
sellar lo hace cubo_fijo sellar (nodo 4b), no este script."""
import sys, os, re, json, math, time, base64, datetime
from pathlib import Path
CAJAS = Path('/opt/myia-taller-n8n/cajas'); sys.path.insert(0, str(CAJAS))
GATE = CAJAS / 'HABILITAR_PAGO_ADN'
CF = CAJAS / 'cubo_fijo'; MA = CF / 'programa' / 'maestros_ako'
OUT = Path('/opt/myia-taller-n8n/trabajo/sello_pago_prueba_fase2_20261109')
PREF = 'taller-sello-'
TOPE_LLAMADA = 0.75; MAX_INTENTOS = 1          # v2: 1 intento, SIN reintento automático
TXT = {'max_out': 8192, 'min_out': 3072, 'tokens_imagen_peor_caso': 2240}
MAESTRO = {'personaje': '02_MAESTRO_PERSONAJE_HOJA_ADN_v2_altura_20261109.txt', 'objeto': '03_MAESTRO_OBJETOS.txt', 'poder': '03_MAESTRO_OBJETOS.txt',
           'escenario': '04_MAESTRO_ESCENARIOS.txt', 'estilo': '05_MAESTRO_ESTILO.txt'}
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{1,79}$')
# Conectado a n8n (inmi 2-nov-2026 17:45 Bogotá): corre como root vía sudo desde entrada_ssh.sh → solo imágenes dentro del taller.
IMG_OK = ('/opt/myia-taller-n8n/trabajo/', '/opt/myia-taller-n8n/cajas/FIJOS_TALLER/', '/opt/myia-taller-n8n/cajas/cubo_fijo/hojas/')
def ruta_ok(x):
    r = os.path.realpath(str(x))
    return r.startswith(IMG_OK) and os.path.splitext(r)[1].lower() in ('.png', '.jpg', '.jpeg', '.webp') and os.path.isfile(r)

def out(d, code=0): print(json.dumps(d, ensure_ascii=False)); sys.exit(code)
def b64(s):
    s = s[4:] if s.startswith('b64.') else s; s += '=' * (-len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(s).decode())
def rj(p): return json.load(open(p, encoding='utf-8'))

def _cubo():
    """parse_ako / canal_info / overrides EXACTOS de cubo_fijo.py (se toma el código hasta la parte de comandos)."""
    src = (CF / 'cubo_fijo_v2_altura_20261109.py').read_text(encoding='utf-8').split('\na = sys.argv[1:]', 1)[0]
    ns = {'__name__': 'cubo_fijo_lib'}; exec(compile(src, str(CF / 'cubo_fijo_v2_altura_20261109.py'), 'exec'), ns); return ns

# ---------------- compuerta y bolsa ----------------
def compuerta():
    if not GATE.is_file(): return None
    t = GATE.read_text(errors='replace'); m = re.search(r'\d+(?:\.\d+)?', t); d = re.search(r'desde=(\S+)', t)
    if not m or not d: return {'error': f'{GATE.name} sin monto o sin desde=ISO'}
    return {'monto': float(m.group()), 'desde': datetime.datetime.fromisoformat(d.group(1)), 'texto': t.strip()[:200]}

def gastado(AR_leer, desde):
    tot, filas = 0.0, []
    for r in AR_leer():
        if not str(r.get('id', '')).startswith(PREF): continue
        try: f = datetime.datetime.fromisoformat(r['fecha'])
        except Exception: continue
        if f.tzinfo is None: continue
        if f < desde or r.get('estado') == 'no_cobrado': continue
        u = float(r.get('costo_estimado_usd') or 0); tot += u
        filas.append({'id': r['id'], 'fecha': r['fecha'], 'modelo': r['modelo'], 'usd': u, 'estado': r['estado']})
    return round(tot, 4), filas

def _leer_ledger():
    import csv
    p = Path('/opt/myia-staging-arreglos-20261026/ledger/ledger_argon.csv')
    return list(csv.DictReader(p.open(newline='', encoding='utf-8'))) if p.exists() else []

def revisar(a, est):
    g = compuerta()
    if g is None: return None, f'pago cerrado: falta {GATE}. No se llamó a nada.'
    if g.get('error'): return None, g['error']
    if a.ok is None or not a.aprobado: return None, 'falta --ok USD y --aprobado QUIEN'
    if a.ok > g['monto'] + 1e-9: return None, f'--ok {a.ok} pasa el monto de la compuerta ({g["monto"]})'
    if est > TOPE_LLAMADA + 1e-9: return None, f'peor caso {est} > tope por llamada {TOPE_LLAMADA}'
    gs, _ = gastado(_leer_ledger, g['desde'])
    if gs + est > min(a.ok, g['monto']) + 1e-9: return None, f'gastado {gs} + peor caso {est} > {min(a.ok, g["monto"])}: no se llama'
    return g, None

# ---------------- app (ledger, Vertex) ----------------
def _app():
    import paso00_cadena as C
    C.bloquear_red(True)
    _A, _P, _PB, AR, FP, F = C.cargar_app(C.copiar_datos(), C.ruta_credencial())
    import llamada_segura as LS
    from google.genai import types
    return {'C': C, 'AR': AR, 'FP': FP, 'F': F, 'LS': LS, 'T': types}

def precios_texto(canal):
    import estilo_taller as ET
    cd = ET.canal_datos(canal) or {}
    sec = cd.get('paso00') or {}
    m, n = sec.get('argon_modelo'), sec.get('argon_nivel')   # del canal; nunca un valor por defecto
    if not m or not n: raise ValueError('el canal no tiene paso00.argon_modelo/argon_nivel')
    if str(ET.REPO) not in sys.path: sys.path.insert(0, str(ET.REPO))
    import precios_myia as PR
    pi, po = PR.tokens_en_fecha(m, time.strftime('%Y-%m-%d'))[:2]
    return m, n, float(pi), float(po)

def precio_imagen(modelo, talla):
    import estilo_taller as ET
    return ET.imagen_canal({'imagen_modelo': modelo, 'imagen_talla': talla})

def dimension_canal(canal):
    """t310u — GENÉRICO: «2D» o «3D» del estilo del canal (estilo_oficial.dimension: style_fijo.dimension o el estilo aprobado)."""
    try:
        import estilo_oficial as EO
        return EO.dimension(canal)['dimension']
    except Exception:
        return '2D'

def secciones_02():
    t = (MA / MAESTRO['personaje']).read_text(encoding='utf-8')
    rol = t[t.index('ROL Y OBJETIVO'):t.index('FASE 1:')].strip()
    f1 = t[t.index('FASE 1:'):t.index('FASE 2:')].strip(); f2 = t[t.index('FASE 2:'):].strip()
    return rol, f1, f2

def guardar(d, nombre, data):
    d.mkdir(parents=True, exist_ok=True); p = d / nombre
    (p.write_bytes if isinstance(data, bytes) else lambda x: p.write_text(x, encoding='utf-8'))(data); return p

# ---------------- HOJA (imagen) ----------------
def prompt_hoja(K, canal, d):
    rol, f1, _ = secciones_02(); ci = K['canal_info'](canal, d)
    f1 = re.sub(r'\b[23]D\b', dimension_canal(canal), f1, count=1)   # t310u: «Character Sheet 2D/3D» sale del estilo del canal (no del Maestro)
    t = K['llenar'](rol + '\n\n' + f1, ci)[0]
    n = len(d['refs'])
    t += (f"\n\nIMÁGENES ADJUNTAS: la{'s' if n > 1 else ''} primera{'s' if n > 1 else ''} {n} = referencia del cliente (identidad EXACTA: rostro, pelo, ropa, colores, accesorios). "
          "La ÚLTIMA imagen = imagen de estilo del canal: copia SOLO su técnica (render, materiales, luz, acabado); NO copies su personaje.")
    ov = K['overrides'](canal, None)
    if ov['prohibiciones']: t += '\nPROHIBIDO: ' + '; '.join(ov['prohibiciones'])
    if d.get('negativo'): t += '\n' + d['negativo']
    if d.get('extra'): t += '\nINDICACIÓN PARA ESTE PERSONAJE: ' + d['extra']
    return t

def hoja(a, d):
    K = _cubo(); canal, i = d['canal'], d['id']
    refs = [Path(x) for x in d['refs']] + [Path(d['estilo_img'])]
    for r in refs:
        if not ruta_ok(r): out({'ok': False, 'error': f'no existe o fuera del taller: {r}', 'llamadas_hechas': 0}, 1)
    I = precio_imagen(d.get('modelo') or 'gemini-3-pro-image', d.get('talla') or '2K')
    est = round(I['usd_por_imagen'] + I['usd_referencia_extra'] * max(0, len(refs) - 1), 4)
    g, err = revisar(a, est)
    if err: out({'ok': False, 'error': err, 'peor_caso': est, 'llamadas_hechas': 0})
    pr = prompt_hoja(K, canal, d); dd = OUT / canal / i; guardar(dd, 'pedido_hoja.txt', pr)
    X = _app(); AR, T, LS = X['AR'], X['T'], X['LS']; cli = AR._cliente()
    partes = [T.Part.from_bytes(data=r.read_bytes(), mime_type='image/png' if r.suffix.lower() == '.png' else 'image/jpeg') for r in refs] + [T.Part.from_text(text=pr)]
    cfg = T.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'], image_config=T.ImageConfig(aspect_ratio=d.get('aspecto') or '16:9', image_size=I['talla']),
                                  http_options=T.HttpOptions(timeout=LS.timeout_ms('imagen')))
    hechas, st = [], time.strftime('%Y%m%d-%H%M%S')
    for k in range(1, MAX_INTENTOS + 1):
        if k > 1:
            _, err = revisar(a, est)
            if err: hechas.append({'intento': k, 'no_llamado': err}); break
        lid = f'{PREF}hoja-{i}-{st}-i{k}'
        try: AR.registrar(lid, f"{I['modelo']} {I['talla']}", est, f'sello hoja Fase 1 Maestro 02 {i} intento {k} (aprobado {a.aprobado})', tipo='imagen', ok_usd=est, tope_usd=TOPE_LLAMADA)
        except Exception as e: hechas.append({'intento': k, 'no_llamado': f'{type(e).__name__}: {str(e)[:200]}'}); break
        try: r = cli.models.generate_content(model=I['modelo'], contents=[T.Content(role='user', parts=partes)], config=cfg)
        except Exception as e:
            AR.marcar(lid, LS.estado_fallo(e), est, ''); hechas.append({'intento': k, 'ledger': lid, 'error': f'{type(e).__name__}: {str(e)[:200]}'}); time.sleep(10); continue
        data = next((pt.inline_data.data for c in (r.candidates or []) for pt in ((c.content.parts or []) if c.content else []) if pt.inline_data and pt.inline_data.data), None)
        if not data: AR.marcar(lid, 'sin_imagen', est, ''); hechas.append({'intento': k, 'ledger': lid, 'error': 'sin imagen'}); continue
        p = guardar(dd, f'hoja_fase1_{st}_i{k}.png', data); AR.marcar(lid, 'ok', est, str(p))
        import hashlib
        hechas.append({'intento': k, 'ledger': lid, 'usd': est, 'hoja': str(p), 'sha256': hashlib.sha256(data).hexdigest()})
        out({'ok': True, 'id': i, 'hoja': str(p), 'intentos': hechas, 'usd': round(sum(h.get('usd', 0) for h in hechas) + est * sum(1 for h in hechas if h.get('error')), 4)})
    out({'ok': False, 'id': i, 'error': 'hoja no salió', 'intentos': hechas})

# ---------------- ADN (texto + visión) ----------------
INSTR = {'personaje': 'Responde SOLO el documento de la FASE 2 (no generes imagen), en español, sin preámbulo: empieza directo con «1. Ficha Antropométrica:» y usa exactamente los 5 títulos numerados del Maestro (1. Ficha Antropométrica, 2. Fisonomía Facial y Cabello, 3. Paleta de Expresiones, 4. Vestuario por Capas, 5. Reglas de Giro). En el bloque 3 nombra las 5 emociones: Normal, Feliz, Nervioso, Enojado, Triste. No escribas marcadores [GAP]. La PRIMERA imagen adjunta es la hoja de modelo (Fase 1) y manda; las demás son la referencia del cliente.',
         'estilo': 'Responde SOLO el documento, sin preámbulo: empieza directo con «1. Estilo de Línea y Entintado (Lineart):» y usa exactamente los 5 títulos numerados del Maestro. Bloques 1 a 4 en español; el bloque 5 (Prompt Compacto de Inyección) en INGLÉS, un solo párrafo de 3 a 4 líneas. Describe solo la técnica visual (no el personaje ni la historia). No escribas marcadores [GAP].',
         'objeto': 'Responde SOLO el documento, en español, sin preámbulo, con los 5 títulos numerados exactos del Maestro. El bloque 5 es un solo párrafo de inyección. No escribas marcadores [GAP].'}
INSTR['poder'] = INSTR['escenario'] = INSTR['objeto']

def texto_fijo(clase):
    if clase == 'personaje':
        rol, _, f2 = secciones_02(); base = rol + '\n\n' + f2
    else: base = (MA / MAESTRO[clase]).read_text(encoding='utf-8')
    return base.strip() + '\n\n' + INSTR[clase]

TABLA = '/opt/myia-taller-n8n/trabajo/biblioteca/{canal}/personajes/personajes.json'
def altura_oficial(K, canal, i):
    """(metros|None, fuente) — v2: SOLO la tabla del ADN del canal (personajes.json). Nunca se inventa."""
    p = Path(TABLA.format(canal=canal))
    if not p.is_file(): return None, f'no existe {p}'
    t = rj(p); _k, e, _ = K['find'](K['catalogo'](), i, canal)
    cand = {i, i.split('gdc-', 1)[-1]} | set((e or {}).get('ids_canal') or [])
    for x in t.get('personajes') or []:
        if x.get('id') in cand or cand & set(x.get('ids_mapa') or []):
            return (float(x['altura_m']) if x.get('altura_m') is not None else None), f"{p}#{x['id']} ({x.get('altura_fuente')})"
    if any(f.get('id') in cand for f in t.get('faltan_datos') or []): return None, f'{p}: FALTA_DATO'
    return None, f'{p}: no está'

def adn(a, d):
    K = _cubo(); canal, i, cl = d['canal'], d['id'], K['ncl'](d.get('clase') or 'personaje')
    h_of, h_fuente = (altura_oficial(K, canal, i) if cl == 'personaje' else (None, None))
    if cl == 'personaje' and h_of is None:
        out({'ok': False, 'id': i, 'estado': 'STOP_FALTA_ALTURA_ADN', 'error': f'sin estatura oficial del ADN: {h_fuente}. No se llama a Argon, no se inventa.', 'llamadas_hechas': 0, 'usd': 0})
    if cl not in MAESTRO: out({'ok': False, 'error': f'clase {cl}'}, 1)
    imgs = [Path(x) for x in d.get('imagenes') or []]
    if cl != 'personaje':   # orden Ricardo 2-nov-2026 (genérico): un objeto/poder/escenario nunca lleva la foto original de un personaje
        _c = K['catalogo'](); _e = K['find'](_c, i, canal)[1] or {'id': i}
        _ok, _av = K['refs_no_personaje'](_c, _e, [str(x) for x in imgs])
        if any(K['foto_de_personaje'](str(x), _c) for x in imgs):
            out({'ok': False, 'error': 'referencia no válida para un objeto: ' + '; '.join(_av) + ' (usa la imagen pintada por el paso 00 o la hoja aprobada)', 'llamadas_hechas': 0}, 1)
        imgs = [Path(x) for x in _ok]
    if not imgs or not all(ruta_ok(x) for x in imgs): out({'ok': False, 'error': 'faltan imágenes', 'llamadas_hechas': 0}, 1)
    _vars = {**K['canal_info'](canal, d), **({'ALTURA_OFICIAL_M': f'{h_of:.2f}'} if h_of is not None else {})}
    fijo_t, _sin = K['llenar'](texto_fijo(cl), _vars)
    if 'ALTURA_OFICIAL_M' in _sin: out({'ok': False, 'id': i, 'error': 'el Maestro quedó sin ALTURA_OFICIAL_M', 'llamadas_hechas': 0}, 1)
    pr = fijo_t + (('\n\nINDICACIÓN PARA ESTE ELEMENTO: ' + d['extra']) if d.get('extra') else '')
    m, n, pi, po = precios_texto(canal)
    ent = (math.ceil(len(pr) / 3) + TXT['tokens_imagen_peor_caso'] * len(imgs)) * pi / 1e6
    mo = TXT['max_out']; g0 = compuerta()
    if g0 and not g0.get('error') and a.ok:   # si el peor caso no cabe en lo que queda, se baja max_out (nunca bajo MIN_OUT)
        q = min(a.ok, g0['monto']) - gastado(_leer_ledger, g0['desde'])[0] - ent
        if q * 1e6 / po < mo: mo = max(TXT['min_out'], int(q * 1e6 / po) // 256 * 256)
    est = round(ent + mo * po / 1e6, 4)
    g, err = revisar(a, est)
    if err: out({'ok': False, 'error': err, 'peor_caso': est, 'llamadas_hechas': 0})
    X = _app(); AR, FP, LS = X['AR'], X['FP'], X['LS']
    partes = {'texto': fijo_t, 'esquema': 'texto libre: 5 bloques numerados con los títulos del Maestro de Ako (lo revisa parse_ako de cubo_fijo)', 'modelo': m, 'nivel': n, 'max_out': mo, 'max_rondas': 1, 'json_out': False}
    fijo = {'paso': f'sello_adn_{cl}_{FP.sha_total(partes)[:10]}', 'partes': partes, 'fragmentos': [fijo_t]}
    X['C'].registrar_taller(fijo, FP, X['F'])
    dd = OUT / canal / i; guardar(dd, f'pedido_adn_{cl}.txt', pr); st = time.strftime('%Y%m%d-%H%M%S'); hechas = []
    for k in range(1, MAX_INTENTOS + 1):
        if k > 1:
            _, err = revisar(a, est)
            if err: hechas.append({'intento': k, 'no_llamado': err}); break
        lid = f'{PREF}adn-{i}-{st}-i{k}'; sal = dd / f'adn_{cl}_{st}_i{k}.txt'
        try:
            r = AR.llamar(lid, pr, str(sal), est, f'sello ADN {cl} {MAESTRO[cl][:2]} {i} intento {k} (aprobado {a.aprobado})', transporte=LS.transporte_texto(AR), modelo=m, nivel=n,
                          max_out=mo, json_out=False, adjuntos=[str(x) for x in imgs], fijo=fijo, cotizacion=AR.cotizacion(est, modelo=m), ok_usd=est, tope_usd=TOPE_LLAMADA)
        except Exception as e:
            st_l = next((x.get('estado') for x in AR._leer() if x.get('id') == lid), None)
            if st_l is None: hechas.append({'intento': k, 'no_llamado': f'{type(e).__name__}: {str(e)[:300]}'}); break
            if LS.es_timeout(e): AR.marcar(lid, 'timeout', est, '')
            hechas.append({'intento': k, 'ledger': lid, 'error': f'{type(e).__name__}: {str(e)[:200]}'}); time.sleep(10); continue
        t = (r.get('texto') or '').strip(); pa = K['parse_ako'](t, cl)
        ha = pa.get('altura_m'); dif = (round((ha / h_of - 1) * 100, 2) if (ha and h_of) else None)
        hechas.append({'intento': k, 'ledger': lid, 'usd': r.get('usd'), 'fin': str(r.get('fin')), 'salida': str(sal), 'status': pa['status'], 'fails': pa['fails'],
                       'altura_oficial_m': h_of, 'altura_fuente': h_fuente, 'altura_argon_m': ha, 'cabezas_argon': pa.get('cabezas'), 'diferencia_pct': dif,
                       'altura_ok': (dif is not None and abs(dif) <= 2.0)})
        if pa['status'] == 'PASS_SELLABLE':
            out({'ok': True, 'id': i, 'clase': cl, 'salida': str(sal), 'intentos': hechas, 'nota': 'v2 prueba: NO se sella (sellar es cubo_fijo sellar)'})
    out({'ok': False, 'id': i, 'clase': cl, 'error': 'ADN no pasa el formato de Ako', 'intentos': hechas})

def estado():
    g = compuerta()
    if g is None: out({'ok': True, 'pago': 'CERRADO', 'compuerta': str(GATE), 'existe': False})
    if g.get('error'): out({'ok': False, 'error': g['error']})
    gs, filas = gastado(_leer_ledger, g['desde'])
    out({'ok': True, 'pago': 'ABIERTO', 'monto': g['monto'], 'desde': g['desde'].isoformat(), 'gastado': gs, 'quedan': round(g['monto'] - gs, 4), 'filas': filas})

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('op', choices=['estado', 'hoja', 'adn']); ap.add_argument('pedido', nargs='?')
    ap.add_argument('--ok', type=float); ap.add_argument('--aprobado')
    a = ap.parse_args()
    if a.op == 'estado': estado()
    d = b64(a.pedido or '')
    if a.op == 'adn' and d.get('formato') == 'ako_json/v1':
        os.execv('/opt/myia-motor-v9/avance06_20261107/entrega/codigo/puente_json.sh', ['puente_json.sh'] + sys.argv[1:])
    if not ID.match(str(d.get('id', ''))) or not ID.match(str(d.get('canal', ''))): out({'ok': False, 'error': 'id/canal inválido'}, 1)
    (hoja if a.op == 'hoja' else adn)(a, d)
