"""PISTA INMI (2026-10-29): orden 70 · GALERÍA para ver en n8n (GRATIS, SOLO LECTURA, sin red, no escribe nada).

Uso (entrada SSH restringida, comando «ver» ya permitido):
  paso00_cadena ver galeria <cubo> --canal <canal> --capitulo <N|ep-…> [--solo id1,id2] [--tipos planta,cam,luz]

Un solo mecanismo para TODOS los cubos que hacen imágenes o videos (tabla CUBOS). Cada cubo dice:
  - qué se ESPERA (molde de Blender, prompts 4a4, fichas de objetos…) → lo que falta o falló sale en ROJO;
  - dónde están los archivos en la carpeta del capítulo.
Salida (una línea JSON):
  html            = galería LIVIANA (miniaturas JPG dentro del HTML, sin JavaScript, < ~0,9 MB) para el nodo HTML de n8n
                    (n8n la limpia y la muestra en un marco sin scripts: por eso agrandar es «pasar el mouse»).
  galeria_b64     = la MISMA galería como archivo HTML completo (imágenes ~1024 px y videos dentro), con clic para agrandar,
                    flechas y videos que se reproducen. El nodo Code de n8n la entrega en la pestaña Binary («galeria_<cubo>.html» → Download).
  archivos_video  = [{nombre, mime, b64}] cada video achicado (640 px) para verlo en n8n con «View» (pestaña Binary).
  grupos/faltan/fallaron/resumen.
"""
import argparse, base64, html as H, io, json, re, shutil, subprocess, tempfile
from pathlib import Path

TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
TOPE_LIGERA = 900 * 1024          # el panel de n8n muestra sin preguntar hasta ~1 MB de datos
TOPE_MEDIOS = 40 * 1024 * 1024    # imágenes grandes + videos del archivo completo
ANCHO_GRANDE = 1024
IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp')
VID_EXT = ('.mp4', '.webm', '.mov', '.mkv')

# Cubo → qué muestra. «fuente» = de dónde salen las imágenes (el cubo que las produce).
CUBOS = {
    '4a3': {'titulo': 'Moldes de Blender de los escenarios', 'fuente': '4a2', 'que': 'moldes', 'grupo': 'escenario'},
    '4a5': {'titulo': 'Escenarios pintados (Nano Banana)', 'fuente': '4a5', 'que': 'pintura', 'grupo': 'escenario'},
    '4a6': {'titulo': 'Escenarios pintados para revisar y recortar', 'fuente': '4a5', 'que': 'pintura', 'grupo': 'escenario',
            'nota': 'El recorte todavía no está programado.'},
    '4b3': {'titulo': 'Objetos de la historia', 'fuente': '4b2', 'que': 'objetos', 'fichas': '4b_objetos_historia.json',
            'carpeta': 'imagenes/4b2', 'grupo': 'dueño'},
    '4c3': {'titulo': 'Objetos del lugar', 'fuente': '4c2', 'que': 'objetos', 'fichas': '4c_objetos_lugar.json',
            'carpeta': 'imagenes/4c2', 'grupo': 'escenario'},
    '02a': {'titulo': 'Videos de Blender (escenas animadas)', 'fuente': '02', 'que': 'carpeta', 'carpeta': 'videos/02', 'grupo': 'escena'},
    '12':  {'titulo': 'Tomas pintadas (revisión después de pintar)', 'fuente': '11', 'que': 'carpeta', 'carpeta': 'imagenes/11', 'grupo': 'escena'},
    '16':  {'titulo': 'Videos animados para revisar', 'fuente': '15', 'que': 'carpeta', 'carpeta': 'videos/15', 'grupo': 'escena'},
}

