"""PISTA INMI (2026-10-29): orden 87 (Ricardo 17:01 COT: «No pintes todavía, mete el método gratis en los cubos 02 y 11»).
CUBO 11 · «Pintar con Nano Banana», tipo de pedido «HÍBRIDO TIRA» (método de Ako): una llamada por HOJA de moldes del cubo 02
(2 tomas × N cuadros) → una tira pintada 2×N que se corta en N paneles para el cubo 12.

Por defecto SOLO COTIZA (US$0): arma el pedido exacto (texto + imágenes en orden) y su precio peor caso, y lo deja en
cubos/11/esc_<N>/<hoja>/{pedido_pintura.txt, pedido_refs.json, cotizacion.json} y cubos/11/cotizacion.json.
Imágenes del pedido, en este orden (cubo11_tira_pedido.construir, el mismo que reproduce el T06 aprobado):
  1. cada personaje que se ve: SOLO su versión APROBADA (personajes.refs_para), vista frente o espalda según hacia dónde mira el
     maniquí en esa hoja (medidas del 02). Falta una aprobada → esa hoja NO se pinta (se dice cuál).
  2. la hoja de moldes del 02 (con su leyenda de colores), 3. la muestra de estilo del canal (si la ficha la tiene),
  4. la tira ANTERIOR aprobada de la escena (continuidad). Pintada y sin aprobar → esa hoja espera.
Textos de viñeta: plan 03 (vinetas) → acción del plan 01 → plantilla de código (paso01_datos/hibrido.json).
Pagar SOLO con --correr + guarda cajas/HABILITAR_PAGO_11 (con monto) + --ok USD + --aprobado QUIEN. Cada intento escribe su línea
de ledger ANTES de llamar; tope de tiempo y ≥1 reintento por timeout (cajas/llamadas_config.json vía llamada_segura).
Después de pintar (gratis): revisión de rejilla, margen blanco y lado de pantalla (espejo) y corte en paneles en
ramas/imagenes/11/esc_<N>/ (los muestra la galería 12). Genérico (regla 6): nada de un canal en el código."""
import json, math, re, threading, time
from pathlib import Path

import cubo02_moldes as CM

AQUI = Path(__file__).resolve().parent


def _v(x):
    if isinstance(x, dict): x = x.get('valor')
    return str(x).strip() if x not in (None, '', 'None') else ''


def _clave(d, claves):
    for k in claves:
        cur = d
        for p in k.split('.'):
            cur = cur.get(p) if isinstance(cur, dict) else None
        if _v(cur): return _v(cur)
    return ''


def _ficha_nivel2(K, D, escenario_id, escena_num):
    """Paso 2: lee escena_nivel2.json si existe (US$0). None si no hay."""
    base = D / 'ramas' / 'moldes' / str(escenario_id)
    for cand in (base / f'escena_nivel2_esc{escena_num}.json', base / 'escena_nivel2.json'):
        doc = K.leer(cand)
        if isinstance(doc, dict) and doc.get('esquema'):
            return doc, cand
    return None, None


