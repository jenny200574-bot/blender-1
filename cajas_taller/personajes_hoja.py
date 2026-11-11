#!/usr/bin/env python3
"""PISTA INMI (2026-10-29): orden 76 — «leer hoja» (Ricardo, pt277u: «cargar el personaje en este o un formato parecido y hacemos
peticion a la ia para que llene los campos de los datos y nos entregue el personaje separado en cada transformacion»;
«no te centres en costos, enfócate en la programación»).

Cómo funciona (por CANAL; sirve para todos los capítulos):
  1. hoja-recibir   (GRATIS)  el usuario sube UNA hoja de personaje (los mismos trozos del formulario: personajes subir --sesion S …).
                              Queda en <biblioteca>/<canal>/personajes/_hojas/<id>/hoja.<ext>  (id = sha256 de la imagen, 16 letras).
  2. hoja-leer      (PAGO)    Argon (visión) lee la hoja y llena los campos (prompts_hoja/leer_hoja.txt + leer_hoja_esquema.json):
                              personajes de la hoja → nombre, rol, edad, descripción, personalidad, «nunca cambia», expresiones,
                              versiones/transformaciones (nombre, altura, descripción visual, dónde está en la hoja, calidad, qué no se ve),
                              etapas de transformación y avisos. El CÓDIGO revisa la lectura (cajas dentro de la hoja, tamaño en píxeles,
                              calidad, cajas repetidas, máximos) y recorta GRATIS cada versión de la hoja (recortes/).
  3. hoja-aplicar   (GRATIS)  la lectura llena personajes.json (lo corre hoja-leer solo): personajes y versiones SIN APROBAR,
                              origen «hoja_ia». No pisa lo que el usuario ya escribió (lo de la IA queda en «propuesto_ia»).
  4. hoja-separar   (PAGO)    Nano Banana (el modelo de imagen del canal) saca UNA imagen limpia por versión, SOLO desde la hoja:
                              ref 1 = recorte de esa versión, ref 2 = la hoja entera (+ ref 3 = otra vista de la misma versión).
                              Nunca inventa: si una versión es pequeña, poco clara o parcial → NO se genera y se avisa
                              (subir una imagen mejor con el formulario o pedir --forzar con OK). Lo que la hoja no muestra queda fuera del cuadro.
                              Cada imagen va a <personaje>/<versión>/refs/ + personajes.json, SIN APROBAR hasta que el usuario apruebe.
  hoja-cotizar      (GRATIS)  escribe los textos EXACTOS que se mandarían (pedidos/) y una línea de cotización.
  El formulario manual («personajes ficha/subir/guardar») sigue igual: sirve de respaldo y para corregir lo que llenó la IA.

Reglas de pago (las mismas de siempre): correr CERRADO sin cajas/HABILITAR_PAGO_HOJA (con el monto), --ok USD y --aprobado QUIEN;
ledger ANTES de cada intento (id propio por intento), intentos acotados (llamada_segura), 429 → no_cobrado, tope por llamada US$0,75,
una imagen a la vez con pausa. Genérico (regla 6): aquí no hay nombres de canales, personajes ni versiones.
"""
import argparse, base64, json, math, os, re, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path: sys.path.insert(0, str(AQUI))
import personajes as PJ
import llamada_segura as LS

PROMPTS = Path(os.environ.get('MYIA_PROMPTS_HOJA', str(AQUI / 'prompts_hoja')))
GUARDA_DIR = Path(os.environ.get('MYIA_GUARDA_DIR', str(AQUI)))

def H(): return PJ.cfg()['hoja']
def texto(nombre): return (PROMPTS / nombre).read_text(encoding='utf-8')
def esquema_txt(): return texto('leer_hoja_esquema.json')
def esquema(): return json.loads(esquema_txt())
def dir_hoja(canal, hid):
    if not PJ.valido_id(hid): raise ValueError('id de hoja no válido')
    return PJ.raiz(canal) / '_hojas' / hid
def hoja_de(canal, hid):
    d = dir_hoja(canal, hid); fs = sorted(d.glob('hoja.*')) if d.is_dir() else []
    if not fs: raise ValueError(f'no hay hoja {hid}')
    return fs[0]

def medidas(f):
    from PIL import Image
    with Image.open(f) as im: return im.size

# ---------------- 1. recibir ----------------
def recibir(canal, sesion):
    """Arma la hoja subida en trozos (mismo formato que personajes subir) y la guarda. UNA imagen por sesión."""
    C = PJ.cfg()['subida']; ses = PJ._sesion(canal, sesion); tz = ses / 'trozos'
    imgs = {}
    for t in sorted(tz.glob('*')) if tz.is_dir() else []:
        nom, parte, de = t.name.rsplit('.', 2); imgs.setdefault(nom, {'de': int(de), 'partes': {}})['partes'][int(parte)] = t
    if len(imgs) != 1: raise ValueError(f'la sesión debe traer UNA hoja (trae {len(imgs)})')
    nom, x = next(iter(imgs.items()))
    if sorted(x['partes']) != list(range(1, x['de'] + 1)): raise ValueError('la hoja llegó incompleta')
    b = b''.join(x['partes'][i].read_bytes() for i in range(1, x['de'] + 1))
    ext = next((e for k, e in PJ.MAGIA.items() if b.startswith(k)), None)
    if not ext or ext == '.webp': raise ValueError('la hoja debe ser png o jpg')
    if len(b) > C['max_mb_por_imagen'] * 1024 * 1024: raise ValueError(f'la hoja pesa más de {C["max_mb_por_imagen"]} MB')
    h = PJ.sha(b); hid = h[:16]; d = dir_hoja(canal, hid); d.mkdir(parents=True, exist_ok=True)
    f = d / f'hoja{ext}'
    nueva = not f.is_file()
    if nueva: f.write_bytes(b)
    w, hh = medidas(f)
    fi = PJ.leer_json(d / 'ficha.json') or {'id': hid, 'sha256': h, 'archivo': f.name, 'nombre_subido': nom, 'ancho': w, 'alto': hh, 'subida': PJ.ahora()}
    PJ.escribir_json(d / 'ficha.json', fi)
    import shutil; shutil.rmtree(ses, ignore_errors=True)
    return {'ok': True, 'accion': 'personajes hoja-recibir', 'hoja': hid, 'nueva': nueva, 'ancho': w, 'alto': hh,
            'siguiente': f'personajes hoja-cotizar --canal {canal} --hoja {hid} (gratis) → hoja-leer con OK'}