def carpeta(canal, capitulo):
    b = TRABAJO / canal
    if not re.fullmatch(r'[A-Za-z0-9._-]+', canal or '') or not b.is_dir(): return None
    ds = sorted(b.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(b.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None

def _json(f):
    try: return json.loads(Path(f).read_text(encoding='utf-8'))
    except Exception: return None

def item(etiqueta, archivo=None, estado='ok', nota='', tipo=None):
    """estado: ok | falta | fallo | normal (sin imagen y está bien) | extra (fuera del plan)."""
    a = Path(archivo) if archivo else None
    if a is not None and not a.is_file():
        a = None
        if estado == 'ok': estado, nota = 'falta', nota or 'no está el archivo'
    if tipo is None: tipo = 'video' if a is not None and a.suffix.lower() in VID_EXT else 'imagen'
    return {'etiqueta': etiqueta, 'archivo': a, 'estado': estado, 'nota': nota, 'tipo': tipo}

# ---------------- qué se espera, por tipo ----------------
def _escenarios(D):
    fe = _json(D / 'ramas' / '4a_escenarios.json')
    if isinstance(fe, list) and fe: return [(x.get('id'), x.get('nombre') or x.get('id'), x) for x in fe if x.get('id')]
    md = D / 'ramas' / 'moldes'
    return [(d.name, d.name, {}) for d in sorted(md.iterdir()) if d.is_dir()] if md.is_dir() else []

def g_moldes(D, solo, tipos):
    grupos = []
    for eid, nombre, x in _escenarios(D):
        if solo and eid not in solo: continue
        d = D / 'ramas' / 'moldes' / eid; m = _json(d / 'molde.json'); its = []; aviso = ''
        if not m:
            if x.get('solo_recuerdo_o_pantalla'): aviso, est = 'Sin molde: es un recuerdo o una pantalla (está bien así).', 'normal'
            else: aviso, est = 'Todavía no tiene molde de Blender (falta correr 4a2).', 'falta'
            grupos.append({'id': eid, 'nombre': nombre, 'aviso': aviso, 'items': [item('sin molde', estado=est, nota=aviso)]}); continue
        if m.get('ok') is False: aviso = 'Blender falló en este escenario: ' + str(m.get('error') or 'ver blender.log')[:160]
        renders = set(m.get('renders') or [])
        cams = (_json(d / 'escenario.json') or {}).get('camaras_sugeridas') or ((x.get('investigacion') or {}).get('camaras_sugeridas')) or []
        if 'planta' in tipos: its.append(item('Planta (vista desde arriba)', d / 'planta.png'))
        if 'cam' in tipos:
            esperadas = {f"cam_{i:02d}_esc{c.get('escena')}.png": (i, c) for i, c in enumerate(cams, 1)}
            for f in sorted(set(esperadas) | {r for r in renders if r.startswith('cam_')}, key=lambda s: s):
                i, c = esperadas.get(f, (int(f[4:6]) if f[4:6].isdigit() else 0, {}))
                et = f"Cámara {i} · escena {c.get('escena', f.split('_esc')[-1][:-4])}" + (f" · {c.get('lente_mm')} mm" if c.get('lente_mm') else '')
                its.append(item(et, d / f, nota='' if f in renders or not renders else 'Blender no la dejó'))
        if 'luz' in tipos:
            for f in sorted((r for r in renders if r.startswith('luz_')), key=lambda s: int(re.sub(r'\D', '', s) or 0)):
                its.append(item(f"Luz de la escena {f[7:-4]}", d / f))
        grupos.append({'id': eid, 'nombre': nombre, 'aviso': aviso, 'items': its})
    return grupos, ([] if grupos else ['Todavía no hay escenarios (falta correr 4a / 4a2).'])

def _razon(r):
    if r is None: return 'todavía no se pintó'
    s = str(r.get('saltado') or '')
    if s.startswith('falta la imagen pintada de'): return 'no se pintó: faltaba su imagen base (' + s.split(' de ', 1)[-1] + ')'
    if s.startswith('sin_presupuesto'): return 'no se pintó: no alcanzó el presupuesto aprobado'
    if s: return 'no se pintó (' + s[:80] + ')'
    e = str(r.get('error') or '')
    if '429' in e: return 'falló: el servicio estaba ocupado (429, no se cobró)'
    return 'falló: ' + (e[:120] or 'sin imagen')

def g_pintura(D, solo, tipos):
    import paso00_pintar as P   # mismo 4a4 que usa la pintura (orden 68/69)
    p4 = P._leer_4a4(D) or {}
    carp = D / 'ramas' / 'imagenes' / '4a5'
    ult = {r.get('id'): r for r in ((_json(D / 'ramas' / 'resultado_4a5_pintar_correr.json') or {}).get('resultados') or [])}
    nombres = {eid: n for eid, n, _ in _escenarios(D)}
    vistos, grupos = set(), []
    def uno(oid, et):
        vistos.add(oid); f = carp / f'{oid}.png'
        if f.is_file(): return item(et, f)
        r = ult.get(oid)
        return item(et, estado='fallo' if r is not None else 'falta', nota=_razon(r))
    for x in p4.get('escenarios') or []:
        eid = x.get('escenario_id')
        if not eid or (solo and eid not in solo): continue
        aviso = ''
        try:
            rc = P.revisar_camaras_4a4(D, x)
            if not rc['completo']: aviso = 'No se pinta todavía: ' + P.LS.texto_camaras(rc).split(': ', 1)[-1] + '. Hay que volver a pedir su 4a4.'
        except Exception: pass
        b = x.get('base') or {}; its = []
        cb = str((b.get('camara') or {}).get('render') or '').replace('.png', '')
        its.append(uno(eid, 'Imagen base' + (f' · {cb}' if cb else '')))
        for k, v in enumerate(x.get('vistas') or [], 1):
            cr = str((v.get('camara') or {}).get('render') or '').replace('.png', '')
            its.append(uno(v.get('vista_id') or f'{eid}__vista{k}', f'Vista {k}' + (f' · {cr}' if cr else '')))
        for q in x.get('variantes') or []:
            vid = q.get('variante_id')
            if not vid: continue
            ev = q.get('en_vistas') or ['base']; nv = vid.split('__')[-1].lstrip('v')
            for t in ev:
                oid = vid if len(ev) == 1 else f'{vid}@{t}'
                sobre = 'base' if t == 'base' else ('vista ' + t.split('vista')[-1] if 'vista' in t else t)
                its.append(uno(oid, f'Variante {nv} (sobre la {sobre})'))
        if aviso:
            for i in its:
                if i['estado'] == 'falta': i['nota'] = 'no se pinta: 4a4 incompleto'
        grupos.append({'id': eid, 'nombre': nombres.get(eid, eid), 'aviso': aviso, 'items': its})
    extras = [f for f in sorted(carp.glob('*.png')) if f.stem not in vistos and (not solo or f.stem.split('__')[0] in solo)] if carp.is_dir() else []
    for f in extras:
        eid = f.stem.split('__')[0]
        g = next((g for g in grupos if g['id'] == eid), None)
        if g is None: g = {'id': eid, 'nombre': nombres.get(eid, eid), 'aviso': '', 'items': []}; grupos.append(g)
        g['items'].append(item(f.stem.replace(eid, '').strip('_') or 'imagen', f, estado='extra', nota='ya no está en el plan de 4a4'))
    av = [] if grupos else ['Todavía no hay prompts de 4a4 ni imágenes de 4a5.']
    return grupos, av

def g_objetos(D, solo, tipos, cfg):
    fo = _json(D / 'ramas' / cfg['fichas'])
    if not isinstance(fo, list): return [], [f"Todavía no hay fichas de objetos (falta correr {cfg['fichas'][:2]})."]
    carp = D / 'ramas' / cfg['carpeta']
    base = _json(D / 'respuestas' / 'base.json') or {}
    pers = {p.get('id'): p.get('nombre') for p in (base.get('catalogo_oficial') or {}).get('personajes', []) if isinstance(p, dict)}
    grupos = {}
    # PISTA INMI (2026-10-29): orden 72 — la pintura de objetos usa el motor de 4a5: lo que falló en la última corrida sale en ROJO
    # con su razón, y lo que no se pinta porque 4b1/4c1 vino incompleta (o no se investigó) lo dice.
    ult = {r.get('id'): r for r in ((_json(D / 'ramas' / f"resultado_{cfg['fuente']}_pintar_correr.json") or {}).get('resultados') or [])}
    try:
        import paso00_pintar as P
        K = P.CAJAS_PINTAR[cfg['fuente']]; regs, fall = P.investigacion_valida(D, K['inv']); cinv = K['cubo_inv']
    except Exception: regs, fall, cinv = None, {}, ''
    nu = (_json(carp / 'NO_USAR.json') or {}).get('items') or []   # PISTA INMI (2026-10-29): orden 75 — marcadas «no usar» (no se borran)
    nu = {z.get('id'): z for z in nu if isinstance(z, dict)}
    etq = lambda i, t: (f'⛔ NO USAR · {t}', 'no usar: ' + str(nu[i].get('motivo') or '')[:110]) if i in nu else (t, '')
    for x in fo:
        oid = x.get('objeto_id')
        if not oid or (solo and oid not in solo): continue
        if cfg['grupo'] == 'dueño': gk = x.get('dueno_id') or 'sin dueño'; gn = 'De: ' + (pers.get(gk) or ('sin dueño' if gk in ('', 'falta', 'sin dueño') else gk))
        else: gk = x.get('escenario_id') or x.get('escenario_nombre') or 'sin escenario'; gn = x.get('escenario_nombre') or gk
        g = grupos.setdefault(gk, {'id': gk, 'nombre': gn, 'aviso': '', 'items': []})
        f = carp / f'{oid}.png'
        if f.is_file(): e_, n_ = etq(oid, x.get('nombre') or oid); g['items'].append(item(e_, f, nota=n_))
        elif oid in ult: g['items'].append(item(x.get('nombre') or oid, estado='fallo', nota=_razon(ult[oid])))
        elif regs is not None and oid not in regs:
            g['items'].append(item(x.get('nombre') or oid, estado='falta', nota=(f"no se pinta: {cinv} incompleto — {fall[oid][:110]}" if oid in fall
                                                                                 else f"no se pinta: {cinv} todavía no investigó este objeto")))
        else: g['items'].append(item(x.get('nombre') or oid, estado='falta', nota=f"todavía sin imagen (la pinta {cfg['carpeta'].split('/')[-1]})"))
        hechos = set()
        for e in sorted(carp.glob(f'{oid}__*.png')) if carp.is_dir() else []:
            hechos.add(e.stem); e_, n_ = etq(e.stem, 'estado: ' + e.stem.split('__', 1)[1]); g['items'].append(item(e_, e, nota=n_))
        for sid, r in ult.items():   # estados que fallaron en la última corrida (y no tienen imagen)
            if sid and sid.startswith(f'{oid}__') and sid not in hechos:
                g['items'].append(item('estado: ' + sid.split('__', 1)[1], estado='fallo', nota=_razon(r)))
    return list(grupos.values()), []

def g_carpeta(D, solo, tipos, cfg):
    carp = D / 'ramas' / cfg['carpeta']
    if not carp.is_dir(): return [], [f"Todavía no hay archivos: la caja {cfg['fuente']} no ha dejado nada en ramas/{cfg['carpeta']} (aún no está programada o no ha corrido)."]
    grupos, nombres = {}, {eid: nom for eid, nom, _ in _escenarios(D)}
    for f in sorted(p for p in carp.rglob('*') if p.is_file() and p.suffix.lower() in IMG_EXT + VID_EXT):
        gk = f.parent.name if f.parent != carp else f.stem.split('__')[0]
        if solo and gk not in solo: continue
        g = grupos.setdefault(gk, {'id': gk, 'nombre': nombres.get(gk) or re.sub(r'^esc(?:ena)?[-_]?(\d+)$', r'Escena \1', gk), 'aviso': '', 'items': []})
        meta = _json(f.with_suffix('.json')) or {}
        if meta.get('ok') is False: g['items'].append(item(f.stem, estado='fallo', nota='falló: ' + str(meta.get('error') or '')[:100])); continue
        g['items'].append(item(f.stem.replace(gk, '').strip('_') or f.stem, f))
    return list(grupos.values()), ([] if grupos else [f"La carpeta ramas/{cfg['carpeta']} está vacía."])

# ---------------- miniaturas y medios ----------------
def _abrir(f):
    from PIL import Image
    im = Image.open(f); im.load()
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); fondo = Image.new('RGB', im.size, (34, 34, 34)); fondo.paste(im, mask=im.split()[-1]); im = fondo
    elif im.mode != 'RGB': im = im.convert('RGB')
    return im

def _jpg(im, ancho, q):
    from PIL import Image
    w, h = im.size
    if w > ancho: im = im.resize((ancho, max(1, round(h * ancho / w))), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True); return b.getvalue()

def miniatura(im, presupuesto):
    """La miniatura más grande que entra en el presupuesto (bytes)."""
    for ancho, q in ((480, 72), (400, 68), (320, 64), (256, 60), (200, 55), (160, 50), (120, 45)):
        d = _jpg(im, ancho, q)
        if len(d) <= presupuesto: return d
    return d

def cuadro_video(f):
    """Un cuadro del video (al 10 %) como imagen + duración. Sin ffmpeg → None."""
    ff, fp = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if not ff: return None, None
    dur = None
    try:
        if fp: dur = float(subprocess.run([fp, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)], capture_output=True, text=True, timeout=30).stdout.strip() or 0) or None
    except Exception: dur = None
    with tempfile.TemporaryDirectory() as t:
        o = Path(t) / 'c.jpg'
        try: subprocess.run([ff, '-v', 'error', '-y', '-ss', str(round((dur or 0) * 0.1, 2)), '-i', str(f), '-frames:v', '1', str(o)], capture_output=True, timeout=60)
        except Exception: return None, dur
        return (_abrir(o) if o.is_file() else None), dur

