#!/usr/bin/env python3
"""PISTA INMI (2026-10-29): orden 82 — cubos 03 «Argon revisa coherencia» y 04 «Aplicar correcciones y repetir». Genérico (regla 6).

VERSIONES de la dirección de una escena (nunca se pisa una anterior):
  v0 = cubos/01/esc_N.json (corrida del 01, o un plan importado a propósito)
  v1, v2… = cubos/04/esc_N.v<k>.json (cada vuelta del 04). Cada una guarda base_sha (= sha del 01 del que sale): si el 01 cambia,
  las versiones viejas dejan de contar solas. El 02 anima SIEMPRE la última y marca cada video con su versión y su cámara.
03 (por escena): toma las tomas del 02 de la versión actual → saca fotogramas → chequeos GRATIS del código (saltos, giros,
  distancias, lado del eje de 180°, daños que desaparecen) → arma el pedido a Argon (prompts_03, en inglés) → cotiza.
  Solo con --correr (guarda HABILITAR_PAGO_03 + --ok + --aprobado) llama; la respuesta se valida y queda en cubos/03/esc_N.json
  con correcciones en mm y grados, cada una con su toma y su figura, y aprobado true/false.
04 (por escena, gratis, sin IA): aplica las correcciones del 03 de ESA versión → escribe la versión k+1 → guarda los videos
  viejos en cubos/04/renders/esc_N/v<k>/ → vuelve a animar en Blender (02) solo esas escenas. Al llegar a max_vueltas
  (paso01_datos/bucles.json) no corrige más: la escena pasa al usuario (cubos/04a/esc_N.json).
PISTA INMI (orden 82): el «programa viejo» (Argon A de la app) pedía un programa externo de escena (MYIA_PROGRAMA_ESCENA) y
  buscaba fotogramas en cubos/02/esc_N/*.png, que el 02 nunca escribe: por eso «le faltaba un archivo». Este 03 no usa nada de eso."""
import copy, hashlib, json, math, re, shutil, subprocess, tempfile, time
from pathlib import Path

import paso01_pago as PG
import motor_02n as M2

EPS = 1e-6


def _sha(x): return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _cfg(): return PG.ajustes()['03']


# ---------------- versiones ----------------
def versiones(K, D, n):
    b = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
    if not (isinstance(b, dict) and b.get('personajes') is not None): return []
    sb = _sha(b); out = [{'k': 0, 'archivo': str(D / 'cubos' / '01' / f'esc_{n}.json'), 'C': b, 'base_sha': sb}]
    carp = D / 'cubos' / '04'
    vs = []
    for f in carp.glob(f'esc_{n}.v*.json') if carp.is_dir() else []:
        m = re.fullmatch(rf'esc_{re.escape(str(n))}\.v(\d+)\.json', f.name)
        x = K.leer(f)
        if m and isinstance(x, dict) and x.get('base_sha') == sb and x.get('personajes') is not None: vs.append((int(m.group(1)), f, x))
    for k, f, x in sorted(vs, key=lambda z: z[0]): out.append({'k': k, 'archivo': str(f), 'C': x, 'base_sha': sb})
    return out


def actual(K, D, n, importados=False):
    vs = versiones(K, D, n)
    if not vs: return None
    v = vs[-1]
    if v['C'].get('importado') and not importados: return None
    return v


# ---------------- tomas del 02 ----------------
def tomas_hechas(K, D, n, k):
    """Tomas que el 02 animó de la versión k (ok, con mp4). Las de otra versión no cuentan (están viejas)."""
    carp = D / 'ramas' / 'videos' / '02' / f'esc_{n}'; ok, otras, paradas = [], 0, 0
    for j in sorted(carp.glob('*.json')) if carp.is_dir() else []:
        m = K.leer(j) or {}
        if m.get('parada'): paradas += 1; continue
        if not (m.get('ok') and j.with_suffix('.mp4').is_file()): continue
        if int(m.get('version') or 0) != int(k): otras += 1; continue
        ok.append({**m, 'video': str(j.with_suffix('.mp4'))})
    return sorted(ok, key=K._orden_toma), otras, paradas


def fotogramas(K, D, n, k, tomas, por_toma, maximo):
    """Saca fotogramas de cada toma (ffmpeg, gratis) a cubos/03/fotogramas/esc_N/v<k>/ con un letrero «toma · segundo»."""
    ff = shutil.which('ffmpeg'); out = []
    if not tomas: return out, None
    if not ff: return out, 'no hay ffmpeg en este equipo: no se pueden sacar fotogramas'
    por = max(1, min(int(por_toma), int(maximo) // max(1, len(tomas))))
    carp = D / 'cubos' / '03' / 'fotogramas' / f'esc_{n}' / f'v{k}'; carp.mkdir(parents=True, exist_ok=True)
    cfg02 = K.dato('animacion_02.json')
    with tempfile.TemporaryDirectory(prefix='cubo03_') as td:
        for t in tomas:
            s0, s1 = [float(x or 0) for x in (t.get('segundos_escena') or [0, 0])]; dur = max(0.0, s1 - s0); fps = float(t.get('fps') or 8)
            for i in range(por):
                if len(out) >= int(maximo): break
                off = min(dur * (i + 0.5) / por, max(0.0, dur - 1.0 / fps)); seg = round(s0 + off, 3)
                nom = re.sub(r'[^A-Za-z0-9_-]+', '_', f"{t['toma']}_s{seg:.2f}") + '.png'; f = carp / nom
                h = int((t.get('res') or [480, 270])[1])
                dt = K._texto_ff([f"shot {t['toma']} · s {seg:.2f}"], cfg02, td, f'l{len(out)}', max(8, int(h * 0.05)), 'x=6:y=6')
                cmd = [ff, '-y', '-loglevel', 'error', '-ss', f'{off:.3f}', '-i', t['video'], '-frames:v', '1'] + (['-vf', dt] if dt else []) + [str(f)]
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if p.returncode == 0 and f.is_file(): out.append({'toma': str(t['toma']), 'segundo': seg, 'archivo': str(f)})
    return out, None


# ---------------- chequeos gratis del código ----------------
def _segs(per): return sorted([s for s in per.get('segmentos') or [] if isinstance(s, dict) and isinstance(s.get('t'), list)], key=lambda s: float(s['t'][0]))


def _dist(a, b): return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(min(len(a), len(b)))))