# ---------------- prompts ----------------
def nombres_mapa(D):
    if D is None: return '(none given)'
    out = []
    for pid, p in PJ.mapa(D).items():
        fs = [f.get('nombre') or fid for fid, f in p['formas'].items()]
        out.append(f"{p['nombre']}" + (f" (versions: {', '.join(fs)})" if fs else ''))
    return '; '.join(out) or '(none given)'

def prompt_lectura(D=None):
    return texto('leer_hoja.txt').replace('{NOMBRES_MAPA}', nombres_mapa(D))

def _lista(x): return ', '.join(str(z) for z in (x or []) if str(z).strip())
def HV(): return H()['vistas']

def _solo_calidad(v):
    """El único motivo para no generar era la calidad/tamaño (no una caja mala, repetida o de más)."""
    if v.get('motivo_tipo'): return v['motivo_tipo'] == 'calidad'
    return str(v.get('motivo_no') or '').startswith(('se ve muy pequeña', 'calidad «'))   # lecturas de antes de la orden 80

def completado(v):
    """PISTA INMI (orden 80): qué tiene que COMPLETAR el modelo en cada vista (lo que la hoja no muestra). Va al prompt y a completado_ia."""
    mv = v.get('mejor_vista') or {}; fv = [str(x).strip() for x in v.get('falta_ver') or [] if str(x).strip()]
    fr = [x for x in fv if not es_espalda(x)]   # lo de la espalda no es tarea de la vista de frente
    if not mv.get('cuerpo_completo'): fr.append('cuerpo completo hasta los pies (la hoja no lo muestra entero)')
    if mv.get('de_frente') is False: fr.append('vista de frente (la hoja no la muestra de frente)')
    es = [x for x in fr if not x.startswith('vista de frente')]
    if not v.get('_espalda'): es = ['espalda completa (la hoja no la muestra)'] + es
    else: es = [x for x in fv if es_espalda(x)] + es   # hay espalda en la hoja, pero la lectura dice que falta algo de ella
    return {'frente': fr, 'espalda': es}

def prompt_vista(vista, p, v, completar, n_refs):
    """Texto EXACTO de una vista (inglés, sin nombres fijos: los nombres vienen de la hoja)."""
    E = HV()['encuadre']
    if vista == 'frente':
        r = ['Reference image 1 is a crop of a character reference sheet showing this version.',
             'Reference image 2 is the whole sheet, for context only (colors, details, other angles of this same version).']
        if n_refs >= 3: r.append('Reference image 3 is another view of this same version on the sheet.')
        esp = ''
    else:
        r = ['Reference image 1 is the clean FULL-BODY FRONT view of this same version: the character must match it exactly.',
             'Reference image 2 is a crop of the character reference sheet showing this version.']
        if v.get('_espalda'):
            r.append('Reference image 3 shows the BACK of this version on the sheet.')
            esp = 'The sheet shows the back (reference image 3): copy its back details exactly.'
        else:
            esp = ('The sheet never shows the back: complete it consistently with the front and the sheet, continuing the same outfit around '
                   'the body with the same colors, materials, seams and design elements.')
        r.append(f'Reference image {len(r) + 1} is the whole sheet, for context only.')
    return (texto(HV()[vista]['prompt'])
            .replace('{PERSONAJE}', p.get('nombre') or p.get('nombre_en_mapa') or '')
            .replace('{VERSION}', v.get('nombre') or v.get('nombre_en_mapa') or '')
            .replace('{REFERENCIAS}', ' '.join(r)).replace('{ESPALDA}', esp)
            .replace('{COMPLETAR}', '; '.join(completar) or 'nothing listed')
            .replace('{ENCUADRE}', E['texto']).replace('{FONDO}', E['fondo'])
            .replace('{DESCRIPCION}', (v.get('descripcion_visual') or '').strip() or '-')
            .replace('{NUNCA_CAMBIA}', _lista(p.get('nunca_cambia')) or '-'))

# ---------------- revisión GRATIS de la lectura ----------------
def _caja_px(c, w, h):
    if not (isinstance(c, list) and len(c) == 4 and all(isinstance(z, (int, float)) for z in c)): return None
    y0, x0, y1, x1 = [max(0, min(1000, z)) for z in c]
    if y1 <= y0 or x1 <= x0: return None
    return (round(x0 * w / 1000), round(y0 * h / 1000), round(x1 * w / 1000), round(y1 * h / 1000))
def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0

def revisar_lectura(L, w, h):
    """Revisa la lectura con reglas fijas (sin IA). Marca en cada versión: generar (bool) y motivo. Devuelve avisos."""
    Hc = H(); q = Hc['calidad_minima']; avisos = list(L.get('avisos') or []); vistas = []
    ps = [p for p in (L.get('personajes') or []) if isinstance(p, dict)]
    if not ps: avisos.append('la lectura no trae personajes')
    if len(ps) > Hc['max_personajes_por_hoja']: avisos.append(f'más de {Hc["max_personajes_por_hoja"]} personajes: se usan los primeros'); ps = ps[:Hc['max_personajes_por_hoja']]
    n = 0
    for p in ps:
        pn = p.get('nombre') or p.get('nombre_en_mapa') or ''
        if PJ._vacio(pn): avisos.append('un personaje no tiene nombre en la hoja: escríbelo en el formulario')
        vs = [v for v in (p.get('versiones') or []) if isinstance(v, dict)]
        if not vs: avisos.append(f'{pn or "?"}: la lectura no trae versiones')
        for v in vs:
            n += 1; vn = v.get('nombre') or v.get('nombre_en_mapa') or ''
            et = f'{pn or "?"} – {vn or "(sin nombre)"}'
            px = _caja_px((v.get('mejor_vista') or {}).get('caja'), w, h); motivo = None
            if n > Hc['max_versiones_por_hoja']: motivo = f'pasa el máximo de {Hc["max_versiones_por_hoja"]} versiones por hoja'
            elif px is None: motivo = 'la lectura no dio una caja válida en la hoja'
            else:
                cw, ch = px[2] - px[0], px[3] - px[1]
                v['_px'] = list(px)
                if min(cw, ch) < q['lado_corto_px'] or cw * ch < q['area_px']: motivo = f'se ve muy pequeña en la hoja ({cw}×{ch} px)'
                elif v.get('calidad') not in q['calidades_que_se_generan']:
                    motivo = f"calidad «{v.get('calidad') or '?'}»" + (f": {v.get('por_que_calidad')}" if v.get('por_que_calidad') else '')
                if motivo: v['motivo_tipo'] = 'calidad'   # orden 80: solo calidad → igual se genera (completado_ia)
                for (e2, p2) in vistas:
                    if _iou(px, p2) >= Hc['caja_repetida_iou']:
                        avisos.append(f'REPETIDA: {et} usa la misma imagen de la hoja que {e2}')
                        if not motivo or v.get('motivo_tipo') == 'calidad': motivo = f'misma imagen que {e2}'; v['motivo_tipo'] = 'repetida'
                vistas.append((et, px))
            v['generar'] = motivo is None; v['motivo_no'] = motivo
            if motivo: avisos.append(f'NO se genera {et}: {motivo} → sube una imagen mejor con el formulario o pide --forzar')
            if not (v.get('mejor_vista') or {}).get('cuerpo_completo'): avisos.append(f'{et}: la hoja no la muestra de cuerpo entero; el modelo completa lo que falta (queda marcado completado_ia)')
    L['personajes'] = ps
    return avisos