def _enriquecer_con_nivel2(desc_set, estilo_extra, cfg_pintura_extra, pers, n2, av):
    """Mezcla campos Nivel 2 en textos del pedido. No inventa; salta FALTA/SIN_ANCLA."""
    extras = []
    mats = (n2.get('MATERIALES_ESCENA') or {})
    if mats.get('texto') and 'FALTA' not in str(mats.get('texto')):
        extras.append(f"Texturas: {mats['texto']}")
    clima = None
    por = n2.get('CLIMA_Y_LUZ_POR_ESCENA') or {}
    # escena_num llega vía ID; el caller ya eligió doc; usar top-level
    clima = (n2.get('CLIMA_Y_LUZ_ESCENA') or {}).get('valor')
    if clima and not str(clima).startswith('FALTA'):
        extras.append(f"Clima y Luz: {clima}")
    fondo = (n2.get('ESTILO_FONDO_INGLES') or {}).get('valor')
    atm = (n2.get('ATMOSFERA_INGLES') or {}).get('valor')
    pal = (n2.get('PALETA_ESCENA_INGLES') or {}).get('valor')
    bits = []
    if fondo and fondo != 'FALTA':
        bits.append(fondo)
    if atm and atm != 'FALTA':
        bits.append(atm)
    if pal and pal != 'FALTA':
        bits.append(f"palette of {pal}")
    if bits:
        add = ', '.join(bits)
        estilo_extra = (estilo_extra + '; ' + add).strip('; ') if estilo_extra else add
    if extras:
        desc_set = (desc_set.rstrip('.') + '. ' + ' '.join(extras)).strip()
    # DESC_ROPA → identidad si hay sidecar
    by_name = {(p.get('nombre') or '').lower(): p for p in (n2.get('PERSONAJES') or [])}
    for p in pers:
        key =[REDACTED]
        hit = by_name.get(key)
        if not hit:
            continue
        ropa = hit.get('DESC_ROPA') or ''
        if ropa and not str(ropa).startswith('FALTA'):
            if ropa not in (p.get('identidad') or ''):
                p['identidad'] = ((p.get('identidad') or '') + ' ' + ropa).strip()
    ancla = n2.get('ANCLA_ESCENA') or {}
    ancla_path = ancla.get('path')
    ancla_ref = None
    if ancla_path and ancla_path not in ('SIN_ANCLA',) and Path(ancla_path).is_file():
        frase = ancla.get('frase_que_copia') or 'scene anchor: copy only paint finish, light and weather'
        ancla_ref = {'ruta': ancla_path, 'desc': frase}
        av.append(f"ficha Nivel 2: ancla de escena {ancla_path}")
    else:
        av.append('ficha Nivel 2: sin ancla de escena (SIN_ANCLA o ausente)')
    av.append('ficha Nivel 2 aplicada a set/estilo_extra')
    return desc_set, estilo_extra, ancla_ref



def indice(K, D, n):
    fs = (D / 'ramas' / 'moldes').glob(f'*/tomas/esc_{n}/moldes.json') if (D / 'ramas' / 'moldes').is_dir() else []
    for f in sorted(fs, key=lambda x: x.stat().st_mtime, reverse=True):   # el más nuevo (si el escenario de la escena cambió, el viejo no manda)
        return K.leer(f), f.parent
    return None, None


def textos_03(K, D, n, aj):
    r = K.leer(D / 'cubos' / '03' / f'esc_{n}.json') or {}
    for k in aj['pintura']['claves_texto_03']:
        for x in (r, r.get('respuesta') if isinstance(r.get('respuesta'), dict) else {}):
            v = x.get(k) if isinstance(x, dict) else None
            if isinstance(v, dict): return {str(a): str(b) for a, b in v.items() if str(b).strip()}
            if isinstance(v, list): return {str(i.get('id')): str(i.get('texto') or i.get('prompt') or '') for i in v if isinstance(i, dict) and i.get('id')}
    return {}


def tira_de(D, n, hid): return D / 'ramas' / 'imagenes' / '11' / f'esc_{n}' / f'{hid}__tira.png'


