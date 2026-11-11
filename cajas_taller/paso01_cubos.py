"""PISTA INMI (2026-10-29): orden 74 — «ajustes Argon» a los cubos 01–14 del flujo n8n (Ricardo/Argon). GRATIS: solo cotiza y calcula.
Uso (por la entrada SSH restringida, dentro de la acción «ver» que ya está permitida):
  paso00_cadena ver cubo <01|02|03|04|05|06|07|08|09|10|11|14> --canal <canal> --capitulo <N|ep-…> [--escena 3,8]
PISTA INMI (2026-10-29): va por «ver cubo …» para NO tocar paso00_cadena.py / entrada_ssh.sh mientras corre la prueba pagada de 4c2
(orden 73). Cuando termine, pasar esto a su propia acción «cubos» en paso00_cadena.py y en la lista permitida de entrada_ssh.sh.

Qué hace cada cubo (todo genérico, regla 6: nada de un canal ni de un episodio; lo que no hay se marca como PISTA/falta):
  01  Cotiza Argon «dirige la escena» (PASO_01 de la app) por escena. NUNCA llama: solo precio.
  02  (orden 78) Blender GRATIS anima la salida del 01: figuras de relleno por personaje que siguen sus recorridos, y un video corto
      de vista previa por toma desde SU cámara (05 → 01 → molde). Videos en ramas/videos/02/esc_<N>/ (los muestra la galería 02a).
      Sin salida del 01 se PARA con aviso: nunca inventa posiciones. Ajustes en paso01_datos/animacion_02.json.
  03  Lee el veredicto de coherencia (si existe) y cotiza Argon A; da la decisión del bucle 03↔04 (máx. vueltas en paso01_datos/bucles.json).
  04  Aplica las correcciones milimétricas del 03 sobre la salida del 01 (gratis) → cubos/04/esc_N.json.
  05  Catálogo de tipos de plano (paso01_datos/tipos_plano.json) × cámaras del molde de Blender → opciones de toma calculadas,
      eje de 180° calculado con las cámaras REALES del molde (Blender) + plan borrador del código (sin Argon) + cotización ARGON_B_v6.
  06  Blender (gratis): pone cada cámara de toma y proyecta personajes y partes del cuerpo con world_to_camera_view.
  07  Lado EN LA IMAGEN de cada rasgo lateral (brazalete, herida, daño…): izquierda/derecha del cuadro, visible o tapado por el cuerpo.
  08  Escribe las posiciones relativas al cuadro (cubos/08/posiciones_cuadro.json) para los prompts por viñeta; cotiza (plantilla falta).
  09  Chequeos GRATIS antes de cualquier validador pago: salto de eje, lado de rasgos que cambia, personaje cortado o fuera, tamaño.
  10  Cruza camara_id de cada toma con la pintura 4a5 (la vista pintada de ESA cámara) y arma tiras de 8.
  11  (orden 87) «Híbrido tira»: pedido Nano Banana sobre la hoja de moldes del 02 + versiones APROBADAS (cubo11_tira.py). Cotiza por defecto.
  14  Decide encadenado vs corte entre tomas con la regla de paso01_datos/reglas_encadenado.json + trucos T1–T12 de Star; cotiza ARGON_VIDEO_v1.
Escribe SOLO en <capítulo>/cubos/<cubo>/ (el 02 además sus videos en ramas/videos/02/). No toca ramas/, ledger, HABILITAR_PAGO*, ni las cajas 4a4/4a5/4b2/4c2.
Salida: una línea JSON {ok, caja:'cubo', cubo, gratis:true, resumen, faltan[], pistas[], …}."""
import argparse, json, math, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, unicodedata
from pathlib import Path

CAJAS = Path(__file__).resolve().parent
DATOS = CAJAS / 'paso01_datos'
TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
REPO = Path(os.environ.get('MYIA_TALLER_APP_REPO') or '/opt/myia-staging-arreglos-20261026/repo')
BLENDERS = [os.environ.get('MYIA_BLENDER') or '', '/opt/myia-herramientas/blender-4.2.3-linux-x64/blender', '/opt/blender/actual/blender',
            '/workspace/tools/blender-4.2.3-linux-x64/blender']
