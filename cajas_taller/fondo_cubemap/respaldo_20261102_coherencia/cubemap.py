"""FC · fondo cubemap universal (1-nov-2026, Ricardo t401u). Entrada: «paso00_cadena cubemap <accion> --canal C --capitulo N --escena E».
Acciones:
  cubo      GRATIS: clona la escena de Blender SIN personajes y hace 6 renders grises F/B/L/R/U/D desde el origen de la cámara (cubemap)
            + molde gris CON personajes por cámara/cuadro (Imagen 2) + camaras.json.
  cotizar   GRATIS: precio de pintar las 6 caras UNA vez (modelo/talla/precio del canal, igual que paso00_pintar).
  pintar    PAGO: SOLO si existe cajas/HABILITAR_PAGO_FC ({"tope_usd": x, "aprobado": "…"}); ledger ANTES de cada llamada.
  proyectar GRATIS: por toma, proyecta el cubemap (pintado si existe; si no, el gris = prueba seca) desde la cámara de ESA toma → imagen1_fondo.png;
            imagen2_molde.png ya trae los personajes.
Salida: <capítulo>/cubos/FC/esc_<E>/ . Límite conocido: la proyección es de entorno (sin paralaje); cámaras lejos del origen ven el fondo
«pegado al infinito». Para tomas muy lejanas, hacer otro cubo con --origen."""
import argparse, glob, json, math, os, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent; CAJAS = AQUI.parent
BLENDER = os.environ.get('FC_BLENDER', '/opt/myia-argon-blender/herramientas/blender-5.2.2-linux-x64/blender')
HISTORIAL = Path('/opt/myia-argon-blender/historial')
GUARDA = CAJAS / 'HABILITAR_PAGO_FC'
CARAS = ['F', 'B', 'L', 'R', 'U', 'D']
NOMBRE = {'F': 'frente', 'B': 'atrás', 'L': 'izquierda', 'R': 'derecha', 'U': 'arriba (cielo/techo)', 'D': 'abajo (piso)'}


def carpeta_cap(canal, capitulo):
    sys.path.insert(0, str(CAJAS)); import paso01_cubos as K
    return K.carpeta(canal, capitulo)


def blend_escena(canal, capitulo, escena):
    pat = str(HISTORIAL / canal / str(int(capitulo)) / f'esc{int(escena):02d}_*' / 'escena_*.blend')
    fs = sorted(glob.glob(pat), key=os.path.getmtime)
    return fs[-1] if fs else None


def blender(blend, script_args, timeout=900):
    p = subprocess.run([BLENDER, '-b', blend, '--python', str(AQUI / 'cubemap_blender.py'), '--'] + script_args,
                       capture_output=True, text=True, timeout=timeout)
    for ln in p.stdout.splitlines()[::-1]:
        if ln.startswith('FC_JSON '): return json.loads(ln[8:])
    return {'ok': False, 'error': 'Blender no devolvió FC_JSON', 'cola': (p.stdout + p.stderr)[-800:]}


# ---------- proyección (numpy) ----------
def proyectar_toma(caras, imgs, t):
    import numpy as np
    W, H = t['W'], t['H']; M = np.array(t['matriz'])[:3, :3]
    f = t['lente_mm']; fit = t['sensor_fit']
    if fit == 'VERTICAL' or (fit == 'AUTO' and H > W): sh = t['sensor_h'] if fit == 'VERTICAL' else t['sensor_w']; sw = sh * W / H
    else: sw = t['sensor_w']; sh = sw * H / W
    big = max(sw, sh)
    xs = ((np.arange(W) + 0.5) / W - 0.5) * sw + t['shift'][0] * big
    ys = (0.5 - (np.arange(H) + 0.5) / H) * sh + t['shift'][1] * big
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, Y, -np.full_like(X, f)], -1) @ M.T   # rayo en mundo
    out = np.zeros((H, W, 3), np.float32); mejor = np.full((H, W), -np.inf)
    for k in CARAS:
        Fw = np.array(caras[k]['adelante'], float); Up = np.array(caras[k]['arriba'], float); Rt = np.array(caras[k]['derecha'], float)
        z = d @ Fw; m = (z > mejor) & (z > 0)
        if not m.any(): continue
        mejor = np.where(m, z, mejor)
        im = imgs[k]; N = im.shape[0]
        u = (d[m] @ Rt) / z[m]; v = (d[m] @ Up) / z[m]
        px = np.clip((u + 1) / 2 * N - 0.5, 0, N - 1); py = np.clip((1 - v) / 2 * N - 0.5, 0, N - 1)
        x0 = np.floor(px).astype(int); y0 = np.floor(py).astype(int); x1 = np.minimum(x0 + 1, N - 1); y1 = np.minimum(y0 + 1, N - 1)
        ax = (px - x0)[:, None]; ay = (py - y0)[:, None]
        out[m] = (im[y0, x0] * (1 - ax) * (1 - ay) + im[y0, x1] * ax * (1 - ay) + im[y1, x0] * (1 - ax) * ay + im[y1, x1] * ax * ay)
    return out