def pedido_hoja(K, P, ET, PT, HP, D, e, C, idx, base, h, prev, cd, est, I, T, aj):
    """Pedido de UNA hoja. Devuelve dict con 'detener' (lista) y, si se puede armar, el pedido y su precio."""
    n = e['numero']; pi = aj['pintura']; canal = D.parent.name; det, av = [], []
    cfgB = K.leer(base / 'config_blender.json') or {}; med = K.leer(base / 'crudos' / 'medidas.json') or {}; cam = K.leer(base / 'crudos' / 'camaras_ajustadas.json') or {}
    fichas = {f['id']: f for f in idx.get('personajes') or []}; accs = {p['id']: p.get('accesorios') or [] for p in cfgB.get('personajes') or []}
    vis = {}
    for k in h['ids']:
        for i, v in ((med.get(k) or {}).get('vis') or {}).items(): vis.setdefault(i, []).append(bool(v.get('mira_a_camara')))
    if not vis: det.append(f"escena {n} hoja {h['id']}: ningún personaje se ve en los moldes: no hay nada que pintar")
    pers = []
    for i, mir in vis.items():
        f = fichas.get(i) or {}; cid = f.get('personaje_id') or i
        lado = None
        if f.get('giro_conocido', True): lado = 'frente' if sum(mir) * 2 >= len(mir) else 'espalda'
        else: av.append(f"{f.get('nombre') or cid}: el 01 no dice hacia dónde mira: la vista de referencia la elige personajes.py")
        try: R = P.refs_para(canal, D, n, personaje=cid, lado=lado)
        except Exception as ex: R = {'ok': False, 'detener': [f'no pude leer personajes.json ({type(ex).__name__}: {ex})'], 'usar': []}
        det += [f"hoja {h['id']}: {x}" for x in R.get('detener') or []]
        usar = [u for u in R.get('usar') or [] if u.get('personaje_id') == cid or u.get('grupo_id') == cid]
        if f.get('forma_id') and any(u.get('forma_id') == f['forma_id'] for u in usar): usar = [u for u in usar if u.get('forma_id') == f['forma_id']]
        if not usar and not R.get('detener'):
            det.append(f"escena {n} hoja {h['id']}: {f.get('nombre') or cid} no tiene versión APROBADA en personajes.json para esta escena: no se pinta (los personajes nunca se generan)")
        refs = []
        for u in usar:
            for r, vista in zip(u['imagenes'], u.get('vistas_usadas') or [None] * len(u['imagenes'])):
                if not Path(r).is_file(): det.append(f"escena {n} hoja {h['id']}: falta el archivo de la versión aprobada {u['personaje']} – {u['version']}: {r}"); continue
                refs.append({'ruta': r, 'desc': pi['ref_personaje_desc'].format(nombre=u['personaje'], version=u['version'], vista=vista or u.get('lado') or 'reference')})
        refs = refs[:int(pi['max_imagenes_por_personaje'])]
        if usar and not refs and not any(u.get('tipo') == 'relleno' for u in usar):
            det.append(f"escena {n} hoja {h['id']}: la versión aprobada de {usar[0]['personaje']} – {usar[0]['version']} no tiene imágenes: no se pinta")
        elif usar and not refs: av.append(f"{usar[0]['personaje']}: relleno sin imagen (orden 88): va solo por su descripción")
        nom = f.get('nombre') or (usar[0]['personaje'] if usar else cid)
        ident = f.get('identidad_en') or (usar[0].get('descripcion') if usar else '') or nom
        if usar and usar[0].get('nunca_cambia'): ident += f" Never changes: {usar[0]['nunca_cambia']}."
        a_ = [{'nombre': x['nombre'], 'nombre_prompt': x.get('nombre_prompt') or x['nombre'], 'color_nombre': x.get('color_nombre') or 'COLOURED'} for x in accs.get(i, [])]
        pers.append({'id': i, 'personaje_id': cid, 'clave': nom, 'nombre_prompt': nom, 'nombre_corto': nom, 'alto_m': float(f.get('alto_m') or 0),
                     'color_nombre': f.get('color_nombre') or 'COLOURED', 'accesorios': a_, 'identidad': ident, 'obligatorias': f.get('obligatorias') or [],
                     'prohibidas': f.get('prohibidas') or [], 'refs': refs, 'lado': lado,
                     'version': usar[0]['version'] if usar else None, 'aprobada': bool(usar)})
    esc = K.leer(D / 'ramas' / 'moldes' / str(idx['escenario_id']) / 'escenario.json') or {}
    set_corto = _clave(esc, pi['claves_set_corto']) or str(idx['escenario_id'])
    desc_set = _clave(esc, pi['claves_descripcion_set'] + ['planta.descripcion'])
    if not desc_set: av.append('el escenario no trae descripción: el pedido solo dice su nombre'); desc_set = set_corto
    # Paso 2 (31-oct-2026): enriquecer con ficha Nivel 2 si existe (gratis). Estilo del canal sigue ÚLTIMO.
    n2_doc, n2_path = _ficha_nivel2(K, D, idx['escenario_id'], n)
    ancla_ref = None
    estilo_extra_n2 = (est or {}).get('fondo_en') or ''
    if n2_doc:
        # prefer clima of this scene number if the pack has POR_ESCENA
        por = n2_doc.get('CLIMA_Y_LUZ_POR_ESCENA') or {}
        if str(n) in por:
            n2_doc = dict(n2_doc)
            n2_doc['CLIMA_Y_LUZ_ESCENA'] = por[str(n)]
        desc_set, estilo_extra_n2, ancla_ref = _enriquecer_con_nivel2(desc_set, estilo_extra_n2, None, pers, n2_doc, av)
        av.append(f'ficha Nivel 2 leída: {n2_path}')
    momento = ', '.join(x for x in (_v((e.get('datos') or {}).get(k)) for k in pi['claves_momento']) if x) or pi['momento_si_falta']
    ar = K.aspecto(cd) or (16, 9)
    filas = (len(h['ids']) + 1) // 2
    muestra = (est or {}).get('imagen') or ''
    if muestra and not Path(muestra).is_file(): av.append(f'la muestra de estilo del canal no está en el disco ({muestra})'); muestra = ''
    if not muestra:
        (det if pi['estilo_muestra_obligatoria'] else av).append('el canal no tiene imagen de muestra de estilo (style_fijo.imagen): el estilo va solo en texto')
    cfgP = {'personajes': pers, 'colores_molde': cfgB.get('colores_molde') or {},
            'escenario': {'set_corto': set_corto, 'escena_corta': _v((e.get('datos') or {}).get('titulo')) or set_corto, 'descripcion_prompt': desc_set},
            'pintura': {'cuadricula': [2, filas], 'aspecto_panel': f'{ar[0]}:{ar[1]}', 'estilo': re.sub(r'\.\.+(?=\s|$)', '.', (est or {}).get('descripcion_en') or '').rstrip('. '),   # sin «..» al unir textos de estilo (la plantilla ya pone el punto)
                        'estilo_extra': estilo_extra_n2, 'momento': momento, 'max_refs': pi['max_refs'],
                        **({'estilo_ref': {'ruta': muestra, 'desc': pi['estilo_muestra_desc']}} if muestra else {})},
            'plan': {'tomas': []}}
    t03 = textos_03(K, D, n, aj); fuente = {}
    por_toma = {}
    for k in h['ids']:
        tid, cn = k.rsplit('_', 1); cu = h['cuadros'].get(k) or {}
        txt = t03.get(k); fuente[k] = 'plan 03' if txt else ('plan 01' if cu.get('accion') else 'plantilla')
        por_toma.setdefault(tid, []).append({'n': int(cn), 't': cu.get('t'), 'accion': txt or cu.get('accion') or pi['accion_si_falta']})
    cfgP['plan']['tomas'] = [{'id': t, 'cuadros': c} for t, c in por_toma.items()]
    pv = {'id': prev, 'estado': None, 'ruta': None}
    if prev:
        fp = tira_de(D, n, prev); mp = K.leer(fp.with_suffix('.json')) or {}
        if fp.is_file() and mp.get('aprobada'): pv.update(estado='aprobada', ruta=str(fp))
        elif fp.is_file(): pv['estado'] = 'pintada_sin_aprobar'; det.append(f"escena {n} hoja {h['id']}: la tira anterior {prev} está pintada pero NO aprobada: esta espera (continuidad)")
        else: pv['estado'] = 'sin_pintar'; av.append(f"la tira anterior {prev} aún no está pintada: se pinta y aprueba primero; esta irá con ella como continuidad")
    if not (est or {}).get('descripcion_en'): det.append('el canal no tiene estilo fijo aprobado (style_fijo): no se pinta')
    out = {'escena': n, 'hoja': h['id'], 'tomas': h['tomas'], 'paneles': h['ids'], 'personajes': [{k: p[k] for k in ('personaje_id', 'nombre_corto', 'version', 'lado', 'aprobada')} | {'refs': [r['ruta'] for r in p['refs']]} for p in pers],
           'hoja_molde': h.get('hoja'), 'previa': pv, 'textos_de': fuente, 'avisos': av, 'detener': det}
    if not pers or not cfgP['pintura']['estilo']: return out
    try:
        vin = HP.vinetas_plantilla(cfgP, med, cam, {k: (h.get('cobertura') or {}).get(k, {}).get('cielo', 0) for k in h['ids']})
        hist = '; '.join(x for x in (_v((e.get('datos') or {}).get('titulo')), _v(C.get('resumen') if C else ''), _v(C.get('dialogo_referencia') if C else '')) if x)
        R = HP.construir(cfgP, vin, h['hoja'], previa=pv['ruta'] or (str(tira_de(D, n, prev)) if prev else None), historia=hist, exclude_extra=(est or {}).get('negativo') or '', ancla=ancla_ref)
    except (ValueError, KeyError) as ex:
        det.append(f"escena {n} hoja {h['id']}: no se pudo armar el pedido: {ex}"); return out
    for d_, r in R['refs']:
        if not Path(r).is_file() and r != str(tira_de(D, n, prev)): det.append(f"escena {n} hoja {h['id']}: falta la imagen {r}")
    # Arreglo 4 continuidad (Ricardo t375u): línea «ESTADO EN ESTA TOMA» por toma (+ cambio a mitad), desde el plan del 05
    import estado_continuidad as EC
    tp_, _ = K._plan(D)
    bloque = EC.bloque_estados(list(por_toma), tp_, lambda m: K.dirigida(D, m)[0], K.leer(D / 'cubos' / 'SB' / 'memoria_continuidad.json', {}) or {})
    if bloque: R['prompt'] += '\n\n' + bloque; R['texto_archivo'] += '\n\n' + bloque
    out['estado_tomas'] = bloque
    usd = PT.precio_llamada(I, T, len(R['prompt']), len(R['refs']))
    tope = float(pi['tope_por_llamada_usd'])
    out.update(texto=R['prompt'], refs=[{'n': i + 1, 'desc': d_, 'ruta': r} for i, (d_, r) in enumerate(R['refs'])], imagen_molde=R['imagen_molde'],
               aspecto=PT.aspecto(h['hoja']), modelo=I['modelo'], talla=I['talla'], usd_peor_caso=usd, cabe_en_tope=usd <= tope + 1e-9, tope_usd=tope,
               chars=len(R['prompt']), n_imagenes=len(R['refs']))
    if not out['cabe_en_tope']: det.append(f"escena {n} hoja {h['id']}: peor caso US${usd} > tope por llamada US${tope}")
    sal = D / 'cubos' / '11' / f'esc_{n}' / h['id']; sal.mkdir(parents=True, exist_ok=True)
    (sal / 'pedido_pintura.txt').write_text(R['texto_archivo'], encoding='utf-8')
    K.guardar(sal / 'pedido_refs.json', out['refs']); K.guardar(sal / 'cotizacion.json', {k: v for k, v in out.items() if k != 'texto'})
    return out