def recortar(canal, hid, L):
    """Recorta GRATIS de la hoja la mejor vista (y la primera otra vista) de cada versión."""
    from PIL import Image
    d = dir_hoja(canal, hid); f = hoja_de(canal, hid); m = H()['separar']['margen_recorte']; (d / 'recortes').mkdir(exist_ok=True)
    with Image.open(f) as im:
        im = im.convert('RGB'); W, Hh = im.size
        def corte(c, nombre):
            px = _caja_px(c, W, Hh)
            if px is None: return None
            mx, my = round((px[2] - px[0]) * m), round((px[3] - px[1]) * m)
            box = (max(0, px[0] - mx), max(0, px[1] - my), min(W, px[2] + mx), min(Hh, px[3] + my))
            o = d / 'recortes' / f'{nombre}.png'; im.crop(box).save(o); return str(o)
        for p in L['personajes']:
            for v in p.get('versiones') or []:
                k = f"{PJ.slug(p.get('nombre') or p.get('nombre_en_mapa'))}__{PJ.slug(v.get('nombre') or v.get('nombre_en_mapa') or 'base')}"
                v['_recorte'] = corte((v.get('mejor_vista') or {}).get('caja'), k)
                ov = [o for o in (v.get('otras_vistas') or []) if isinstance(o, dict)]
                es = [o for o in ov if es_espalda(o.get('que_muestra'))]; no = [o for o in ov if not es_espalda(o.get('que_muestra'))]   # orden 80
                v['_otra'] = corte(no[0].get('caja'), k + '__otra') if no else None
                v['_espalda'] = corte(es[0].get('caja'), k + '__espalda') if es else None

def es_espalda(t):
    """PISTA INMI (orden 80): ¿la «otra vista» de la hoja es la espalda? Por palabras de hoja.vistas.palabras_espalda (sin tildes)."""
    t = PJ.sin_tildes(str(t or '')).lower()
    return any(re.search(r'(?<![a-z])' + re.escape(PJ.sin_tildes(w).lower()) + r'(?![a-z])', t) for w in HV()['palabras_espalda'])

def guardar_lectura(canal, hid, L, origen, extra=None):
    d = dir_hoja(canal, hid); w, h = medidas(hoja_de(canal, hid))
    avisos = revisar_lectura(L, w, h); recortar(canal, hid, L)
    L.update(origen=origen, hoja=hid, revisada=PJ.ahora(), avisos_codigo=avisos, **(extra or {}))
    PJ.escribir_json(d / ('lectura.json' if origen == 'ia' else f'lectura_{origen}.json'), L)
    return L, avisos

def lectura_de(canal, hid, permitir_simulada=False):
    d = dir_hoja(canal, hid)
    L = PJ.leer_json(d / 'lectura.json')
    if L is None and permitir_simulada:
        L = PJ.leer_json(d / 'lectura_simulada.json')
    return L

# ---------------- 3. aplicar (GRATIS) ----------------
def _altura_m(s):
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*m\b', str(s or ''))
    return float(m.group(1).replace(',', '.')) if m else None