def _danos(x, claves):
    """Daños/heridas que dice un objeto (cualquier clave de claves_dano, a cualquier profundidad)."""
    out = set(); cl = {K_.lower() for K_ in claves}
    def ver(v, dentro):
        if isinstance(v, dict):
            for k, w in v.items(): ver(w, dentro or str(k).lower() in cl)
            if dentro and not any(isinstance(w, (dict, list)) for w in v.values()):
                out.add(str(v.get('nombre') or v.get('descripcion') or v.get('tipo') or json.dumps(v, sort_keys=True, ensure_ascii=False)).strip().lower())
        elif isinstance(v, list):
            for w in v: ver(w, dentro)
        elif dentro and isinstance(v, str) and v.strip(): out.add(v.strip().lower())
    ver(x, False); return out


def _danos_per(per, claves):
    sin_segs = {k: v for k, v in per.items() if k != 'segmentos'}
    return _danos(sin_segs, claves) | set().union(*[_danos(s, claves) for s in _segs(per)] or [set()])


def chequeos(K, D, n, C, tomas, PC):
    cf = _cfg(); ch = cf['chequeos']; claves = cf['claves_dano']; h = []
    fps = float(K._num(C.get('fps')) or 8)
    pers = [p for p in C.get('personajes') or [] if isinstance(p, dict) and p.get('id')]
    for p in pers:
        ss = _segs(p); prev = None
        for i, s in enumerate(ss):
            t0, t1 = float(s['t'][0]), float(s['t'][1]); a, b = K._xyz(C, s['pos'][0]), K._xyz(C, s['pos'][-1])
            if a and b and t1 > t0 and _dist(a, b) / (t1 - t0) > float(ch['velocidad_max_mps']):
                h.append({'tipo': 'salto', 'figura': p['id'], 'segundo': t0, 'que': f"va a {round(_dist(a, b) / (t1 - t0), 2)} m/s entre {t0} y {t1} s (máx {ch['velocidad_max_mps']})"})
            if prev is not None:
                pt1, pb, prot = prev
                gap = max(t0 - pt1, 0.0)
                if pb and a:
                    d = _dist(pb, a)
                    if d > float(ch['salto_max_m']) and (gap < EPS or d / gap > float(ch['velocidad_max_mps'])):
                        h.append({'tipo': 'salto', 'figura': p['id'], 'segundo': t0, 'que': f'salta {round(d * 1000)} mm de golpe en el segundo {t0}'})
                r = K._num(s.get('rot'))
                if r is not None and prot is not None:
                    dg = abs((r - prot + 180) % 360 - 180)
                    if dg / max(gap, 1.0 / fps) > float(ch['giro_max_grados_por_s']):
                        h.append({'tipo': 'pose', 'figura': p['id'], 'segundo': t0, 'que': f'gira {round(dg)}° de golpe en el segundo {t0}'})
            r = K._num(s.get('rot')); prev = (t1, b, r if r is not None else (prev[2] if prev else None))
    fin = K._num(C.get('duracion_s')) or max([float(s['t'][1]) for p in pers for s in _segs(p)] or [0])
    paso = float(ch['paso_s']); vistos = set(); t = 0.0
    while t <= fin + EPS and len(pers) > 1:
        pos = {p['id']: K.pos_en(C, p, t)[0] for p in pers}
        for i, x in enumerate(pers):
            for y in pers[i + 1:]:
                a, b = pos[x['id']], pos[y['id']]
                if a and b and (x['id'], y['id']) not in vistos and _dist(a[:2], b[:2]) < float(ch['distancia_min_m']):
                    vistos.add((x['id'], y['id']))
                    h.append({'tipo': 'distancia', 'figura': x['id'], 'otra': y['id'], 'segundo': round(t, 3),
                              'que': f"{x['id']} y {y['id']} quedan a {round(_dist(a[:2], b[:2]) * 1000)} mm (mín {round(float(ch['distancia_min_m']) * 1000)} mm)"})
        t += paso
    lados = []
    for tm in tomas:
        cu = tm.get('camara_usada') or {}; s0, s1 = [float(v or 0) for v in (tm.get('segundos_escena') or [0, 0])]; mid = (s0 + s1) / 2
        vis = [(p['id'], K.pos_en(C, p, mid)[0]) for p in pers]; vis = [v for v in vis if v[1]]
        if len(vis) < 2 or not cu.get('loc'): continue
        linea, de, lado01 = K.eje_en(C, mid)
        linea = [K._xyz(C, q) for q in linea] if linea else None
        if not linea or None in linea: linea = [vis[0][1], vis[1][1]]
        lado = K.lado_eje(linea, cu['loc']); lados.append((tm['toma'], lado))
        if lado01 and lado != 'sobre_la_linea' and lado != lado01:
            h.append({'tipo': 'eje_180', 'toma': tm['toma'], 'segundo': mid, 'que': f"la cámara de la toma {tm['toma']} está del lado {lado}; el 01 pide el lado {lado01}"})
    for (ta, la), (tb, lb) in zip(lados, lados[1:]):
        if 'sobre_la_linea' not in (la, lb) and la != lb:
            h.append({'tipo': 'eje_180', 'toma': tb, 'que': f'de la toma {ta} (lado {la}) a la {tb} (lado {lb}) se cruza el eje de 180°'})
    for p in pers:   # daños: lo que tenía antes sigue
        ss = _segs(p); vistos = set()
        for s in ss:
            d = _danos(s, claves)
            for x in sorted(vistos - d) if d or any(k in s for k in claves) else []:
                h.append({'tipo': 'dano', 'figura': p['id'], 'segundo': float(s['t'][0]), 'que': f'«{x}» desaparece en el segundo {s["t"][0]}'})
            vistos |= d
    ant = _anterior(K, D, n)
    if ant:
        for p in pers:
            q = next((z for z in ant.get('personajes') or [] if K._norm(z.get('id')) == K._norm(p['id'])), None)
            if not q: continue
            falta = _danos_per(q, claves) - _danos_per(p, claves)
            for x in sorted(falta):
                h.append({'tipo': 'dano', 'figura': p['id'], 'segundo': 0.0, 'que': f'en la escena anterior tenía «{x}» y aquí no aparece'})
    for i, x in enumerate(h): x['id'] = f'c{i + 1}'
    return h