def revisar(tira, hoja_molde, ids, panel, aj):
    """Revisión GRATIS de la tira pintada: rejilla 2×N con calles blancas, margen blanco y lado de pantalla (espejo) por panel."""
    import numpy as np
    from PIL import Image, ImageFilter, ImageOps
    import cubo02_moldes_convertir as HC
    rv = aj['revision']; M = Image.open(hoja_molde).convert('RGB'); S = Image.open(tira).convert('RGB').resize(M.size, Image.LANCZOS)
    A = np.asarray(ImageOps.grayscale(S)).astype(float); W, Hh = panel; cajas = HC.geometria(len(ids), W, Hh)
    blanco = lambda z: float((z >= rv['blanco_min']).mean()) if z.size else 1.0
    mg = 48; pr = {'margen': min(blanco(A[:mg]), blanco(A[-mg:]), blanco(A[:, :mg]), blanco(A[:, -mg:]))}
    x0 = cajas[0][2]; pr['calle_columnas'] = blanco(A[mg:-mg, x0 + 4:x0 + 20])
    pr['calles_filas'] = [blanco(A[c[3] + 4:c[3] + 20, mg:-mg]) for c in cajas[1::2][:-1]] if len(cajas) > 2 else []
    rej = all(v >= rv['fraccion_blanca_calle'] for v in [pr['calle_columnas'], *pr['calles_filas']]); mar = pr['margen'] >= rv['fraccion_blanca_calle']

    def bordes(im): return np.asarray(ImageOps.grayscale(im).filter(ImageFilter.FIND_EDGES).resize((96, 54))).astype(float).ravel()

    def corr(a, b):
        a = a - a.mean(); b = b - b.mean(); d = math.sqrt((a * a).sum() * (b * b).sum()) or 1.0; return float((a * b).sum() / d)
    paneles = []
    for k, c in zip(ids, cajas):
        p = S.crop(c); m = M.crop(c); bp = bordes(p)
        r1, r2 = corr(bp, bordes(m)), corr(bp, bordes(ImageOps.mirror(m)))
        paneles.append({'id': k, 'caja': list(c), 'parecido_molde': round(r1, 3), 'parecido_espejo': round(r2, 3), 'volteado': r2 > r1 + rv['espejo_peor_por']})
    return {'ok': rej and mar and not any(p['volteado'] for p in paneles), 'rejilla_ok': rej, 'margen_ok': mar, 'medidas': pr, 'paneles': paneles,
            'tamano_pintado': list(Image.open(tira).size), 'tamano_molde': list(M.size)}