def aplicar(canal, hid, D=None):
    """Lectura de la IA → personajes.json. Todo SIN APROBAR; no pisa lo que el usuario escribió."""
    L = lectura_de(canal, hid)
    if not L: raise ValueError('no hay lectura de la IA para esa hoja (hoja-leer)')
    mp = PJ.mapa(D) if D is not None else {}
    hechas = []
    with PJ.Candado(canal):
        m = PJ.leer_manifiesto(canal)
        for p in L['personajes']:
            pn = p.get('nombre_en_mapa') or p.get('nombre')
            if PJ._vacio(pn): continue
            pm = PJ.buscar_personaje(m, None, pn) or PJ.buscar_personaje(m, None, p.get('nombre'))
            g = PJ.buscar_grupo(m, None, pn)   # orden 85: el nombre del mapa ya es un GRUPO dividido → el personaje es el de su propio nombre
            if pm is None and g is not None and not PJ._vacio(p.get('nombre')): pn = p.get('nombre')
            if pm is None:
                pm = {'id': PJ.slug(pn), 'nombre': pn, 'carpeta': PJ.slug(pn), 'ids_mapa': [], 'nunca_cambia': None, 'versiones': [], 'origen': 'hoja_ia'}
                m['personajes'].append(pm)
            for pid, x in mp.items():
                if PJ.igual(x['nombre'], pn) and pid not in pm['ids_mapa'] and not PJ.buscar_grupo(m, pid): pm['ids_mapa'].append(pid)
            prop = {'nombre_en_hoja': p.get('nombre'), 'rol': p.get('rol'), 'edad': p.get('edad'), 'descripcion': p.get('descripcion'),
                    'personalidad': p.get('personalidad') or [], 'nunca_cambia': p.get('nunca_cambia') or [],
                    'expresiones': [e.get('nombre') for e in p.get('expresiones') or [] if isinstance(e, dict)],
                    'etapas_transformacion': [e.get('nombre') for e in p.get('etapas_transformacion') or [] if isinstance(e, dict)], 'hoja': hid}
            pm['propuesto_ia'] = prop
            if not pm.get('nunca_cambia') and prop['nunca_cambia']: pm['nunca_cambia'] = '; '.join(prop['nunca_cambia'])
            for k in ('rol', 'edad', 'descripcion', 'personalidad', 'expresiones'):   # orden 77: lo puesto a mano («manual») no se toca
                if k not in (pm.get('manual') or {}) and not pm.get(k) and prop.get(k): pm[k] = prop[k]
            for v in p.get('versiones') or []:
                vn = v.get('nombre_en_mapa') or v.get('nombre') or 'base'
                vm = PJ.buscar_version(pm, None, vn) or PJ.buscar_version(pm, None, v.get('nombre'))
                if vm is None:
                    vm = {'id': PJ.slug(vn), 'nombre': vn, 'forma_id': None, 'ids_mapa': [], 'carpeta': PJ.slug(vn), 'refs': [], 'refs_sha256': [],
                          'estado': 'pendiente', 'origen': 'hoja_ia', 'desde': None, 'hasta': None, 'creada': PJ.ahora()}
                    pm['versiones'].append(vm)
                for pid in pm['ids_mapa']:
                    for fid, fo in mp.get(pid, {}).get('formas', {}).items():
                        if (PJ.igual(fo.get('nombre'), vn) or PJ.igual(fid, vn)) and fid not in vm['ids_mapa']: vm['ids_mapa'].append(fid)
                vm['propuesto_ia'] = {'nombre_en_hoja': v.get('nombre'), 'descripcion_visual': v.get('descripcion_visual'), 'altura': v.get('altura'),
                                      'es_transformacion_de': v.get('es_transformacion_de'), 'calidad': v.get('calidad'), 'falta_ver': v.get('falta_ver') or [],
                                      'cuerpo_completo': bool((v.get('mejor_vista') or {}).get('cuerpo_completo')), 'caja': (v.get('mejor_vista') or {}).get('caja'),
                                      'recorte': v.get('_recorte'), 'se_genera': v.get('generar'), 'motivo_no': v.get('motivo_no'), 'hoja': hid}
                if not vm.get('descripcion') and v.get('descripcion_visual'): vm['descripcion'] = v['descripcion_visual']
                if vm.get('altura_m') in (None, '') and _altura_m(v.get('altura')) is not None: vm['altura_m'] = _altura_m(v.get('altura'))
                hechas.append(f'{pm["nombre"]} – {vm["nombre"]} ({vm["estado"]})')
        PJ.guardar_manifiesto(canal, m)
    return {'ok': True, 'accion': 'personajes hoja-aplicar', 'hoja': hid, 'versiones': hechas,
            'nota': 'todo queda SIN APROBAR; corrige con el formulario y aprueba versión por versión'}

# ---------------- cotizar (GRATIS) ----------------
def precios(canal):
    """(modelo, nivel, US$ por 1M entrada/salida) de Argon del canal y (modelo, talla, US$ imagen, ref extra) del canal. Sin red."""
    import estilo_taller as ET
    cd = ET.canal_datos(canal) or {}
    sec = cd.get(H()['lectura']['seccion_canal']) or {}
    m, n = sec.get('argon_modelo'), sec.get('argon_nivel')
    if not m or not n: raise ValueError(f'el canal no tiene {H()["lectura"]["seccion_canal"]}.argon_modelo/argon_nivel')
    if str(ET.REPO) not in sys.path: sys.path.insert(0, str(ET.REPO))
    import precios_myia as PR
    pi, po = PR.tokens_en_fecha(m, time.strftime('%Y-%m-%d'))[:2]   # devuelve (entrada, salida, entrada_audio)
    I = ET.imagen_canal(cd)
    return {'texto': {'modelo': m, 'nivel': n, 'entrada': float(pi), 'salida': float(po)}, 'imagen': I}

def est_lectura(P, chars):
    Lc = H()['lectura']
    return round((math.ceil(chars / 3) + Lc['tokens_imagen_peor_caso']) * P['texto']['entrada'] / 1e6 + Lc['max_out'] * P['texto']['salida'] / 1e6, 4)
def est_imagen(P, n_refs):
    I = P['imagen']; return round(I['usd_por_imagen'] + I['usd_referencia_extra'] * max(0, n_refs - 1), 4)

def plan_separar(L, solo=None, forzar=()):
    """PISTA INMI (orden 80): por versión, el JUEGO ESTÁNDAR de hoja.vistas (frente y espalda), cuerpo completo, mismo encuadre.
    Se genera toda versión con recorte, aunque la calidad sea baja (lo que falta lo completa el modelo y queda marcado);
    NO se genera si no hay caja válida, si es la misma imagen que otra versión o si pasa el máximo (salvo --forzar)."""
    out = []
    for p in L.get('personajes') or []:
        for v in p.get('versiones') or []:
            et = f"{p.get('nombre') or p.get('nombre_en_mapa')} – {v.get('nombre') or v.get('nombre_en_mapa') or 'base'}"
            k = f"{PJ.slug(p.get('nombre') or p.get('nombre_en_mapa'))}__{PJ.slug(v.get('nombre') or v.get('nombre_en_mapa') or 'base')}"
            if solo and k not in solo and et not in solo: continue
            ok = bool(v.get('_recorte')) and bool(v.get('generar') or k in forzar or (HV()['generar_aunque_calidad'] and _solo_calidad(v)))
            comp = completado(v); vistas = {}
            for vista in HV()['lista']:
                if vista == 'frente': refs = [r for r in (v.get('_recorte'), '@hoja', v.get('_otra')) if r]
                else: refs = [r for r in ('@frente', v.get('_recorte'), v.get('_espalda'), '@hoja') if r]
                refs = refs[:HV()[vista]['max_refs']]
                vistas[vista] = {'refs': refs, 'completado': comp.get(vista, []), 'texto': prompt_vista(vista, p, v, comp.get(vista, []), len(refs))}
            out.append({'clave': k, 'etiqueta': et, 'p': p, 'v': v, 'generar': ok, 'motivo_no': None if ok else (v.get('motivo_no') or 'sin recorte de la hoja'),
                        'aspecto': HV()['encuadre']['aspecto'], 'vistas': vistas,
                        'refs': vistas[HV()['lista'][0]]['refs'], 'texto': vistas[HV()['lista'][0]]['texto']})
    return out