def _anterior(K, D, n):
    ns = [e['numero'] for e in K.escenas(D)]
    if str(n) not in ns or ns.index(str(n)) == 0: return None
    v = actual(K, D, ns[ns.index(str(n)) - 1], importados=True)
    return v and v['C']


# ---------------- pedido a Argon ----------------
def _bloque(nombre, x): return f"\n\n=== {nombre} ===\n{json.dumps(x, ensure_ascii=False, indent=1)}\n=== END {nombre} ==="


def pedido03(K, D, n, v, tomas, fotos, hall, PC):
    cf = _cfg(); txt = PG.texto(cf['prompt']); esq = PG.texto(cf['esquema']); claves = cf['claves_dano']
    C = v['C']
    rend = [{'shot': str(t['toma']), 'scene_seconds': t.get('segundos_escena'), 'framing': t.get('tipo'), 'camera': t.get('camara_usada'),
             'figures': [{'id': f.get('id_01') or f.get('personaje'), 'colour_rgb': f.get('color'), 'height_m': f.get('altura')} for f in t.get('figuras') or []],
             'frames': [{'file': Path(f['archivo']).name, 'second': f['segundo']} for f in fotos if f['toma'] == str(t['toma'])]} for t in tomas]
    ant = _anterior(K, D, n)
    cont = {'previous_scene_end': {p.get('id'): sorted(_danos_per(p, claves)) for p in (ant or {}).get('personajes') or []} if ant else None,
            'this_scene': {p.get('id'): sorted(_danos_per(p, claves)) for p in C.get('personajes') or [] if isinstance(p, dict)}}
    dirig = {k: w for k, w in C.items() if k not in ('correcciones_aplicadas', 'no_aplicadas')}
    # Arreglo 2 continuidad (Ricardo, resp. a t375s1320): estado esperado por toma y fotograma, del 01 + memoria (el 03 va antes del 05; no guarda nada)
    import estado_continuidad as EC
    est03, _ = EC.estado_para_03(C, n, K.leer(D / 'cubos' / 'SB' / 'memoria_continuidad.json', {}) or {}, [e['numero'] for e in K.escenas(D)],
                                 [{'shot': r['shot'], 'scene_seconds': r['scene_seconds'], 'frames': r['frames']} for r in rend])
    prompt = txt + _bloque('DIRECTED_SCENE', dirig) + _bloque('RENDERED_SHOTS', rend) + _bloque('CONTINUITY', cont) + _bloque('STATE_PER_SHOT', est03) + _bloque('CODE_CHECKS', hall) + '\n\nSCHEMA\n' + esq
    return prompt, txt, json.loads(esq)


