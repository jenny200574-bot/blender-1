"""PISTA INMI (2026-10-29): orden 87 (Ricardo 17:01 COT: «No pintes todavía, mete el método gratis en los cubos 02 y 11»).
CUBO 02 · paso «MOLDES DE TOMA» (método HÍBRIDO de Ako, gratis, sin red). Después de los videos de vista previa, el 02 saca por
cada toma N cuadros con maniquíes de color plano sobre el set del molde (cubo02_moldes_blender.py) y arma la HOJA 2×N
(cubo02_moldes_convertir.py) que el cubo 11 «híbrido tira» pinta encima.

Todo sale de los datos (regla 6), nada de un canal en el código:
  · set: <capítulo>/ramas/moldes/<escenario>/molde.blend
  · personajes: altura (01 → forma del canal → personajes.json), y de personajes.json → molde {color_molde, color_nombre, grosor,
    accesorios, obligatorias, prohibidas, identidad_en} (campos genéricos, ver paso01_datos/hibrido.json). Vacío → aviso, NO se inventa.
  · recorrido: segmentos del 01 (pos, rot, pose, a_pose, mira_a); tomas: tomas_plan del 01 / plan 05 / cámaras (+ correcciones del 04).
Salida: ramas/moldes/<escenario>/tomas/esc_<N>/{crudos/, H01/, H02/…, moldes.json, config_blender.json}; la hoja se copia (solo PNG)
a ramas/videos/02/esc_<N>/moldes_H01.png para que la galería 02a la muestre. Sin altura, sin plan, plan no animable o eje que el
método no puede corregir → esa escena/hoja PARA con el motivo (y el 11 no la pinta)."""
import json, math, re, shutil, subprocess
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI / 'cubo02_moldes_blender.py'


def ajustes(): return json.loads((AQUI / 'paso01_datos' / 'hibrido.json').read_text(encoding='utf-8'))


def poses(): return json.loads((AQUI / 'paso01_datos' / 'poses_maniqui.json').read_text(encoding='utf-8'))['poses']


def _sid(x): return re.sub(r'[^A-Za-z0-9_-]+', '_', str(x or 'pj')).strip('_') or 'pj'


def rgb(h):
    h = str(h or '').strip().lstrip('#')
    if not re.fullmatch(r'[0-9A-Fa-f]{6}', h): return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def nombre_color(hexa, marcadores):
    c = rgb(hexa)
    if not c: return None
    return min(marcadores, key=lambda m: sum((a - b) ** 2 for a, b in zip(c, rgb(m['hex']))))['nombre']


def manifiesto(canal):
    """personajes.json de la biblioteca (SOLO lectura; los estados de aprobación no se tocan)."""
    try:
        import personajes as P
        return P, P.leer_manifiesto(canal)
    except Exception as e:
        return None, {'_error': f'{type(e).__name__}: {e}'}