def cargar_caras(E):
    import numpy as np; from PIL import Image
    caras = json.load(open(E / 'caras.json'))['caras']
    pint = all((E / 'pintado' / f'{k}.png').is_file() for k in CARAS)
    src = 'pintado' if pint else 'gris'
    N = json.load(open(E / 'caras.json'))['res']
    imgs = {k: np.asarray(Image.open(E / src / f'{k}.png').convert('RGB').resize((N, N)), np.float32) for k in CARAS}
    return caras, imgs, src


def cmd_proyectar(E):
    import numpy as np; from PIL import Image
    if not (E / 'caras.json').is_file() or not (E / 'camaras.json').is_file(): return {'ok': False, 'error': 'falta el cubo: corre primero «cubemap cubo»'}
    caras, imgs, src = cargar_caras(E); tomas = json.load(open(E / 'camaras.json'))['tomas']; res = []
    for t in tomas:
        if t.get('tipo') != 'PERSP': res.append({'toma': t['toma'], 'saltado': f"cámara {t.get('tipo')} (solo PERSP)"}); continue
        o = proyectar_toma(caras, imgs, t); d = Path(t['molde']).parent; d.mkdir(parents=True, exist_ok=True)
        f1 = d / 'imagen1_fondo.png'; Image.fromarray(np.clip(o, 0, 255).astype('uint8')).save(f1)
        res.append({'toma': t['toma'], 'imagen1_fondo': str(f1), 'imagen2_molde': t['molde'], 'fuente_cubemap': src})
    man = {'ok': True, 'fuente_cubemap': src, 'prueba_seca': src == 'gris', 'tomas': res, 'fecha': time.strftime('%F %T %z')}
    json.dump(man, open(E / 'manifiesto.json', 'w'), ensure_ascii=False, indent=1)
    return man


def cmd_cubo(E, blend, origen='', cuadros=''):
    r1 = blender(blend, ['cubo', '--salida', str(E)] + (['--origen', origen] if origen else []))
    if not r1.get('ok'): return r1
    r2 = blender(blend, ['molde', '--salida', str(E)] + (['--cuadros', cuadros] if cuadros else []))
    if not r2.get('ok'): return r2
    return {'ok': True, 'blend_original': blend, 'clon_sin_personajes': r1['clon_sin_personajes'], 'origen': r1['origen'],
            'camara_origen': r1['camara_origen'], 'personajes_quitados': r1['personajes_quitados'], 'props_animados_quitados': r1.get('props_animados_quitados'), 'no_set_quitados': r1.get('no_set_quitados'), 'modo_lista_blanca_set': r1.get('modo_lista_blanca_set'), 'caras_grises': [r1['caras'][k]['png'] for k in CARAS],
            'n_tomas': r2['n_tomas']}


# ---------- pintura (pago) ----------
ESPERAS_429 = [20, 60, 120]   # inmi 2-nov: un 429 no cobra; se reintenta con espera creciente (máx 3) antes de rendirse


def _es_429(e):
    t = str(e)
    return '429' in t or 'RESOURCE_EXHAUSTED' in t or getattr(e, 'code', None) == 429

def _texto(k, estilo):
    return (f'Pinta esta vista gris de un escenario 3D (cara «{NOMBRE[k]}» de un cubemap de 90°). Conserva EXACTAMENTE la geometría, '
            'la perspectiva, los bordes y la posición de cada objeto; solo dale material, color, luz y textura. Sin personas ni personajes, '
            'sin texto. Debe empalmar sin costuras con las otras 5 caras (misma luz, misma hora, misma paleta).'
            + (f' Estilo: {estilo}' if estilo else ''))