# ---------------- leer la respuesta de Argon ----------------
def interpretar(K, obj, n, C, tomas, PC):
    """Respuesta de Argon (esquema prompts_03) → veredicto con correcciones en mm y grados. Lo que no cuadra va a «invalidas»."""
    lim = _cfg()['limites']; fin = K._num(C.get('duracion_s')) or max([float(s['t'][1]) for p in C.get('personajes') or [] for s in _segs(p)] or [0])
    ids = {K._norm(p.get('id')): p.get('id') for p in C.get('personajes') or [] if isinstance(p, dict)}
    for p in C.get('personajes') or []:
        cid = K._id_personaje(p, PC); ids.setdefault(K._norm(cid), p.get('id'))
        if (PC.get(cid) or {}).get('nombre'): ids.setdefault(K._norm(PC[cid]['nombre']), p.get('id'))
    toms = {str(t['toma']) for t in tomas}; corr, inv, fallas = [], [], []
    for i, f in enumerate(obj.get('fallas') or []):
        if not isinstance(f, dict): continue
        fid = str(f.get('id') or f'f{i + 1}'); fallas.append({**f, 'id': fid}); c = f.get('correccion')
        if not isinstance(c, dict): continue
        mal = []; o = c.get('objetivo'); toma = c.get('toma') or f.get('toma')
        fig = ids.get(K._norm(c.get('id') or f.get('figura') or '')) if o == 'figura' else None
        if o == 'figura' and not fig: mal.append(f"la figura {c.get('id') or f.get('figura')!r} no está en la escena")
        if o == 'camara' and str(toma) not in toms: mal.append(f'la toma {toma!r} no se animó en esta versión')
        if o not in ('figura', 'camara'): mal.append('objetivo debe ser figura o camara')
        seg = K._num(f.get('segundo')); d0 = K._num(c.get('desde_s')); d1 = K._num(c.get('hasta_s'))
        d0 = d0 if d0 is not None else (seg if seg is not None else 0.0); d1 = d1 if d1 is not None else (seg if seg is not None else fin)
        if d0 > d1: d0, d1 = d1, d0
        d0, d1 = max(0.0, d0), min(float(fin), d1)
        mv = c.get('mover_mm'); am = c.get('mira_mover_mm')
        for nom, x in (('mover_mm', mv), ('mira_mover_mm', am)):
            if x is None: continue
            if not (isinstance(x, list) and len(x) == 3 and all(K._num(z) is not None for z in x)): mal.append(f'{nom} debe ser [dx, dy, dz] en mm')
            elif max(abs(float(z)) for z in x) > float(lim['mover_max_mm']): mal.append(f"{nom} pasa {lim['mover_max_mm']} mm")
        for nom in ('girar_grados', 'mirar_grados'):
            if c.get(nom) is not None and (K._num(c[nom]) is None or abs(float(c[nom])) > float(lim['giro_max_grados'])): mal.append(f'{nom} fuera de rango')
        if c.get('lente_mm') is not None and not (lim['lente_mm'][0] <= (K._num(c['lente_mm']) or -1) <= lim['lente_mm'][1]): mal.append('lente_mm fuera de rango')
        if not any(c.get(k) is not None for k in ('mover_mm', 'girar_grados', 'mirar_grados', 'mira_mover_mm', 'lente_mm')): mal.append('la corrección no mueve ni gira nada')
        if mal: inv.append({'falla': fid, 'por_que': mal}); continue
        corr.append({'id': fid, 'tipo': f.get('tipo'), 'toma': str(toma) if toma is not None else None, 'figura': fig, 'segundo': seg,
                     'descripcion': f.get('descripcion'), 'objetivo': o, 'objetivo_id': fig if o == 'figura' else str(toma), 'desde_s': d0, 'hasta_s': d1,
                     'mover_mm': [float(z) for z in mv] if mv else None, 'girar_grados': K._num(c.get('girar_grados')),
                     'rot_grados': K._num(c.get('mirar_grados')), 'mira_mover_mm': [float(z) for z in am] if am else None, 'lente_mm': K._num(c.get('lente_mm'))})
    apr = bool(obj.get('aprobado')) and not fallas
    return {'aprobado': apr, 'resumen': obj.get('resumen'), 'fallas': fallas, 'correcciones': corr, 'invalidas': inv,
            'aviso': 'Argon dijo aprobado pero listó fallas: NO se aprueba' if obj.get('aprobado') and fallas else None}


def veredicto(K, D, n, v):
    x = K.leer(D / 'cubos' / '03' / f'esc_{n}.json')
    if isinstance(x, dict) and v and x.get('base_sha') == v['base_sha'] and int(x.get('version_revisada', -1)) == int(v['k']): return x
    return None


# ---------------- 02N (motor de Ako) ----------------
def _camara_02n(K, D, e, C, c):
    """Cámara con la que el motor renderizó: la del molde que el 01 eligió para las tomas del tramo (cubo01_tomas). Sin molde → {}."""
    ids = set((c['tramo_json'] or {}).get('cubo01_tomas') or [])
    nombres = [t.get('camara_molde') or (t.get('camara') or {}).get('molde') for t in C.get('tomas_plan') or [] if isinstance(t, dict) and (not ids or t.get('id') in ids)]
    nombres = [x for x in nombres if x]
    if not nombres: return {}
    M, err = K.molde(D, e['escenario_id'])
    cam = next((m for m in (M or {}).get('camaras_molde') or [] if m.get('nombre') == nombres[0]), None)
    return {'nombre': nombres[0], 'loc': cam.get('loc') if cam else None, 'lente': cam.get('lente') if cam else None}