TOKENS_IMG_PEOR =[REDACTED]
CUBOS = ('01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '14')   # PISTA INMI (2026-10-29): orden 87 — + 11 «híbrido tira» (cubo11_tira.py)
CAM_RX = re.compile(r'^cam_(\d+)_esc(.+)$')
CANAL_DATOS = None        # las pruebas lo cambian por uno falso (sin base de datos)
PERSONAJES_CANAL = None


# ---------------- utilidades ----------------
def carpeta(canal, capitulo):
    b = TRABAJO / canal
    if not re.fullmatch(r'[A-Za-z0-9._-]+', canal or '') or not b.is_dir(): return None
    ds = sorted(b.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(b.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None


def leer(f, d=None):
    try: return json.loads(Path(f).read_text(encoding='utf-8'))
    except Exception: return d


def guardar(f, x):
    f = Path(f); f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + '.tmp'); tmp.write_text(json.dumps(x, ensure_ascii=False, indent=1), encoding='utf-8'); tmp.replace(f)
    return str(f)


def dato(nombre): return leer(DATOS / nombre, {})


def _norm(s):
    s = unicodedata.normalize('NFKD', str(s or '').lower()); return ''.join(c for c in s if not unicodedata.combining(c))


def canal(canal_id):
    if CANAL_DATOS: return CANAL_DATOS(canal_id) or {}
    try:
        import estilo_taller as ET
        return ET.canal_datos(canal_id) or {}
    except Exception:
        return {}


def personajes_canal(canal_id):
    """id → {nombre, formas{forma_id: altura_m}} desde la base del estudio (solo lectura)."""
    if PERSONAJES_CANAL: return PERSONAJES_CANAL(canal_id) or {}
    out = {}
    try:
        import estilo_taller as ET
        ids = (canal(canal_id) or {}).get('characters') or []
        s = sqlite3.connect(f'file:{ET.STUDIO_DB}?mode=ro', uri=True)
        try:
            for cid in ids:
                r = s.execute('SELECT id, name, formas FROM characters WHERE id=?', (cid,)).fetchone()
                if not r: continue
                fs = json.loads(r[2] or '[]') if isinstance(r[2], str) else (r[2] or [])
                out[r[0]] = {'nombre': r[1], 'formas': {f.get('id'): {'nombre': f.get('nombre'), 'altura_m': f.get('altura_m'),
                                                                       'accesorios': f.get('accesorios'), 'imagenes_referencia': f.get('imagenes_referencia') or []} for f in fs if isinstance(f, dict)}}
        finally: s.close()
    except Exception:
        pass
    return out


def aspecto(cd):
    a = str((cd or {}).get('aspect') or (cd or {}).get('aspecto') or '')
    m = re.fullmatch(r'\s*(\d+)\s*:\s*(\d+)\s*', a)
    if not m: return None
    w, h = int(m.group(1)), int(m.group(2)); return [1920, int(round(1920 * h / w))] if w >= h else [int(round(1920 * w / h)), 1920]


def escenas(D, solo=None):
    b = leer(D / 'respuestas' / 'base.json', {}) or {}
    out = []
    for e in b.get('escenas') or []:
        n = str(e.get('numero'))
        if solo and n not in solo: continue
        out.append({'numero': n, 'escenario_id': e.get('escenario_id'), 'titulo': e.get('titulo'),
                    'personajes': [p.get('personaje_id') for p in e.get('personajes') or [] if p.get('presencia') == 'en_cuadro'],
                    'datos': e})
    return out


def dirigida(D, n, importados=False):
    """Dirección actual de la escena n (formato PASO_01): la ÚLTIMA versión (v0 = cubos/01/esc_N.json; v1… = cubos/04/esc_N.v<k>.json, orden 82).
    PISTA INMI (orden 79): un plan aprobado IMPORTADO (importar_plan_aprobado.py, marca «importado») NO cuenta como corrida del 01
    para nadie salvo quien lo pide a propósito (el 02, para ensayar)."""
    import paso01_revision as RV
    v = RV.actual(sys.modules[__name__], D, n, importados)
    if not v: return None, None
    return v['C'], ('01' if v['k'] == 0 else f"04 v{v['k']}")


def _argon():
    for p in (str(REPO / 'web'), str(REPO)):
        if p not in sys.path: sys.path.insert(0, p)
    import myia_argon as AR
    return AR


def modelo_canal(cd):
    p = (cd or {}).get('paso01') or {}
    return p.get('argon_modelo'), p.get('argon_nivel'), p.get('max_output_tokens')


def cotizar(chars, n_img, cd, para):
    """Precio PEOR CASO de UNA llamada (texto + imágenes + salida máxima). Nunca llama a Argon."""
    modelo, nivel, mo = modelo_canal(cd)
    if not modelo or not mo:
        return {'ok': False, 'usd': None, 'motivo': 'el canal no fija paso01.argon_modelo / max_output_tokens: no se puede cotizar (decide Ricardo)'}
    try:
        AR = _argon()
        usd = round(AR.estimar(int(chars), max_out=int(mo), modelo=modelo) + n_img * TOKENS_IMG_PEOR * AR.precio(modelo)[0] / 1e6, 4)
    except Exception as e:
        return {'ok': False, 'usd': None, 'motivo': f'no pude cargar el tarifario de myia_argon ({type(e).__name__})'}
    r = {'ok': True, 'usd': usd, 'modelo': modelo, 'nivel': nivel, 'max_salida_tokens': int(mo), 'chars_texto': int(chars),
         'imagenes': n_img, 'tokens_imagenes_peor': n_img * TOKENS_IMG_PEOR, 'para': para}
    if para != '01':
        r['pista'] = (f'PISTA INMI (2026-10-29): el canal no fija modelo para el cubo {para}; se cotiza con el del paso 01 '
                      f'({modelo} {nivel}) hasta que Ricardo fije uno.')
    return r


def plantilla(nombre):
    f = REPO / 'web' / 'prompts_argon' / nombre
    return f.read_text(encoding='utf-8') if f.is_file() else None


def _j(x): return json.dumps(x, ensure_ascii=False)


# ---------------- molde de Blender ----------------
def blender():
    for b in BLENDERS:
        if b and os.path.isfile(b) and os.access(b, os.X_OK): return b
    return None


def correr_blender(blend, entrada, timeout=300, script='blender_camaras.py'):
    b = blender()
    if not b: return None, 'no hay Blender en este equipo'
    with tempfile.TemporaryDirectory(prefix='cubos_o74_') as td:
        fe, fs = Path(td) / 'e.json', Path(td) / 's.json'
        fe.write_text(_j(entrada), encoding='utf-8')
        cmd = ['nice', '-n', '15', b, '-b', str(blend), '--factory-startup', '--python', str(CAJAS / script), '--', str(fe), str(fs)]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, 'Blender tardó demasiado'
        if not fs.is_file(): return None, 'Blender no devolvió datos: ' + (p.stderr or p.stdout or '')[-300:]
        return leer(fs), None


_CACHE_MOLDE = {}


def molde(D, eid):
    """Cámaras REALES del molde (desde el .blend) + medidas. None si el escenario no tiene molde."""
    if eid in _CACHE_MOLDE: return _CACHE_MOLDE[eid]
    blend = D / 'ramas' / 'moldes' / str(eid) / 'molde.blend'
    if not blend.is_file(): _CACHE_MOLDE[eid] = (None, f'el escenario {eid} no tiene molde de Blender'); return _CACHE_MOLDE[eid]
    x, err = correr_blender(blend, {'medidas': True})
    if x:
        x['camaras_molde'] = [c for c in x.get('camaras_molde') or [] if CAM_RX.match(c['nombre'])]
        for c in x['camaras_molde']: c['escena_molde'] = CAM_RX.match(c['nombre']).group(2)
    _CACHE_MOLDE[eid] = (x, err)
    return _CACHE_MOLDE[eid]


def camaras_de_escena(M, n, eid, avisos):
    cams = (M or {}).get('camaras_molde') or []
    propias = [c for c in cams if c['escena_molde'] == str(n)]
    if propias: return propias
    if cams:
        avisos.append(f'escena {n}: ninguna cámara del molde {eid} dice «esc{n}» (dicen {sorted({c["escena_molde"] for c in cams})}); '
                      f'se ofrecen TODAS las del escenario. PISTA: la numeración de escenas del 4a/2a no coincide con base.json.')
    return cams


# ---------------- geometría (genérica) ----------------
def _v(a, b): return [b[i] - a[i] for i in range(len(a))]


def _u(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0; return [x / n for x in v]


def cruz2(a, b, c):
    """(b−a)×(c−a) en planta (x,y): >0 = c a la izquierda de la línea a→b."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def lado_eje(linea, cam_loc):
    s = cruz2(linea[0], linea[1], cam_loc)
    return 'A' if s > 1e-9 else ('B' if s < -1e-9 else 'sobre_la_linea')


def punto(C, x):
    if isinstance(x, str): return (C.get('puntos') or {}).get(x)
    return x


def pos_en(C, per, t):
    """Posición y giro del personaje en el segundo t (interpolado en su segmento). Formato PASO_01."""
    for s in per.get('segmentos') or []:
        tt = s.get('t') if isinstance(s, dict) else None
        if not (isinstance(tt, (list, tuple)) and len(tt) == 2 and isinstance(s.get('pos'), list) and s['pos']): continue
        t0, t1 = _num(tt[0]), _num(tt[1])
        if t0 is None or t1 is None: continue
        if t0 <= t <= t1:
            # 2026-11-01 (cubo 05 IndexError): el 01 de Argon puede dar puntos de piso [x, y]; _xyz los normaliza a [x, y, z]
            # (z=0) igual que el resto de las cajas (02, 03, 04, validar_01). Lo que no sea [x,y] / [x,y,z] / punto con nombre → None.
            a, b = _xyz(C, s['pos'][0]), _xyz(C, s['pos'][-1])
            if a is None or b is None: return None, None
            f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            try: rot = float(s.get('rot'))
            except (TypeError, ValueError): rot = None
            return [a[i] + (b[i] - a[i]) * f for i in range(3)], rot
    return None, None


def _id_personaje(per, PC):
    """El 01 usa el nombre de la ficha como id; lo cruzo con el id del canal."""
    pid = str(per.get('id') or '')
    if pid in PC: return pid
    for k, v in PC.items():
        if _norm(v.get('nombre')) == _norm(pid): return k
    return pid


_CACHE_BIBLIO = {}


def _altura_biblioteca(D, cid, fid):
    """Altura desde la biblioteca de personajes del canal (versión de esa forma, si no el personaje). (None, None) si no está."""
    canal = Path(D).parent.name if D else None
    if not canal: return None, None
    try:
        import personajes as PJ
        if canal not in _CACHE_BIBLIO: _CACHE_BIBLIO[canal] = PJ.leer_manifiesto(canal)
        pm = PJ.buscar_personaje(_CACHE_BIBLIO[canal], cid, None)
        v = PJ.buscar_version(pm, fid, None) if (pm and fid) else None
    except Exception:
        return None, None
    for o, de in ((v, f'biblioteca del canal: versión {(v or {}).get("id")} altura_m'), (pm, 'biblioteca del canal: personaje altura_m')):
        h = _num((o or {}).get('altura_m'))
        if h and h > 0: return h, de
    return None, None


def _altura_diseno(D, cid, n):
    """(tamaño, fuente) medido en el diseño de Blender de ESA escena (alturas_blender.py), o (None, None)."""
    canal = Path(D).parent.name if D else None
    m = re.match(r'cap(\d+)_', Path(D).name) if D else None   # misma convención que carpeta(): cap<NN>_<episodio>
    if not (canal and cid and m): return None, None
    try:
        import alturas_blender as AB
        h, de = AB.altura(canal, str(int(m.group(1))), n, cid)
        return (float(h), de) if h and float(h) > 0 else (None, None)
    except Exception: return None, None


def altura(per, cid, n, D, PC, faltan, notas=None):
    if isinstance(per, dict) and per.get('altura'):
        try: return float(per['altura']), 'cubo 01 (altura)'
        except (TypeError, ValueError): pass
    fid = None
    for p in (leer(D / 'respuestas' / 'personajes.json', {}) or {}).get('personajes') or []:
        if p.get('personaje_id') == cid:
            for e in p.get('estados') or []:
                if str(e.get('escena')) == str(n): fid = ((e.get('inicio') or {}).get('forma_id'))
    f = ((PC.get(cid) or {}).get('formas') or {}).get(fid) or {}
    # 2026-11-01 (cubo 05): la base del canal puede traer un marcador de texto («falta») en vez del número: eso es «no la tiene», no un error.
    h = _num(f.get('altura_m'))
    if h and h > 0: return h, f'canal: forma {fid} altura_m'
    # 2026-11-02: misma fuente que ya usa el 02 (cubo02_moldes.ficha): la biblioteca de personajes del canal (personajes.json),
    # que llenan «leer hoja» (altura escrita en la hoja) y el formulario «personajes ficha/guardar». Nunca se inventa.
    hb, deb = _altura_biblioteca(D, cid, fid)
    if hb: return hb, deb
    # 2026-11-02 (Ricardo t306u/t308u): NO hay altura fija: el tamaño lo define el diseño de Blender de CADA escena (corrida real del
    # motor, 02N). Si nadie la escribió, se mide en el diseño de esa escena (alturas_blender.py); la fuente dice qué archivo.
    hd, ded = _altura_diseno(D, cid, n)
    if hd: return hd, ded
    # Sin altura escrita ni diseño de la escena: NO es un faltante ni un error y NO se inventa un número: se sigue sin ella
    # (solo los planos que se calculan con el tamaño del cuerpo quedan fuera; el plano del molde sí sale). Queda como nota informativa.
    # «faltan» se conserva en la firma por compatibilidad, pero ya no se usa para la altura.
    if notas is not None:
        notas.append(f'escena {n}: {cid} sin altura escrita ni diseño de Blender de la escena: se sigue sin ella (no se inventa; '
                     f'los planos que dependen del tamaño del cuerpo no se calculan)')
    return None, None


def eje_en(C, t):
    """Línea de acción en el segundo t: la que dio el 01 (ejes[].linea) o, si no, la que une a los dos primeros personajes."""
    # 2026-11-01 (cubo 05): el 01 dirigido por Argon (o109) da «ejes» como FRASES (texto para la persona), no como líneas.
    # Solo se usan los ejes que traen una línea de verdad (2 puntos [x,y] / [x,y,z] / con nombre); el resto cae al cálculo de abajo.
    for e in C.get('ejes') or []:
        if not isinstance(e, dict): continue
        tt = e.get('t') if isinstance(e.get('t'), (list, tuple)) and e.get('t') else [0, 0]
        t0, t1 = _num(tt[0]), _num(tt[-1])
        ln = e.get('linea') if isinstance(e.get('linea'), (list, tuple)) and len(e.get('linea')) == 2 else None
        ln = [_xyz(C, x) for x in ln] if ln else None
        if t0 is not None and t1 is not None and t0 <= t <= t1 and ln and all(ln): return [p[:2] for p in ln], 'cubo 01 (ejes)', e.get('lado_camara')
    ps = [pos_en(C, p, t)[0] for p in C.get('personajes') or []]
    ps = [p for p in ps if p]
    if len(ps) >= 2: return [ps[0][:2], ps[1][:2]], 'calculado: línea entre los dos primeros personajes del 01', None
    return None, None, None


def lado_maestro(C, linea):
    for c in C.get('camaras') or []:
        if isinstance(c, dict) and c.get('clave') == 'M' and c.get('loc'): return lado_eje(linea, c['loc']), 'cámara maestra del 01'
    return None, None


def camara_tipo(tipo, cam, sujeto, H, ar, cat, otro=None, lado_bueno=None, linea=None):
    """Cámara calculada para un tipo de plano: misma DIRECCIÓN que la cámara del molde (no cambia de lado del eje)."""
    if tipo.get('usa_camara_molde'):
        mira = [cam['loc'][i] + cam['dir'][i] * 10 for i in range(3)]
        return {'loc': cam['loc'], 'mira': mira, 'lente': cam['lente_mm'], 'sensor_ancho_mm': cam['sensor_ancho_mm'], 'de': 'molde tal cual'}
    if not sujeto or not H: return None
    lente, sw = cam['lente_mm'], cam['sensor_ancho_mm']
    # PISTA INMI (2026-10-29): sensor_fit de Blender. AUTO = el sensor cubre el lado MÁS LARGO del cuadro (horizontal → ancho,
    # vertical 9:16 → alto). HORIZONTAL/VERTICAL usan sensor_ancho/sensor_alto. Así sirve para cualquier formato de canal.
    fit = str(cam.get('sensor_fit') or cam.get('fit') or 'AUTO').upper()
    if fit == 'VERTICAL': alto_sensor = cam.get('sensor_alto_mm') or sw
    elif fit == 'HORIZONTAL' or ar[0] >= ar[1]: alto_sensor = sw * ar[1] / ar[0]
    else: alto_sensor = sw
    span = tipo['alto_cuadro'] * H
    dist = (span / 2) * lente / (alto_sensor / 2)
    obj = [sujeto[0], sujeto[1], sujeto[2] + tipo['centro'] * H]
    if tipo['id'] == 'OTS':
        if not otro: return None
        d = _u([obj[0] - otro[0], obj[1] - otro[1], 0])     # del que escucha hacia el que habla
        lat = [-d[1], d[0], 0]                              # izquierda de esa dirección
        if linea and lado_bueno in ('A', 'B'):
            prueba = [otro[0] + lat[0], otro[1] + lat[1]]
            if lado_eje(linea, prueba) != lado_bueno: lat = [-lat[0], -lat[1], 0]
        loc = [otro[0] - d[0] * tipo['detras_m_en_alturas'] * H + lat[0] * tipo['lado_hombro_en_alturas'] * H,
               otro[1] - d[1] * tipo['detras_m_en_alturas'] * H + lat[1] * tipo['lado_hombro_en_alturas'] * H,
               otro[2] + tipo['alto_camara'] * H]
        return {'loc': [round(x, 3) for x in loc], 'mira': [round(x, 3) for x in obj], 'lente': lente, 'sensor_ancho_mm': sw, 'sensor_alto_mm': cam.get('sensor_alto_mm'), 'sensor_fit': fit,
                'de': 'detrás del hombro del que escucha, del lado bueno del eje'}
    hd = _u([cam['dir'][0], cam['dir'][1], 0])
    ojos = sujeto[2] + cat.get('ojos_en_alturas', 0.93) * H
    loc = [obj[0] - hd[0] * dist, obj[1] - hd[1] * dist, ojos if tipo['id'] == 'PP' else obj[2]]
    return {'loc': [round(x, 3) for x in loc], 'mira': [round(x, 3) for x in obj], 'lente': lente, 'sensor_ancho_mm': sw,
            'distancia_m': round(dist, 3), 'de': 'misma dirección que la cámara del molde, a la distancia que da el tipo de plano'}


def puntos_personaje(pos, rot, H, partes):
    """Puntos 3D del cuerpo. rot en grados (0° = mira hacia +x, 90° = hacia +y, como PASO_01). Izquierda del cuerpo = (−sen, cos)."""
    out = {}
    if pos is None or H is None: return out
    if rot is None:
        for k in ('pies', 'cabeza', 'tope'):
            p = partes.get(k) or {}; out[k] = [pos[0], pos[1], pos[2] + p.get('alto', 0) * H]
        return out
    r = math.radians(rot); izq = [-math.sin(r), math.cos(r)]
    for k, p in partes.items():
        z = pos[2] + p.get('alto', 0) * H; d = p.get('lado', 0) * H
        if d:
            out[k + '_izquierda'] = [pos[0] + izq[0] * d, pos[1] + izq[1] * d, z]
            out[k + '_derecha'] = [pos[0] - izq[0] * d, pos[1] - izq[1] * d, z]
        else:
            out[k] = [pos[0], pos[1], z]
    out['frente'] = [pos[0] + math.cos(r) * 0.3 * H, pos[1] + math.sin(r) * 0.3 * H, pos[2] + 0.53 * H]
    return out


# ---------------- rasgos laterales ----------------
LADO_RX = re.compile(r'\b(izquierd[oa]s?|derech[oa]s?)\b')


def rasgos_laterales(D, C, cid, n, PC, P):
    """Rasgos de UN lado del cuerpo (brazalete, herida, daño…). Fuentes, en orden: 01 (personajes[].rasgos_laterales),
    archivo cubos/entradas/rasgos_laterales.json, accesorios de la forma del canal con «lado», heridas de personajes.json que
    digan izquierda/derecha. Si nadie dice el lado, NO se inventa: queda en faltan."""
    out = []
    for per in (C or {}).get('personajes') or []:
        if _id_personaje(per, PC) == cid:
            for r in per.get('rasgos_laterales') or []:
                out.append({**r, 'origen': 'cubo 01'})
    ext = leer(D / 'cubos' / 'entradas' / 'rasgos_laterales.json', {}) or {}
    for r in ext.get(cid) or []:
        if not r.get('escenas') or str(n) in [str(x) for x in r['escenas']]: out.append({**r, 'origen': 'cubos/entradas/rasgos_laterales.json'})
    for f in ((PC.get(cid) or {}).get('formas') or {}).values():
        for a in f.get('accesorios') or []:
            if isinstance(a, dict) and a.get('lado'): out.append({'que': a.get('nombre') or a.get('que'), 'parte': a.get('parte'), 'lado': a['lado'], 'origen': 'canal: accesorios'})
    for p in (leer(D / 'respuestas' / 'personajes.json', {}) or {}).get('personajes') or []:
        if p.get('personaje_id') != cid: continue
        for e in p.get('estados') or []:
            if str(e.get('escena')) != str(n): continue
            for h in (e.get('inicio') or {}).get('heridas') or []:
                m = LADO_RX.search(_norm(h))
                if m: out.append({'que': h, 'lado': 'izquierda' if m.group(1).startswith('izq') else 'derecha', 'origen': 'personajes.json (herida)', 'cita': h})
    for r in out:
        r['lado'] = 'izquierda' if _norm(r.get('lado')).startswith('izq') else ('derecha' if _norm(r.get('lado')).startswith('der') else None)
        if not r.get('parte'):
            txt = _norm(f"{r.get('que', '')} {r.get('cita', '')}")
            r['parte'] = next((k for k, ws in (P.get('palabras') or {}).items() if any(_norm(w) in txt for w in ws)), None)
    return [r for r in out if r['lado']]


# ---------------- cubos ----------------
def r_base(cubo, D, extra=None):
    return {'ok': True, 'caja': 'cubo', 'cubo': cubo, 'gratis': True, 'modo': 'cotizar', 'carpeta': str(D),
            'llamadas_pagas': 0, 'usd_gastado': 0, **(extra or {})}


def cubo01(D, a, cd, PC):
    """Orden 83: ver paso01_dirigir.py (cotiza por defecto; paga solo con guarda + --correr --ok --aprobado)."""
    import paso01_pago as _PG
    if str((_PG.ajustes().get('01') or {}).get('version') or 'o109') == 'accion':
        import cubo01_accion as C1   # 2026-11-01 reorganización: el 01 dirige SOLO la acción (sin cámaras/tomas; las elige el 06)
    else:
        import cubo01_o109 as C1   # PISTA INMI (2026-10-30): orden 109 — el cubo 01 consolidado (solo cámaras del molde + palabras + parametros_3d)
    return C1.cubo01(sys.modules[__name__], D, a, cd, PC)


def _guion(D):
    for f in sorted((D / 'pedidos').glob('*.txt')) if (D / 'pedidos').is_dir() else []:
        s = f.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'=== GUION_COMPLETO ===\n(.*?)\n=== FIN GUION ===', s, re.S)
        if m: return m.group(1)
    return None


def cubo03(D, a, cd, PC):
    """Orden 82: ver paso01_revision.py (cotiza por defecto; paga solo con guarda + --correr --ok --aprobado)."""
    import paso01_revision as RV
    return RV.cubo03(sys.modules[__name__], D, a, cd, PC)


def cubo04(D, a, cd, PC):
    """Orden 82: aplica las correcciones del 03 (gratis, sin IA) → versión nueva → reanima el 02 de esas escenas."""
    import paso01_revision as RV
    return RV.cubo04(sys.modules[__name__], D, a, cd, PC)


def plan_borrador(D, a, cd, PC, avisos, faltan, notas=None):
    """Opciones de toma por escena: tipos de plano del catálogo × cámaras REALES del molde; eje de 180° con esas cámaras."""
    cat = dato('tipos_plano.json'); tipos = cat.get('tipos') or []
    ar = aspecto(cd) or [16, 9]
    if not aspecto(cd): faltan.append('formato (aspect) del canal; uso 16:9 para calcular')
    tomas, esc_info = [], []
    for e in escenas(D, a.solo):
        n = e['numero']; M, err = molde(D, e['escenario_id'])
        if err: faltan.append(f'escena {n}: {err}'); continue
        cams = camaras_de_escena(M, n, e['escenario_id'], avisos)
        C, origen = dirigida(D, n); t0 = 0.0
        sujetos = []
        if C:
            for per in C.get('personajes') or []:
                pos, rot = pos_en(C, per, t0); cid = _id_personaje(per, PC); H, deH = altura(per, cid, n, D, PC, faltan, notas)
                if pos: sujetos.append({'id': cid, 'pos': pos, 'rot': rot, 'altura': H, 'altura_de': deH})
        else:
            faltan.append(f'escena {n}: salida del 01 (posición y giro de cada personaje) → solo plano general del molde')
        linea, linea_de, lado_01 = eje_en(C, t0) if C else (None, None, None)
        bueno, bueno_de = (lado_01, 'cubo 01 (ejes.lado_camara)') if lado_01 else ((lado_maestro(C, linea) if (C and linea) else (None, None)))
        if linea and not bueno and cams: bueno, bueno_de = lado_eje(linea, cams[0]['loc']), f'primera cámara del molde ({cams[0]["nombre"]})'
        esc_info.append({'escena': n, 'escenario_id': e['escenario_id'], 'eje': linea, 'eje_de': linea_de, 'lado_bueno': bueno, 'lado_bueno_de': bueno_de,
                         'camaras_molde': [c['nombre'] for c in cams], 'dirigida_por': origen})
        k = 0
        for cam in cams:
            lado = lado_eje(linea, cam['loc']) if linea else None
            for tp in tipos:
                if len(sujetos) < tp.get('personajes_min', 0): continue
                s1 = sujetos[0] if sujetos else None; s2 = sujetos[1] if len(sujetos) > 1 else None
                cc = camara_tipo(tp, cam, s1 and s1['pos'], s1 and s1['altura'], ar, cat, s2 and s2['pos'], bueno, linea)
                if not cc: continue
                k += 1
                lado_t = lado_eje(linea, cc['loc']) if linea else None
                tomas.append({'id': f'e{n}_t{k:02d}', 'escena': n, 'escenario_id': e['escenario_id'], 'camara_id': cam['nombre'], 'tipo': tp['id'],
                              'camara': cc, 'sujeto': s1 and s1['id'], 'escucha': s2 and s2['id'] if tp['id'] == 'OTS' else None, 't': t0,
                              'lado_eje': lado_t, 'cruza_eje': any(x not in (None, bueno) for x in (lado_t, lado)) if bueno else None, 'lado_camara_molde': lado})
                # PISTA INMI (2026-10-29): también cruza si la CÁMARA DEL MOLDE está del otro lado: su pintura (4a5) muestra el fondo del lado malo.
    return tomas, esc_info


def cubo05(D, a, cd, PC):
    avisos, faltan, notas = [], [], []
    tomas, info = plan_borrador(D, a, cd, PC, avisos, faltan, notas)
    argon = leer(D / 'cubos' / '05' / 'plan_argon.json')
    plan = {'origen': 'borrador del código (sin Argon)', 'tomas': [t for t in tomas if not t['cruza_eje']]}
    if isinstance(argon, dict) and argon.get('tomas'):
        plan = {'origen': 'Argon (cubos/05/plan_argon.json)', 'tomas': argon['tomas']}
    # Arreglo 1 continuidad (Ricardo, resp. a t371s1296): «foto» del estado de cada toma + nota si un cambio cae dentro
    import estado_continuidad as EC
    avisos += EC.anotar_plan(plan['tomas'], lambda n: dirigida(D, n)[0], leer(D / 'cubos' / 'SB' / 'memoria_continuidad.json', {}) or {},
                             [str(i['escena']) for i in info])
    sin_cam = [t.get('id') for t in plan['tomas'] if not t.get('camara_id')]
    if sin_cam: faltan.append(f'camara_id en tomas {sin_cam[:5]} del plan de Argon (el 10 no puede elegir la pintura)')
    tpl = plantilla('ARGON_B_v6.txt'); cot_e = []
    for i in info:
        ts = [t for t in tomas if t['escena'] == i['escena']]
        C, _ = dirigida(D, i['escena'])
        imgs = 1 + len(i['camaras_molde'])   # planta + renders de cámara
        cot_e.append({'escena': i['escena'], **cotizar(len(tpl or '') + len(_j(C or {})) + len(_j(ts)) + len(_j(dato('tipos_plano.json'))) + len(_j(dato('trucos_camara.json'))), imgs, cd, '05')})
    if tpl is None: faltan.append('plantilla ARGON_B_v6.txt')
    tot = round(sum(c['usd'] or 0 for c in cot_e), 4)
    guardar(D / 'cubos' / '05' / 'plan_tomas.json', {**plan, 'escenas': info, 'opciones': tomas, 'catalogo': 'paso01_datos/tipos_plano.json'})
    return r_base('05', D, {'escenas': info, 'opciones': len(tomas), 'plan_origen': plan['origen'], 'tomas_plan': len(plan['tomas']),
                            'descartadas_por_eje': sum(1 for t in tomas if t['cruza_eje']), 'cotizacion': cot_e, 'total_usd_peor_caso': tot,
                            'avisos': avisos, 'faltan': sorted(set(faltan)), 'notas': sorted(set(notas)), 'archivo': str(D / 'cubos' / '05' / 'plan_tomas.json'),
                            'pistas': ['PISTA INMI (2026-10-29): Argon (pago) elige entre estas opciones y escribe cubos/05/plan_argon.json con camara_id; aquí no se llama.'],
                            'resumen': f"05 · {len(tomas)} opciones de toma en {len(info)} escenas ({plan['origen']}); cotización Argon US$ {tot} peor caso (no se llamó)"})


def _plan(D):
    p = leer(D / 'cubos' / '05' / 'plan_tomas.json', {}) or {}
    return p.get('tomas') or [], p


def cubo06(D, a, cd, PC):
    tomas, P05 = _plan(D); faltan, res, notas = [], [], []
    if not tomas: faltan.append('plan de tomas del 05 (correr el 05 antes)')
    partes = (dato('partes_cuerpo.json').get('partes') or {}); ar = aspecto(cd) or [1920, 1080]
    por_esc = {}
    for t in tomas:
        if a.solo and str(t['escena']) not in a.solo: continue
        por_esc.setdefault(t['escenario_id'], []).append(t)
    for eid, ts in por_esc.items():
        blend = D / 'ramas' / 'moldes' / eid / 'molde.blend'
        if not blend.is_file(): faltan.append(f'molde de {eid}'); continue
        pedido = []
        for t in ts:
            C, _ = dirigida(D, t['escena']); pts = {}
            if not (C and C.get('personajes')): faltan.append(f"escena {t['escena']}: posiciones del 01 (solo cámara, sin personajes)")
            for per in (C or {}).get('personajes') or []:
                cid = _id_personaje(per, PC); pos, rot = pos_en(C, per, t.get('t', 0)); H, _ = altura(per, cid, t['escena'], D, PC, faltan, notas)
                for k, p in puntos_personaje(pos, rot, H, partes).items(): pts[f'{cid}|{k}'] = p
            pts['_mira'] = t['camara']['mira']
            pedido.append({'id': t['id'], 'camara': {'molde': t['camara_id']} if t.get('tipo') == 'PG' else t['camara'], 'puntos': pts})
        x, err = correr_blender(blend, {'res': ar, 'tomas': pedido})
        if err: faltan.append(f'{eid}: {err}'); continue
        for r in x['tomas']: r['escenario_id'] = eid
        res += x['tomas']
    out = {'tomas': res, 'res': ar, 'blender': blender()}
    guardar(D / 'cubos' / '06' / 'proyecciones.json', out)
    n_pers = sum(1 for r in res if any('|' in k for k in r.get('uv') or {}))
    return r_base('06', D, {'tomas': len(res), 'con_personajes': n_pers, 'faltan': sorted(set(faltan)), 'notas': sorted(set(notas)), 'archivo': str(D / 'cubos' / '06' / 'proyecciones.json'),
                            'pistas': ['PISTA INMI (2026-10-29): sin salida del 01 no hay personajes que proyectar; la cámara sí se calcula.'],
                            'resumen': f'06 · Blender proyectó {len(res)} tomas ({n_pers} con personajes) con world_to_camera_view (gratis)'})


def _uv_img(v):
    """world_to_camera_view → cuadro: x 0 izq … 1 der; y 0 arriba … 1 abajo (1 − v)."""
    return [round(v[0], 4), round(1 - v[1], 4), v[2]]


def cubo07(D, a, cd, PC):
    pr = leer(D / 'cubos' / '06' / 'proyecciones.json', {}) or {}; tomas, _ = _plan(D); T = {t['id']: t for t in tomas}
    P = dato('partes_cuerpo.json'); faltan, filas = [], []
    if not pr.get('tomas'): faltan.append('proyecciones del 06')
    for r in pr.get('tomas') or []:
        t = T.get(r['id']) or {}; n = t.get('escena'); C, _ = dirigida(D, n)
        pers = sorted({k.split('|')[0] for k in r.get('uv') or {} if '|' in k})
        for cid in pers:
            uv = {k.split('|')[1]: v for k, v in r['uv'].items() if k.startswith(cid + '|')}
            rs = rasgos_laterales(D, C, cid, n, PC, P)
            if not rs: faltan.append(f'lado de rasgos laterales (brazalete, herida…) de {cid} en la escena {n}: nadie lo dice')
            for rg in rs:
                parte = rg.get('parte') or 'muneca'
                p_l, p_r = uv.get(f'{parte}_{rg["lado"]}'), uv.get(f'{parte}_{"derecha" if rg["lado"] == "izquierda" else "izquierda"}')
                fr = uv.get('frente')
                if not p_l or not p_r:
                    filas.append({'toma': r['id'], 'personaje': cid, 'rasgo': rg.get('que'), 'lado_cuerpo': rg['lado'], 'lado_imagen': None, 'por_que': 'sin giro del personaje en el 01'}); continue
                lado_img = 'izquierda' if p_l[0] < p_r[0] else 'derecha'
                ci, cdh = uv.get('cadera_izquierda'), uv.get('cadera_derecha')
                ve_frente = bool(fr and ci and cdh and fr[2] < (ci[2] + cdh[2]) / 2)   # el frente del cuerpo está más cerca de la cámara
                visible = p_l[2] <= p_r[2] + 0.02 or (fr and fr[2] < min(p_l[2], p_r[2]))   # más cerca de la cámara que su par = se ve
                filas.append({'toma': r['id'], 'personaje': cid, 'rasgo': rg.get('que'), 'parte': parte, 'lado_cuerpo': rg['lado'],
                              'lado_imagen': lado_img, 've_frente': ve_frente, 'posicion_cuadro': _uv_img(p_l)[:2], 'visible': bool(visible), 'origen': rg.get('origen')})
    guardar(D / 'cubos' / '07' / 'lados.json', {'lados': filas})
    return r_base('07', D, {'lados': len(filas), 'faltan': sorted(set(faltan)), 'archivo': str(D / 'cubos' / '07' / 'lados.json'),
                            'pistas': ['PISTA INMI (2026-10-29): Motor 1 (colorear) sigue igual; este cubo solo agrega el lado EN LA IMAGEN de cada rasgo.'],
                            'resumen': f'07 · {len(filas)} rasgos con lado en la imagen calculado (world_to_camera_view)'})


def cuadro_de(uv, cid):
    ks = {k.split('|')[1]: _uv_img(v) for k, v in uv.items() if k.startswith(cid + '|')}
    pts = [v for v in ks.values() if v[2] > 0]
    if not pts: return {'en_cuadro': False, 'detras_camara': True}
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pie, cab = ks.get('pies'), ks.get('tope') or ks.get('cabeza')
    caja = [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]
    cx = (caja[0] + caja[2]) / 2
    return {'caja': caja, 'centro': [round(cx, 4), round((caja[1] + caja[3]) / 2, 4)],
            'tercio': 'izquierdo' if cx < 1 / 3 else ('derecho' if cx > 2 / 3 else 'centro'),
            'alto_pct': round(abs((pie or caja)[1] - (cab or caja)[1]) * 100, 1) if pie and cab else None,
            'en_cuadro': caja[2] > 0 and caja[0] < 1 and caja[3] > 0 and caja[1] < 1,
            'cortado': caja[0] < 0 or caja[2] > 1 or caja[1] < 0 or caja[3] > 1,
            'cabeza_fuera': bool(cab) and not (0 <= cab[0] <= 1 and 0 <= cab[1] <= 1 and cab[2] > 0), 'distancia_m': round(min(p[2] for p in pts), 3)}


def cubo08(D, a, cd, PC):
    pr = leer(D / 'cubos' / '06' / 'proyecciones.json', {}) or {}; lados = (leer(D / 'cubos' / '07' / 'lados.json', {}) or {}).get('lados') or []
    tomas, _ = _plan(D); T = {t['id']: t for t in tomas}; faltan, filas = [], []
    if not pr.get('tomas'): faltan.append('proyecciones del 06')
    for r in pr.get('tomas') or []:
        uv = r.get('uv') or {}; pers = sorted({k.split('|')[0] for k in uv if '|' in k})
        filas.append({'toma': r['id'], 'escena': (T.get(r['id']) or {}).get('escena'), 'camara_id': (T.get(r['id']) or {}).get('camara_id'),
                      'tipo': (T.get(r['id']) or {}).get('tipo'), 'personajes': {c: cuadro_de(uv, c) for c in pers},
                      'rasgos': [l for l in lados if l['toma'] == r['id']]})
    guardar(D / 'cubos' / '08' / 'posiciones_cuadro.json', {'nota': 'x 0 = borde izquierdo … 1 = derecho; y 0 = arriba … 1 = abajo; caja = [x0,y0,x1,y1]', 'tomas': filas})
    faltan.append('plantilla del prompt por viñeta del 08 (no está en web/prompts_argon): no se puede cotizar exacto')
    cot = cotizar(len(_j(filas)) + 4000, 0, cd, '08') if filas else None
    return r_base('08', D, {'tomas': len(filas), 'faltan': sorted(set(faltan)), 'archivo': str(D / 'cubos' / '08' / 'posiciones_cuadro.json'), 'cotizacion': cot,
                            'pistas': ['PISTA INMI (2026-10-29): cotización aproximada (datos + 4000 caracteres de plantilla supuesta); cambiar cuando exista la plantilla del 08.'],
                            'resumen': f'08 · posiciones relativas al cuadro escritas para {len(filas)} tomas'})


def cubo09(D, a, cd, PC):
    b = dato('bucles.json').get('08_09') or {}
    pos = (leer(D / 'cubos' / '08' / 'posiciones_cuadro.json', {}) or {}).get('tomas') or []
    tomas, _ = _plan(D); T = {t['id']: t for t in tomas}
    alto = ((cd or {}).get('paso01') or {}).get('alto_cuadro_pct')
    prob, faltan, avisos = [], [], []
    if not pos: faltan.append('posiciones del 08')
    sin = [f['toma'] for f in pos if not f.get('personajes')]
    if sin: prob.append({'toma': ','.join(sin[:8]) + ('…' if len(sin) > 8 else ''), 'tipo': 'sin_personajes', 'que': f'{len(sin)} tomas sin personajes que revisar (falta la salida del 01)'})
    prev = {}
    for f in pos:
        t = T.get(f['toma']) or {}
        if t.get('cruza_eje'): prob.append({'toma': f['toma'], 'tipo': 'eje', 'que': 'la cámara cruza el eje de 180° (otro lado que la maestra)'})
        for cid, c in (f.get('personajes') or {}).items():
            if not c.get('en_cuadro'): prob.append({'toma': f['toma'], 'tipo': 'fuera', 'que': f'{cid} queda fuera del cuadro'})
            elif c.get('cortado') and t.get('tipo') == 'PG': prob.append({'toma': f['toma'], 'tipo': 'cortado', 'que': f'{cid} queda cortado por el borde'})
            elif c.get('cabeza_fuera') and cid == t.get('sujeto'): prob.append({'toma': f['toma'], 'tipo': 'cortado', 'que': f'a {cid} se le sale la cabeza del cuadro'})
            if alto and c.get('alto_pct') and t.get('tipo') == 'PG' and not (alto[0] <= c['alto_pct'] <= alto[1]):
                prob.append({'toma': f['toma'], 'tipo': 'tamano', 'que': f'{cid} ocupa {c["alto_pct"]}% del alto (canal pide {alto[0]}–{alto[1]}%)'})
        for l in f.get('rasgos') or []:
            k = (f.get('escena'), l['personaje'], l.get('rasgo'))
            if l.get('lado_imagen') and k in prev and prev[k][0] != l['lado_imagen']:
                x = {'toma': f['toma'], 'tipo': 'lado', 'que': f"{l['personaje']}: {l.get('rasgo')} cambia de lado en la imagen ({prev[k][0]} → {l['lado_imagen']})"}
                if prev[k][1] == l.get('ve_frente'): prob.append(x)      # misma cara del cuerpo a cámara: NO debería cambiar
                else: avisos.append({**x, 'que': x['que'] + ' — normal: una toma lo ve de frente y la otra de espaldas'})
            if l.get('lado_imagen'): prev[k] = (l['lado_imagen'], l.get('ve_frente'))
    if not alto: faltan.append('alto_cuadro_pct del canal (no se revisa el tamaño)')
    v = leer(D / 'cubos' / '09' / 'veredicto.json')
    pago = None if not isinstance(v, dict) else bool(v.get('aprobado'))
    ok_gratis = bool(pos) and not prob
    apr = ok_gratis and pago is True
    cot = cotizar(len(_j(pos)) + 4000, len(pos), cd, '09') if ok_gratis else None
    faltan.append('plantilla del validador pago del 09 (no está en web/prompts_argon)')
    out = r_base('09', D, {'aprobado': apr, 'aprobado_gratis': ok_gratis, 'validador_pago': 'sin veredicto (no se llamó)' if pago is None else pago,
                           'bucle': b, 'problemas': prob, 'avisos': avisos, 'faltan': sorted(set(faltan)), 'cotizacion_validador': cot,
                           'pistas': ['PISTA INMI (2026-10-29): el validador pago solo se cotiza si los chequeos gratis pasan; su veredicto se lee de cubos/09/veredicto.json.'],
                           'resumen': f"09 · chequeos gratis: {'OK' if ok_gratis else f'{len(prob)} problemas'} · validador pago: {'sin veredicto' if pago is None else pago}"})
    out['archivo'] = guardar(D / 'cubos' / '09' / 'resultado.json', out)
    return out


def pintura_por_camara(D):
    """camara_id → imagen pintada 4a5 (base o vista de ESA cámara) + ediciones (variantes) sobre ella, desde los .json de 4a5 y 4a4."""
    base = D / 'ramas' / 'imagenes' / '4a5'; idx, ed = {}, {}
    for f in sorted(base.glob('*.json')) if base.is_dir() else []:
        j = leer(f, {}) or {}
        if not (f.with_suffix('.png')).is_file(): continue
        if j.get('camara'):
            idx[(j.get('escenario_id'), Path(j['camara']).stem)] = {'id': j.get('id'), 'tipo': j.get('tipo'), 'png': str(f.with_suffix('.png').relative_to(D))}
        if j.get('tipo') == 'edicion':
            k = j.get('en_vista') if j.get('en_vista') not in (None, '', 'base') else f"{j.get('escenario_id')}@base"
            ed.setdefault(k, []).append({'id': j.get('id'), 'png': str(f.with_suffix('.png').relative_to(D))})
    var = {}
    for f in sorted((D / 'respuestas').glob('prompts_escenarios__*.json')) if (D / 'respuestas').is_dir() else []:
        for e in (leer(f, {}) or {}).get('escenarios') or []:
            for v in e.get('variantes') or []: var[v.get('variante_id')] = [str(x) for x in v.get('escenas') or []]
    return idx, ed, var


def _sello_estilo(canal_id):
    """Imagen del SELLO de estilo del canal (estilo_oficial v2: FIJOS_TALLER/estilo/<canal>/sello.json). Nunca la de otro canal."""
    s = leer(Path('/opt/myia-taller-n8n/cajas/FIJOS_TALLER/estilo') / str(canal_id) / 'sello.json', {}) or {}
    img = s.get('imagen')
    return (img if img and Path(img).is_file() else None), s


def _casting_escenas(D, PC):
    """Casting por escena (v2 cubo 10, 2-nov-2026). Fuentes en orden: 1) base.json del 00 (personajes en_cuadro, escenario, objetos);
    2) cubos/entradas/casting_escenas.json (casting puesto por una persona desde el guion del cliente, con «fuente»; lo reemplaza el 05).
    Nada se inventa: si no hay ninguna, el casting queda vacío y 10c FALLA claro."""
    out = {}
    for e in escenas(D):
        dat = e.get('datos') or {}
        objs = [o.get('objeto_id') or o.get('id') or o.get('nombre') if isinstance(o, dict) else o for o in (dat.get('objetos') or dat.get('props') or [])]
        out[e['numero']] = {'personajes': [_id_personaje({'id': p}, PC) for p in e['personajes'] if p], 'objetos': [o for o in objs if o],
                            'escenario_id': e.get('escenario_id'), 'fuente': 'respuestas/base.json (00)', 'tomas': []}
    m = leer(D / 'cubos' / 'entradas' / 'casting_escenas.json', {}) or {}
    for n, e in (m.get('escenas') or {}).items():
        x = out.setdefault(str(n), {'personajes': [], 'objetos': [], 'escenario_id': None, 'tomas': []})
        if not x['personajes']: x['personajes'] = [_id_personaje({'id': p}, PC) for p in e.get('personajes') or []]
        if not x['objetos']: x['objetos'] = list(e.get('objetos') or [])
        x['escenario_id'] = x.get('escenario_id') or e.get('escenario_id')
        x['tomas'] = e.get('tomas') or []
        x['fuente'] = (x.get('fuente') + ' + ' if x.get('fuente') else '') + 'cubos/entradas/casting_escenas.json: ' + str(e.get('fuente') or m.get('fuente') or 'sin fuente')
    return out


def _molde_de(D, toma_id):
    b = D / 'cubos' / '02'
    if not toma_id or not b.is_dir(): return None
    for f in sorted(b.rglob(f'*{toma_id}*.png')): return str(f)
    return None


def cubo10(D, a, cd, PC):
    """v2 (2-nov-2026, aprobado inmi): además de cruzar cámara↔pintura, ENTREGA EL CASTING de cada toma (personajes, objetos,
    escenario, fondo_ref, molde_ref, estilo_ref del sello del canal) y arriba «canal», «toma» (la 1.ª con casting) y «tomas_casting».
    Si no hay plan del 05 pero sí casting de la escena, sale una «toma de escena» (marcada) para que el PROM 10a→10c pueda revisar."""
    tomas, _ = _plan(D); idx, ed, var = pintura_por_camara(D); faltan, filas = [], []
    canal_id = getattr(a, 'canal', None) or D.parent.name
    CE = _casting_escenas(D, PC); est_img, est_sello = _sello_estilo(canal_id)
    if not tomas: faltan.append('plan de tomas del 05')
    def casting(n, t=None):
        c = CE.get(str(n)) or {}
        per = list(c.get('personajes') or [])
        for k in ('sujeto', 'escucha'):   # el 05 marca quién habla/escucha: si es del canal y no estaba, también está en cuadro
            v = (t or {}).get(k)
            for x in (v if isinstance(v, list) else [v]):
                if x:
                    cid = _id_personaje({'id': x}, PC)
                    if cid in PC and cid not in per: per.append(cid)
        return per, list(c.get('objetos') or []), c.get('escenario_id'), c.get('fuente')
    for t in tomas:
        if a.solo and str(t['escena']) not in a.solo: continue
        p = idx.get((t['escenario_id'], t.get('camara_id')))
        fila = {'toma': t['id'], 'escena': t['escena'], 'camara_id': t.get('camara_id'), 'tipo': t.get('tipo'), 'pintura': p and p['png'], 'pintura_id': p and p['id']}
        if p:
            clave =[REDACTED]
            for e in ed.get(clave, []):
                vid = e['id'].split('@')[0]
                if str(t['escena']) in var.get(vid, []): fila.update({'pintura': e['png'], 'pintura_id': e['id'], 'variante': vid})
        else:
            fila['falta'] = f"no hay pintura 4a5 de la cámara {t.get('camara_id')} ({t['escenario_id']})"
        per, objs, esc, fte = casting(t['escena'], t)
        fila.update({'personajes': per, 'objetos': objs, 'escenario_id': t.get('escenario_id') or esc, 'casting_fuente': fte})
        filas.append(fila)
    if not tomas:   # sin 05: una «toma de escena» por escena pedida que tenga casting (o las tomas que trae el casting manual)
        for n, c in sorted(CE.items(), key=lambda kv: (len(kv[0]), kv[0])):
            if a.solo and n not in a.solo: continue
            sub = c.get('tomas') or [{'id': f'esc{n}_escena', 'personajes': c.get('personajes'), 'objetos': c.get('objetos')}]
            for t in sub:
                filas.append({'toma': t.get('id'), 'escena': n, 'camara_id': None, 'tipo': t.get('tipo') or 'toma_de_escena (sin plan 05)',
                              'pintura': None, 'pintura_id': None, 'falta': 'sin plan 05 ni pintura 4a5: toma de escena desde el casting',
                              'personajes': [_id_personaje({'id': x}, PC) for x in (t.get('personajes') or c.get('personajes') or [])],
                              'objetos': list(t.get('objetos') or c.get('objetos') or []), 'escenario_id': t.get('escenario_id') or c.get('escenario_id'),
                              'descripcion': t.get('descripcion'), 'casting_fuente': c.get('fuente')})
    for f in filas:
        f['fondo_ref'] = str(D / f['pintura']) if f.get('pintura') else None
        f['molde_ref'] = _molde_de(D, f.get('toma'))
        f['estilo_ref'] = est_img
    tiras = [{'tira': i // 8 + 1, 'tomas': filas[i:i + 8]} for i in range(0, len(filas), 8)]
    sin = [f['toma'] for f in filas if not f.get('pintura')]
    if sin: faltan.append(f'pintura 4a5 para {len(sin)} tomas (su cámara no fue pintada)')
    sin_cast = [f['toma'] for f in filas if not f.get('personajes')]
    if not filas: faltan.append('casting: no hay plan 05 ni casting de escena (base.json del 00 o cubos/entradas/casting_escenas.json)')
    elif sin_cast: faltan.append(f'casting vacío en {len(sin_cast)} tomas')
    if not est_img: faltan.append('estilo: el canal no tiene imagen de estilo aprobada en su sello (FIJOS_TALLER/estilo/<canal>/sello.json)')
    guardar(D / 'cubos' / '10' / 'tiras.json', {'tiras': tiras})
    con = [f for f in filas if f.get('personajes')]
    t0 = con[0] if con else (filas[0] if filas else None)
    toma = ({'id': t0['toma'], 'escena': t0['escena'], 'camara_id': t0.get('camara_id'), 'tipo': t0.get('tipo'), 'personajes': t0.get('personajes') or [],
             'objetos': t0.get('objetos') or [], 'escenario_id': t0.get('escenario_id'), 'fondo_ref': t0.get('fondo_ref'), 'molde_ref': t0.get('molde_ref'),
             'estilo_ref': t0.get('estilo_ref'), 'descripcion': t0.get('descripcion'), 'casting_fuente': t0.get('casting_fuente')} if t0 else None)
    return r_base('10', D, {'version_cubo10': 'v2 casting 2-nov-2026', 'canal': canal_id, 'escena': (t0 or {}).get('escena'),
                            'tomas': len(filas), 'con_pintura': len(filas) - len(sin), 'tiras': len(tiras), 'faltan': faltan,
                            'toma': toma, 'tomas_casting': [{'id': f['toma'], 'escena': f['escena'], 'personajes': f.get('personajes'), 'objetos': f.get('objetos'),
                                                             'escenario_id': f.get('escenario_id')} for f in filas],
                            'estilo_sello': {'imagen': est_img, 'version': est_sello.get('version'), 'estado': est_sello.get('estado')},
                            'archivo': str(D / 'cubos' / '10' / 'tiras.json'),
                            'pistas': ['PISTA INMI (2026-10-29): «elegir imágenes» final (cuál de las variantes) sigue siendo del usuario.',
                                       'v2 (2-nov-2026): el casting sale del 00/05 o del casting manual del guion; nunca se inventa.'],
                            'resumen': f'10 · {len(filas)} tomas cruzadas con la pintura 4a5 de su cámara ({len(filas) - len(sin)} con imagen) · {len(tiras)} tiras de 8 · casting en {len(con)} tomas'})


def decidir(prev, sig, reglas, orden):
    seguido = sig.get('t') is not None and prev.get('t_fin', prev.get('t')) is not None and abs(float(sig['t']) - float(prev.get('t_fin', prev.get('t')))) < 1e-6
    o = {x: i for i, x in enumerate(orden)}
    hechos = {'misma_escena': str(prev.get('escena')) == str(sig.get('escena')), 'misma_camara': prev.get('camara_id') == sig.get('camara_id'),
              'mismo_tipo': prev.get('tipo') == sig.get('tipo'), 'tiempo_seguido': seguido, 'cruza_eje': bool(sig.get('cruza_eje')),
              'mas_cerrado': o.get(sig.get('tipo'), -1) > o.get(prev.get('tipo'), 99)}
    for r in reglas:
        if all(hechos.get(k) == v for k, v in (r.get('si') or {}).items()):
            return {'decision': r['decision'], 'truco': r.get('truco'), 'regla': r['id'], 'por_que': r.get('por_que'), 'aviso': r.get('aviso'), 'hechos': hechos}
    return {'decision': 'corte', 'truco': None, 'regla': None, 'por_que': 'ninguna regla aplica: corte por seguridad', 'hechos': hechos}


def cubo14(D, a, cd, PC):
    tomas, _ = _plan(D); R = dato('reglas_encadenado.json'); TR = {t['id']: t for t in dato('trucos_camara.json').get('trucos') or []}
    filas, faltan = [], []
    if not tomas: faltan.append('plan de tomas del 05')
    for i in range(1, len(tomas)):
        d = decidir(tomas[i - 1], tomas[i], R.get('reglas') or [], R.get('orden_cerrado') or [])
        tr = TR.get(d['truco']) or {}
        filas.append({'de': tomas[i - 1]['id'], 'a': tomas[i]['id'], **d, 'truco_estado': tr.get('estado'), 'truco_nombre': tr.get('nombre')})
    tpl = plantilla('ARGON_VIDEO_v1.txt')
    if tpl is None: faltan.append('plantilla ARGON_VIDEO_v1.txt')
    cot = cotizar((len(tpl or '') + len(_j(TR))) * max(1, len(tomas)) + len(_j(tomas)), 8 * max(1, len(tomas)) if tomas else 0, cd, '14') if tomas else None
    guardar(D / 'cubos' / '14' / 'encadenado.json', {'uniones': filas, 'reglas': 'paso01_datos/reglas_encadenado.json', 'trucos': 'paso01_datos/trucos_camara.json'})
    enc = sum(1 for f in filas if f['decision'] == 'encadenado')
    return r_base('14', D, {'uniones': len(filas), 'encadenados': enc, 'cortes': len(filas) - enc, 'cotizacion_argon_video': cot, 'faltan': faltan,
                            'archivo': str(D / 'cubos' / '14' / 'encadenado.json'),
                            'pistas': ['PISTA INMI (2026-10-29): en el borrador del 05 todas las tomas tienen t=0 (sin tiempos de Argon): «tiempo_seguido» sale verdadero dentro de la escena; con plan_argon.json (t, t_fin) la regla usa los tiempos reales.',
                                       'PISTA INMI (2026-10-29): cotización peor caso = 1 llamada ARGON_VIDEO_v1 por toma con hasta 8 imágenes; NO se genera video.'],
                            'resumen': f'14 · {len(filas)} uniones: {enc} encadenadas, {len(filas) - enc} con corte (regla + trucos de Star)'})



# ---------------- cubo 02 · Blender anima escenas (orden 78) ----------------
def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def _xyz(C, x):
    p = punto(C, x)
    if isinstance(p, (list, tuple)) and len(p) in (2, 3) and all(_num(v) is not None for v in p):
        return [float(v) for v in p] + ([0.0] if len(p) == 2 else [])
    return None


def validar_01(C):
    """Contrato de entrada del 02 (= lo que ya esperan 01/05/06/08, formato PASO_01). Devuelve (errores, avisos). Con errores NO se anima."""
    err, av = [], []
    if not isinstance(C, dict): return ['la salida del 01 no es un objeto JSON'], av
    pers = C.get('personajes')
    if not isinstance(pers, list) or not pers: return ['«personajes» falta o está vacío'], av
    if C.get('fps') is not None and (_num(C['fps']) is None or _num(C['fps']) <= 0): err.append('«fps» no es un número > 0')
    if C.get('duracion_s') is not None and (_num(C['duracion_s']) is None or _num(C['duracion_s']) <= 0): err.append('«duracion_s» no es un número > 0')
    for i, p in enumerate(pers):
        q = f"personajes[{i}] ({p.get('id') if isinstance(p, dict) else '?'})"
        if not isinstance(p, dict) or not p.get('id'): err.append(f'{q}: falta «id»'); continue
        segs = p.get('segmentos')
        if not isinstance(segs, list) or not segs: err.append(f'{q}: sin «segmentos» (no se sabe dónde está)'); continue
        for j, sg in enumerate(segs):
            w = f'{q}.segmentos[{j}]'
            t = sg.get('t') if isinstance(sg, dict) else None
            if not (isinstance(t, list) and len(t) == 2 and all(_num(v) is not None for v in t)): err.append(f'{w}: «t» debe ser [inicio, fin] en segundos'); continue
            if _num(t[0]) > _num(t[1]) or _num(t[0]) < 0: err.append(f'{w}: «t» al revés o negativo {t}')
            pos = sg.get('pos')
            if not (isinstance(pos, list) and len(pos) >= 1): err.append(f'{w}: falta «pos» [inicio, fin]'); continue
            for k in (pos[0], pos[-1]):
                if _xyz(C, k) is None: err.append(f'{w}: posición {k!r} no es [x,y,z] ni un punto de «puntos»')
            if sg.get('rot') is not None and _num(sg.get('rot')) is None: err.append(f'{w}: «rot» no es un número de grados')
            elif sg.get('rot') is None: av.append(f'{w}: sin «rot» (se deja el giro anterior)')
    return err, av


def _color(c, i, cfg):
    if isinstance(c, list) and len(c) >= 3 and all(_num(v) is not None for v in c[:3]):
        v = [float(x) for x in c[:3]]
        return [x / 255 for x in v] if max(v) > 1 else v
    pal = cfg['figura']['colores']; return pal[i % len(pal)]


def claves_02(C, per, fps):
    """Claves de animación (cuadro → posición, giro) de un personaje, en segundos de la ESCENA (cuadro 1 = segundo 0)."""
    cl, rot = [], None
    for sg in sorted(per['segmentos'], key=lambda s: float(s['t'][0])):
        t0, t1 = float(sg['t'][0]), float(sg['t'][1]); r = _num(sg.get('rot'))
        rot = r if r is not None else rot
        for t, x in ((t0, sg['pos'][0]), (t1, sg['pos'][-1])):
            cl.append({'f': 1 + int(round(t * fps)), 'pos': _xyz(C, x), 'rot': rot})
    vis = [cl[0]['f'], cl[-1]['f']] if cl else None
    ent = _num(((per.get('entrada') or {}) if isinstance(per.get('entrada'), dict) else {}).get('t'))
    if vis and ent is not None: vis[0] = min(vis[0], 1 + int(round(ent * fps)))
    return cl, vis


def tomas_02(D, n, eid, C, M, avisos):
    """Tomas a sacar para la escena n: las del 05 (si hay) → las cámaras del 01 con loc y mira → las cámaras del molde de esa escena."""
    p05 = [t for t in (_plan(D)[0] or []) if str(t.get('escena')) == str(n)]
    if p05:
        out = []
        for t in p05:
            cam = {'molde': t['camara_id']} if (t.get('tipo') == 'PG' or not t.get('camara')) and t.get('camara_id') else dict(t.get('camara') or {})
            if 'lente' not in cam and cam.get('lente_mm'): cam['lente'] = cam['lente_mm']
            out.append({'id': str(t.get('id')), 'camara_id': t.get('camara_id'), 'tipo': t.get('tipo'), 'camara': cam, 't': [_num(t.get('t')), _num(t.get('t_fin'))], 'de': 'cubo 05'})
        return out
    out = []
    for c in C.get('camaras') or []:
        if isinstance(c, dict) and _xyz(C, c.get('loc')) and _xyz(C, c.get('mira')) and c.get('clave') != 'P':
            nom = str(c.get('nombre') or c.get('clave') or 'cam')
            out.append({'id': re.sub(r'[^A-Za-z0-9_-]+', '_', f'01_{nom}'), 'camara_id': nom, 'tipo': None, 'de': 'cámara del cubo 01',
                        'camara': {'loc': _xyz(C, c['loc']), 'mira': _xyz(C, c['mira']), 'lente': _num(c.get('lente')) or 35}, 't': [None, None]})
    for c in camaras_de_escena(M, n, eid, avisos):
        out.append({'id': c['nombre'], 'camara_id': c['nombre'], 'tipo': 'PG', 'camara': {'molde': c['nombre']}, 't': [None, None], 'de': 'cámara del molde'})
    if not p05: avisos.append(f'escena {n}: sin plan del 05 → tomas con las cámaras del 01 y del molde')
    return out


def camara_usada(cam, M):
    """PISTA INMI (orden 82): cámara con la que el 02 sacó la toma, en números (loc, mira, lente): el 04 la corrige en mm."""
    if not isinstance(cam, dict): return None
    if cam.get('molde'):
        c = next((x for x in (M or {}).get('camaras_molde') or [] if x['nombre'] == cam['molde']), None)
        if not c or not c.get('loc') or not c.get('dir'): return {'molde': cam['molde']}
        d = float(dato('argon_pago.json').get('03', {}).get('distancia_mira_m') or 10)
        return {'molde': cam['molde'], 'loc': [float(v) for v in c['loc']], 'mira': [round(float(c['loc'][i]) + float(c['dir'][i]) * d, 6) for i in range(3)],
                'lente': c.get('lente_mm'), 'sensor_ancho_mm': c.get('sensor_ancho_mm'), 'sensor_alto_mm': c.get('sensor_alto_mm'), 'sensor_fit': c.get('sensor_fit')}
    return {k: cam.get(k) for k in ('loc', 'mira', 'lente', 'sensor_ancho_mm', 'sensor_alto_mm', 'sensor_fit') if cam.get(k) is not None}


def res_previa(cd, lado):
    ar = aspecto(cd)
    if not ar: return None
    k = lado / max(ar); w, h = int(round(ar[0] * k / 2) * 2), int(round(ar[1] * k / 2) * 2)   # H.264 pide medidas pares
    return [max(w, 16), max(h, 16)]


def _png_tarjeta(f, res, lineas, cfg):
    """Tarjeta gris (PNG) con texto: ffmpeg si está; si no, un PNG gris liso sin texto (solo marca)."""
    f = Path(f); f.parent.mkdir(parents=True, exist_ok=True)
    if _ffmpeg_tarjeta(f, res, lineas, cfg, segundos=None): return str(f)
    import zlib, struct
    w, h = res; fila = b'\x00' + bytes([90, 90, 90]) * w
    def ch(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    f.write_bytes(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(fila * h)) + ch(b'IEND', b''))
    return str(f)


def _fuente(cfg):
    return next((x for x in (cfg.get('capitulo') or {}).get('fuentes') or [] if Path(x).is_file()), None)


def _texto_ff(lineas, cfg, td, nombre, tam, pos):
    """Filtro drawtext con el texto en un archivo (sin problemas de comillas ni dos puntos)."""
    fu = _fuente(cfg)
    if not fu: return None
    tf = Path(td) / f'{nombre}.txt'; tf.write_text('\n'.join(lineas), encoding='utf-8')
    return (f"drawtext=fontfile={fu}:textfile={tf}:expansion=none:fontsize={tam}:fontcolor=white:line_spacing=4:"
            f"box=1:boxcolor=black@0.45:boxborderw=4:{pos}")


def _ffmpeg_tarjeta(f, res, lineas, cfg, segundos=None, fps=8):
    ff = shutil.which('ffmpeg')
    if not ff: return False
    cc = cfg.get('capitulo') or {}; w, h = res
    with tempfile.TemporaryDirectory(prefix='cubo02_tj_') as td:
        dt = _texto_ff(lineas, cfg, td, 'tj', max(9, int(h * float(cc.get('letra_tarjeta_en_alto', 0.055)))), 'x=(w-text_w)/2:y=(h-text_h)/2')
        src = f"color=c={cc.get('color_tarjeta', '0x5a5a5a')}:s={w}x{h}:r={fps}" + (f':d={segundos}' if segundos else '')
        cmd = [ff, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', src] + (['-vf', dt] if dt else [])
        cmd += (['-frames:v', '1', str(f)] if not segundos else ['-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', str(fps), str(f)])
        try: p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired: return False
        return p.returncode == 0 and Path(f).is_file()


def _envolver(txt, ancho):
    import textwrap
    return [l for parte in str(txt).split('\n') for l in (textwrap.wrap(parte, ancho) or [''])]


def _orden_toma(m):
    s = m.get('segundos_escena') or [0, 0]
    return (float(s[0] or 0), str(m.get('toma')))


def capitulo_02(D, a, res, cfg, estado):
    """PISTA INMI (orden 80b): animática del CAPÍTULO ENTERO. Recorre TODAS las escenas en el orden del mapa (base.json); por escena pone
    sus tomas del 02 en orden (con un letrero «Esc N · toma X» quemado) o, si no hay, una tarjeta gris que dice por qué (nunca inventa
    posiciones). Une todo en ramas/videos/02/capitulo_<cap>.mp4 (baja resolución). estado = {escena: motivo} de esta corrida."""
    cc = cfg['capitulo']; ff = shutil.which('ffmpeg')
    if not ff: return None, 'no hay ffmpeg en este equipo: no se arma el video del capítulo'
    fps = int(cc['fps']); w, h = res; carp = D / 'ramas' / 'videos' / '02'
    cap = re.sub(r'[^A-Za-z0-9_-]+', '_', str(a.capitulo)); salida = carp / f'capitulo_{cap}.mp4'
    piezas, ancho = [], int(cc['letras_por_linea'])
    with tempfile.TemporaryDirectory(prefix='cubo02_cap_') as td:
        for e in escenas(D):
            n = e['numero']; metas = []
            for j in sorted((carp / f'esc_{n}').glob('*.json')) if (carp / f'esc_{n}').is_dir() else []:
                m = leer(j) or {}
                if m.get('ok') and j.with_suffix('.mp4').is_file(): metas.append((m, j.with_suffix('.mp4')))
            if metas:
                for m, v in sorted(metas, key=lambda x: _orden_toma(x[0])):
                    seg = Path(td) / f'p{len(piezas):04d}.mp4'
                    lbl = cc['etiqueta_toma'].format(n=n, toma=m.get('toma'))
                    dt = _texto_ff([lbl], cfg, td, f'l{len(piezas)}', max(8, int(h * float(cc['letra_etiqueta_en_alto']))), 'x=6:y=6')
                    vf = f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}' + (f',{dt}' if dt else '') + ',format=yuv420p'
                    p = subprocess.run([ff, '-y', '-loglevel', 'error', '-i', str(v), '-an', '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-r', str(fps), str(seg)],
                                       capture_output=True, text=True, timeout=300)
                    if p.returncode == 0: piezas.append({'escena': n, 'que': 'toma', 'toma': m.get('toma'), 'archivo': str(seg), 'video': str(v)})
                continue
            motivo = estado.get(n)
            if not motivo:   # de una corrida anterior (p. ej. con --escena): paradas en disco o un 01 sin videos todavía
                pa = [leer(j) or {} for j in sorted((carp / f'esc_{n}').glob('*.json'))] if (carp / f'esc_{n}').is_dir() else []
                pa = [m for m in pa if m.get('parada')]
                if pa: motivo = cc['texto_paradas'].format(n=n, k=len(pa), motivo=pa[0].get('error'))
                elif dirigida(D, n, importados=True)[0]: motivo = cc['texto_sin_videos'].format(n=n)
            txt = motivo or cc['texto_falta_01'].format(n=n)
            seg = Path(td) / f'p{len(piezas):04d}.mp4'
            if _ffmpeg_tarjeta(seg, res, _envolver(txt, ancho), cfg, segundos=float(cc['segundos_tarjeta']), fps=fps):
                piezas.append({'escena': n, 'que': 'tarjeta', 'texto': txt, 'archivo': str(seg)})
        if not piezas: return None, 'no se pudo armar ninguna pieza del capítulo'
        lista = Path(td) / 'lista.txt'; lista.write_text(''.join(f"file '{p['archivo']}'\n" for p in piezas), encoding='utf-8')
        carp.mkdir(parents=True, exist_ok=True); tmp = salida.with_name(salida.stem + '.tmp.mp4')
        p = subprocess.run([ff, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lista), '-c', 'copy', str(tmp)], capture_output=True, text=True, timeout=600)
        if p.returncode != 0 or not tmp.is_file(): return None, 'ffmpeg no pudo unir el capítulo: ' + (p.stderr or '')[-200:]
        tmp.replace(salida)
    dur = None
    fp = shutil.which('ffprobe')
    if fp:
        q = subprocess.run([fp, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(salida)], capture_output=True, text=True)
        dur = _num((q.stdout or '').strip())
    for p in piezas: p.pop('archivo', None)
    meta = {'ok': True, 'cubo': '02', 'tipo': 'capitulo', 'capitulo': str(a.capitulo), 'res': res, 'fps': fps, 'segundos': dur,
            'tomas': sum(1 for p in piezas if p['que'] == 'toma'), 'tarjetas': sum(1 for p in piezas if p['que'] == 'tarjeta'),
            'piezas': piezas, 'es_vista_previa': True}
    guardar(salida.with_suffix('.json'), meta)
    return {'video': str(salida), **{k: meta[k] for k in ('segundos', 'tomas', 'tarjetas')}}, None


def _parada(D, n, eid, t, motivo, origen, res, cfg, carp_v):
    """Toma que el 02 NO anima: deja una marca (PNG gris + .json con ok:false y el motivo) para que la galería 02a la muestre."""
    nombre = re.sub(r'[^A-Za-z0-9_-]+', '_', str(t['id'])); f = carp_v / f'esc_{n}' / f'{nombre}.png'
    for viejo in (f.with_suffix('.mp4'),):
        if viejo.is_file(): viejo.unlink()
    _png_tarjeta(f, res, _envolver(f"Esc {n} · toma {t['id']}: PARADA. {motivo}", int(cfg['capitulo']['letras_por_linea'])), cfg)
    guardar(f.with_suffix('.json'), {'ok': False, 'cubo': '02', 'escena': n, 'escenario_id': eid, 'toma': t['id'], 'parada': True,
                                     'error': motivo, 'dirigida_por': origen, 'segundos_escena': t.get('t'), 'es_vista_previa': True})
    return {'escena': n, 'toma': t['id'], 'motivo': motivo}


def cubo02(D, a, cd, PC):
    cfg = dato('animacion_02.json'); vp = cfg['vista_previa']; fg = cfg['figura']
    faltan, avisos, hechas, fallas, esc_out, paradas, estado = [], [], [], [], [], [], {}
    res = res_previa(cd, int(vp['lado_largo_px']))
    if not res:
        res = res_previa({'aspect': '16:9'}, int(vp['lado_largo_px'])); faltan.append('formato (aspect) del canal; la vista previa usa 16:9')
    carp_v = D / 'ramas' / 'videos' / '02'; carp_c = D / 'cubos' / '02' / 'cuadros'
    dirigidas = 0; resto = int(vp['tomas_max_por_corrida'])
    for e in escenas(D, a.solo):
        n, eid = e['numero'], e['escenario_id']
        C, origen = dirigida(D, n, importados=True)
        if not C: faltan.append(f'escena {n}: salida del 01 (cubos/01/esc_{n}.json): no se anima, NO se inventan posiciones'); continue
        dirigidas += 1
        if C.get('importado'):   # PISTA INMI (orden 79): plan aprobado importado (nunca una corrida real del 01)
            origen = f"{origen} · {C.get('origen') or 'importado'}"
            if C.get('escenario_id') and C['escenario_id'] != eid:
                avisos.append(f"escena {n}: el plan importado va en el molde {C['escenario_id']} ({C.get('escenario_elegido_por') or 'lo dice el importado'}); base.json dice {eid}")
                eid = C['escenario_id']
            if C.get('motivo_no_animable'):
                ps = [_parada(D, n, eid, t, C['motivo_no_animable'], origen, res, cfg, carp_v) for t in C.get('tomas_plan') or [{'id': 'escena', 't': None}]]
                paradas += ps; estado[n] = cfg['capitulo']['texto_paradas'].format(n=n, k=len(ps), motivo=C['motivo_no_animable'])
                esc_out.append({'escena': n, 'escenario_id': eid, 'ok': False, 'dirigida_por': origen, 'tomas': 0, 'paradas': len(ps), 'motivo': C['motivo_no_animable']})
                continue
        err, av = validar_01(C)
        if err:
            esc_out.append({'escena': n, 'ok': False, 'contrato': err[:12]}); faltan.append(f'escena {n}: la salida del {origen} no cumple el contrato ({len(err)} errores)')
            estado[n] = f'Escena {n}: la salida del 01 no cumple el contrato ({len(err)} errores)'; continue
        M, merr = molde(D, eid)
        if merr: faltan.append(f'escena {n}: {merr}'); estado[n] = f'Escena {n}: {merr}'; continue
        fps = int(min(_num(C.get('fps')) or vp['fps_si_01_no_dice'], vp['fps_max']))
        figs = []
        for i, per in enumerate(C['personajes']):
            cid = _id_personaje(per, PC); H, deH = altura(per, cid, n, D, PC, [])
            if not H: H, deH = float(fg['altura_si_falta_m']), fg['altura_si_falta_aviso']; avisos.append(f'escena {n}: {cid}: {deH}')
            cl, vis = claves_02(C, per, fps)
            sin_giro = all(k.get('rot') is None for k in cl)
            if sin_giro: avisos.append(f'escena {n}: {cid}: la entrada no dice hacia dónde mira: la figura va SIN nariz (no se inventa el giro)')
            figs.append({'id': re.sub(r'[^A-Za-z0-9_-]+', '_', cid), 'personaje': cid, 'id_01': per.get('id'), 'altura': H, 'altura_de': deH, 'color': _color(per.get('color'), i, cfg),
                         'radio_cuerpo': fg['radio_cuerpo_en_alturas'], 'radio_cabeza': fg['radio_cabeza_en_alturas'], 'nariz': None if sin_giro else fg['nariz_en_alturas'],
                         'claves': cl, 'visible': vis})
        fin = _num(C.get('duracion_s')) or max(float(sg['t'][1]) for p in C['personajes'] for sg in p['segmentos'])
        if C.get('tomas_plan'):   # tomas del plan importado: las que no se pueden animar se paran con su motivo
            lista = []
            for t in C['tomas_plan']:
                if t.get('motivo_no_animable') or not t.get('camara'): paradas.append(_parada(D, n, eid, t, t.get('motivo_no_animable') or 'sin cámara', origen, res, cfg, carp_v)); continue
                lista.append({'id': str(t['id']), 'camara_id': t['camara'].get('molde'), 'tipo': t.get('plano'), 'camara': t['camara'], 't': [_num(x) for x in t['t']],
                              'de': 'plan importado' if C.get('importado') else 'plan del 01'})
        else:
            lista = tomas_02(D, n, eid, C, M, avisos)
        for t in lista:   # PISTA INMI (orden 82): cámara corregida por el 04 para esa toma
            o = (C.get('camaras_toma') or {}).get(str(t['id']))
            if isinstance(o, dict) and o.get('loc') and o.get('mira'):
                t['camara'] = {k: o[k] for k in ('loc', 'mira', 'lente', 'sensor_ancho_mm', 'sensor_alto_mm', 'sensor_fit') if o.get(k) is not None}
                t['de'] = f"{t['de']} · cámara corregida por el 04 ({o.get('correccion_04')})"
        pedido = []
        for t in lista:
            if resto <= 0: faltan.append(f'escena {n}: toma {t["id"]} no se sacó (tope de {vp["tomas_max_por_corrida"]} tomas por corrida)'); continue
            t0 = t['t'][0] if t['t'][0] is not None else 0.0; t1 = t['t'][1] if t['t'][1] is not None else fin
            if t1 - t0 > vp['segundos_max_por_toma']: avisos.append(f"escena {n}: toma {t['id']} recortada a {vp['segundos_max_por_toma']} s"); t1 = t0 + vp['segundos_max_por_toma']
            nombre = re.sub(r'[^A-Za-z0-9_-]+', '_', str(t['id']))
            pedido.append({**t, 'frames': [1 + int(round(t0 * fps)), 1 + int(round(t1 * fps))], 'video': str(carp_v / f'esc_{n}' / f'{nombre}.mp4'),
                           'cuadro': str(carp_c / f'esc_{n}' / f'{nombre}.png'), 'segundos_escena': [t0, t1]})
            resto -= 1
        if not pedido:
            faltan.append(f'escena {n}: sin cámaras para sacar tomas'); estado.setdefault(n, f'Escena {n}: sin tomas animables'); continue
        x, berr = correr_blender(D / 'ramas' / 'moldes' / eid / 'molde.blend',
                                 {'res': res, 'fps': fps, 'motor': vp['motor'], 'hilos': vp['hilos'], 'calidad': vp['calidad_video'], 'figuras': figs, 'tomas': pedido},
                                 timeout=int(vp['segundos_max_blender_por_escena']), script='blender_animar.py')
        if berr: fallas.append({'escena': n, 'error': berr}); estado[n] = f'Escena {n}: Blender falló ({berr[:80]})'; continue
        por_id = {r['id']: r for r in x.get('tomas') or []}
        for t in pedido:
            r = por_id.get(t['id']) or {'ok': False, 'error': 'Blender no la devolvió'}
            meta = {'ok': r['ok'], 'cubo': '02', 'escena': n, 'escenario_id': eid, 'toma': t['id'], 'camara_id': t['camara_id'], 'tipo': t.get('tipo'),
                    'camara_de': t['de'], 'dirigida_por': origen, 'segundos_escena': t['segundos_escena'], 'fps': fps, 'res': res,
                    'figuras': [{k: f[k] for k in ('personaje', 'id_01', 'altura', 'altura_de', 'color')} for f in figs], 'error': r.get('error'),
                    'cuadro_png': t['cuadro'] if r['ok'] else None, 'es_vista_previa': True,
                    'version': int(C.get('version') or 0), 'camara_usada': camara_usada(t['camara'], M)}
            Path(t['video']).parent.mkdir(parents=True, exist_ok=True)
            vieja = Path(t['video']).with_suffix('.png')
            if vieja.is_file(): vieja.unlink()   # marca de una parada anterior de la misma toma
            guardar(Path(t['video']).with_suffix('.json'), meta)
            (hechas if r['ok'] else fallas).append({'escena': n, 'toma': t['id'], 'video': t['video'] if r['ok'] else None, 'error': r.get('error')})
        esc_out.append({'escena': n, 'escenario_id': eid, 'ok': True, 'dirigida_por': origen, 'tomas': len(pedido), 'fps': fps, 'figuras': len(figs), 'avisos_contrato': av[:5]})
    parado = dirigidas == 0
    # PISTA INMI (2026-10-29): orden 87 — paso «moldes de toma» (método híbrido de Ako, gratis): hoja 2×N por cada 2 tomas para el 11
    try:
        import cubo02_moldes as CM
        mold = CM.capitulo(sys.modules[__name__], D, a, cd, PC)
    except Exception as e:
        mold = {'activo': True, 'error': f'{type(e).__name__}: {e}', 'hojas': 0, 'faltan': [f'moldes de toma: {type(e).__name__}: {e}']}
    faltan += mold.get('faltan') or []
    capi, cerr = capitulo_02(D, a, res, cfg, estado) if cfg.get('capitulo') else (None, None)
    if cerr: faltan.append(cerr)
    out = {'escenas': esc_out, 'videos': hechas, 'paradas': paradas, 'fallas': fallas, 'res': res, 'carpeta_videos': str(carp_v), 'capitulo': capi, 'moldes_toma': mold}
    guardar(D / 'cubos' / '02' / 'videos.json', out)
    cap_txt = f" · capítulo: {capi['tomas']} tomas + {capi['tarjetas']} tarjetas grises ({capi['segundos']} s)" if capi else ''
    res_txt = (f'⛔ 02 PARADO · no hay salida del 01 en ninguna escena: no se anima nada (nunca se inventan posiciones). Correr el 01 primero.'
               if parado else f'02 · Blender sacó {len(hechas)} videos de vista previa ({res[0]}×{res[1]}) en {sum(1 for e in esc_out if e.get("ok"))} escenas'
               + (f' · {len(paradas)} tomas paradas' if paradas else '') + (f' · {len(fallas)} fallas' if fallas else '') + ' (gratis)') + cap_txt + (f" · {mold['resumen']}" if mold.get('resumen') else '')
    motivos = {}
    for p in paradas: motivos.setdefault(p['motivo'], []).append(f"{p['escena']}:{p['toma']}")
    return r_base('02', D, {'parado': parado, 'videos': len(hechas), 'paradas': len(paradas),
                            'paradas_por_motivo': [{'motivo': m, 'tomas': v} for m, v in motivos.items()], 'res': res, 'fallas': fallas[:20],
                            'escenas': esc_out, 'capitulo': capi, 'avisos': sorted(set(avisos))[:30],
                            'moldes_toma': {k: mold.get(k) for k in ('escenas', 'hojas', 'avisos', 'resumen', 'error') if k in mold},
                            'faltan': sorted(set(faltan)), 'archivo': str(D / 'cubos' / '02' / 'videos.json'), 'carpeta_videos': str(carp_v),
                            'pistas': ['PISTA INMI (2026-10-29): orden 78 — figuras de relleno (no son los personajes): solo para revisar recorridos, '
                                       'tiempos, lados y cámaras. Contrato de entrada en paso01_datos/animacion_02.json.',
                                       'PISTA INMI (orden 79/80b): tomas de un plan IMPORTADO se marcan «importado»; las paradas dicen por qué; '
                                       'el capítulo entero queda en ramas/videos/02/capitulo_<cap>.mp4 (tarjeta gris donde falta el 01).',
                                       'PISTA INMI (2026-10-29): orden 87 — además, «moldes de toma» (cubo02_moldes.py): hoja 2×N de maniquíes de color por cada 2 tomas '
                                       'en ramas/moldes/<escenario>/tomas/esc_<N>/ (y moldes_H<k>.png en la galería 02a) para el 11 «híbrido tira».'],
                            'resumen': res_txt})


def cubo11(D, a, cd, PC):
    """PISTA INMI (2026-10-29): orden 87 — ver cubo11_tira.py (pedido «híbrido tira» sobre la hoja de moldes del 02; cotiza por defecto;
    paga solo con su guarda de pago (hibrido.json → pintura.guarda) + --correr --ok --aprobado)."""
    import cubo11_tira as CT
    return CT.cubo11(sys.modules[__name__], D, a, cd, PC)


FUNC = {'01': cubo01, '02': cubo02, '03': cubo03, '04': cubo04, '05': cubo05, '06': cubo06, '07': cubo07, '08': cubo08, '09': cubo09, '10': cubo10, '11': cubo11, '14': cubo14}


def main(argv):
    ap = argparse.ArgumentParser(prog='ver cubo')
    ap.add_argument('cubo', choices=CUBOS)
    ap.add_argument('--canal', required=True)
    ap.add_argument('--capitulo', required=True)
    ap.add_argument('--escena', default='')
    ap.add_argument('--correr', action='store_true', help='SOLO 01, 03 y 11: llamada PAGA (pide la guarda del cubo + --ok + --aprobado; ver paso01_pago.py)')
    ap.add_argument('--ok', type=float, default=None)
    ap.add_argument('--aprobado', default=None)
    ap.add_argument('--max-intentos', dest='max_intentos', type=int, default=None)
    a = ap.parse_args(argv)
    if a.correr and a.cubo not in ('01', '03', '11'): return {'ok': False, 'caja': 'cubo', 'cubo': a.cubo, 'error': f'el cubo {a.cubo} no tiene camino pago (--correr solo en 01, 03 y 11)'}
    a.solo = {x for x in a.escena.split(',') if x}
    D = carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'caja': 'cubo', 'cubo': a.cubo, 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    t0 = time.time(); _CACHE_MOLDE.clear()
    cd = canal(a.canal); PC = personajes_canal(a.canal)
    try:
        r = FUNC[a.cubo](D, a, cd, PC)
    except Exception as e:   # un cubo nunca rompe el flujo: devuelve el error
        return {'ok': False, 'caja': 'cubo', 'cubo': a.cubo, 'gratis': True, 'error': f'{type(e).__name__}: {e}'}
    r['segundos'] = round(time.time() - t0, 2)
    return r


if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