def ficha(K, P, m, D, n, per, PC, H, deH, usados, aj, avisos):
    """Datos del maniquí de un personaje del 01. Devuelve dict (o None + motivo si falta la altura)."""
    cid = K._id_personaje(per, PC); mo = aj['moldes']
    nombre = (PC.get(cid) or {}).get('nombre') or per.get('nombre') or per.get('id')
    pm = P.buscar_personaje(m, cid, nombre) if P else None
    nombre = (pm or {}).get('nombre') or nombre   # el nombre de la biblioteca (el de la versión aprobada) manda en los textos
    fid = None
    if P:
        for pid, fi, _ in P.estados_escena(D, n):
            if pid == cid: fid = fi
    v = P.buscar_version(pm, per.get('forma_id') or fid, None) if (P and pm) else None
    if not H:
        for o, de in ((v, 'personajes.json: versión altura_m'), (pm, 'personajes.json: personaje altura_m')):
            if o and K._num(o.get('altura_m')): H, deH = float(o['altura_m']), de; break
    if not H: return None, f'falta la altura de {nombre} ({cid}) en la escena {n} (ni el 01, ni la forma del canal, ni personajes.json): sin moldes, no se inventa'
    md = {**((pm or {}).get('molde') or {}), **((v or {}).get('molde') or {})}
    av = []
    col = md.get('color_molde') if rgb(md.get('color_molde')) else None
    if not col:
        libres = [x for x in mo['marcadores_auto'] if x['hex'].upper() not in usados]
        if not libres: return None, f'escena {n}: más personajes que colores de marca en hibrido.json (marcadores_auto)'
        col = libres[0]['hex']; av.append(f'{nombre}: sin molde.color_molde en personajes.json → color de marca automático {libres[0]["nombre"]} (solo marca de posición)')
    usados.add(col.upper())
    g = K._num(md.get('grosor'))
    if g is None: g = float(mo['grosor_si_falta']); av.append(f'{nombre}: sin molde.grosor en personajes.json → {g} (complexión normal)')
    acc = [a for a in md.get('accesorios') or [] if isinstance(a, dict) and a.get('nombre') and rgb(a.get('color'))]
    if not md.get('accesorios'): av.append(f'{nombre}: sin molde.accesorios en personajes.json → maniquí sin accesorios')
    for a in acc:
        a.setdefault('color_nombre', nombre_color(a['color'], mo['marcadores_auto']))
        usados.add(a['color'].upper())
    avisos += [f'escena {n}: {x}' for x in av]
    return {'id': _sid(cid), 'personaje_id': cid, 'id_01': per.get('id'), 'nombre': nombre, 'alto_m': round(float(H), 3), 'altura_de': deH,
            'grosor': g, 'color_molde': col, 'color_nombre': md.get('color_nombre') or nombre_color(col, mo['marcadores_auto']),
            'accesorios': acc, 'obligatorias': md.get('obligatorias') or [], 'prohibidas': md.get('prohibidas') or [],
            'identidad_en': md.get('identidad_en') or (v or {}).get('descripcion') or (pm or {}).get('descripcion') or '',
            'version': (v or {}).get('nombre'), 'forma_id': (v or {}).get('forma_id') or fid, 'avisos': av}, None


def segmentos(K, C, per, ids01, PS, aj, avisos, n, nombre):
    """Segmentos del 01 → formato del maniquí. Giro del taller (0° = mira a +x) → maniquí (0° = mira a +y): rot − 90."""
    out, rot, sin_giro = [], None, True
    for sg in sorted(per['segmentos'], key=lambda s: float(s['t'][0])):
        a, b = K._xyz(C, sg['pos'][0]), K._xyz(C, sg['pos'][-1])
        r = K._num(sg.get('rot'))
        if r is not None: rot = r; sin_giro = False
        pose = sg.get('pose') if sg.get('pose') in PS else None
        if sg.get('pose') and not pose: avisos.append(f"escena {n}: {nombre}: pose «{sg['pose']}» no está en poses_maniqui.json → {aj['moldes']['pose_si_falta']}")
        x = {'t': [float(sg['t'][0]), float(sg['t'][1])], 'pos': [a, b], 'pose': pose or aj['moldes']['pose_si_falta']}
        if sg.get('a_pose') in PS: x['a_pose'] = sg['a_pose']
        ma = sg.get('mira_a'); es_id = isinstance(ma, str) and ma in ids01; pm = K._xyz(C, ma) if (ma is not None and not es_id) else None
        if es_id: x['mira_a'] = ids01[ma]; sin_giro = False
        elif pm: x['mira_a'] = pm[:2]; sin_giro = False
        elif rot is not None: x['rot'] = rot - 90.0
        out.append(x)
    if sin_giro and not any('mira_a' in s for s in out):
        avisos.append(f'escena {n}: {nombre}: el 01 no dice hacia dónde mira: el maniquí queda de frente al eje +x del set y el 11 no sabe si es frente o espalda')
    return out, sin_giro


def tomas(K, D, n, eid, C, avisos):
    """Tomas (id, cámara, t) del plan: tomas_plan del 01 → plan 05 / cámaras (K.tomas_02) → + cámara corregida por el 04."""
    paradas = []
    if C.get('tomas_plan'):
        lista = []
        for t in C['tomas_plan']:
            if t.get('motivo_no_animable') or not t.get('camara'): paradas.append({'toma': t.get('id'), 'motivo': t.get('motivo_no_animable') or 'sin cámara'}); continue
            lista.append({'id': str(t['id']), 'camara': t['camara'], 't': [K._num(x) for x in (t.get('t') or [None, None])], 'cuadros': t.get('cuadros'),
                          'plano': t.get('plano'), 'orden': t.get('orden'), 'accion': t.get('accion') or t.get('descripcion'), 'cambio_eje': t.get('cambio_eje'), 'de': 'tomas_plan del 01'})
    else:
        M, merr = K.molde(D, eid)
        lista = [] if merr else [{**t, 'de': t.get('de')} for t in K.tomas_02(D, n, eid, C, M, avisos)]
    for t in lista:
        o = (C.get('camaras_toma') or {}).get(str(t['id']))
        if isinstance(o, dict) and o.get('loc') and o.get('mira'):
            t['camara'] = {k: o[k] for k in ('loc', 'mira', 'lente') if o.get(k) is not None}; t['de'] = f"{t['de']} · cámara corregida por el 04"
    return lista, paradas