def fotos_02n(D, n, k, c, fotos):
    """Copia los renders de la corrida 02N a cubos/03/fotogramas/esc_N/v<k>_02n/ (el 03 queda autocontenido; el historial no se toca)."""
    carp = D / 'cubos' / '03' / 'fotogramas' / f'esc_{n}' / f'v{k}_02n'; carp.mkdir(parents=True, exist_ok=True); out = []
    for f in fotos:
        dst = carp / f"{c['id']}_{Path(f['archivo']).name}"
        if not dst.is_file(): shutil.copy2(f['archivo'], dst)
        out.append({**f, 'archivo': str(dst), 'original': f['archivo']})
    return out, str(carp)


# ---------------- cubo 03 ----------------
def cubo03(K, D, a, cd, PC):
    cf = _cfg(); b = K.dato('bucles.json').get('03_04') or {}; mx = int(b.get('max_vueltas') or 1)
    faltan = [f'archivo {x} (cajas/)' for x in PG.archivos_que_faltan('03')]
    if faltan: return K.r_base('03', D, {'ok': False, 'aprobado': False, 'bucle': b, 'faltan': faltan, 'resumen': '03 · falta ' + ', '.join(faltan)})
    filas, pedidos, ctx = [], [], {}
    cfg2n = M2.ajustes()
    for e in K.escenas(D, a.solo):
        n = e['numero']; v = actual(K, D, n, importados=True)
        if not v: filas.append({'escena': n, 'estado': 'falta_01', 'aprobado': False, 'por_que': f'falta 01 (cubos/01/esc_{n}.json): no hay qué revisar', 'cotizacion': None}); continue
        tomas, otras, paradas = tomas_hechas(K, D, n, v['k'])
        base = {'escena': n, 'version': v['k'], 'archivo_revisado': v['archivo'], 'importado': bool(v['C'].get('importado')), 'fuente': '02'}
        c2n = M2.mejor(a.canal, a.capitulo, n, cfg2n) if cfg2n['usar_si_hay'] else None   # 2026-11-01: renders del motor de Ako (02N)
        if c2n and c2n['renders']:
            tomas, fotos2n = M2.tomas_y_fotos(c2n, _camara_02n(K, D, e, v['C'], c2n)); r2n = M2.resumen(c2n)
            coincide = bool(r2n['ledger_01']) and r2n['ledger_01'] == v['C'].get('ledger') and int(v['k']) == 0
            base.update(fuente='02N', corrida_02n=r2n, version_01_coincide=coincide)
            if not coincide: faltan.append(f"escena {n}: la corrida 02N {c2n['id']} se armó con otro 01 (ledger {r2n['ledger_01']}; ahora v{v['k']} {v['C'].get('ledger')}): volver a correr el 02N")
            if c2n['modo'] == 'seco': faltan.append(f"escena {n}: la corrida 02N es EN SECO (Argon falso): sirve para probar la conexión, no la dirección")
        if not tomas:
            pq = (f'nada que revisar: el 02 paró todas las tomas ({paradas})' if paradas and not otras else
                  f"el 02 aún no animó la versión v{v['k']}" + (f' (hay {otras} videos de otra versión)' if otras else '') + ': correr el 02')
            filas.append({**base, 'estado': 'nada_que_revisar', 'aprobado': False, 'por_que': pq, 'cotizacion': None}); continue
        if base['fuente'] == '02N':
            fotos, carp_f = fotos_02n(D, n, v['k'], c2n, fotos2n[:int(cf['max_imagenes'])]); ferr = None
        else:
            fotos, ferr = fotogramas(K, D, n, v['k'], tomas, cf['fotogramas_por_toma'], cf['max_imagenes'])
            carp_f = str(D / 'cubos' / '03' / 'fotogramas' / f'esc_{n}' / f"v{v['k']}")
        if ferr: faltan.append(f'escena {n}: {ferr}')
        hall = chequeos(K, D, n, v['C'], tomas, PC)
        if base['fuente'] == '02N':
            hall += M2.hallazgos_revisor(c2n)
            for i, x in enumerate(hall): x['id'] = f'c{i + 1}'
        prompt, txt, esq = pedido03(K, D, n, v, tomas, fotos, hall, PC)
        fp = K.guardar(D / 'cubos' / '03' / 'pedidos' / f"esc_{n}_v{v['k']}.json", {'prompt_chars': len(prompt), 'fotogramas': fotos})
        (D / 'cubos' / '03' / 'pedidos' / f"esc_{n}_v{v['k']}.txt").write_text(prompt, encoding='utf-8')
        cot = K.cotizar(len(prompt), len(fotos), cd, '03')
        ver = veredicto(K, D, n, v)
        est = _estado(ver, v['k'], mx)
        filas.append({**base, 'estado': est, 'aprobado': bool(ver and ver.get('aprobado')), 'tomas_revisadas': [t['toma'] for t in tomas], 'fotogramas': len(fotos),
                      'carpeta_fotogramas': carp_f, 'hallazgos_codigo': hall,
                      'correcciones': len((ver or {}).get('correcciones') or []), 'pedido': fp.replace('.json', '.txt'), 'cotizacion': cot,
                      'veredicto': None if ver is None else ver.get('de')})
        ctx[n] = (v, tomas, fotos, hall, prompt, txt, esq, cot)
        if cot.get('ok'): pedidos.append(n)
    pago = None
    if getattr(a, 'correr', False):
        pago = _pagar03(K, D, a, cd, PC, ctx, [n for n in pedidos if not veredicto(K, D, n, ctx[n][0])], mx, filas)
    for f in filas:   # la salida al usuario (04a) cuando se agotan las vueltas
        if f.get('estado') == 'usuario':
            v = ctx[f['escena']][0]; ver = veredicto(K, D, f['escena'], v)
            K.guardar(D / 'cubos' / '04a' / f"esc_{f['escena']}.json", {'escena': f['escena'], 'version': v['k'], 'archivo': v['archivo'], 'max_vueltas': mx,
                      'por_que': f'{mx} vueltas 03↔04 sin aprobar: decide el usuario', 'correcciones_pendientes': (ver or {}).get('correcciones'),
                      'fallas': (ver or {}).get('fallas'), 'fotogramas': str(D / 'cubos' / '03' / 'fotogramas' / f"esc_{f['escena']}" / f"v{v['k']}")})
    revis = [f for f in filas if f.get('estado') not in ('falta_01', 'nada_que_revisar')]
    apr = bool(revis) and all(f['aprobado'] for f in revis)
    tot = round(sum((f.get('cotizacion') or {}).get('usd') or 0 for f in filas), 4)
    if not revis: faltan.append('salida del 01 animada por el 02 en alguna escena (el 03 no tiene qué revisar)')
    cuenta = {k: sum(1 for f in filas if f.get('estado') == k) for k in ('aprobado', 'corregir', 'usuario', 'sin_veredicto', 'nada_que_revisar', 'falta_01')}
    dec = ('sigue_' + str(b.get('sigue_si_aprueba'))) if apr else ('04' if cuenta['corregir'] else (str(b.get('salida_usuario')) if cuenta['usuario'] else 'esperar_veredicto'))
    cuenta['revisadas_con_02N'] = sum(1 for f in filas if f.get('fuente') == '02N' and f.get('estado') not in ('falta_01', 'nada_que_revisar'))
    out = K.r_base('03', D, {'aprobado': apr, 'bucle': b, 'decision': dec, 'cuenta': cuenta, 'escenas': filas, 'total_usd_peor_caso': tot, 'faltan': sorted(set(faltan)),
                             'pistas': ['PISTA INMI (orden 82): prompt cajas/prompts_03/revisar_coherencia.txt (inglés) + esquema; pedido exacto en cubos/03/pedidos/esc_N_v<k>.txt. '
                                        'Sin --correr NO se llama: solo precio.',
                                        'PISTA INMI (orden 82): pagar = guarda cajas/HABILITAR_PAGO_03 + «--correr --ok USD --aprobado QUIEN» (manual; el flujo n8n rechaza salidas pagadas).'],
                             'resumen': f"03 · {'aprobado' if apr else 'no aprobado'} · " + ', '.join(f'{v} {k}' for k, v in cuenta.items() if v) + f' · cotización US$ {tot} peor caso'})
    if pago: out.update(pago)
    out['archivo'] = K.guardar(D / 'cubos' / '03' / 'resultado.json', out)
    return out