def est_version(P, q, lista=None):
    return round(sum(est_imagen(P, len(q['vistas'][x]['refs'])) for x in (lista or HV()['lista'])), 4)

def cotizar(canal, hid, D=None, simulada=None):
    """GRATIS: escribe los textos EXACTOS (pedidos/) y una línea de cotización. simulada = lectura hecha a mano (solo para probar)."""
    d = dir_hoja(canal, hid); hoja_de(canal, hid); (d / 'pedidos').mkdir(exist_ok=True)
    pr = prompt_lectura(D); (d / 'pedidos' / 'leer_hoja.txt').write_text(pr, encoding='utf-8')
    avisos = []
    if simulada is not None:
        guardar_lectura(canal, hid, simulada, 'simulada', {'nota': 'lectura hecha A MANO para probar (no es de la IA): no sirve para separar'})
    L = lectura_de(canal, hid, permitir_simulada=True)
    if L: recortar(canal, hid, L)   # orden 80: gratis, agrega el recorte de la espalda a lecturas viejas
    plan = plan_separar(L) if L else []
    for q in plan:
        if q['generar']:
            for vista, x in q['vistas'].items(): (d / 'pedidos' / f"separar__{q['clave']}__{vista}.txt").write_text(x['texto'], encoding='utf-8')
    if L: avisos = L.get('avisos_codigo') or []
    n = sum(1 for q in plan if q['generar']); nv = len(HV()['lista']); ya = (L or {}).get('origen') == 'ia'
    try:
        P = precios(canal); img = round(sum(est_version(P, q) for q in plan if q['generar']), 4) if L else None
        usd = round((0 if ya else est_lectura(P, len(pr))) + img, 4) if L else None
        if not L: usd_sin = round(est_lectura(P, len(pr)) + H()['max_versiones_por_hoja'] * nv * est_imagen(P, 4), 4)
    except Exception as e:
        P, usd, usd_sin = None, None, None; avisos.append(f'sin precio del canal: {type(e).__name__}: {str(e)[:120]}')
    linea = (f"{'lectura ya hecha' if ya else '1 lectura'} + {n} versiones × {nv} vistas = {n * nv} imágenes ≈ US${usd} peor caso" if L and usd is not None else
             f'1 lectura + hasta {H()["max_versiones_por_hoja"]} versiones × {nv} vistas ≈ US${usd_sin} peor caso (N exacto después de leer)' if not L and P else 'sin cotización')
    r = {'ok': True, 'accion': 'personajes hoja-cotizar', 'hoja': hid, 'lectura': (L or {}).get('origen') or 'aún no',
         'versiones': [{'version': q['etiqueta'], 'se_genera': q['generar'], 'motivo_no': q['motivo_no'], 'aspecto': q['aspecto'],
                        'refs': ' · '.join(f"{k} {len(x['refs'])}" for k, x in q['vistas'].items()),   # columna «Refs» del flujo n8n (sin tocar el flujo)
                        'vistas': {k: {'refs': len(x['refs']), 'completado_ia': bool(x['completado']), 'completado': x['completado']} for k, x in q['vistas'].items()},
                        'recorte': (q['v'].get('_recorte') or '').split('/_hojas/')[-1]} for q in plan],
         'campos': [{'personaje': p.get('nombre'), 'nunca_cambia': p.get('nunca_cambia'), 'expresiones': [e.get('nombre') for e in p.get('expresiones') or []],
                     'versiones': [(v.get('nombre'), v.get('altura')) for v in p.get('versiones') or []]} for p in (L or {}).get('personajes') or []],
         'avisos': avisos, 'cotizacion': linea, 'pedidos': str(d / 'pedidos'), 'llamadas_hechas': 0, 'usd': 0}
    PJ.escribir_json(d / 'cotizacion.json', r)
    return r

# ---------------- pago (CERRADO sin guarda) ----------------
def revisar_guarda(a):
    G = GUARDA_DIR / H()['guarda']
    if not G.is_file(): return f'leer hoja cerrada: falta {G.name} (pago no aprobado). No se llamó a nada.'
    if a.ok is None or not a.aprobado: return 'falta --ok USD y --aprobado QUIEN'
    mm = re.search(r'\d+(?:\.\d+)?', G.read_text(errors='replace'))
    if not mm: return f'{G.name} no trae el monto aprobado: no se llama'
    if a.ok > float(mm.group()) + 1e-9: return f'--ok {a.ok} pasa el monto habilitado en {G.name} ({mm.group()})'
    return None

def _app():
    """App del staging (ledger, Argon, cliente de Vertex). Red solo a *.googleapis.com. La credencial va por RUTA (no se abre aquí)."""
    import paso00_cadena as C
    C.bloquear_red(True)
    _A, _P, _PB, AR, FP, F = C.cargar_app(C.copiar_datos(), C.ruta_credencial())
    from google.genai import types
    return {'C': C, 'AR': AR, 'FP': FP, 'F': F, 'types': types, 'cli': None, 'ritmo_dir': C.TRABAJO / '_ritmo', 'dormir': time.sleep}

def _intentar(X, a, est, bolsa, base_id, hacer):
    tope = H()['tope_por_llamada_usd']
    if est > tope + 1e-9: raise LS.NoLlamado(f'peor caso {est} > tope por llamada {tope}')
    def uno(n):
        lid = base_id + ('' if n == 1 else f'-i{n}')
        if bolsa['gastado'] + est > a.ok + 1e-9: raise LS.SinPresupuesto(f"gastado {round(bolsa['gastado'], 4)} + {est} > --ok {a.ok}")
        try: return lid, hacer(lid, n)
        except Exception as e:
            if LS.clasificar_error(e)['cobro'] == 'error_posible_cobro': bolsa['gastado'] += est   # orden 81: un timeout también (peor caso)
            raise
    return LS.intentar(uno, max_intentos=max(1, min(6, int(getattr(a, 'max_intentos', None) or H()['max_intentos']))), max_transitorios=1,
                       dormir=X.get('dormir', time.sleep), puede_otro=lambda n, c: bolsa['gastado'] + est <= a.ok + 1e-9)