def cortar(K, tira, rv, D, n, hid, meta):
    from PIL import Image
    M = Image.open(tira).convert('RGB'); sal = D / 'ramas' / 'imagenes' / '11' / f'esc_{n}'; out = []
    sx = M.size[0] / rv['tamano_molde'][0]; sy = M.size[1] / rv['tamano_molde'][1]
    for p in rv['paneles']:
        c = p['caja']; f = sal / f"{p['id']}.png"
        M.crop((round(c[0] * sx), round(c[1] * sy), round(c[2] * sx), round(c[3] * sy))).save(f)
        ok = rv['rejilla_ok'] and rv['margen_ok'] and not p['volteado']
        K.guardar(f.with_suffix('.json'), {'ok': ok, 'cubo': '11', 'tipo': 'hibrido_tira', 'escena': n, 'hoja': hid, 'panel': p['id'], 'tira': str(tira),
                                           'error': None if ok else ('panel volteado (espejo) respecto al molde' if p['volteado'] else 'la rejilla/margen de la tira no cuadra'),
                                           'revision': p, 'ledger': meta.get('ledger'), 'aprobada': False})
        out.append(str(f))
    return out


def correr(K, D, a, cd, listos, I, T, aj, app=None, dormir=time.sleep):
    """Camino PAGO (solo con guarda + --ok + --aprobado). Una llamada por hoja; ledger ANTES de cada intento."""
    import llamada_segura as LS, paso01_pago as PG, paso00_pintar as PT
    pi = aj['pintura']; G = PG.GUARDA_DIR / pi['guarda']
    if not G.is_file(): return {'ok': False, 'error': f'pago del cubo 11 cerrado: falta cajas/{G.name} (pago no aprobado). No se llamó a nada.', 'llamadas_hechas': 0}
    if a.ok is None or not a.aprobado: return {'ok': False, 'error': 'falta --ok USD y --aprobado QUIEN', 'llamadas_hechas': 0}
    mm = re.search(r'\d+(?:[.,]\d+)?', G.read_text(errors='replace'))
    if not mm: return {'ok': False, 'error': f'{G.name} no trae el monto aprobado: no se llama', 'llamadas_hechas': 0}
    if float(a.ok) > float(mm.group().replace(',', '.')) + 1e-9: return {'ok': False, 'error': f'--ok {a.ok} pasa el monto habilitado en {G.name}', 'llamadas_hechas': 0}
    if not listos: return {'ok': False, 'error': 'ninguna hoja está lista para pintar (ver «detener»)', 'llamadas_hechas': 0}
    X = app() if app else PG.app(); AR = X['AR']; dormir = X.get('dormir') or dormir
    from google.genai import types
    cli = AR._cliente(); corrida = time.strftime('%Y%m%d-%H%M%S'); bolsa = {'gastado': 0.0, 'reservado': 0.0}; lock = threading.Lock(); hechas = []
    for q in listos:
        if q['previa'].get('id') and q['previa'].get('estado') != 'aprobada':
            hechas.append({'escena': q['escena'], 'hoja': q['hoja'], 'ok': False, 'saltada': f"espera: la tira anterior {q['previa']['id']} tiene que estar pintada y APROBADA", 'usd': 0}); continue
        est = q['usd_peor_caso']; base_lid = f"taller11-hibrido-esc{q['escena']}-{q['hoja']}-{corrida}"
        partes = [types.Part.from_bytes(data=Path(r['ruta']).read_bytes(), mime_type='image/png' if r['ruta'].endswith('.png') else 'image/jpeg') for r in q['refs']]
        partes.append(types.Part.from_text(text=q['texto']))
        cfg = types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'], image_config=types.ImageConfig(aspect_ratio=q['aspecto'], image_size=q['talla']),
                                          http_options=types.HttpOptions(timeout=LS.timeout_ms('imagen')))
        t0 = time.time()

        def intento(k, q=q, est=est, base_lid=base_lid, partes=partes, cfg=cfg):
            lid = base_lid + ('' if k == 1 else f'-i{k}')
            with lock:
                if bolsa['gastado'] + bolsa['reservado'] + est > a.ok + 1e-9: raise LS.SinPresupuesto(f"sin_presupuesto (gastado {round(bolsa['gastado'], 4)} + esta {est} > --ok {a.ok})")
                bolsa['reservado'] += est
                try: AR.registrar(lid, f"{q['modelo']} {q['talla']}", est, f"11 hibrido tira esc {q['escena']} {q['hoja']} intento {k} (aprobado {a.aprobado})", tipo='imagen', ok_usd=est, tope_usd=pi['tope_por_llamada_usd'])
                except Exception as e0: bolsa['reservado'] -= est; raise LS.NoLlamado(f'{type(e0).__name__}: {str(e0)[:200]}') from e0
            try: return lid, cli.models.generate_content(model=q['modelo'], contents=[types.Content(role='user', parts=partes)], config=cfg)
            except Exception as e:
                cobro = LS.estado_fallo(e)
                with lock:
                    AR.marcar(lid, cobro, est, ''); bolsa['reservado'] -= est
                    if cobro != 'no_cobrado': bolsa['gastado'] += est
                raise
        try:
            (lid, r), ints = LS.intentar(intento, max_intentos=max(1, min(6, int(getattr(a, 'max_intentos', None) or PT.MAX_INTENTOS))), max_transitorios=1, dormir=dormir,
                                         ritmo=None, ahora=PT.ahora, espera_base=LS.num_env('TALLER_ESPERA_429_S', 20), espera_max=LS.num_env('TALLER_ESPERA_MAX_S', 120),
                                         puede_otro=lambda k, c_, est=est: bolsa['gastado'] + bolsa['reservado'] + est <= a.ok + 1e-9)
        except LS.IntentosAgotados as e:
            hechas.append({'escena': q['escena'], 'hoja': q['hoja'], 'ok': False, 'error': str(e)[:300], 'intentos': e.intentos,
                           'usd': round(sum(est for z in e.intentos if LS.cuenta_peor_caso(z.get('cobro'))), 4)}); continue
        data = None
        for cnd in (r.candidates or []):
            for pt in ((cnd.content.parts or []) if cnd.content else []):
                if pt.inline_data and pt.inline_data.data: data = pt.inline_data.data; break
            if data: break
        um = getattr(r, 'usage_metadata', None); cr = PT.costo_real(I, T, um, len(q['refs'])); usd = cr if cr is not None else est
        f = tira_de(D, q['escena'], q['hoja'])
        with lock:
            if data: f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
            AR.marcar(lid, 'ok' if data else 'sin_imagen', usd, str(f) if data else ''); bolsa['reservado'] -= est; bolsa['gastado'] += usd
        if not data: hechas.append({'escena': q['escena'], 'hoja': q['hoja'], 'ok': False, 'error': 'sin imagen en la respuesta', 'usd': usd, 'ledger': lid}); continue
        rv = revisar(f, q['hoja_molde'], q['paneles'], tuple(q['panel_px']), aj)
        meta = {'ok': True, 'cubo': '11', 'tipo': 'hibrido_tira', 'escena': q['escena'], 'hoja': q['hoja'], 'modelo': q['modelo'], 'talla': q['talla'], 'usd': usd,
                'ledger': lid, 'intentos': len(ints), 'aprobado_pago': a.aprobado, 'aprobada': False, 'revision': rv, 'segundos': round(time.time() - t0, 1), 'fecha': PT.ahora(),
                'texto': q['texto'], 'refs': q['refs']}
        K.guardar(f.with_suffix('.json'), meta)
        cort = cortar(K, f, rv, D, q['escena'], q['hoja'], meta)
        hechas.append({'escena': q['escena'], 'hoja': q['hoja'], 'ok': True, 'tira': str(f), 'paneles': cort, 'revision_ok': rv['ok'], 'usd': usd, 'ledger': lid})
    g = round(sum(x.get('usd') or 0 for x in hechas), 4)
    return {'ok': True, 'modo': 'correr', 'gratis': False, 'llamadas_hechas': len(hechas), 'usd_gastado': g, 'hechas': hechas}