def _estado(ver, k, mx):
    if ver is None: return 'sin_veredicto'
    if ver.get('aprobado'): return 'aprobado'
    return 'corregir' if int(k) < mx else 'usuario'


def _pagar03(K, D, a, cd, PC, ctx, quien, mx, filas):
    """Camino PAGO del 03 (nunca por defecto). Cotización fresca = la que se acaba de calcular arriba con el pedido exacto."""
    msg = PG.revisar_guarda('03', a.ok, a.aprobado)
    if msg: return {'pago': {'llamado': False, 'por_que': msg}}
    tot = round(sum(ctx[n][7]['usd'] for n in quien), 4)
    if tot > float(a.ok) + 1e-9: return {'pago': {'llamado': False, 'por_que': f'cotización fresca US${tot} > --ok {a.ok}: no se llama'}}
    X = a.X if getattr(a, 'X', None) else PG.app()
    AR = X['AR']; modelo, nivel, mo = K.modelo_canal(cd); hechas = []
    peds = []
    for n in quien:
        v, tomas, fotos, hall, prompt, txt, esq, cot = ctx[n]
        peds.append({'clave': f"esc{n}-v{v['k']}", 'n': n, 'prompt': prompt, 'salida': D / 'cubos' / '03' / 'respuestas' / f"esc_{n}_v{v['k']}.txt",
                     'est': cot['usd'], 'adjuntos': [f['archivo'] for f in fotos], 'esquema': esq, 'modelo': modelo, 'nivel': nivel, 'max_out': mo,
                     'fijo': PG.fijo('03', txt, json.dumps(esq, ensure_ascii=False, sort_keys=True), modelo, nivel, mo, X.get('FP')),
                     'nota': f'cubo 03 coherencia esc {n} v{v["k"]}'})
        Path(peds[-1]['salida']).parent.mkdir(parents=True, exist_ok=True)
    res, bolsa = PG.correr(peds, a, X, cd, '03')
    for q, r in zip(peds, res):
        n = q['n']; v, tomas = ctx[n][0], ctx[n][1]; fila = next(f for f in filas if f['escena'] == n)
        if not r['ok']: fila['pago'] = r; hechas.append({'escena': n, **{k: r.get(k) for k in ('ok', 'error', 'no_llamado')}}); continue
        rv = PG.LS.revisar_respuesta(r['texto'], q['esquema'], r.get('fin'))
        if rv['obj'] is None or rv.get('esquema_errores'):
            fila['pago'] = {'ok': False, 'ledger': r['ledger'], 'error': f"respuesta no válida ({rv['estado']}; {rv.get('esquema_errores', [])[:3]})"}; hechas.append({'escena': n, **fila['pago']}); continue
        ver = interpretar(K, rv['obj'], n, v['C'], tomas, PC)
        ver.update({'escena': n, 'version_revisada': v['k'], 'base_sha': v['base_sha'], 'archivo_revisado': v['archivo'], 'de': 'argon',
                    'ledger': r['ledger'], 'usd': r.get('usd'), 'hallazgos_codigo': ctx[n][3], 'fecha': time.strftime('%Y-%m-%dT%H:%M:%S%z')})
        K.guardar(D / 'cubos' / '03' / f'esc_{n}.json', ver)
        K.guardar(D / 'cubos' / '03' / 'historial' / f"esc_{n}_v{v['k']}.json", ver)
        fila.update({'estado': _estado(ver, v['k'], mx), 'aprobado': ver['aprobado'], 'correcciones': len(ver['correcciones']), 'veredicto': 'argon', 'ledger': r['ledger']})
        hechas.append({'escena': n, 'ok': True, 'ledger': r['ledger'], 'usd': r.get('usd'), 'aprobado': ver['aprobado']})
    usd = round(sum(float(r.get('usd') or 0) for r in res if r.get('ok')), 6)
    return {'gratis': False, 'modo': 'correr', 'llamadas_pagas': sum(int(r.get('anotados') or 0) for r in res), 'usd_gastado': usd,
            'pago': {'llamado': True, 'aprobado_por': a.aprobado, 'ok_usd': a.ok, 'cotizacion_fresca_usd': tot, 'bolsa_peor_caso': round(bolsa['gastado'], 4), 'escenas': hechas}}


