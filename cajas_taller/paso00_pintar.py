#!/usr/bin/env python3
"""MYIA · Taller n8n · Caja 4a5 = PINTAR escenarios con Nano Banana (orden 59; preparada en orden 63, pt446u; raíz corregida en orden 65, pt455u).
Staging 213 SOLAMENTE. Se llama así:   paso00_cadena.py pintar cotizar|correr --canal C --capitulo N [--solo ids] [--ok USD --aprobado QUIEN]

Reglas (Ricardo, orden 59, pt446u y pt455u):
- Por escenario: 1 imagen BASE pintada UNA vez sobre el render de SU cámara del molde de Blender (4a2) (base.camara.render).
- VISTAS (orden 65): el MISMO lugar desde OTRA cámara del mismo molde, para cada zona del guion que la base no muestra.
  Se pintan sobre el render de esa cámara + la base ya pintada (mismos materiales, luz y estilo).
- Cada VARIANTE es una EDICIÓN de la imagen donde ocurre (en_vistas: la base o una vista), «cambia SOLO …».
- Estilo (orden 65): el código pega al final de CADA pedido el estilo fijo COMPLETO del canal (estilo_taller.resolver: recupera el texto
  entero aunque la ficha lo tenga cortado a 480) + la regla «técnica sí, contenido adaptado al lugar». El modelo no lo copia.
- Modelo y talla (orden 65): los del CANAL (channels.data.imagen_modelo / imagen_talla), igual que web/myia_imagen.py. Precio de
  precios_myia.json (imagen.modelos[modelo][talla] + referencia_extra por cada imagen de entrada extra); si el modelo tiene tramo por
  tokens vigente se toma el mayor de los dos. Sin modelo, talla o precio → no se cotiza ni se llama.
- Personajes: NUNCA por texto. Las imágenes de escenario van vacías; si un prompt nombra a un personaje del catálogo, NO se manda.
- Ledger ANTES de cada llamada (myia_argon.registrar, mismo ledger_argon.csv, tipo «imagen») y marcar después con el costo.
- PISTA INMI (2026-10-29): orden 68 — intentos ACOTADOS (llamada_segura.py), nunca silenciosos: cada intento con SU línea de ledger
  ANTES de llamar (…-i2, -i3, -i4). 429 → no_cobrado (no cuenta en lo gastado) y espera Retry-After/retryDelay o 20-40-80 s (+azar),
  hasta --max-intentos (4). Otro error → error_posible_cobro (cuenta el peor caso), 1 reintento si alcanza --ok. 400/403/404 no se repite.
  Una imagen a la vez y pausa entre llamadas (TALLER_PAUSA_IMAGEN_S, 12 s, compartida entre procesos). Todo queda en «intentos».
  --solo-fallidos: cotiza/pinta SOLO lo que falló (o se saltó por falta de su base) en la última corrida.
- Tope por llamada US$0,75. Corrida: se para ANTES de una llamada que haría pasar lo gastado de --ok (orden 65: tope total).
- correr está CERRADO sin cajas/HABILITAR_PAGO_4A5, y --ok no puede pasar el monto escrito en ese archivo (orden 65).
- Biblioteca (orden 62): una base que ya está en la biblioteca, o ya pintada con el MISMO pedido, NO se vuelve a pintar.
- cotizar: GRATIS, sin red, sin app, no toca el ledger.
- PISTA INMI (2026-10-29): orden 72 (Ricardo, pt251u) — el MISMO motor pinta 4b2 (objetos de la historia) y 4c2 (objetos del lugar):
  --caja 4a5|4b2|4c2 (defecto 4a5). Código compartido, no copias: plan propio por caja (plan / plan_objetos) y lo demás igual
  (una imagen a la vez, 12 s entre imágenes, 429 con espera y no_cobrado, ledger por intento, --solo-fallidos, tope, guarda).
  Objetos: 1 imagen BASE por objeto (prompt_imagen de 4b1/4c1 + negativo + estilo fijo del canal, objeto solo en fondo neutro,
  sin personas) y 1 EDICIÓN de esa base por cada estado (prompts_por_estado). Solo se pinta un objeto cuya investigación el CÓDIGO
  da por buena (un registro por id, con sus campos); si 4b1/4c1 vino incompleta o falta → no se pinta y se dice por qué.
  correr cerrado sin cajas/HABILITAR_PAGO_4B2 / HABILITAR_PAGO_4C2 (no existen: nadie aprobó pagar objetos todavía).
- PISTA INMI (2026-10-29): orden 75 (Ricardo: «que no se generen los protagonistas») — GUARDA DE PERSONAJES en 4a5/4b2/4c2 (personajes.py):
  antes de pintar, cada pedido se revisa con las palabras de personajes_config.json (figura / ropa puesta, varios idiomas; no cuentan
  las negaciones). Si lo que se pide pintar ES una figura o ropa puesta → NO se pinta (saltar «personaje: …») y se dice a qué versión
  del mapa del paso 00 corresponde. Si es un objeto MEZCLADO → se pinta solo la parte que es objeto (se quitan esas frases).
  Imágenes marcadas en <carpeta>/NO_USAR.json no se borran, pero nunca se adjuntan como referencia. Estos cubos NUNCA adjuntan
  personajes: costo extra US$0 (las tomas con personaje usan personajes.refs_para).
"""
import os, re, sys, json, math, time, argparse, threading, struct, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

CAJAS = Path('/opt/myia-taller-n8n/cajas')
TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
REPO = Path('/opt/myia-staging-arreglos-20261026/repo')
GUARDA = CAJAS / 'HABILITAR_PAGO_4A5'
TOPE_LLAMADA = 0.75
MARGEN_PENSAMIENTO = 2000      # solo si el modelo cobra por tokens (tramo): texto/razonamiento que puede devolver
PARALELO = 1   # PISTA INMI (2026-10-29): orden 68 — una a la vez (con 2 hubo 5 × 429 en la orden 66). Antes: orden 65, 2
PAUSA_IMAGEN_S = 12   # orden 68: separación mínima entre llamadas de imagen (TALLER_PAUSA_IMAGEN_S); calibrar con prueba paga
MAX_INTENTOS = 4
IMG_OUT = 'ramas/imagenes/4a5'
SIN_PERSONAS = ('No people, no characters, no creatures, no animals in this image: it is an empty set. '
                'Characters are added later from their own reference images.')
GUIA_MOLDE = 'Reference image 1 is the 3D mold render of this location from this camera: follow it exactly for layout, camera angle and proportions; paint over it.'
GUIA_VISTA = ('Reference image 1 is the 3D mold render of this SAME location from a NEW camera: follow it exactly for camera, layout and proportions. '
              'Reference image 2 is the already painted image of this same room: copy its materials, colors, furniture design, light and painting style exactly. '
              'Same room, same style; only the camera changes.')
GUIA_EDICION = 'Reference image 1 is the painted image of this same location from this camera: keep everything identical except the listed changes.'
# PISTA INMI (2026-10-29): orden 72 — objetos 4b2/4c2
SOLO_OBJETO = ('Single object only, alone and complete, centered on a pure white (#FFFFFF) studio background, soft studio light, clear scale. '
               'No people, no hands, no characters, no creatures, no text, no letters, no logos.')