def video_chico(f, tope):
    """MP4 de 640 px para verlo en n8n (no se toca el original). Si no entra o no hay ffmpeg → None."""
    ff = shutil.which('ffmpeg')
    if not ff: return None
    with tempfile.TemporaryDirectory() as t:
        o = Path(t) / 'v.mp4'
        try:
            subprocess.run([ff, '-v', 'error', '-y', '-i', str(f), '-vf', "scale='min(640,iw)':-2", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '30',
                            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', str(o)], capture_output=True, timeout=300)
        except Exception: return None
        if not o.is_file() or o.stat().st_size > tope: return None
        return o.read_bytes()

# ---------------- HTML ----------------
CSS = ('body{margin:0;font:13px/1.35 system-ui,-apple-system,Segoe UI,sans-serif;background:#141414;color:#eee}'
       '.cab{padding:10px 14px;background:#1d1d1d;border-bottom:1px solid #333}.cab b{font-size:15px}.cab .r{color:#bbb;margin-top:3px}'
       '.cab .ay{color:#8fc1ff;margin-top:4px}.av{color:#ffb3b3;margin:4px 0}.g{padding:4px 14px 10px}'
       '.g h2{font-size:14px;margin:12px 0 4px;color:#fff}.g .n{color:#999;font-weight:normal;font-size:12px}'
       '.ga{background:#3a1717;border:1px solid #a33;color:#ffc9c9;border-radius:6px;padding:4px 8px;margin:4px 0 6px;font-size:12px}'
       '.f{display:flex;flex-wrap:wrap;gap:8px}.c{width:196px;background:#1f1f1f;border:1px solid #383838;border-radius:8px;overflow:hidden;position:relative}'
       '.m{height:110px;background-color:#262626;background-size:cover;background-position:center;background-repeat:no-repeat}'
       '.e{padding:4px 7px 6px;font-size:12px;color:#ddd}.e i{display:block;font-style:normal;font-size:11px;color:#999}'
       '.c.falta,.c.fallo{border-color:#d33}.c.falta .m,.c.fallo .m{background:#3a1515;color:#ff8a8a;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:bold;padding:6px}'
       '.c.falta .e i,.c.fallo .e i{color:#ff8a8a}.c.normal .m{background:#232a33;color:#9ab;display:flex;align-items:center;justify-content:center;text-align:center;padding:6px}'
       '.c.extra{border-style:dashed}.c .v{position:absolute;left:6px;top:6px;background:#000b;color:#fff;border-radius:10px;padding:1px 7px;font-size:11px}'
       '.z{display:none;position:fixed;left:1%;top:1%;width:98%;height:98%;background-color:#000e;background-size:contain;background-position:center;'
       'background-repeat:no-repeat;pointer-events:none;z-index:9;border-radius:6px}.c:hover .z{display:block}.c:hover{border-color:#8fc1ff}')

def _t(s):   # texto seguro (y sin «{{», que n8n leería como expresión)
    return H.escape(str(s or '')).replace('{{', '{ {').replace('}}', '} }')

ETQ = {'falta': 'FALTA', 'fallo': 'FALLÓ', 'normal': '—', 'extra': ''}

def armar(cubo, cfg, grupos, avisos, ancho_grande=ANCHO_GRANDE):
    todos = [i for g in grupos for i in g['items']]
    con = [i for i in todos if i['archivo'] is not None]
    presupuesto = int((TOPE_LIGERA - 60 * 1024 - 900 * len(todos)) * 0.75 / max(1, len(con)))
    css, ligera, completa, medios, total_m, cortados = [], [], [], [], 0, []
    for k, i in enumerate(todos):
        i['k'] = k
        if i['archivo'] is None: continue
        try:
            if i['tipo'] == 'video':
                im, dur = cuadro_video(i['archivo']); i['duracion'] = dur
                data = video_chico(i['archivo'], TOPE_MEDIOS - total_m)
                if im is None and not data and shutil.which('ffmpeg'):
                    i.update(archivo=None, estado='fallo', nota='no se pudo leer el video (archivo dañado o incompleto)'); continue
                if im is None:
                    from PIL import Image
                    im = Image.new('RGB', (320, 180), (40, 40, 60))
                    if not shutil.which('ffmpeg'): i['nota'] = 'sin vista previa (falta ffmpeg en el servidor)'
                if data: medios.append({'n': len(medios), 'mime': 'video/mp4', 'b64': base64.b64encode(data).decode(), 'nombre': i['archivo'].stem + '.mp4'}); i['medio'] = medios[-1]['n']; total_m += len(data)
                else: cortados.append(i['archivo'].name)
            else:
                im = _abrir(i['archivo'])
                g = _jpg(im, ancho_grande, 82)
                if total_m + len(g) <= TOPE_MEDIOS:
                    medios.append({'n': len(medios), 'mime': 'image/jpeg', 'b64': base64.b64encode(g).decode(), 'nombre': i['archivo'].stem + '.jpg'}); i['medio'] = medios[-1]['n']; total_m += len(g)
                else: cortados.append(i['archivo'].name)
            i['mini'] = base64.b64encode(miniatura(im, presupuesto)).decode()
            css.append(f".i{k}{{background-image:url(data:image/jpeg;base64,{i['mini']})}}")
        except Exception as e:
            i.update(archivo=None, estado='fallo', nota=f'no se pudo abrir ({type(e).__name__})')
    faltan = [f"{g['nombre']}: {i['etiqueta']}" for g in grupos for i in g['items'] if i['estado'] == 'falta']
    fallaron = [f"{g['nombre']}: {i['etiqueta']} ({i['nota']})" for g in grupos for i in g['items'] if i['estado'] == 'fallo']
    n_img = sum(1 for i in todos if i['archivo'] is not None and i['tipo'] == 'imagen'); n_vid = sum(1 for i in todos if i['archivo'] is not None and i['tipo'] == 'video')
    pl = lambda n, s1, s2: f"{n} {s1 if n == 1 else s2}"
    res = (pl(n_img, 'imagen', 'imágenes') + (' y ' + pl(n_vid, 'video', 'videos') if n_vid else '') + ' de ' + pl(len(grupos), cfg['grupo'], cfg['grupo'] + 's')
           + (f" · faltan {len(faltan)}" if faltan else '') + (f" · fallaron {len(fallaron)}" if fallaron else '') + (' · todo completo' if todos and not faltan and not fallaron else ''))
    titulo = f"{cubo} · {cfg['titulo']}"
    def cuerpo(completo):
        out = []
        for g in grupos:
            out.append(f"<div class=\"g\"><h2>{_t(g['nombre'])} <span class=\"n\">· {len([i for i in g['items'] if i['archivo'] is not None])} de {len(g['items'])}</span></h2>")
            if g.get('aviso'): out.append(f"<div class=\"ga\">{_t(g['aviso'])}</div>")
            out.append('<div class="f">')
            for i in g['items']:
                k, est = i['k'], i['estado'] if i['archivo'] is None else ('extra' if i['estado'] == 'extra' else 'ok')
                vid = '<span class="v">▶ video' + (f" {round(i['duracion'])} s" if i.get('duracion') else '') + '</span>' if i['tipo'] == 'video' and i['archivo'] is not None else ''
                nota = f"<i>{_t(i['nota'])}</i>" if i['nota'] else ''
                if i['archivo'] is None:
                    out.append(f"<div class=\"c {est}\"><div class=\"m\">{_t(ETQ.get(est, ''))}</div><div class=\"e\">{_t(i['etiqueta'])}{nota}</div></div>")
                elif completo:
                    out.append(f"<div class=\"c {est}\" data-k=\"{k}\" data-t=\"{_t(g['nombre'] + ' · ' + i['etiqueta'])}\" data-m=\"{i.get('medio', '')}\" data-tipo=\"{i['tipo']}\">"
                               f"<div class=\"m i{k}\"></div>{vid}<div class=\"e\">{_t(i['etiqueta'])}{nota}</div></div>")
                else:
                    out.append(f"<div class=\"c {est}\"><div class=\"m i{k}\"></div>{vid}<div class=\"e\">{_t(i['etiqueta'])}{nota}</div><div class=\"z i{k}\"></div></div>")
            out.append('</div></div>')
        return ''.join(out)
    av = ''.join(f"<div class=\"av\">{_t(a)}</div>" for a in avisos + ([cfg['nota']] if cfg.get('nota') else []))
    ayuda_l = ('Pasa el mouse sobre una miniatura para verla grande. Para abrirlas con clic, pasar con flechas y reproducir los videos: '
               f'abre el cubo «{cubo} · galería (armar)», pestaña Binary, archivo «galeria_{cubo}.html» → Download y ábrelo en el navegador.')
    cab = lambda ay: f"<div class=\"cab\"><b>{_t(titulo)}</b><div class=\"r\">{_t(res)}</div>{av}<div class=\"ay\">{_t(ay)}</div></div>"
    ligera = f"<style>{CSS}{''.join(css)}</style>{cab(ayuda_l)}{cuerpo(False)}"
    if not todos: ligera = f"<style>{CSS}</style>{cab('Cuando haya imágenes o videos aparecerán aquí, agrupados.')}"
    js = ('<div id="lb"><div id="vis"></div><div id="tt"></div><button id="an">‹</button><button id="si">›</button><button id="ce">✕ cerrar (Esc)</button></div>'
          '<script>const M=window.MEDIOS||{};const cs=[...document.querySelectorAll(".c[data-k]")];let cur=-1;const $=s=>document.querySelector(s);'
          'function ab(n){cur=(n+cs.length)%cs.length;const c=cs[cur],m=M[c.dataset.m];$("#tt").textContent=c.dataset.t;'
          '$("#vis").innerHTML=!m?"<p>(no entró en el archivo; está en el servidor)</p>":c.dataset.tipo=="video"?`<video controls autoplay src="${m}"></video>`:`<img src="${m}">`;$("#lb").className="on";}'
          'cs.forEach((c,n)=>c.onclick=()=>ab(n));$("#ce").onclick=()=>{$("#lb").className="";$("#vis").innerHTML="";};$("#an").onclick=()=>ab(cur-1);$("#si").onclick=()=>ab(cur+1);'
          'onkeydown=e=>{if($("#lb").className!="on")return;if(e.key=="Escape")$("#ce").click();if(e.key=="ArrowLeft")ab(cur-1);if(e.key=="ArrowRight")ab(cur+1);};</script>')
    css_c = ('.c[data-k]{cursor:zoom-in}#lb{display:none;position:fixed;inset:0;background:#000f;z-index:9}#lb.on{display:block}'
             '#vis{position:absolute;inset:40px 50px 10px;display:flex;align-items:center;justify-content:center}#vis img,#vis video{max-width:100%;max-height:100%}'
             '#tt{position:absolute;top:10px;left:14px;right:160px;color:#fff;font-size:14px}#lb button{position:absolute;background:#333;color:#fff;border:0;border-radius:6px;padding:6px 12px;font-size:18px;cursor:pointer}'
             '#an{left:8px;top:50%}#si{right:8px;top:50%}#ce{right:10px;top:6px;font-size:13px!important}')
    medios_js = '<script>window.MEDIOS={' + ','.join(f'"{m["n"]}":"data:{m["mime"]};base64,{m["b64"]}"' for m in medios) + '};</script>'
    completa = (f"<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><title>{_t(titulo)}</title><style>{CSS}{css_c}{''.join(css)}</style></head><body>"
                f"{cab('Clic en una miniatura para verla grande (flechas ← → para pasar, Esc para cerrar). Los videos se reproducen al abrirlos.')}"
                f"{cuerpo(True)}{medios_js}{js}</body></html>")
    resumen_grupos = [{'id': g['id'], 'nombre': g['nombre'], 'aviso': g.get('aviso') or '', 'total': len(g['items']),
                       'con_archivo': sum(1 for i in g['items'] if i['archivo'] is not None),
                       'items': [{'etiqueta': i['etiqueta'], 'estado': i['estado'] if i['archivo'] is None else ('extra' if i['estado'] == 'extra' else 'ok'),
                                  'nota': i['nota'], 'tipo': i['tipo'], 'archivo': i['archivo'].name if i['archivo'] else None} for i in g['items']]} for g in grupos]
    completa_b = completa.encode('utf-8')
    return {'titulo': titulo, 'html': ligera, 'bytes_html': len(ligera.encode()), 'galeria_b64': base64.b64encode(completa_b).decode(),
            'bytes_galeria': len(completa_b), 'archivos_video': [{'nombre': m['nombre'], 'mime': m['mime'], 'b64': m['b64']} for m in medios if m['mime'].startswith('video/')],
            'bytes_medios': total_m, 'no_entraron': cortados, 'imagenes': n_img, 'videos': n_vid, 'faltan': faltan, 'fallaron': fallaron,
            'grupos': resumen_grupos, 'resumen': res}

def main(argv):
    ap = argparse.ArgumentParser(prog='ver galeria')
    ap.add_argument('cubo', choices=sorted(CUBOS))
    ap.add_argument('--canal', required=True)
    ap.add_argument('--capitulo', required=True)
    ap.add_argument('--solo', default='')
    ap.add_argument('--tipos', default='planta,cam')
    a = ap.parse_args(argv)
    cfg = CUBOS[a.cubo]
    D = carpeta(a.canal, a.capitulo)
    base = {'ok': True, 'caja': 'ver', 'que': 'galeria', 'cubo': a.cubo, 'fuente': cfg['fuente'], 'gratis': True, 'solo_lectura': True}
    if not D: return dict(base, ok=False, error=f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}')
    solo = {x for x in a.solo.split(',') if x}; tipos = {x.strip() for x in a.tipos.split(',') if x.strip()}
    q = cfg['que']
    grupos, avisos = (g_moldes(D, solo, tipos) if q == 'moldes' else g_pintura(D, solo, tipos) if q == 'pintura'
                      else g_objetos(D, solo, tipos, cfg) if q == 'objetos' else g_carpeta(D, solo, tipos, cfg))
    r = armar(a.cubo, cfg, grupos, avisos)
    return dict(base, carpeta=str(D), avisos=avisos, **r)