# ---------------- cubo 04 ----------------
def _partir(per, t):
    """Si t cae DENTRO de un segmento, lo parte en dos (misma recta, misma pose) para corregir solo un tramo."""
    for i, s in enumerate(per['segmentos']):
        t0, t1 = float(s['t'][0]), float(s['t'][1])
        if t0 + EPS < t < t1 - EPS:
            return s, i, t0, t1
    return None


def aplicar_figura(K, C, c):
    per = next((p for p in C.get('personajes') or [] if K._norm(p.get('id')) == K._norm(c['objetivo_id'])), None)
    if per is None: return False, 'la figura no está en esta versión'
    d0, d1 = float(c['desde_s']), float(c['hasta_s'])
    for s in per['segmentos']:   # nombres de puntos → [x,y,z] (mover una figura no mueve el punto para las otras)
        s['pos'] = [K._xyz(C, s['pos'][0]), K._xyz(C, s['pos'][-1])]
    for t in sorted({d0, d1}):
        x = _partir(per, t)
        if x:
            s, i, t0, t1 = x; f = (t - t0) / (t1 - t0); m = [s['pos'][0][j] + (s['pos'][1][j] - s['pos'][0][j]) * f for j in range(3)]
            a = {**copy.deepcopy(s), 't': [t0, t], 'pos': [s['pos'][0], m]}; b = {**copy.deepcopy(s), 't': [t, t1], 'pos': [list(m), s['pos'][1]]}
            per['segmentos'][i:i + 1] = [a, b]
    per['segmentos'].sort(key=lambda s: float(s['t'][0])); hizo, no = False, []
    if c.get('mover_mm'):
        dv = [float(z) / 1000.0 for z in c['mover_mm']]
        for s in per['segmentos']:
            for j, tt in ((0, float(s['t'][0])), (1, float(s['t'][1]))):
                if d0 - EPS <= tt <= d1 + EPS: s['pos'][j] = [round(s['pos'][j][q] + dv[q], 6) for q in range(3)]; hizo = True
    if c.get('girar_grados') is not None or c.get('rot_grados') is not None:
        for s in per['segmentos']:
            t0, t1 = float(s['t'][0]), float(s['t'][1])
            if not (t0 < d1 + EPS and t1 > d0 - EPS) and not (d0 == d1 and t0 - EPS <= d0 <= t1 + EPS): continue
            if c.get('rot_grados') is not None: s['rot'] = round(float(c['rot_grados']) % 360, 4); hizo = True
            elif K._num(s.get('rot')) is None: no.append(f"segmento {s['t']}: sin «rot» en el 01, no se puede girar relativo (usar mirar_grados)")
            else: s['rot'] = round((float(s['rot']) + float(c['girar_grados'])) % 360, 4); hizo = True
    for s in per['segmentos']:
        if d0 - EPS <= float(s['t'][0]) <= d1 + EPS or d0 - EPS <= float(s['t'][1]) <= d1 + EPS: s.setdefault('correcciones_04', []).append(c['id'])
    return hizo, '; '.join(no) or (None if hizo else 'ningún segmento cae en ese tramo')