GUIA_ESTADO = ('Reference image 1 is this SAME catalog object already painted in its base look: keep its identity, proportions, materials, colors '
               'and painting style; paint it in the state described below and change only what that state needs.')
# t849u/t850u: ONE model/turnaround sheet per object (all views+states on one white image); no utilería; stop before 4a5
HOJA_MODELO_OBJETO = (
    'OBJECT MODEL SHEET / TURNAROUND: paint ONE pure white (#FFFFFF) studio image that is a model sheet of THIS SINGLE object only. '
    'Like a character turnaround sheet: arrange multiple clear panels of the SAME object on that one white background — '
    'front, three-quarter, side, back, and every distinct state listed below. '
    'Identity, proportions, materials, colors and painting style stay identical across panels; only pose/state changes. '
    'No other objects, no people, no hands, no characters, no environment, no scenery, no props besides this object, '
    'no invented text/logos. Soft studio light. Style is fixed by the channel block below.'
)
CLASE_DE_INV_PINTAR = {'inv_obj_historia': 'personaje', 'inv_obj_lugar': 'escenario'}  # utilería excluded (t849u)

def clase_objeto_pintar(obj):
    """Canonical class for 4b2/4c2 filter. Compat with old tipo historia/lugar."""
    if not isinstance(obj, dict):
        return ''
    c = (obj.get('clase') or '').strip()
    if c in ('utileria', 'escenario', 'personaje'):
        return c
    t = (obj.get('tipo') or '').strip()
    if t == 'historia':
        due = (obj.get('dueno_id') or '').strip()
        return 'personaje' if due and due not in ('', 'ninguno', 'falta', 'nadie', 'none', 'null') else 'escenario'
    if t == 'lugar':
        return 'escenario'
    if t in ('utileria', 'escenario', 'personaje'):
        return t
    return c or t

CAJAS_PINTAR = {   # orden 72: una entrada por caja que pinta; el motor es el mismo
    '4a5': {'guarda': 'HABILITAR_PAGO_4A5', 'out': 'ramas/imagenes/4a5', 'plan': 'plan', 'que': 'escenarios'},
    '4b2': {'guarda': 'HABILITAR_PAGO_4B2', 'out': 'ramas/imagenes/4b2', 'plan': 'plan_objetos', 'que': 'objetos de la historia',
            'inv': 'inv_obj_historia', 'cubo_inv': '4b1', 'tipo': 'historia'},
    '4c2': {'guarda': 'HABILITAR_PAGO_4C2', 'out': 'ramas/imagenes/4c2', 'plan': 'plan_objetos', 'que': 'objetos del lugar',
            'inv': 'inv_obj_lugar', 'cubo_inv': '4c1', 'tipo': 'lugar'},
}
def guarda_de(caja): return GUARDA if caja == '4a5' else CAJAS / CAJAS_PINTAR[caja]['guarda']   # 4a5: GUARDA (las pruebas la cambian)
def out_de(caja): return IMG_OUT if caja == '4a5' else CAJAS_PINTAR[caja]['out']
def plan_de(caja): return globals()[CAJAS_PINTAR[caja]['plan']]   # se busca al llamar (las pruebas lo cambian)
RATIOS = {'1:1': 1, '16:9': 16 / 9, '9:16': 9 / 16, '4:3': 4 / 3, '3:4': 3 / 4, '3:2': 1.5, '2:3': 2 / 3, '21:9': 21 / 9}