def resolver_canal(canal, ET):
    """id exacto; si no existe, alias único: slug sin acentos vs id «cn-<slug>-<hash>» (la base guarda «gnesis» por la é perdida)."""
    import sqlite3, unicodedata, difflib, re
    if ET.canal_datos(canal) is not None: return canal
    n = lambda x: re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', x.lower()).encode('ascii', 'ignore').decode())
    s = sqlite3.connect(f'file:{ET.STUDIO_DB}?mode=ro', uri=True)
    try: ids = [r[0] for r in s.execute('SELECT id FROM channels')]
    finally: s.close()
    c = n(canal); hits = []
    for i in ids:
        core = n(re.sub(r'^cn-|-[0-9a-f]{6,}$', '', i))
        if core.startswith(c) or difflib.SequenceMatcher(None, c, core[:len(c)]).ratio() >= 0.9: hits.append(i)
    return hits[0] if len(hits) == 1 else canal


def _precio(canal):
    sys.path.insert(0, str(CAJAS)); import estilo_taller as ET, paso00_pintar as P
    cd = ET.canal_datos(resolver_canal(canal, ET))   # inmi 2-nov: alias (p.ej. «genesis-digital» -> cn-gnesis-digital-…)
    if cd is None: return None, None, None, f'el canal no está en la base del estudio ({canal})'
    try: I = ET.imagen_canal(cd); T = P.tramo(I['modelo'], I['talla'])
    except Exception as e: return None, None, None, f'ficha de imagen del canal: {e}'
    return I, T, P, None


def cmd_cotizar(E, canal):
    I, T, P, err = _precio(canal)
    if err: return {'ok': False, 'error': err}
    filas = [{'cara': k, 'peor_caso_usd': P.precio_llamada(I, T, len(_texto(k, '')) + 400, 1 if k == 'F' else 2)} for k in CARAS]
    tot = round(sum(x['peor_caso_usd'] for x in filas), 4)
    return {'ok': True, 'modelo': I['modelo'], 'talla': I['talla'], 'por_cara': filas, 'total_peor_caso_usd': tot, 'llamadas': 6,
            'una_vez_por_escenario': True, 'ya_pintado': all((E / 'pintado' / f'{k}.png').is_file() for k in CARAS),
            'para_pagar': f'crear cajas/{GUARDA.name} con {{"tope_usd": {tot}, "aprobado": "Ricardo …"}}'}