def aplicar_camara(K, C, c, metas):
    m = metas.get(str(c['objetivo_id']))
    cu = (m or {}).get('camara_usada')
    if not cu or not cu.get('loc') or not cu.get('mira'): return False, 'no sé qué cámara usó el 02 en esa toma (falta camara_usada)'
    nueva = copy.deepcopy(cu)
    if c.get('mover_mm'): nueva['loc'] = [round(cu['loc'][q] + float(c['mover_mm'][q]) / 1000.0, 6) for q in range(3)]
    if c.get('mira_mover_mm'): nueva['mira'] = [round(cu['mira'][q] + float(c['mira_mover_mm'][q]) / 1000.0, 6) for q in range(3)]
    if c.get('lente_mm'): nueva['lente'] = float(c['lente_mm'])
    nueva['correccion_04'] = c['id']
    C.setdefault('camaras_toma', {})[str(c['objetivo_id'])] = nueva
    return True, None


def cubo04(K, D, a, cd, PC):
    b = K.dato('bucles.json').get('03_04') or {}; mx = int(b.get('max_vueltas') or 1)
    filas, rehacer = [], set()
    for e in K.escenas(D, a.solo):
        n = e['numero']; v = actual(K, D, n, importados=True)
        if not v: filas.append({'escena': n, 'aplicadas': 0, 'por_que': 'falta 01'}); continue
        ver = veredicto(K, D, n, v)
        if not ver: filas.append({'escena': n, 'version': v['k'], 'aplicadas': 0, 'por_que': f"sin veredicto del 03 para la versión v{v['k']}"}); continue
        if ver.get('aprobado'): filas.append({'escena': n, 'version': v['k'], 'aplicadas': 0, 'por_que': 'el 03 la aprobó: nada que corregir'}); continue
        if int(v['k']) >= mx:
            filas.append({'escena': n, 'version': v['k'], 'aplicadas': 0, 'a_usuario': True, 'por_que': f'ya van {mx} vueltas (bucles.json): pasa al usuario (04a), no se corrige más'}); continue
        tomas, _, _ = tomas_hechas(K, D, n, v['k']); metas = {str(t['toma']): t for t in tomas}
        C2 = copy.deepcopy(v['C']); hechas, no = [], []
        for c in ver.get('correcciones') or []:
            ok, pq = (aplicar_figura(K, C2, c) if c['objetivo'] == 'figura' else aplicar_camara(K, C2, c, metas))
            (hechas if ok else no).append({**c, **({'por_que': pq} if pq else {})})
        if not hechas:
            filas.append({'escena': n, 'version': v['k'], 'aplicadas': 0, 'no_aplicadas': no, 'a_usuario': True, 'por_que': 'ninguna corrección se pudo aplicar: pasa al usuario (04a)'})
            K.guardar(D / 'cubos' / '04a' / f'esc_{n}.json', {'escena': n, 'version': v['k'], 'por_que': 'el 04 no pudo aplicar ninguna corrección', 'no_aplicadas': no}); continue
        k2 = int(v['k']) + 1; f2 = D / 'cubos' / '04' / f'esc_{n}.v{k2}.json'
        if f2.exists(): filas.append({'escena': n, 'version': v['k'], 'aplicadas': 0, 'por_que': f'{f2.name} ya existe (no se pisa)'}); continue
        C2.update({'version': k2, 'de_version': v['k'], 'base_sha': v['base_sha'], 'correcciones_aplicadas': hechas, 'no_aplicadas': no,
                   'veredicto_03': {'ledger': ver.get('ledger'), 'de': ver.get('de')}, 'fecha_04': time.strftime('%Y-%m-%dT%H:%M:%S%z')})
        err, _ = K.validar_01(C2)
        if err: filas.append({'escena': n, 'version': v['k'], 'aplicadas': 0, 'por_que': f'la versión corregida no cumple el contrato: {err[:3]}'}); continue
        K.guardar(f2, C2)
        vid = D / 'ramas' / 'videos' / '02' / f'esc_{n}'
        if vid.is_dir():
            dst = D / 'cubos' / '04' / 'renders' / f'esc_{n}' / f"v{v['k']}"
            if dst.exists(): shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(vid), str(dst))
        rehacer.add(n)
        filas.append({'escena': n, 'version': v['k'], 'nueva_version': k2, 'archivo': str(f2), 'aplicadas': len(hechas), 'no_aplicadas': no,
                      'renders_anteriores': str(D / 'cubos' / '04' / 'renders' / f'esc_{n}' / f"v{v['k']}")})
    r02 = None
    if rehacer and not getattr(a, 'sin_rerender', False):
        a2 = copy.copy(a); a2.solo = set(rehacer); r02 = K.cubo02(D, a2, cd, PC)
        r02 = {k: r02.get(k) for k in ('resumen', 'videos', 'paradas', 'fallas', 'faltan', 'capitulo')}
    n_ap = sum(f.get('aplicadas') or 0 for f in filas)
    return K.r_base('04', D, {'escenas': filas, 'bucle': b, 'reanimado_02': r02, 'siguiente': '03' if rehacer else None,
                              'faltan': [] if n_ap else ['correcciones del 03 para la versión actual (no hay nada que aplicar)'],
                              'pistas': ['PISTA INMI (orden 82): versión nueva en cubos/04/esc_N.v<k>.json (nunca se pisa la anterior); videos viejos en cubos/04/renders/esc_N/v<k>/.'],
                              'resumen': f'04 · {n_ap} correcciones aplicadas en {len(rehacer)} escenas → versión nueva y 02 reanimado (gratis)'
                                         + (f" · {sum(1 for f in filas if f.get('a_usuario'))} escenas pasan al usuario (04a)" if any(f.get('a_usuario') for f in filas) else '')})