if str(CAJAS) not in sys.path: sys.path.insert(0, str(CAJAS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo_taller as ET
import llamada_segura as LS   # PISTA INMI (2026-10-29): orden 68
import personajes as PJ   # PISTA INMI (2026-10-29): orden 75 — guarda de personajes (genérica)

def ahora(): return time.strftime('%Y-%m-%dT%H:%M:%S%z')

def carpeta(canal, capitulo):
    b = TRABAJO / canal
    ds = sorted(b.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(b.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None

def leer(f):
    f = Path(f)
    if not f.is_file(): return None
    t = f.read_text(encoding='utf-8').strip()
    try: return json.loads(t[t.find('{'):t.rfind('}') + 1])
    except Exception: return None

def _pr():
    if str(REPO) not in sys.path: sys.path.insert(0, str(REPO))
    import precios_myia as PR
    return PR

def tramo(m, talla):
    """Tramo por tokens del modelo si existe y está vigente (p. ej. gemini-3-pro-image). None si el modelo cobra precio fijo por imagen."""
    PR = _pr()
    try: t = PR.imagen_tokens_en_fecha(m, time.strftime('%Y-%m-%d'))
    except Exception: return None
    try:
        return {'entrada': float(t['entrada']), 'salida_texto': float(t['salida_texto']), 'salida_imagen': float(t['salida_imagen']),
                'tok_img_in': int(t.get('tokens_imagen_entrada') or 560), 'tok_img_out': int(t['tokens_imagen_salida'][talla]),
                'fuente': t.get('fuente'), 'vigente_desde': t.get('vigente_desde')}
    except Exception: return None

def precio_llamada(I, T, chars, n_img):
    """Peor caso de UNA llamada: precio fijo del canal (+ referencia_extra por cada imagen extra) y, si hay tramo por tokens, el mayor."""
    fijo = I['usd_por_imagen'] + I['usd_referencia_extra'] * max(0, n_img - 1)
    if not T: return round(fijo, 4)
    tok = (math.ceil(chars / 3) + n_img * T['tok_img_in']) * T['entrada'] / 1e6 + T['tok_img_out'] * T['salida_imagen'] / 1e6 + MARGEN_PENSAMIENTO * T['salida_texto'] / 1e6
    return round(max(fijo, tok), 4)

def costo_real(I, T, um, n_img):
    """Con tramo: lo que devuelve Google (usage_metadata). Sin tramo: el precio fijo de la lista (como cobra la app). None si no hay datos."""
    if not T: return round(I['usd_por_imagen'] + I['usd_referencia_extra'] * max(0, n_img - 1), 4)
    if um is None: return None
    pin = getattr(um, 'prompt_token_count', None) or 0
    img = txt = 0
    for d in (getattr(um, 'candidates_tokens_details', None) or []):
        mod = str(getattr(d, 'modality', '')).upper()
        if 'IMAGE' in mod: img += d.token_count or 0
        else: txt += d.token_count or 0
    if not (img or txt): img = getattr(um, 'candidates_token_count', 0) or 0
    txt += getattr(um, 'thoughts_token_count', 0) or 0
    return round(pin * T['entrada'] / 1e6 + img * T['salida_imagen'] / 1e6 + txt * T['salida_texto'] / 1e6, 4)

def uso(um):
    if um is None: return None
    return {k: getattr(um, k, None) for k in ('prompt_token_count', 'candidates_token_count', 'thoughts_token_count', 'total_token_count')}

def aspecto(png, canal_aspect=None):
    if canal_aspect in RATIOS: return canal_aspect
    try:
        b = Path(png).read_bytes()[:24]; w, h = struct.unpack('>II', b[16:24]); r = w / h
        return min(RATIOS, key=lambda k: abs(RATIOS[k] - r))
    except Exception: return '16:9'

def nombres_personajes(base):
    cat = (base or {}).get('catalogo_oficial') or {}
    out = set()
    for x in cat.get('personajes', []) or []:
        for k in ('id', 'nombre', 'personaje_id'):
            v = str(x.get(k) or '').strip()
            if len(v) >= 3: out.add(v)
        for f in x.get('formas', []) or []:
            if isinstance(f, dict) and (f.get('forma_id') or f.get('id')): out.add(str(f.get('forma_id') or f.get('id')))
    return out

def personaje_en_texto(txt, nombres):
    return sorted(n for n in nombres if re.search(r'(?<![\w-])' + re.escape(n) + r'(?![\w-])', txt, re.I))

def img_obj(D, ref):
    sub = {'objeto_4b2': 'ramas/imagenes/4b2', 'objeto_4c2': 'ramas/imagenes/4c2'}.get(ref.get('tipo'))
    if not sub: return None
    if ref.get('id') in PJ.no_usar(D, sub): return None   # orden 75: una imagen marcada «no usar» nunca va como referencia
    for ext in ('.png', '.jpg', '.webp'):
        f = D / sub / f"{ref.get('id')}{ext}"
        if f.is_file(): return f
    return None

def quitar_estilo(txt, est):
    """Si el prompt ya trae el texto del estilo (respuestas viejas que lo copiaban, a veces cortado), se quita: el código lo pega COMPLETO una vez."""
    t = str(txt or '')
    for cab in ([est['descripcion_en'][:60]] if est else []):
        k = t.find(cab)
        if k > 0: t = t[:k].rstrip()
    return t

def validar_escenario(x, D):
    """orden 65 (misma regla en 4a4 unir y en 4a5): vistas con cámara REAL del molde, en_vistas válidos, zonas del guion cubiertas.
    Corrige en el sitio lo que no se puede usar (se aparta con aviso) y devuelve la lista de avisos."""
    eid = x.get('escenario_id'); md = Path(D) / 'ramas' / 'moldes' / str(eid); av = []
    b = x.get('base') if isinstance(x.get('base'), dict) else {}
    rb = str((b.get('camara') or {}).get('render') or '')
    if x.get('tiene_molde_blender') and rb and not (md / rb).is_file(): av.append(f'{eid}: la base pide la cámara {rb} y ese render no existe en el molde')
    vs, ids = [], {'base'}
    for v in x.get('vistas') or []:
        if not isinstance(v, dict): continue
        vid = str(v.get('vista_id') or ''); r = str((v.get('camara') or {}).get('render') or '')
        if not re.fullmatch(re.escape(str(eid)) + r'__vista\d+', vid) or vid in ids:
            av.append(f'{eid}: vista con id no válido o repetido «{vid}» → se aparta'); continue
        if not r or not (md / r).is_file():
            av.append(f'{eid}: {vid} pide la cámara «{r}» y ese render no existe en el molde → se aparta (necesita cámara nueva en 4a1/4a2)'); continue
        if r == rb: av.append(f'{eid}: {vid} usa la MISMA cámara que la base ({r}); se pinta igual, revisa si sobra')
        ids.add(vid); vs.append(v)
    x['vistas'] = vs
    for q in x.get('variantes') or []:
        ev = [('base' if e == eid else e) for e in (q.get('en_vistas') or []) if isinstance(e, str)]
        ok = [e for e in dict.fromkeys(ev) if e in ids]
        if not ok:
            av.append(f"{eid}: {q.get('variante_id')} sin en_vistas válido ({ev}) → se edita la base"); ok = ['base']
        q['en_vistas'] = ok
    falt = [str(c.get('zona') or '') for c in (x.get('camaras_faltantes') or []) if isinstance(c, dict)]
    for z in ((x.get('analisis') or {}).get('zonas_del_guion') or []):
        if not isinstance(z, dict): continue
        cp = str(z.get('cubierta_por') or '')
        if cp == eid: cp = 'base'
        if cp == 'camara_faltante':
            av.append(f"{eid}: la zona «{z.get('zona')}» (escenas {z.get('escenas')}) no tiene cámara en el molde → no se pinta; hace falta cámara nueva en 4a1/4a2"
                      + ('' if z.get('zona') in falt else ' (y no está en camaras_faltantes)'))
        elif cp not in ids:
            av.append(f"{eid}: la zona «{z.get('zona')}» dice cubierta_por «{cp}», que no existe → zona SIN cubrir")
    if not ((x.get('analisis') or {}).get('zonas_del_guion')): av.append(f'{eid}: respuesta sin analisis.zonas_del_guion (formato anterior a la orden 65)')
    return av

def guarda(D, mp, iid, texto, nombre=None):
    """PISTA INMI (2026-10-29): orden 75 — (texto, saltar, info). Bloquea figuras o ropa puesta; parte los objetos mezclados."""
    g = PJ.revisar_pedido(iid, texto, mp, nombre)
    if not g: return texto, None, None
    info = {'id': iid, 'accion': g['accion'], 'motivo': g['motivo'], 'frases': [x['frase'] for x in g['golpes']][:4],
            'version_del_mapa': [f"{v['personaje']} – {v['version']}" for v in g.get('vinculo') or []]}
    if g['accion'] == 'partir': return g['texto'], None, info
    return texto, 'personaje: ' + g['motivo'], info

def huella(texto, imgs, I):
    return hashlib.sha256(json.dumps([texto, [Path(i).name if not str(i).startswith('@') else i for i in imgs], I['modelo'], I['talla']]).encode()).hexdigest()[:16]

def ya_pintada(D, nombre, h, caja='4a5'):
    f = D / out_de(caja) / f'{nombre}.png'
    if not f.is_file(): return None
    j = leer(f.with_suffix('.json')) or {}
    return 'ya_pintada' if j.get('huella') == h else None   # otro pedido (otro estilo, otra cámara, otro modelo) → se vuelve a pintar

def _resp_valida(D, nombre):
    """PISTA INMI (2026-10-29): orden 68 — respuesta de un pedido 4a4 SOLO si resultados dice que sirve (ok con JSON válido, o
    «reparado» aplicado con OK → su .reparado.json). Un JSON roto o un .reparado.json sin aplicar NO se pinta."""
    r = leer(D / 'resultados' / f'{nombre}.json') or {}   # orden 69: «incompleto» (faltan cámaras) tampoco se pinta
    if r.get('estado') == 'ok' and r.get('json_valido') is not False: return leer(D / 'respuestas' / f'{nombre}.json')
    if r.get('estado') == 'reparado': return leer(D / 'respuestas' / f'{nombre}.reparado.json')
    return None

def _leer_4a4(D):
    """PISTA INMI (2026-10-29): orden 73 — la unión (prompts_escenarios.json) es la base, pero un pedido 4a4 por escenario VÁLIDO y más
    nuevo que la unión (un rehecho con --solo, que no se une mientras otro siga incompleto) la reemplaza para ese escenario."""
    fu = D / 'respuestas' / 'prompts_escenarios.json'
    p4 = leer(fu)
    base = p4.get('escenarios') if isinstance(p4, dict) and isinstance(p4.get('escenarios'), list) else None
    t0 = fu.stat().st_mtime if base else 0
    regs = {x['escenario_id']: x for x in (base or []) if isinstance(x, dict) and x.get('escenario_id')}
    fs = [f for f in (D / 'respuestas').glob('prompts_escenarios_*.json') if not f.name.endswith('.reparado.json')
          and (f.stem.startswith('prompts_escenarios__') or re.fullmatch(r'prompts_escenarios_g\d+de\d+(_solo(_[0-9a-f]+)?)?', f.stem))]
    for f in sorted(fs, key=lambda f: f.stat().st_mtime):   # prueba barata (4a4 --solo / por escenario): pedidos sueltos ya hechos y VÁLIDOS
        rf = D / 'resultados' / f'{f.stem}.json'
        if base and max(f.stat().st_mtime, rf.stat().st_mtime if rf.exists() else 0) <= t0: continue   # ya está en la unión
        for x in ((_resp_valida(D, f.stem) or {}).get('escenarios') or []):
            if isinstance(x, dict) and x.get('escenario_id'): regs[x['escenario_id']] = x   # el más nuevo gana
    if base is None: return {'escenarios': list(regs.values())} if regs else None
    out = dict(p4); out['escenarios'] = list(regs.values())
    return out

def plan(D, cd, solo=None):
    """Lista de pedidos: bases → vistas → ediciones. Sin red, sin app. Imagen «@id» = la imagen ya pintada de ese id (se resuelve al correr)."""
    try: I = ET.imagen_canal(cd)
    except ET.FaltaImagen as e: return None, str(e)
    est = ET.resolver(cd)
    if not est: return None, 'el canal no tiene estilo fijo APROBADO (style_fijo): no se pinta sin estilo'
    p4 = _leer_4a4(D)
    if not isinstance(p4, dict) or not p4.get('escenarios'):
        return None, 'falta 4a4 (respuestas/prompts_escenarios.json): corre primero «paso00_cadena correr prompts_escenarios» (Argon, pago)'
    base = leer(D / 'respuestas' / 'base.json') or {}
    pb = (leer(D / 'ramas' / 'biblioteca_plan.json') or {}).get('plan', {}).get('4a5') or {}
    de_bib = pb.get('base_de_biblioteca') or {}; ref_bib = pb.get('referencia_para_base') or {}
    reus = {z.get('variante_id') for z in (pb.get('ediciones_reutilizadas') or [])}
    nombres = nombres_personajes(base)
    solo = set(solo or [])
    neg_estilo = est.get('negativo') or ''
    bases, vistas, eds, avisos, incompletos = [], [], [], list(est.get('avisos') or []), []
    mp, gp = PJ.mapa(D), []   # orden 75
    for x in p4['escenarios']:
        eid = x.get('escenario_id')
        if not eid or (solo and eid not in solo): continue
        rc = revisar_camaras_4a4(D, x)   # PISTA INMI (2026-10-29): orden 69 — UNA imagen por cámara del molde; si no, no se pinta
        if not rc['completo']:
            avisos.append(LS.texto_camaras(rc) + ' → NO se pinta; hay que volver a pedir su 4a4 (paso00_cadena cotizar prompts_escenarios)')
            incompletos.append({k: rc[k] for k in ('escenario_id', 'faltan', 'repetidas', 'ajenas', 'imagenes_esperadas', 'vistas_recibidas')}); continue
        avisos += validar_escenario(x, D)
        md = D / 'ramas' / 'moldes' / eid
        bloque = ET.bloque_pintura(est, x.get('adaptacion_estilo_en') or '')
        b = x.get('base') or {}
        rb = str((b.get('camara') or {}).get('render') or '')
        molde = md / rb if rb and (md / rb).is_file() else (D / 'ramas' / 'moldes' / f'{eid}.png')
        imgs, guia = [], []
        if x.get('tiene_molde_blender'):
            if not molde.is_file(): avisos.append(f'{eid}: 4a4 dice que tiene molde pero no está el render (corre 4a2)'); continue
            if molde.name == f'{eid}.png': avisos.append(f'{eid}: base sin camara.render válido → se usa {molde.name} (render por defecto)')
            imgs.append(str(molde)); guia.append(GUIA_MOLDE)
        if eid in ref_bib and Path(ref_bib[eid]).is_file(): imgs.append(ref_bib[eid]); guia.append(f'Reference image {len(imgs)}: saved look of this location in the channel library; keep it.')
        for r in b.get('referencias_imagen') or []:
            f = img_obj(D, r)
            if f: imgs.append(str(f)); guia.append(f"Reference image {len(imgs)}: catalog object {r.get('id')}; keep its design exactly, do not redesign it.")
        pe = quitar_estilo(b.get('prompt_en'), est)
        pe, sg, gi = guarda(D, mp, eid, pe)
        if gi: gp.append(gi)
        neg = '; '.join(z for z in (b.get('negativo_en'), neg_estilo, 'people; characters; readable invented text') if z)
        txt = '\n'.join([*guia, pe, SIN_PERSONAS, bloque, f'Avoid: {neg}.'])
        asp = aspecto(molde, (cd or {}).get('aspect'))
        h = huella(txt, imgs, I)
        bases.append({'id': eid, 'tipo': 'base', 'escenario_id': eid, 'camara': molde.name if imgs else '', 'imagenes': imgs, 'texto': txt, 'chars': len(txt),
                      'aspecto': asp, 'salida': str(D / IMG_OUT / f'{eid}.png'), 'huella': h, 'depende': [],
                      'saltar': sg or ('biblioteca' if eid in de_bib else ya_pintada(D, eid, h)), 'personaje_en_texto': personaje_en_texto(pe, nombres)})
        for v in x.get('vistas') or []:
            vid = v['vista_id']; r = (v.get('camara') or {}).get('render')
            vi = [str(md / r), f'@{eid}']; vg = [GUIA_VISTA]
            for rr in v.get('referencias_imagen') or []:
                f = img_obj(D, rr)
                if f: vi.append(str(f)); vg.append(f"Reference image {len(vi)}: catalog object {rr.get('id')}; keep its design exactly.")
            pv = quitar_estilo(v.get('prompt_en'), est)
            pv, sg, gi = guarda(D, mp, vid, pv)
            if gi: gp.append(gi)
            nv = '; '.join(z for z in (v.get('negativo_en'), neg_estilo, 'people; characters; readable invented text') if z)
            vt = '\n'.join([*vg, pv, SIN_PERSONAS, bloque, f'Avoid: {nv}.'])
            h = huella(vt, vi, I)
            vistas.append({'id': vid, 'tipo': 'vista', 'escenario_id': eid, 'zona': v.get('zona'), 'camara': r, 'imagenes': vi, 'texto': vt, 'chars': len(vt),
                           'aspecto': asp, 'salida': str(D / IMG_OUT / f'{vid}.png'), 'huella': h, 'depende': [eid],
                           'saltar': sg or ya_pintada(D, vid, h), 'personaje_en_texto': personaje_en_texto(pv, nombres)})
        for q in x.get('variantes') or []:
            vid = q.get('variante_id')
            if not vid: continue
            ev = q.get('en_vistas') or ['base']
            for t in ev:
                tid = eid if t == 'base' else t
                oid = vid if len(ev) == 1 else f'{vid}@{t}'
                vi = [f'@{tid}']; vg = [GUIA_EDICION]
                for r in q.get('referencias_imagen') or []:
                    f = img_obj(D, r)
                    if f: vi.append(str(f)); vg.append(f"Reference image {len(vi)}: catalog object {r.get('id')} in its new state; keep its design.")
                pq = quitar_estilo(q.get('prompt_edicion_en'), est)
                pq, sg, gi = guarda(D, mp, oid, pq)
                if gi: gp.append(gi)
                vt = '\n'.join([*vg, pq, 'Keep unchanged: ' + '; '.join(q.get('se_mantiene') or []), SIN_PERSONAS, bloque,
                                f"Avoid: {'; '.join(z for z in (q.get('negativo_en'), neg_estilo) if z)}."])
                h = huella(vt, vi, I)
                eds.append({'id': oid, 'tipo': 'edicion', 'variante_id': vid, 'escenario_id': eid, 'en_vista': t, 'imagenes': vi, 'texto': vt, 'chars': len(vt),
                            'aspecto': asp, 'salida': str(D / IMG_OUT / f'{oid}.png'), 'huella': h, 'depende': [tid],
                            'saltar': sg or ('biblioteca' if vid in reus else ya_pintada(D, oid, h)), 'personaje_en_texto': personaje_en_texto(pq, nombres)})
    return {'bases': bases, 'vistas': vistas, 'ediciones': eds, 'avisos': avisos, 'imagen': I, 'estilo': est, 'incompletos_4a4': incompletos, 'guarda_personajes': gp}, None

def investigacion_valida(D, p):
    """orden 72: {objeto_id: registro} de 4b1/4c1 que el CÓDIGO da por buenos (un registro por id, con sus campos), y
    {objeto_id: motivo} de los que fallaron. Misma revisión que la cadena (paso00_cadena.cobertura_inv / fallidos_inv)."""
    import paso00_cadena as C
    regs = {}
    for i, z in C.cobertura_inv(D, p).items():
        j = C._obj_resp(D, z['paso']) or {}
        v = next((x for x in (j.get('objetos') or []) if isinstance(x, dict) and x.get('objeto_id') == i), None)
        if v: regs[i] = v
    return regs, {i: v['texto'] for i, v in C.fallidos_inv(D, p).items()}

def plan_objetos(D, cd, solo=None, caja='4b2'):
    """PISTA INMI (2026-10-29): orden 72 — plan de 4b2/4c2.
    t849u/t850u: UNA hoja modelo/turnaround por objeto (todas las vistas y estados en UNA imagen fondo blanco).
    Solo clases personaje (4b2) y escenario (4c2); utilería NO se pinta aquí. Sin red, sin app."""
    K = CAJAS_PINTAR[caja]
    try: I = ET.imagen_canal(cd)
    except ET.FaltaImagen as e: return None, str(e)
    est = ET.resolver(cd)
    if not est: return None, 'el canal no tiene estilo fijo APROBADO (style_fijo): no se pinta sin estilo'
    e2b = leer(D / 'respuestas' / 'objetos.json') or {}
    clase_want = CLASE_DE_INV_PINTAR.get(K['inv'])  # personaje for 4b2, escenario for 4c2
    obs = []
    for x in (e2b.get('objetos') or []):
        if not isinstance(x, dict) or not x.get('objeto_id'):
            continue
        cl = clase_objeto_pintar(x)
        if cl == 'utileria':
            continue  # t849u: no utilería sheets
        # prefer canonical class; fall back to old tipo filter for pre-3clases catalogs
        if clase_want:
            if cl == clase_want:
                obs.append(x)
            elif not cl and x.get('tipo') == K['tipo']:
                obs.append(x)
        elif x.get('tipo') == K['tipo']:
            obs.append(x)
    if not obs: return None, f"falta la lista de {K['que']} (4p, respuestas/objetos.json; clase {clase_want}, sin utilería)"
    regs, fall = investigacion_valida(D, K['inv'])
    base = leer(D / 'respuestas' / 'base.json') or {}
    nombres = nombres_personajes(base); solo = set(solo or []); out = out_de(caja)
    neg_estilo = est.get('negativo') or ''
    bloque = ET.bloque_pintura(est, '')
    bases, eds, avisos, incompletos = [], [], list(est.get('avisos') or []), []
    mp, gp = PJ.mapa(D), []   # orden 75
    for x in obs:
        oid = x['objeto_id']
        if solo and oid not in solo: continue
        v = regs.get(oid)
        if not v or not str(v.get('prompt_imagen') or '').strip():
            mot = (f"falta {K['cubo_inv']}: incompleto — {fall[oid]}" if oid in fall else
                   f"falta {K['cubo_inv']}: sin prompt_imagen" if v else f"falta {K['cubo_inv']}: todavía no investigado")
            incompletos.append({'objeto_id': oid, 'motivo': mot}); avisos.append(f'{oid}: NO se pinta ({mot})')
            bases.append({'id': oid, 'tipo': 'base', 'objeto_id': oid, 'escenario_id': x.get('escenario_id'), 'imagenes': [], 'texto': '', 'chars': 0, 'aspecto': '1:1',
                          'salida': str(D / out / f'{oid}.png'), 'huella': '', 'depende': [], 'saltar': mot, 'personaje_en_texto': [],
                          'sheet': True, 'clase': clase_objeto_pintar(x)})
            continue
        neg = '; '.join(z for z in (v.get('prompt_negativo'), neg_estilo, 'people; hands; characters; readable invented text; extra objects; environment') if z)
        pe = quitar_estilo(v.get('prompt_imagen'), est)
        pe, sg, gi = guarda(D, mp, oid, pe, x.get('nombre') or v.get('nombre'))
        if gi: gp.append(gi)
        # collect states into the SAME sheet (no separate estado images)
        estados_txt = []
        for k, e_ in enumerate(v.get('prompts_por_estado') or [], 1):
            if not isinstance(e_, dict) or not str(e_.get('prompt_imagen') or '').strip():
                avisos.append(f'{oid}: estado {k} sin prompt_imagen → omitido en hoja')
                continue
            pq = quitar_estilo(e_.get('prompt_imagen'), est)
            lab = e_.get('estado') or f'state {k}'
            esc = ','.join(str(s) for s in (e_.get('escenas') or [])) or '?'
            estados_txt.append(f'Panel state «{lab}» (scenes {esc}): {pq}')
        # also fold 2b estado_por_escena hints if inv has no prompts_por_estado
        if not estados_txt:
            for ep in (x.get('estado_por_escena') or []):
                if not isinstance(ep, dict): continue
                ini = (ep.get('inicio') or '').strip(); fin = (ep.get('fin') or '').strip()
                if not (ini or fin): continue
                estados_txt.append(f"Panel state scene {ep.get('escena')}: start «{ini}»; end «{fin}».")
        body = pe
        if estados_txt:
            body = pe + '\n\nStates to include as separate panels on this same sheet:\n- ' + '\n- '.join(estados_txt)
        txt = '\n'.join([HOJA_MODELO_OBJETO, body, SOLO_OBJETO, bloque, f'Avoid: {neg}.'])
        h = huella(txt, [], I)
        bases.append({'id': oid, 'tipo': 'base', 'objeto_id': oid, 'escenario_id': v.get('escenario_id') or x.get('escenario_id'), 'imagenes': [], 'texto': txt, 'chars': len(txt),
                      'aspecto': '1:1', 'salida': str(D / out / f'{oid}.png'), 'huella': h, 'depende': [], 'saltar': sg or ya_pintada(D, oid, h, caja),
                      'personaje_en_texto': personaje_en_texto(pe, nombres), 'sheet': True, 'clase': clase_objeto_pintar(x),
                      'n_estados_en_hoja': len(estados_txt)})
        # t849u: NO ediciones por estado — todo va en la hoja base
    avisos.append('t849u/t850u: plan_objetos en modo HOJA (1 imagen/objeto; sin ediciones por estado; sin utilería)')
    return {'bases': bases, 'vistas': [], 'ediciones': eds, 'avisos': avisos, 'imagen': I, 'estilo': est, 'incompletos': incompletos, 'guarda_personajes': gp, 'modo_hoja': True}, None


def revisar_camaras_4a4(D, x):
    """orden 69: misma revisión que hace la cadena (cámaras del molde según molde.json, en disco)."""
    import paso00_cadena as C
    return LS.revisar_camaras(x, C.camaras_obligatorias(D, x.get('escenario_id')))

def rehechos_4a4(D):
    """PISTA INMI (2026-10-29): orden 69 — escenarios cuyo 4a4 vino INCOMPLETO y ya se volvió a pedir COMPLETO (resultados por escenario
    con «antes_incompleto» y que ahora sirve). --solo-fallidos los incluye: sus imágenes son nuevas, no un reintento cualquiera."""
    import paso00_cadena as C
    out = set()
    for f in (D / 'resultados').glob('prompts_escenarios__*.json'):
        r = leer(f) or {}
        if r.get('antes_incompleto') and C.ya_hecho(D, f.stem): out.update(r.get('ids') or [])
    return out

def fallidos_ultima(D, caja='4a5'):
    """orden 68: ids que fallaron (o se saltaron por falta de su imagen base / presupuesto) en la última corrida pagada. orden 72: por caja."""
    r = leer(D / 'ramas' / f'resultado_{caja}_pintar_correr.json') or {}
    out = []
    for x in r.get('resultados') or []:
        sal = str(x.get('saltado') or '')
        if ('saltado' not in x and not x.get('ok')) or sal.startswith(('falta la imagen pintada', 'sin_presupuesto')): out.append(x.get('id'))
    return out

def cotizar(D, cd, solo=None, solo_ids=None, caja='4a5'):
    P, err = (plan(D, cd, solo) if caja == '4a5' else plan_de(caja)(D, cd, solo, caja))   # PISTA INMI (2026-10-29): orden 72 — plan por caja
    if err: return {'ok': False, 'error': err, 'caja': caja}
    reh = rehechos_4a4(D) if (solo_ids is not None and caja == '4a5') else set()
    if solo_ids is not None:   # PISTA INMI (2026-10-29): orden 68 — reintentar SOLO lo fallido (lo demás no se cotiza ni se pinta)
        for q in P['bases'] + P['vistas'] + P['ediciones']:   # orden 69: + todo lo de escenarios cuyo 4a4 incompleto ya se rehízo
            if not q['saltar'] and q['id'] not in solo_ids and q.get('escenario_id') not in reh: q['saltar'] = 'no_fallido'
    I = P['imagen']; T = tramo(I['modelo'], I['talla'])
    filas, total = [], 0.0
    for q in P['bases'] + P['vistas'] + P['ediciones']:
        est = precio_llamada(I, T, q['chars'], len(q['imagenes']))
        q['peor_caso_usd'] = est; q['cabe_en_tope'] = est <= TOPE_LLAMADA + 1e-9
        if not q['saltar']: total += est
        filas.append({k: q.get(k) for k in ('id', 'tipo', 'escenario_id', 'objeto_id', 'estado', 'zona', 'camara', 'en_vista', 'chars', 'aspecto', 'saltar', 'peor_caso_usd', 'cabe_en_tope', 'personaje_en_texto', 'depende') if k in q}
                     | {'n_imagenes_entrada': len(q['imagenes'])})
    n = sum(1 for q in filas if not q['saltar'])
    e = P['estilo']
    tipos = list(dict.fromkeys(['base', 'vista', 'edicion'] if caja == '4a5' else ['base', 'estado']))
    return {'ok': True, 'accion': 'pintar cotizar', 'caja': caja, 'que': CAJAS_PINTAR[caja]['que'], 'modelo': I['modelo'], 'talla': I['talla'], 'fuente_modelo': I['fuente_modelo'],
            'usd_por_imagen': I['usd_por_imagen'], 'usd_referencia_extra': I['usd_referencia_extra'], 'fuente_precio': I['fuente_precio'],
            'cobro': 'por_tokens (tramo vigente)' if T else 'precio fijo por imagen (lista de la app)', 'precio_tramo': T,
            'estilo': {'nombre': e['nombre'], 'chars_usados': e['largo_usado'], 'chars_en_ficha': e['largo_en_ficha'], 'origen': e['origen_texto']},
            'tope_por_llamada_usd': TOPE_LLAMADA, 'pedidos': filas, 'a_pintar': n,
            'por_tipo': {t: sum(1 for q in filas if q['tipo'] == t and not q['saltar']) for t in tipos},
            'total_peor_caso_usd': round(total, 4), 'avisos': P['avisos'], 'habilitado': guarda_de(caja).is_file(), 'guarda': guarda_de(caja).name, 'llamadas_hechas': 0,
            'no_se_pinta': P.get('incompletos') or [],
            'solo_fallidos': sorted(solo_ids) if solo_ids is not None else None, 'rehechos_4a4': sorted(reh), 'incompletos_4a4': P.get('incompletos_4a4') or [], 'paralelo': PARALELO, 'pausa_s': LS.num_env('TALLER_PAUSA_IMAGEN_S', PAUSA_IMAGEN_S),
            'max_intentos': MAX_INTENTOS, 'personajes': resumen_personajes(D, P, caja)}, P

def resumen_personajes(D, P, caja):
    """PISTA INMI (2026-10-29): orden 75 — lo que la guarda de personajes hizo en este cubo, en palabras simples."""
    gp = P.get('guarda_personajes') or []
    return {'regla': 'Este cubo NUNCA genera ni adjunta personajes. Los personajes salen solo de sus imágenes cargadas (cubo «Cargar personajes»).',
            'no_se_pinta': [g for g in gp if g['accion'] == 'bloquear'], 'objetos_partidos': [g for g in gp if g['accion'] == 'partir'],
            'marcadas_no_usar': sorted(PJ.no_usar(D, out_de(caja))), 'usd_extra_por_personajes': 0.0}

def monto_guarda(caja='4a5'):
    try:
        m = re.search(r'\d+(?:\.\d+)?', guarda_de(caja).read_text(errors='replace'))
        return float(m.group()) if m else None
    except Exception: return None

def correr(D, cd, a, solo=None, solo_ids=None, dormir=time.sleep, caja='4a5'):
    G = guarda_de(caja); OUT = out_de(caja)   # PISTA INMI (2026-10-29): orden 72 — misma corrida segura para 4a5, 4b2 y 4c2
    if not G.is_file():
        return {'ok': False, 'caja': caja, 'error': f'{caja} cerrada: falta {G} (pago de imágenes no aprobado). No se llamó a nada.', 'llamadas_hechas': 0}
    if a.ok is None or not a.aprobado:
        return {'ok': False, 'caja': caja, 'error': 'falta --ok USD y --aprobado QUIEN', 'llamadas_hechas': 0}
    mg = monto_guarda(caja)
    if mg is None: return {'ok': False, 'caja': caja, 'error': f'{G.name} no trae el monto aprobado: no se llama', 'llamadas_hechas': 0}
    if a.ok > mg + 1e-9: return {'ok': False, 'caja': caja, 'error': f'--ok {a.ok} pasa el monto habilitado en {G.name} ({mg})', 'llamadas_hechas': 0}
    r_ = cotizar(D, cd, solo, solo_ids, caja)
    if not isinstance(r_, tuple): return r_
    c, P = r_
    malos = [q['id'] for q in c['pedidos'] if not q['saltar'] and not q['cabe_en_tope']]
    if malos: return {'ok': False, 'error': f'no cabe en el tope por llamada {TOPE_LLAMADA}: {malos}', 'llamadas_hechas': 0}
    pers = [q['id'] for q in c['pedidos'] if not q['saltar'] and q['personaje_en_texto']]
    if pers: return {'ok': False, 'error': f'prompt que nombra personajes (regla: personajes solo por imagen de referencia): {pers}', 'llamadas_hechas': 0}
    # app (ledger y cliente de Vertex), igual que paso00_cadena correr: red solo a *.googleapis.com, credencial por RUTA (no se abre aquí)
    import paso00_cadena as C
    C.bloquear_red(True)
    A_, P_, PB_, AR, FP_, F_ = C.cargar_app(C.copiar_datos(), C.ruta_credencial())
    from google.genai import types
    I = P['imagen']; m, talla = I['modelo'], I['talla']; T = tramo(m, talla)
    (D / OUT).mkdir(parents=True, exist_ok=True)
    lock = threading.Lock(); corrida = time.strftime('%Y%m%d-%H%M%S')
    bolsa = {'gastado': 0.0, 'reservado': 0.0}
    cli = AR._cliente()
    hechas = {}

    pausa = LS.Ritmo(C.TRABAJO / '_ritmo', m, LS.num_env('TALLER_PAUSA_IMAGEN_S', PAUSA_IMAGEN_S), dormir=dormir)
    max_int = max(1, min(6, int(getattr(a, 'max_intentos', None) or MAX_INTENTOS)))

    def uno(q):
        if q['saltar']: return {'id': q['id'], 'tipo': q['tipo'], 'saltado': q['saltar']}
        imgs = []
        for f in q['imagenes']:
            if str(f).startswith('@'):
                dep = D / OUT / f'{f[1:]}.png'
                if not dep.is_file(): return {'id': q['id'], 'tipo': q['tipo'], 'saltado': f'falta la imagen pintada de {f[1:]}'}
                imgs.append(str(dep))
            else: imgs.append(f)
        est = precio_llamada(I, T, len(q['texto']), len(imgs))
        if est > TOPE_LLAMADA + 1e-9: return {'id': q['id'], 'tipo': q['tipo'], 'ok': False, 'error': f'peor caso {est} > tope'}
        base_lid = f"taller00-{caja}-{q['id']}-{corrida}"
        partes = [types.Part.from_bytes(data=Path(f).read_bytes(), mime_type='image/png' if f.endswith('.png') else 'image/jpeg') for f in imgs]
        partes.append(types.Part.from_text(text=q['texto']))
        cfg = types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'], image_config=types.ImageConfig(aspect_ratio=q['aspecto'], image_size=talla),
                                          http_options=types.HttpOptions(timeout=LS.timeout_ms('imagen')))   # orden 81: tope de tiempo → «timeout» y 1 reintento
        t0 = time.time()

        def intento(n):   # PISTA INMI (2026-10-29): orden 68 — UN intento = su línea de ledger ANTES; 429 → no_cobrado y se libera lo reservado
            lid = base_lid + ('' if n == 1 else f'-i{n}')
            with lock:   # tope TOTAL: antes de llamar, lo gastado + lo reservado + esta llamada ≤ --ok; LEDGER ANTES de llamar
                if bolsa['gastado'] + bolsa['reservado'] + est > a.ok + 1e-9:
                    raise LS.SinPresupuesto(f"sin_presupuesto (gastado {round(bolsa['gastado'], 4)} + esta {est} > --ok {a.ok})")
                bolsa['reservado'] += est
                try: AR.registrar(lid, f'{m} {talla}', est, f"{caja} {q['tipo']} {q['id']} intento {n} (aprobado {a.aprobado})", tipo='imagen', ok_usd=est, tope_usd=TOPE_LLAMADA)
                except Exception as e0:
                    bolsa['reservado'] -= est; raise LS.NoLlamado(f'{type(e0).__name__}: {str(e0)[:200]}') from e0
            try:
                return lid, cli.models.generate_content(model=m, contents=[types.Content(role='user', parts=partes)], config=cfg)
            except Exception as e:
                cobro = LS.estado_fallo(e)   # orden 81: «timeout» si se venció (cuenta el peor caso)
                with lock:
                    AR.marcar(lid, cobro, est, '')   # 429/400/403/404: no_cobrado (no suma); otro: error_posible_cobro (queda el peor caso)
                    bolsa['reservado'] -= est
                    if cobro != 'no_cobrado': bolsa['gastado'] += est
                raise

        try:
            (lid, r), ints = LS.intentar(intento, max_intentos=max_int, max_transitorios=1, dormir=dormir, ritmo=pausa, ahora=ahora,
                                         espera_base=LS.num_env('TALLER_ESPERA_429_S', 20), espera_max=LS.num_env('TALLER_ESPERA_MAX_S', 120),
                                         puede_otro=lambda n, c_: bolsa['gastado'] + bolsa['reservado'] + est <= a.ok + 1e-9)
        except LS.IntentosAgotados as e:
            for z in e.intentos: z['ledger'] = base_lid + ('' if z['n'] == 1 else f"-i{z['n']}")
            if isinstance(e.ultimo, LS.SinPresupuesto) and len(e.intentos) == 1:
                return {'id': q['id'], 'tipo': q['tipo'], 'saltado': str(e.ultimo)}
            usd_e = round(sum(est for z in e.intentos if LS.cuenta_peor_caso(z.get('cobro'))), 4)
            return {'id': q['id'], 'tipo': q['tipo'], 'ok': False, 'error': str(e)[:300], 'usd': usd_e, 'ledger': [z['ledger'] for z in e.intentos if z.get('cobro')],
                    'intentos': e.intentos, 'reintentos_429': sum(1 for z in e.intentos if z.get('clase') == '429'), 'segundos': round(time.time() - t0, 1)}
        for z in ints: z['ledger'] = base_lid + ('' if z['n'] == 1 else f"-i{z['n']}")
        data = None
        for cnd in (r.candidates or []):
            for pt in ((cnd.content.parts or []) if cnd.content else []):
                if pt.inline_data and pt.inline_data.data: data = pt.inline_data.data; break
            if data: break
        um = getattr(r, 'usage_metadata', None)
        cr = costo_real(I, T, um, len(imgs)); usd = cr if cr is not None else est
        if data:
            Path(q['salida']).write_bytes(data)
            json.dump({'id': q['id'], 'caja': caja, 'tipo': q['tipo'], 'escenario_id': q.get('escenario_id'), 'objeto_id': q.get('objeto_id'), 'estado': q.get('estado'), 'camara': q.get('camara'), 'en_vista': q.get('en_vista'),
                       'modelo': m, 'talla': talla, 'aspecto': q['aspecto'], 'texto': q['texto'], 'imagenes_entrada': imgs, 'usd': usd, 'uso': uso(um),
                       'ledger': lid, 'huella': q['huella'], 'aprobado': a.aprobado, 'segundos': round(time.time() - t0, 1), 'fecha': ahora(), 'intentos': len(ints)},
                      open(q['salida'][:-4] + '.json', 'w'), ensure_ascii=False, indent=1)
        with lock:
            AR.marcar(lid, 'ok' if data else 'sin_imagen', usd, q['salida'] if data else '')
            bolsa['reservado'] -= est; bolsa['gastado'] += usd
        usd_e = round(sum(est for z in ints if LS.cuenta_peor_caso(z.get('cobro'))), 4)
        return {'id': q['id'], 'tipo': q['tipo'], 'ok': bool(data), 'usd': round(usd + usd_e, 4), 'ledger': lid, 'salida': q['salida'] if data else '',
                'reintentos_429': sum(1 for z in ints if z.get('clase') == '429'), 'intentos': ints, 'uso': uso(um), 'segundos': round(time.time() - t0, 1)}

    res = []
    with ThreadPoolExecutor(PARALELO) as ex: res += list(ex.map(uno, P['bases']))     # bases (orden 68: PARALELO=1, una a la vez con pausa)
    with ThreadPoolExecutor(PARALELO) as ex: res += list(ex.map(uno, P['vistas']))    # vistas (cada una necesita SU base pintada)
    for q in P['ediciones']: res.append(uno(q))                                       # ediciones en orden, cada una sobre su imagen
    llamadas = [x for x in res if 'saltado' not in x]
    sin_pres = [x['id'] for x in res if str(x.get('saltado', '')).startswith('sin_presupuesto')]
    return {'ok': all(x.get('ok') for x in llamadas) and not sin_pres, 'accion': 'pintar correr', 'caja': caja, 'modelo': m, 'talla': talla, 'cobro': c['cobro'],
            'resultados': res, 'llamadas_hechas': len(llamadas), 'sin_presupuesto': sin_pres, 'avisos': c['avisos'],
            'usd_total': round(sum(float(x.get('usd') or 0) for x in llamadas), 4), 'ok_usd': a.ok, 'cotizado_peor_caso_usd': c['total_peor_caso_usd'],
            'reintentos_429': sum(int(x.get('reintentos_429') or 0) for x in llamadas), 'fallidos': [x['id'] for x in llamadas if not x.get('ok')],
            'no_se_pinta': c.get('no_se_pinta') or [],
            'reintentar': f'paso00_cadena.py pintar cotizar --caja {caja} --solo-fallidos (gratis) y luego correr --caja {caja} --solo-fallidos con OK'}

def main(argv):
    ap = argparse.ArgumentParser(prog='paso00_cadena.py pintar')
    ap.add_argument('accion', choices=['cotizar', 'correr'])
    ap.add_argument('--caja', default='4a5', choices=list(CAJAS_PINTAR), help='orden 72: 4a5 escenarios, 4b2 objetos de la historia, 4c2 objetos del lugar')
    ap.add_argument('--canal', default='cn-gnesis-digital-el-de-ed178619')
    ap.add_argument('--capitulo', default='1')
    ap.add_argument('--solo', default=None, help='ids de escenario (4a5) u objeto (4b2/4c2) separados por coma (prueba barata)')
    ap.add_argument('--ok', type=float, default=None)
    ap.add_argument('--aprobado', default=None)
    ap.add_argument('--reintento-429', dest='reintento_429', action='store_true', help='(compatibilidad) orden 68: los reintentos acotados ante 429 van siempre')
    ap.add_argument('--max-intentos', dest='max_intentos', type=int, default=MAX_INTENTOS, help='orden 68: intentos por imagen ante 429 (1..6)')
    ap.add_argument('--solo-fallidos', dest='solo_fallidos', action='store_true', help='orden 68: solo lo que falló o se saltó en la última corrida')
    a = ap.parse_args(argv)
    D = carpeta(a.canal, a.capitulo)
    if D is None: return {'ok': False, 'error': f'no hay carpeta del capítulo {a.capitulo}'}
    cd = ET.canal_datos(a.canal)
    if cd is None: return {'ok': False, 'error': f'el canal {a.canal} no está en la base del estudio'}
    solo = [x for x in (a.solo or '').split(',') if x]
    solo_ids = None
    if a.solo_fallidos:   # PISTA INMI (2026-10-29): orden 68
        solo_ids = set(fallidos_ultima(D, a.caja))
        if not solo_ids and (a.caja != '4a5' or not rehechos_4a4(D)): return {'ok': True, 'accion': f'pintar {a.accion}', 'caja': a.caja, 'nota': 'la última corrida no dejó nada fallido', 'llamadas_hechas': 0, 'total_peor_caso_usd': 0.0}
    if a.accion == 'cotizar':
        r = cotizar(D, cd, solo, solo_ids, a.caja)
        r = r[0] if isinstance(r, tuple) else r
    else:
        r = correr(D, cd, a, solo, solo_ids, caja=a.caja)
    try:
        k_ = a.caja   # orden 72: resultado y archivo por caja (4a5 igual que antes)
        fo = D / 'ramas' / f"resultado_{k_}_pintar_{a.accion}.json"
        if a.accion == 'correr' and fo.is_file() and r.get('llamadas_hechas'):   # orden 68: la corrida anterior no se pierde (de ahí salen los fallidos)
            (D / 'ramas' / f'archivo_{k_}').mkdir(exist_ok=True); fo.replace(D / 'ramas' / f'archivo_{k_}' / f"resultado_{k_}_pintar_correr_{time.strftime('%Y%m%d-%H%M%S')}.json")
        fo.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
    except Exception: pass
    return r