def fijo_lectura(FP, m, n):
    """PISTA INMI (orden 77): parte fija de la lectura con TODAS las partes obligatorias de myia_fijo_prompt (texto, esquema,
    modelo, nivel, max_out, max_rondas). El nombre del paso lleva el sha de esas partes: si cambia el texto, el registro del
    taller es otro (nunca se pisa uno congelado). Los fragmentos fijos = el texto sin el hueco {NOMBRES_MAPA}, en orden."""
    if FP is None: import myia_fijo_prompt as FP
    Lc = H()['lectura']; t = texto('leer_hoja.txt')
    partes = {'texto': t, 'esquema': esquema_txt(), 'modelo': m, 'nivel': n, 'max_out': Lc['max_out'], 'max_rondas': 1, 'json_out': Lc['json_out']}
    return {'paso': f"{Lc['paso_fijo']}_{FP.sha_total(partes)[:10]}", 'partes': partes, 'fragmentos': [f for f in t.split('{NOMBRES_MAPA}') if f.strip()]}

def _no_llamado_si_no_anotado(AR, lid, exc):
    """PISTA INMI (orden 77): si falló ANTES de anotar en el ledger (fijo bloqueado, sin modelo, sin precio…) no hubo llamada ni
    cobro: NoLlamado (definitivo, sin reintento y sin sumar «posible cobro»). Si ya estaba anotado, el error sigue igual."""
    try: est = next((r.get('estado') for r in AR._leer() if r.get('id') == lid), None)
    except Exception: est = 'desconocido'
    if est is None: raise LS.NoLlamado(f'{type(exc).__name__}: {str(exc)[:300]}') from exc

def leer(canal, hid, a, D=None, X=None):
    """PAGO: Argon lee la hoja y llena los campos. Luego revisa, recorta y aplica (gratis)."""
    err = revisar_guarda(a)
    if err: return {'ok': False, 'error': err, 'llamadas_hechas': 0}
    f = hoja_de(canal, hid); d = dir_hoja(canal, hid)
    P = (X or {}).get('precios') or precios(canal); pr = prompt_lectura(D); est = est_lectura(P, len(pr))
    if est > a.ok + 1e-9: return {'ok': False, 'error': f'la lectura cuesta hasta US${est} y --ok es {a.ok}', 'llamadas_hechas': 0}
    X = X or _app(); AR = X['AR']; Lc = H()['lectura']; m, n = P['texto']['modelo'], P['texto']['nivel']
    fijo = fijo_lectura(X['FP'], m, n)
    X['C'].registrar_taller(fijo, X['FP'], X['F'])
    (d / 'pedidos').mkdir(exist_ok=True); (d / 'pedidos' / 'leer_hoja.txt').write_text(pr, encoding='utf-8')
    salida = d / 'respuestas' / 'lectura_ia.json'; bolsa = {'gastado': 0.0}; base = f"taller-hoja-{hid}-{time.strftime('%Y%m%d-%H%M%S')}"
    def hacer(lid, k):
        try:
            r = AR.llamar(lid, pr, str(salida), est, f'taller n8n leer hoja {hid} intento {k} (aprobado: {a.aprobado})', transporte=X.get('transporte') or LS.transporte_texto(AR), modelo=m, nivel=n,
                          max_out=Lc['max_out'], json_out=Lc['json_out'], adjuntos=[str(f)], fijo=fijo, cotizacion=AR.cotizacion(est, modelo=m),
                          ok_usd=est, tope_usd=H()['tope_por_llamada_usd'], esquema=esquema())
        except Exception as e:
            _no_llamado_si_no_anotado(AR, lid, e)
            if LS.es_timeout(e): AR.marcar(lid, 'timeout', est, '')   # orden 81: queda «timeout» (peor caso) y se reintenta
            raise
        bolsa['gastado'] += float(r.get('usd') or 0); return r
    try: (lid, r), ints = _intentar(X, a, est, bolsa, base, hacer)
    except LS.IntentosAgotados as e:
        return {'ok': False, 'error': str(e)[:300], 'intentos': e.intentos, 'usd': round(bolsa['gastado'], 4), 'llamadas_hechas': len(e.intentos)}
    except LS.NoLlamado as e: return {'ok': False, 'error': str(e), 'llamadas_hechas': 0}
    rv = LS.revisar_respuesta(r.get('texto') or '', esquema(), r.get('fin'))
    if rv['obj'] is None or rv.get('esquema_errores'):
        return {'ok': False, 'error': f"la lectura no vino completa ({rv['estado']}): {rv.get('esquema_errores') or rv.get('motivo')}", 'ledger': lid,
                'usd': round(bolsa['gastado'], 4), 'llamadas_hechas': len(ints), 'respuesta': str(salida)}
    L, avisos = guardar_lectura(canal, hid, rv['obj'], 'ia', {'ledger': lid, 'usd': r.get('usd'), 'modelo': m, 'nivel': n})
    ap = aplicar(canal, hid, D)
    return {'ok': True, 'accion': 'personajes hoja-leer', 'hoja': hid, 'ledger': lid, 'usd': round(bolsa['gastado'], 4), 'llamadas_hechas': len(ints),
            'avisos': avisos, 'aplicado': ap['versiones'], 'siguiente': cotizar(canal, hid, D)['cotizacion']}