def _texto(d, claves):
    for k in claves:
        if isinstance(d, dict) and str(d.get(k) or '').strip(): return str(d[k]).strip()
    return None


def toma_maniqui(K, C, t, fin, ids01, aj, k):
    mo = aj['moldes']; cam = t['camara']
    t0 = t['t'][0] if t['t'][0] is not None else 0.0; t1 = t['t'][1] if (len(t['t']) > 1 and t['t'][1] is not None) else fin
    x = {'id': _sid(t['id']), 'cambio_eje': bool(t.get('cambio_eje'))}
    if isinstance(t.get('orden'), list): x['orden'] = [ids01.get(i, i) for i in t['orden']]
    if cam.get('molde'): x['camara_molde'] = cam['molde']; x['camara'] = {kk: cam[kk] for kk in ('mira', 'lente') if cam.get(kk)}
    else: x['camara'] = {'loc': K._xyz(C, cam.get('loc')), 'mira': K._xyz(C, cam.get('mira')), 'lente': K._num(cam.get('lente')) or 35}
    cu = t.get('cuadros') if isinstance(t.get('cuadros'), list) and t.get('cuadros') else None
    if cu:
        out = []
        for i, c in enumerate(cu):
            tc = K._num(c.get('t')); tc = t0 + (t1 - t0) * i / max(1, len(cu) - 1) if tc is None else tc
            y = {'n': i + 1, 't': tc, 'accion': _texto(c, mo['claves_texto_cuadro']) or t.get('accion') or ''}
            if isinstance(c.get('alto_pct'), dict): y['alto_pct'] = {ids01.get(a, a): v for a, v in c['alto_pct'].items()}
            out.append(y)
    else:
        N = int(mo['cuadros_por_toma_si_el_plan_no_dice'])
        out = [{'n': i + 1, 't': round(t0 + (t1 - t0) * (i + 0.5) / N, 3), 'accion': t.get('accion') or ''} for i in range(N)]
    x['cuadros'] = out
    x['reencuadrar'] = any(c.get('alto_pct') for c in out)
    return x


def _tarjeta(K, f, texto):
    cfg = K.dato('animacion_02.json')
    try: K._png_tarjeta(f, [960, 540], K._envolver(texto, int(cfg['capitulo']['letras_por_linea'])), cfg)
    except Exception: pass