def cubo11(K, D, a, cd, PC, app=None):
    import personajes as P, estilo_taller as ET, paso00_pintar as PT, cubo11_tira_pedido as HP
    aj = CM.ajustes(); detener, avisos, pedidos = [], [], []
    try: I = ET.imagen_canal(cd)
    except Exception as ex: I = None; detener.append(f'no se puede cotizar: {ex}')
    T = PT.tramo(I['modelo'], I['talla']) if I else None
    est = ET.resolver(cd)
    if not est: detener.append('el canal no tiene estilo fijo aprobado (style_fijo): no se pinta')
    for e in K.escenas(D, a.solo):
        n = e['numero']; idx, base = indice(K, D, n)
        if not idx: detener.append(f'escena {n}: el 02 no sacó moldes de toma (corre el 02 primero)'); continue
        if not idx.get('ok'): detener.append(f"escena {n}: los moldes del 02 están PARADOS: {idx.get('motivo')}"); continue
        C, _ = K.dirigida(D, n, importados=True); prev = None
        for h in idx['hojas']:
            if not h.get('ok'): detener.append(f"escena {n} hoja {h['id']}: molde parado: {h.get('motivo')}"); prev = h['id']; continue
            if not I or not est: prev = h['id']; continue
            q = pedido_hoja(K, P, ET, PT, HP, D, e, C, idx, base, h, prev, cd, est, I, T, aj)
            q['panel_px'] = h.get('panel_px'); pedidos.append(q); detener += q['detener']; avisos += [f"escena {n} hoja {h['id']}: {x}" for x in q['avisos']]
            prev = h['id']
    listos = [q for q in pedidos if not q['detener'] and q.get('texto')]
    total = round(sum(q.get('usd_peor_caso') or 0 for q in listos), 4)
    cot = {'cubo': '11', 'tipo': 'hibrido_tira', 'modelo': (I or {}).get('modelo'), 'talla': (I or {}).get('talla'), 'fuente_precio': (I or {}).get('fuente_precio'),
           'hojas': [{k: v for k, v in q.items() if k != 'texto'} for q in pedidos], 'listas': len(listos), 'usd_peor_caso_total': total, 'detener': detener}
    K.guardar(D / 'cubos' / '11' / 'cotizacion.json', cot)
    if a.correr:
        r = correr(K, D, a, cd, listos, I, T, aj, app=app)
        return {**K.r_base('11', D, {'modo': 'correr'}), **r, 'detener': sorted(set(detener))}
    res = (f"11 · híbrido tira: {len(listos)} de {len(pedidos)} hojas listas para pintar, peor caso US${total} ({(I or {}).get('modelo')} {(I or {}).get('talla')})"
           + (f' · {len(set(detener))} motivos de parada' if detener else '') + ' · SOLO COTIZA (US$0)')
    if not pedidos: res = '⛔ 11 PARADO · ninguna hoja de moldes del 02 se puede pintar: ' + (detener[0] if detener else 'no hay escenas')
    return K.r_base('11', D, {'tipo': 'hibrido_tira', 'hojas': len(pedidos), 'listas': len(listos), 'usd_peor_caso_total': total,
                              'detener': sorted(set(detener))[:40], 'avisos': sorted(set(avisos))[:40], 'archivo': str(D / 'cubos' / '11' / 'cotizacion.json'),
                              'pedidos': [{'escena': q['escena'], 'hoja': q['hoja'], 'usd': q.get('usd_peor_caso'), 'imagenes': q.get('n_imagenes'), 'listo': not q['detener'],
                                           'archivo': str(D / 'cubos' / '11' / f"esc_{q['escena']}" / q['hoja'] / 'pedido_pintura.txt')} for q in pedidos],
                              'pistas': ['PISTA INMI (2026-10-29): orden 87 — método híbrido de Ako: el 11 pinta ENCIMA de la hoja de moldes del 02; los personajes '
                                         'solo entran por sus versiones APROBADAS; nunca se generan. Pagar pide HABILITAR_PAGO_11 + --correr --ok --aprobado.'],
                              'resumen': res})