def separar(canal, hid, a, D=None, X=None, solo=None, forzar=(), vistas=None):
    """PAGO: por versión el JUEGO ESTÁNDAR (orden 80): refs/frente.png y refs/espalda.png, cuerpo completo, mismo fondo y encuadre.
    La espalda usa la frente limpia + recortes de la hoja (y la espalda de la hoja si la hay). Todo SIN APROBAR."""
    err = revisar_guarda(a)
    if err: return {'ok': False, 'error': err, 'llamadas_hechas': 0}
    L = lectura_de(canal, hid)
    if not L or L.get('origen') != 'ia': return {'ok': False, 'error': 'primero hoja-leer (la lectura simulada no sirve para separar)', 'llamadas_hechas': 0}
    f = hoja_de(canal, hid); recortar(canal, hid, L); plan = plan_separar(L, set(solo or []) or None, set(forzar or ()))
    lista = [x for x in HV()['lista'] if not vistas or x in vistas]
    P = (X or {}).get('precios') or precios(canal)
    X = X or _app(); AR, T = X['AR'], X['types']; cli = X.get('cli') or AR._cliente()
    I = P['imagen']; m, talla = I['modelo'], I['talla']
    ritmo = LS.Ritmo(X['ritmo_dir'], m, LS.num_env('TALLER_PAUSA_IMAGEN_S', H()['separar']['pausa_s']), dormir=X.get('dormir', time.sleep))
    bolsa = {'gastado': 0.0}; corrida = time.strftime('%Y%m%d-%H%M%S'); res = []
    for q in plan:
        if not q['generar']: res.append({'version': q['etiqueta'], 'saltado': q['motivo_no']}); continue
        frente = None
        for vista in lista:
            spec = q['vistas'][vista]; refs = []
            for r in spec['refs']:
                if r == '@frente': r = frente or vista_guardada(canal, q, 'frente')
                refs.append(str(f) if r == '@hoja' else r)
            if None in refs: res.append({'version': q['etiqueta'], 'vista': vista, 'saltado': 'falta la vista de frente (hazla primero)'}); continue
            est = est_imagen(P, len(refs))
            partes = [T.Part.from_bytes(data=Path(r).read_bytes(), mime_type='image/png' if r.endswith('.png') else 'image/jpeg') for r in refs] + [T.Part.from_text(text=spec['texto'])]
            cfg_ = T.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'], image_config=T.ImageConfig(aspect_ratio=q['aspecto'], image_size=talla),
                                           http_options=T.HttpOptions(timeout=LS.timeout_ms('imagen')))   # orden 81: tope de tiempo (llamadas_config.json)
            def hacer(lid, k, q=q, est=est, partes=partes, cfg_=cfg_, vista=vista):
                ritmo.esperar()
                try: AR.registrar(lid, f'{m} {talla}', est, f"hoja {hid} separar {q['clave']} {vista} intento {k} (aprobado {a.aprobado})", tipo='imagen', ok_usd=est, tope_usd=H()['tope_por_llamada_usd'])
                except Exception as e: _no_llamado_si_no_anotado(AR, lid, e); raise
                try: return cli.models.generate_content(model=m, contents=[T.Content(role='user', parts=partes)], config=cfg_)
                except Exception as e:
                    AR.marcar(lid, LS.estado_fallo(e), est, ''); raise   # orden 81: «timeout» si se venció
            try: (lid, r), ints = _intentar(X, a, est, bolsa, f"taller-hoja-{hid}-{q['clave'][:36]}-{vista}-{corrida}", hacer)
            except LS.IntentosAgotados as e:
                if isinstance(e.ultimo, LS.SinPresupuesto) and len(e.intentos) == 1: res.append({'version': q['etiqueta'], 'vista': vista, 'saltado': str(e.ultimo)}); continue
                res.append({'version': q['etiqueta'], 'vista': vista, 'ok': False, 'error': str(e)[:300], 'intentos': e.intentos}); continue
            except LS.NoLlamado as e: res.append({'version': q['etiqueta'], 'vista': vista, 'ok': False, 'error': str(e)}); continue
            data = next((pt.inline_data.data for c in (r.candidates or []) for pt in ((c.content.parts or []) if c.content else []) if pt.inline_data and pt.inline_data.data), None)
            AR.marcar(lid, 'ok' if data else 'sin_imagen', est, ''); bolsa['gastado'] += est
            if not data: res.append({'version': q['etiqueta'], 'vista': vista, 'ok': False, 'error': 'el modelo no devolvió imagen', 'ledger': lid}); continue
            g = guardar_vista(canal, hid, q, vista, data, lid, refs, spec)
            if vista == 'frente': frente = str(PJ.raiz(canal) / g['imagen'])
            res.append({'version': q['etiqueta'], 'vista': vista, 'ok': True, 'ledger': lid, 'usd': est, 'completado_ia': bool(spec['completado']), **g})
    hechas = [x for x in res if 'saltado' not in x]
    return {'ok': all(x.get('ok') for x in hechas), 'accion': 'personajes hoja-separar', 'hoja': hid, 'vistas': lista, 'resultados': res, 'llamadas_hechas': len(hechas),
            'usd': round(bolsa['gastado'], 4), 'nota': 'imágenes SIN APROBAR (frente y espalda, cuerpo completo): revisa lo «completado_ia» y aprueba en el formulario'}

def vista_guardada(canal, q, vista):
    """Ruta de la vista ya guardada de esa versión (corrida anterior), o None."""
    p, v = q['p'], q['v']; m = PJ.leer_manifiesto(canal)
    pm = PJ.buscar_personaje(m, None, p.get('nombre_en_mapa') or p.get('nombre')) or PJ.buscar_personaje(m, None, p.get('nombre'))   # orden 85
    vm = PJ.buscar_version(pm, None, v.get('nombre_en_mapa') or v.get('nombre') or 'base') if pm else None
    rel = ((vm or {}).get('vistas') or {}).get(vista)
    return str(PJ.raiz(canal) / rel) if rel and (PJ.raiz(canal) / rel).is_file() else None

def reparar_refs(pm, vm, hid):
    """PISTA INMI (orden 77): «repara versiones». Cuando una versión SIN APROBAR ya tiene su imagen limpia de la hoja, las refs viejas
    que eran la HOJA ENTERA o la MISMA imagen que otra versión del personaje (p. ej. copiadas del estudio) salen de «refs» y pasan a
    «refs_reemplazadas» (el archivo queda en disco, nada se borra). Nunca toca refs subidas a mano (versión de origen «usuario»)
    ni versiones aprobadas."""
    if vm.get('estado') == 'aprobada' or vm.get('origen') == 'usuario': return []
    ro = vm.get('refs_origen') or {}
    if not any(ro.get(r) == 'hoja_ia' for r in vm.get('refs') or []): return []
    otras = {h for o in pm.get('versiones') or [] if o is not vm for h in (o.get('refs_sha256') or [])}
    refs, shas, fuera = [], [], []
    for r, h in zip(vm.get('refs') or [], vm.get('refs_sha256') or []):
        if ro.get(r) != 'hoja_ia' and (str(h).startswith(hid) or h in otras):
            fuera.append({'ref': r, 'sha256': h, 'motivo': 'era la hoja entera' if str(h).startswith(hid) else 'misma imagen que otra versión',
                          'hoja': hid, 'fecha': PJ.ahora()})
        else: refs.append(r); shas.append(h)
    if fuera:
        vm['refs'], vm['refs_sha256'] = refs, shas; vm.setdefault('refs_reemplazadas', []).extend(fuera)
    return fuera