def cmd_pintar(E, canal):
    if not GUARDA.is_file(): return {'ok': True, 'cerrado': True, 'llamadas_pagas': 0, 'usd_gastado': 0, 'nota': f'pago cerrado (falta cajas/{GUARDA.name}); no se llamó a nada'}
    g = json.loads(GUARDA.read_text(encoding='utf-8')); tope = float(g.get('tope_usd') or 0); aprob = g.get('aprobado')
    if not aprob or tope <= 0: return {'ok': False, 'error': f'{GUARDA.name} sin tope_usd/aprobado: no se paga', 'llamadas_pagas': 0}
    if not (E / 'caras.json').is_file(): return {'ok': False, 'error': 'falta el cubo gris', 'llamadas_pagas': 0}
    I, T, P, err = _precio(canal)
    if err: return {'ok': False, 'error': err, 'llamadas_pagas': 0}
    import paso00_cadena as C
    C.bloquear_red(True)
    A_, P_, PB_, AR, FP_, F_ = C.cargar_app(C.copiar_datos(), C.ruta_credencial())
    from google.genai import types
    cli = AR._cliente(); m, talla = I['modelo'], I['talla']; corrida = time.strftime('%Y%m%d-%H%M%S')
    (E / 'pintado').mkdir(exist_ok=True); gastado = 0.0; res = []
    for k in CARAS:
        out = E / 'pintado' / f'{k}.png'
        if out.is_file(): res.append({'cara': k, 'saltado': 'ya pintada'}); continue
        imgs = [E / 'gris' / f'{k}.png'] + ([E / 'pintado' / 'F.png'] if k != 'F' and (E / 'pintado' / 'F.png').is_file() else [])
        txt = _texto(k, g.get('estilo', '')) + (' La segunda imagen es la cara frente YA pintada: copia su estilo y luz.' if len(imgs) > 1 else '')
        est = P.precio_llamada(I, T, len(txt), len(imgs))
        if gastado + est > tope + 1e-9: res.append({'cara': k, 'saltado': f'sin_presupuesto ({round(gastado,4)} + {est} > {tope})'}); break
        lid = f'taller00-FC-{E.name}-{k}-{corrida}'
        AR.registrar(lid, f'{m} {talla}', est, f'FC cubemap {E.name} cara {k} (aprobado {aprob})', tipo='imagen', ok_usd=est, tope_usd=P.TOPE_LLAMADA)
        partes = [types.Part.from_bytes(data=f.read_bytes(), mime_type='image/png') for f in imgs] + [types.Part.from_text(text=txt)]
        cfg = types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'], image_config=types.ImageConfig(aspect_ratio='1:1', image_size=talla))
        r = None; err = None
        for intento, espera in enumerate(ESPERAS_429 + [None]):   # inmi 2-nov: 429/RESOURCE_EXHAUSTED -> backoff 20/60/120 s; ledger ANTES de cada intento
            if intento: lid = f'{lid}-r{intento}'; AR.registrar(lid, f'{m} {talla}', est, f'FC cubemap {E.name} cara {k} reintento {intento} (aprobado {aprob})', tipo='imagen', ok_usd=est, tope_usd=P.TOPE_LLAMADA)
            try: r = cli.models.generate_content(model=m, contents=[types.Content(role='user', parts=partes)], config=cfg); err = None; break
            except Exception as e:
                err = e
                if _es_429(e) and espera is not None:
                    AR.marcar(lid, 'rechazado_429_sin_cobro', 0, ''); time.sleep(espera); continue
                break
        if err is not None:
            if _es_429(err): AR.marcar(lid, 'rechazado_429_sin_cobro', 0, ''); res.append({'cara': k, 'ok': False, 'error': '429 tras reintentos: ' + str(err)[:160]}); break
            AR.marcar(lid, 'error_posible_cobro', est, ''); gastado += est; res.append({'cara': k, 'ok': False, 'error': str(err)[:200]}); break
        data = next((pt.inline_data.data for c in (r.candidates or []) for pt in ((c.content.parts or []) if c.content else []) if pt.inline_data and pt.inline_data.data), None)
        cr = P.costo_real(I, T, getattr(r, 'usage_metadata', None), len(imgs)); usd = cr if cr is not None else est
        if data: out.write_bytes(data)
        AR.marcar(lid, 'ok' if data else 'sin_imagen', usd, str(out) if data else ''); gastado += usd
        res.append({'cara': k, 'ok': bool(data), 'usd': round(usd, 4), 'ledger': lid})
    return {'ok': all(x.get('ok', True) for x in res), 'llamadas_pagas': sum(1 for x in res if 'ledger' in x or 'error' in x),
            'usd_gastado': round(gastado, 4), 'tope_usd': tope, 'resultados': res}


def n8n(argv):
    ap = argparse.ArgumentParser(prog='cubemap')
    ap.add_argument('accion', choices=['cubo', 'cotizar', 'pintar', 'proyectar'])
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', default='1'); ap.add_argument('--escena', required=True)
    ap.add_argument('--origen', default=''); ap.add_argument('--cuadros', default='')
    a = ap.parse_args(argv); a.capitulo = str(int(float(a.capitulo)))
    D = carpeta_cap(a.canal, a.capitulo)
    if D is None: return {'ok': False, 'error': f'no hay carpeta del capítulo {a.capitulo}'}
    E = D / 'cubos' / 'FC' / f'esc_{a.escena}'; E.mkdir(parents=True, exist_ok=True)
    base = {'caja': 'FC', 'accion': a.accion, 'escena': a.escena, 'carpeta': str(E)}
    if a.accion == 'cubo':
        if not a.origen.strip():   # inmi 2-nov: --origen OBLIGATORIO (plan §1/§5: sin origen = FAIL). Valor = nombre de la cámara origen del cubo.
            return dict(base, ok=False, error='falta --origen <CAMARA>: el cubo debe declarar su cámara de origen (PLAN_FLUJO §5 FC)', llamadas_pagas=0, usd_gastado=0)
        b = blend_escena(a.canal, a.capitulo, a.escena)
        if not b: return dict(base, ok=True, nada_todavia=True, llamadas_pagas=0, usd_gastado=0, nota='aún no hay diseño de Blender de esta escena')
        r = cmd_cubo(E, b, a.origen, a.cuadros); r.update(llamadas_pagas=0, usd_gastado=0)
    elif a.accion == 'cotizar': r = cmd_cotizar(E, a.canal); r.update(llamadas_pagas=0, usd_gastado=0)
    elif a.accion == 'pintar': r = cmd_pintar(E, a.canal)
    else: r = cmd_proyectar(E); r.update(llamadas_pagas=0, usd_gastado=0)
    return dict(base, **r)


if __name__ == '__main__':
    print(json.dumps(n8n(sys.argv[1:]), ensure_ascii=False))