def escena(K, D, n, eid, C, origen, cd, PC, aj, avisos, faltan, solo_cfg=False):
    """Moldes de una escena. Devuelve el índice (moldes.json)."""
    mo = aj['moldes']; base = D / 'ramas' / 'moldes' / str(eid) / 'tomas' / f'esc_{n}'; vid = D / 'ramas' / 'videos' / '02' / f'esc_{n}'
    idx = {'ok': False, 'cubo': '02', 'paso': 'moldes_de_toma', 'escena': n, 'escenario_id': eid, 'dirigida_por': origen,
           'version': int(C.get('version') or 0) if C else None, 'hojas': [], 'personajes': [], 'avisos': [], 'carpeta': str(base)}

    def parar(motivo):
        idx['motivo'] = motivo; base.mkdir(parents=True, exist_ok=True); K.guardar(base / 'moldes.json', idx)
        for v in vid.glob('moldes_*.png') if vid.is_dir() else []: v.unlink()
        if vid.is_dir(): _tarjeta(K, vid / 'moldes_PARADA.png', f'Esc {n} · moldes de toma: PARADA. {motivo}')   # sin carpeta de la escena no se crea una (el 02 ya dice PARADO)
        faltan.append(f'escena {n} (moldes): {motivo}'); return idx

    if not C: return parar(f'no hay plan del 01 (cubos/01/esc_{n}.json): sin moldes, no se inventan posiciones')
    if C.get('importado') and C.get('escenario_id'):   # el plan importado manda: las carpetas van en SU escenario
        eid = C['escenario_id']; idx['escenario_id'] = eid; base = D / 'ramas' / 'moldes' / str(eid) / 'tomas' / f'esc_{n}'; idx['carpeta'] = str(base)
    if C.get('motivo_no_animable'): return parar(f"el plan no se puede animar en este molde: {C['motivo_no_animable']}")
    err, _ = K.validar_01(C)
    if err: return parar(f'el plan del 01 no cumple el contrato ({len(err)} errores: {err[0]})')
    blend = D / 'ramas' / 'moldes' / str(eid) / 'molde.blend'
    if not blend.is_file(): return parar(f'el escenario {eid} no tiene molde de Blender (ramas/moldes/{eid}/molde.blend)')
    P, m = manifiesto(D.parent.name)
    if m.get('_error'): avisos.append(f'escena {n}: no pude leer personajes.json ({m["_error"]}): moldes sin color/grosor/accesorios propios')
    PS = poses(); ids01 = {}; figs = []; usados = set(); segs = []
    for per in C['personajes']: ids01[per['id']] = _sid(K._id_personaje(per, PC))
    for per in C['personajes']:
        cid = K._id_personaje(per, PC); H, deH = K.altura(per, cid, n, D, PC, [])
        f, mot = ficha(K, P, m, D, n, per, PC, H, deH, usados, aj, avisos)
        if mot: return parar(mot)
        sg, sin_giro = segmentos(K, C, per, ids01, PS, aj, avisos, n, f['nombre'])
        f['giro_conocido'] = not sin_giro; figs.append(f); segs.append({'id': f['id'], 'segmentos': sg})
    lista, par = tomas(K, D, n, eid, C, avisos)
    for p in par: avisos.append(f"escena {n}: toma {p['toma']} sin molde: {p['motivo']}")
    if not lista: return parar('el plan no trae ninguna toma con cámara')
    if len(lista) > int(mo['tomas_max_por_corrida']):
        faltan.append(f"escena {n} (moldes): {len(lista) - int(mo['tomas_max_por_corrida'])} tomas quedan para otra corrida (tope {mo['tomas_max_por_corrida']})")
        lista = lista[:int(mo['tomas_max_por_corrida'])]
    fin = K._num(C.get('duracion_s')) or max(float(sg['t'][1]) for p in C['personajes'] for sg in p['segmentos'])
    tm = [toma_maniqui(K, C, t, fin, ids01, aj, k + 1) for k, t in enumerate(lista)]
    ar = K.aspecto(cd) or (16, 9); L = int(mo['render_lado_largo_px']); Lp = int(mo['panel_lado_largo_px'])
    res = [int(round(L * ar[0] / max(ar) / 2) * 2), int(round(L * ar[1] / max(ar) / 2) * 2)]
    panel = (int(round(Lp * ar[0] / max(ar))), int(round(Lp * ar[1] / max(ar))))
    cfg = {'escenario': {'molde_blend': str(blend), 'cuadricula_m': float(mo['cuadricula_m'])}, 'colores_molde': mo['colores_molde'],
           'personajes': [{k: f[k] for k in ('id', 'alto_m', 'grosor', 'color_molde', 'accesorios')} for f in figs],
           'plan': {'personajes': segs, 'tomas': tm}, 'resolucion': res, 'poses': str(AQUI / 'paso01_datos' / 'poses_maniqui.json')}
    import cubo02_moldes_convertir as HC
    try: HC.paleta(cfg)
    except ValueError as e: return parar(f'los colores del molde se confunden ({e}): cambia molde.color_molde en personajes.json')
    base.mkdir(parents=True, exist_ok=True); K.guardar(base / 'config_blender.json', cfg)
    idx['personajes'] = [{k: f[k] for k in f if k != 'accesorios'} | {'accesorios': [a['nombre'] for a in f['accesorios']]} for f in figs]
    if solo_cfg: return idx
    crudos = base / 'crudos'
    if crudos.exists(): shutil.rmtree(crudos)
    try:
        r = subprocess.run([K.blender(), '-b', '--factory-startup', '-noaudio', '-P', str(SCRIPT), '--', str(base / 'config_blender.json'), str(crudos)],
                           capture_output=True, text=True, timeout=int(mo['segundos_max_blender_por_escena']))
    except subprocess.TimeoutExpired: return parar(f"Blender tardó más de {mo['segundos_max_blender_por_escena']} s")
    med = K.leer(crudos / 'medidas.json'); eje = K.leer(crudos / 'continuidad_eje.json') or []
    if r.returncode != 0 or not med:
        return parar('Blender falló al sacar los moldes: ' + ((r.stderr or r.stdout or '')[-300:].strip().replace('\n', ' ') or f'código {r.returncode}'))
    eje_por = {e['toma']: e for e in eje}
    for v in vid.glob('moldes_*.png') if vid.is_dir() else []: v.unlink()
    T = int(mo['tomas_por_hoja'])
    for h in range(0, len(tm), T):
        grupo = tm[h:h + T]; hid = f'H{h // T + 1:02d}'; ids = [f"{t['id']}_{c['n']}" for t in grupo for c in t['cuadros']]
        e = [eje_por.get(t['id']) or {} for t in grupo]
        hj = {'id': hid, 'tomas': [t['id'] for t in grupo], 'ids': ids, 'panel_px': list(panel), 'eje': e,
              'cuadros': {f"{t['id']}_{c['n']}": {'t': c['t'], 'accion': c.get('accion')} for t in grupo for c in t['cuadros']},
              'camara': {t['id']: (t.get('camara_molde') or 'plan') for t in grupo}}
        mal = [x for x in e if str(x.get('accion') or x.get('estado') or '').startswith('FALLO')]   # el script de Blender escribe «accion»
        if mal:
            hj.update(ok=False, motivo=f"eje: {mal[0]['toma']} cruza la línea y el método no lo puede corregir sin cambiar la cámara (marca cambio_eje en el plan o cambia la cámara)")
            _tarjeta(K, vid / f'moldes_{hid}_PARADA.png', f"Esc {n} · hoja {hid}: PARADA. {hj['motivo']}")
            idx['hojas'].append(hj); faltan.append(f"escena {n} hoja {hid} (moldes): {hj['motivo']}"); continue
        fh, st = HC.convertir(cfg, str(crudos), base / hid, ids, panel=panel, nombre=f'hoja_moldes_{hid}.png')
        vac = [i for i, s in st.items() if not any(v > 0 for k, v in s.items() if k not in ('piel', 'nuca', 'cielo'))]
        if vac: avisos.append(f"escena {n} hoja {hid}: paneles sin ningún maniquí a la vista: {', '.join(vac)}")
        vid.mkdir(parents=True, exist_ok=True); shutil.copy2(fh, vid / f'moldes_{hid}.png')
        hj.update(ok=True, hoja=fh, paneles=[str(base / hid / f'{i}.png') for i in ids], galeria=str(vid / f'moldes_{hid}.png'), cobertura=st)
        idx['hojas'].append(hj)
    pv = vid / 'moldes_PARADA.png'
    if pv.is_file(): pv.unlink()
    idx['medidas'] = str(crudos / 'medidas.json'); idx['ok'] = any(x.get('ok') for x in idx['hojas'])
    if not idx['ok']: idx['motivo'] = 'ninguna hoja salió (ver hojas[].motivo)'
    K.guardar(base / 'moldes.json', idx)
    return idx