def guardar_vista(canal, hid, q, vista, data, lid, refs, spec):
    """PISTA INMI (orden 80): imagen de UNA vista → refs/<vista>.png de su versión, SIN APROBAR, con completado_ia y la lista de lo
    completado (en la ficha .json y en vistas_info). La vista anterior y las imágenes limpias de antes pasan a refs_reemplazadas
    (el archivo queda en disco, renombrado si hace falta). Versión APROBADA → va a refs_propuestas, no se mezcla."""
    aplicar(canal, hid)   # asegura personaje y versión en el manifiesto
    p, v = q['p'], q['v']; pn = p.get('nombre_en_mapa') or p.get('nombre'); vn = v.get('nombre_en_mapa') or v.get('nombre') or 'base'
    with PJ.Candado(canal):
        m = PJ.leer_manifiesto(canal); pm = PJ.buscar_personaje(m, None, pn) or PJ.buscar_personaje(m, None, p.get('nombre'))   # orden 85
        vm = PJ.buscar_version(pm, None, vn)
        h = PJ.sha(data); R = PJ.raiz(canal); dst = R / pm['carpeta'] / vm['carpeta'] / 'refs'; dst.mkdir(parents=True, exist_ok=True)
        info = {'vista': vista, 'completado_ia': bool(spec['completado']), 'completado': list(spec['completado']), 'encuadre': HV()['encuadre'],
                'hoja': hid, 'ledger': lid, 'fecha': PJ.ahora()}
        meta = {'origen': 'hoja_ia', **info, 'refs_entrada': refs, 'texto': spec['texto'], 'aprobada': False}
        if vm.get('estado') == 'aprobada':
            o = dst / f'propuesta_{vista}_{h[:16]}.png'; o.write_bytes(data); PJ.escribir_json(o.with_suffix('.json'), meta)
            rel = str(o.relative_to(R)); vm.setdefault('refs_propuestas', []).append(rel)
            vm.setdefault('vistas_propuestas', {})[vista] = {'imagen': rel, **info}
            PJ.guardar_manifiesto(canal, m)
            return {'imagen': rel, 'donde': 'refs_propuestas (la versión ya estaba aprobada)'}
        o = dst / HV()[vista]['archivo']; rel = str(o.relative_to(R)); fuera = []
        pares = list(zip(vm.get('refs') or [], vm.get('refs_sha256') or []))
        if o.is_file():
            hv = PJ.sha(o.read_bytes())
            if hv != h:
                viejo = o.with_name(f'{o.stem}_{hv[:16]}{o.suffix}'); o.rename(viejo)
                if o.with_suffix('.json').is_file(): o.with_suffix('.json').rename(viejo.with_suffix('.json'))
                fuera.append({'ref': str(viejo.relative_to(R)), 'sha256': hv, 'motivo': f'vista «{vista}» anterior', 'hoja': hid, 'fecha': PJ.ahora()})
            pares = [(r, x) for r, x in pares if r != rel]
        o.write_bytes(data); PJ.escribir_json(o.with_suffix('.json'), meta)
        ro = vm.setdefault('refs_origen', {}); ro[rel] = 'hoja_ia'
        vs = vm.setdefault('vistas', {}); vs[vista] = rel; vm.setdefault('vistas_info', {})[vista] = info
        actuales = set(vs.values()); quedan = []
        for r, x in pares:
            if ro.get(r) == 'hoja_ia' and r not in actuales:
                fuera.append({'ref': r, 'sha256': x, 'motivo': 'imagen limpia anterior (antes del estándar frente/espalda)', 'hoja': hid, 'fecha': PJ.ahora()})
            elif r not in actuales: quedan.append((r, x))
        pv = [(vs[k], h if k == vista else PJ.sha((R / vs[k]).read_bytes())) for k in HV()['lista'] if vs.get(k) and (R / vs[k]).is_file()]
        vm['refs'] = [r for r, _ in pv + quedan]; vm['refs_sha256'] = [x for _, x in pv + quedan]
        if fuera: vm.setdefault('refs_reemplazadas', []).extend(fuera)
        vm['estado'] = 'pendiente'
        hoja_vieja = reparar_refs(pm, vm, hid)
        PJ.guardar_manifiesto(canal, m)
    n = len(fuera) + len(hoja_vieja)
    return {'imagen': rel, 'donde': 'refs (sin aprobar)' + (f' · {n} imagen(es) anterior(es) → refs_reemplazadas' if n else '')}

# ---------------- entrada ----------------
def main(accion, a, D=None):
    if accion == 'hoja-recibir': return recibir(a.canal, a.sesion)
    if accion == 'hoja-cotizar':
        sim = getattr(a, 'simulada', None)
        if sim:   # PISTA INMI: lectura hecha a mano (gratis). Queda como lectura_simulada.json y separar la rechaza.
            sim = json.loads(base64.urlsafe_b64decode(sim + '=' * (-len(sim) % 4)).decode('utf-8'))
            if not isinstance(sim, dict) or not isinstance(sim.get('personajes'), list): return {'ok': False, 'error': '--simulada no es una lectura'}
        return cotizar(a.canal, a.hoja, D, simulada=sim or None)
    if accion == 'hoja-aplicar': return aplicar(a.canal, a.hoja, D)
    if accion == 'hoja-leer': return leer(a.canal, a.hoja, a, D)
    if accion == 'hoja-separar':
        return separar(a.canal, a.hoja, a, D, solo=[s for s in (a.solo or '').split(',') if s], forzar=[s for s in (a.forzar or '').split(',') if s],
                       vistas=[s for s in (getattr(a, 'vistas', None) or '').split(',') if s] or None)
    raise ValueError('acción de hoja no válida')