def capitulo(K, D, a, cd, PC):
    """Moldes de todas las escenas (o --solo). Lo llama el cubo 02 al final. US$0."""
    aj = ajustes(); avisos, faltan, out = [], [], []
    if not (aj.get('moldes') or {}).get('activo'): return {'activo': False}
    for e in K.escenas(D, a.solo):
        n, eid = e['numero'], e['escenario_id']; C, origen = K.dirigida(D, n, importados=True)
        x = escena(K, D, n, eid, C, origen, cd, PC, aj, avisos, faltan)
        out.append({'escena': n, 'escenario_id': x['escenario_id'], 'ok': x['ok'], 'motivo': x.get('motivo'),
                    'hojas': [{'id': h['id'], 'ok': h['ok'], 'tomas': h['tomas'], 'hoja': h.get('galeria'), 'motivo': h.get('motivo')} for h in x['hojas']]})
    hojas = sum(1 for e in out for h in e['hojas'] if h['ok'])
    return {'activo': True, 'escenas': out, 'hojas': hojas, 'avisos': sorted(set(avisos))[:40], 'faltan': sorted(set(faltan)),
            'resumen': f'moldes de toma: {hojas} hojas 2×N en {sum(1 for e in out if e["ok"])} escenas'
                       + (f' · {sum(1 for e in out if not e["ok"])} escenas paradas' if any(not e['ok'] for e in out) else '') + ' (gratis)'}
