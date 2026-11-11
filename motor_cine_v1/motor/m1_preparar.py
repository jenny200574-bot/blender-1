"""m1_preparar — motor unificado v1 [10-nov-2026]. Corre en 213 (python3, sin Blender).
Junta TODO lo que el motor necesita para una escena, sin crear nada:
  - 01 de la escena (cubos/01/esc_N.json), storyboard (cubos/SB/esc_N.json) y cámara v2 con altura_m (cubos/SB/blender/esc_N_camara_v2_altura.json)
  - moldes de personaje publicados en la biblioteca (/opt/myia-biblioteca/<canal>/personajes/<id>/meta.json -> última versión 'blend')
  - molde de escenario publicado (biblioteca escenarios/<id>); si la fábrica aún no lo publicó, se usa el molde del taller
    (ramas/moldes/<id>/molde.blend) SOLO si --permitir_escenario_taller, y se marca en el reporte.
  - programa 2B de Argon si existe (cubos/2B/esc_N.json) — opcional.
Si falta un molde de personaje: STOP «MOLDE_FALTANTE» (o, con --permitir_faltantes, se reporta y ese personaje no sale).
Nunca modifica moldes: los copia (sha256 verificado) a la carpeta de la corrida.
Aplica el historial de la historia al CARGAR (variante aprobada, ocultar parte, material).
Si la variante aún no tiene approval_ref: aviso tipado VARIANTE_NO_APROBADA y fallback declarado
(placeholder = se copia el molde base, nunca en silencio; o block si --exigir_variante_aprobada).
El molde base en la biblioteca no se edita ni se borra."""
import json, argparse, shutil, hashlib, sys, re
from pathlib import Path
from datetime import datetime
import historial_historia as HH

ESTADOS_OK = ('aprobado', 'publicado', 'hoja_lista', 'listo')        # hoja_lista = pendiente aprobación de Ricardo (modo prueba)

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def ultima(meta, kind):
    vs = [v for v in meta.get('versiones', []) if v.get('kind') == kind]
    return vs[-1] if vs else None

def stem01(pid):  # ch-<nombre>-<hash> -> <nombre> (nombres compuestos incluidos)
    m = re.match(r'ch-(.+)-[0-9a-f]{4}$', pid); return m.group(1) if m else pid

def prefijo_bib(bib):
    """prefijo de ids del canal (p. ej. '<prefijo>-') sacado de lo publicado en la biblioteca del canal; '' si no hay uno común (>=60 %)."""
    import collections
    ids = [d.name for t in ('personajes', 'objetos', 'objetos_usuario') if (bib / t).is_dir() for d in (bib / t).iterdir() if d.is_dir()]
    pre = [m.group(1) for m in (re.match(r'^([a-z0-9]{2,6}-)', i) for i in ids) if m]
    if len(ids) < 2 or not pre: return ''
    p, n = collections.Counter(pre).most_common(1)[0]
    return p if n >= 0.6 * len(ids) else ''

CUBO = Path('/opt/myia-taller-n8n/cajas/cubo_fijo')     # sellos y ADN de objetos (la biblioteca aún no copia el ADN de objetos)

def leer_adn(d, pid):
    for f in ([d / 'adn' / f'{pid}_ako.json'] if d else []) + [CUBO / 'adn' / f'{pid}_ako.json']:
        if f.is_file():
            try: return json.load(open(f))
            except Exception: pass
    return {}

def sujeto_kimodo(adn, plantilla=None):
    """sujeto del texto de Kimodo según el ADN (línea «Edad visual» / plantilla); 'A child' SOLO si el ADN dice niño o edad < 13."""
    t = str(adn.get('texto') or '')
    mv = re.search(r'Edad visual[^\n]{0,140}', t, re.I); lin = mv.group(0) if mv else t[:300]
    if re.search(r'ave|cuadr|animal|pez|insecto', str(plantilla or ''), re.I) or re.search(r'\b(ave|pájaro|polluelo|animal|cuadrúpedo|perro|gato|cachorro)\b', lin, re.I):
        return 'An animal', 'ADN/plantilla: animal'
    m = re.search(r'(\d{1,3})(?:\s*(?:-|a|–)\s*(\d{1,3}))?\s*años', lin, re.I) or re.search(r'Edad visual[^0-9\n]{0,40}(\d{1,3})(?:\s*(?:-|a|–)\s*(\d{1,3}))?', t, re.I)
    if m:
        e = (int(m.group(1)) + int(m.group(2) or m.group(1))) / 2
        s = 'A child' if e < 13 else 'A teenager' if e < 18 else 'An elderly person' if e >= 60 else 'An adult'
        return s, f'ADN edad visual ~{e:g} años'
    if re.search(r'\bniñ[oa]\b|infantil', lin, re.I): return 'A child', 'ADN: niño'
    if re.search(r'robot|criatura|monstruo|alien', lin, re.I): return 'A creature', 'ADN: criatura'
    return 'A person', 'ADN sin edad: neutro'

def base_obj(x):
    return re.sub(r'(__.*|#\d+)$', '', str(x or '')).strip()

def _id_de_biblioteca(b, idx=None):
    """Id de objeto de la escena: prefijo obj- (contrato actual) o una pieza que ya existe en la biblioteca del canal."""
    if not b:
        return ''
    if re.match(r'^obj-[a-z0-9-]+$', b):
        return b
    if idx and any(b == c or b == x['dir'].name for x in idx for c in (x.get('claves') or set()) | {x['dir'].name}):
        return b
    return ''


def objetos_pedidos(D, sb, pjs, idx=None):
    """objetos que pide la escena: 01 (acciones[].objeto) + storyboard (director_imagen.objetos) + props portados de los personajes."""
    ped = {}
    for a in D.get('acciones', []):
        b = _id_de_biblioteca(base_obj(a.get('objeto')), idx)
        if b: ped.setdefault(b, {"fuentes": set(), "actores": []})["fuentes"].add('01')
        if b and a.get('actor') and a['actor'] not in ped[b]['actores']: ped[b]['actores'].append(a['actor'])
    for v in (sb or {}).get('vinetas', []):
        for o in ((v.get('director_imagen') or {}).get('objetos') or []):
            b = _id_de_biblioteca(base_obj(o.get('nombre') if isinstance(o, dict) else o), idx)
            if b:   # ids de biblioteca; los nombres libres del SB los resuelve el escenario
                ped.setdefault(b, {"fuentes": set(), "actores": []})["fuentes"].add('SB')
    for pid, bibname in pjs.items():          # props portados (sello del objeto: dueno = personaje)
        for sp in sorted((CUBO / 'objetos_pj').glob('*.json')):
            try: s_ = json.load(open(sp))
            except Exception: continue
            if s_.get('dueno') == bibname and (s_.get('subclase') == 'portado'):
                for b in [x for x in (s_.get('ids_canal') or []) if x.startswith('obj-')][:1] or ['obj-' + sp.stem]:
                    ped.setdefault(b, {"fuentes": set(), "actores": []})["fuentes"].add('portado')
                    if pid not in ped[b]['actores']: ped[b]['actores'].insert(0, pid)
    return ped

def indice_objetos(bib):
    """pieza de la biblioteca por id del canal: instancia de origen (v2_3d), ids_canal del sello, nombre de carpeta."""
    idx = []
    for t in ('objetos_usuario', 'objetos'):
        for d in sorted((bib / t).iterdir()) if (bib / t).is_dir() else []:
            mp = d / 'meta.json'
            if not mp.is_file(): continue
            m = json.load(open(mp)); bl = ultima(m, 'blend')
            if not bl or not (d / bl['path']).is_file(): continue
            s_ = {}
            if (CUBO / 'objetos_pj' / f'{d.name}.json').is_file():
                try: s_ = json.load(open(CUBO / 'objetos_pj' / f'{d.name}.json'))
                except Exception: s_ = {}
            claves = {base_obj(((m.get('v2_3d') or {}).get('origen') or {}).get('instancia'))} | set(s_.get('ids_canal') or []) | {d.name}
            idx.append({"dir": d, "tipo": t, "meta": m, "blend": bl, "sello": s_, "claves": {c for c in claves if c}})
    return idx

def hueso_de(sello, adn):
    """hueso del portador: el sello manda; si no, lo dice el ADN (anclaje facial / sujeción manual / antebrazo)."""
    if sello.get('hueso'): return sello['hueso'], 'sello.hueso'
    t = str(adn.get('texto') or '')[:1500]
    if re.search(r'facial|nasal|craneal|sobre la cabeza|en la cabeza|ojos|gafas|casco|sombrero|corona', t, re.I): return 'cabeza', 'ADN: se lleva en la cabeza/cara'
    if re.search(r'antebrazo|muñeca|brazalete|manilla', t, re.I) and not re.search(r'una sola mano|empuñadura', t, re.I): return 'antebrazo_L', 'ADN: antebrazo'
    return 'mano_R', 'ADN: sujeción manual (o sin dato: mano)'

def buscar_molde(bib, pid):
    base = bib / 'personajes'
    for d in sorted(base.iterdir()) if base.exists() else []:
        mp = d / 'meta.json'
        if not mp.exists(): continue
        m = json.load(open(mp))
        ficha = ultima(m, 'ficha_esqueleto'); ids = []
        if ficha and (d / ficha['path']).exists():
            try: ids = json.load(open(d / ficha['path'])).get('ids_mapa', [])
            except Exception: ids = []
        if pid in ids or d.name == prefijo_bib(bib) + stem01(pid) or d.name == stem01(pid): return d, m
    return None, None

def _linea_de(D):
    bc = D.get('bloqueo_corte') or {}
    blob = json.dumps(bc, ensure_ascii=False).lower()
    if bc.get('linea_temporal') == 'flashback' or bc.get('tipo') == 'flashback' or 'flashback' in blob:
        return 'flashback', bc.get('escena_flashback') or bc.get('escena_destino')
    return bc.get('linea_temporal') or 'presente', bc.get('escena_flashback')


def aplicar_copia(bib, tipo, pid, escena, src_base, dst, E, *, exigir=False, linea='presente', flash=None):
    """Copia a la corrida el molde que corresponde al estado de ESTA escena. Nunca escribe en el molde base."""
    rec = {'id': pid, 'tipo': tipo, 'aplicar': 'base', 'en_base': True, 'cambio': None,
           'variante_ref': None, 'variante_aprobada': False, 'fallback': None, 'aviso': None,
           'codigo': None, 'faltante_variante': False, 'ocultar': [], 'material': None,
           'bloqueo': False, 'gap': False, 'molde_base': str(src_base), 'origen_usado': str(src_base)}
    hist_dir = HH.pieza_dir(bib, tipo, pid) / 'historial_historia'
    if not hist_dir.exists() and not (HH.pieza_dir(bib, tipo, pid) / 'variantes_historia').exists():
        shutil.copy2(src_base, dst)
        rec['sha256'] = sha(dst)
        return rec
    est = HH.resolver(bib, tipo, pid, escena=escena, linea_temporal=linea, escena_flashback=flash, gap_hereda=True)
    app = HH.aplicar_en_preparar(est, exigir_aprobada=exigir)
    rec.update(aplicar=app['aplicar'], en_base=est.get('en_base'), cambio=est.get('cambio'),
               variante_ref=est.get('variante_ref'), variante_aprobada=est.get('variante_aprobada'),
               fallback=app.get('fallback'), aviso=app.get('aviso'), codigo=app.get('codigo'),
               faltante_variante=bool(app.get('faltante_variante')), ocultar=app.get('ocultar') or [],
               material=app.get('material'), bloqueo=bool(app.get('bloqueo')), gap=bool(est.get('gap')),
               evento_id=est.get('evento_id'), approval_ref=est.get('approval_ref'))
    if app.get('aviso'):
        E.setdefault('avisos', []).append(app['aviso'])
    if app.get('faltante_variante') or app.get('bloqueo'):
        HH.log_decision_fallback(bib, rec, escena=escena)
        E.setdefault('decisiones_historial', []).append({
            'pieza_id': pid, 'escena': escena, 'codigo': rec.get('codigo'),
            'fallback': rec.get('fallback') or ('block' if rec['bloqueo'] else None),
            'para_ricardo': '¿El fallback por variante no aprobada debe ser placeholder (default) o block (STOP)?',
        })
    if app.get('bloqueo'):
        rec['sha256'] = None
        return rec
    src = Path(src_base)
    if app['aplicar'] == 'variante' and (app.get('swap_blend') or est.get('variante_path')):
        cand = None
        if app.get('swap_blend') and est.get('variante_path'):
            cand = Path(est['variante_path']) / app['swap_blend']
        if cand is not None and cand.is_file():
            src = cand
        else:
            rec['codigo'] = rec['codigo'] or 'VARIANTE_SIN_ARCHIVO'
            rec['aviso'] = (rec.get('aviso') or '') + f'; VARIANTE_SIN_ARCHIVO ({cand}); fallback={HH.FALLBACK_VARIANTE}'
            rec['faltante_variante'] = True
            rec['fallback'] = HH.FALLBACK_VARIANTE
            rec['aplicar'] = 'placeholder_base'
            E.setdefault('avisos', []).append(rec['aviso'])
            HH.log_decision_fallback(bib, rec, escena=escena)
    shutil.copy2(src, dst)
    rec['origen_usado'] = str(src)
    rec['sha256'] = sha(dst)
    rec['base_intacto'] = Path(src_base).is_file()
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cadena', required=True, help='carpeta del capítulo en paso00_cadena')
    ap.add_argument('--escena', required=True); ap.add_argument('--biblioteca', required=True)
    ap.add_argument('--corrida', required=True); ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--permitir_faltantes', action='store_true'); ap.add_argument('--permitir_escenario_taller', action='store_true')
    ap.add_argument('--solo_estado_aprobado', action='store_true')
    ap.add_argument('--exigir_variante_aprobada', action='store_true',
                    help='STOP si un cambio de historia necesita una variante aún no aprobada (default: aviso tipado + placeholder, molde base)')
    a = ap.parse_args()
    cad = Path(a.cadena); bib = Path(a.biblioteca); out = Path(a.corrida); (out / 'moldes').mkdir(parents=True, exist_ok=True)
    f01 = cad / 'cubos/01' / f'esc_{a.escena}.json'
    if not f01.exists(): print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "FALTA_01", "ruta": str(f01)})); sys.exit(2)
    D = json.load(open(f01)); ok_est = ('aprobado', 'publicado') if a.solo_estado_aprobado else ESTADOS_OK
    fps = a.fps; N = int(round(float(D['duracion_s']) * fps))
    alturas = {}
    pj = cad / 'cubos/escena/personajes.json'
    for cand in [pj, cad / 'cubos/entradas/personajes.json']:
        if cand.exists():
            try:
                for x in json.load(open(cand)).get('personajes', []): alturas[x.get('id')] = x.get('altura_m') or x.get('altura')
            except Exception: pass
    E = {"contrato": "entrada_motor_v1", "creado": datetime.now().astimezone().isoformat(timespec='seconds'),
         "cadena": str(cad), "escena": str(a.escena), "fps": fps, "fps_01": D.get('fps'), "duracion_s": D['duracion_s'], "N": N,
         "aspecto": D.get('aspecto', [1920, 1080]), "puntos": {k: v[:2] for k, v in D['puntos'].items()},
         "personajes": [], "segmentos_01": {}, "acciones_01": D.get('acciones', []), "hechos": D.get('hechos', []),
         "bloqueo_01": D.get('bloqueo'), "bloqueo_corte": D.get('bloqueo_corte'),
         "faltantes": [], "avisos": [], "escenario": None, "historial": [], "decisiones_historial": []}
    linea, flash = _linea_de(D)
    E['linea_temporal'] = linea
    E['escena_flashback'] = flash
    exigir = bool(a.exigir_variante_aprobada)
    for p in D['personajes']:
        pid = p['id']; E['segmentos_01'][pid] = p.get('segmentos', [])
        d, m = buscar_molde(bib, pid)
        blend = ultima(m, 'blend') if m else None
        if not d or not blend or not (d / blend['path']).exists() or m.get('estado') not in ok_est:
            E['faltantes'].append({"id": pid, "motivo": "MOLDE_FALTANTE" if not blend else f"estado {m.get('estado')}",
                                   "biblioteca": str(d) if d else None, "quien_arregla": "fábrica de personajes"}); continue
        src = d / blend['path']; dst = out / 'moldes' / f"{d.name}.blend"
        hrec = aplicar_copia(bib, 'personajes', d.name, a.escena, src, dst, E, exigir=exigir, linea=linea, flash=flash)
        if hrec.get('bloqueo'):
            E['faltantes'].append({"id": pid, "motivo": "VARIANTE_NO_APROBADA", "variante_ref": hrec.get('variante_ref'),
                                   "quien_arregla": "Ricardo (aprobar variante de historia o confirmar fallback placeholder)"}); continue
        E['historial'].append(hrec)
        ficha = ultima(m, 'ficha_esqueleto'); fj = json.load(open(d / ficha['path'])) if ficha else {}
        v23 = m.get('v2_3d') or {}
        alt = (m.get('altura_v2') or {}).get('altura_adn_m') or v23.get('altura_m_adn') or alturas.get(pid) or fj.get('altura_m')
        E['personajes'].append({"id": pid, "bib": d.name, "blend": f"moldes/{d.name}.blend", "blend_origen": str(src), "sha256": sha(dst),
                                "version": (v23.get('version') or blend['path'].split('/')[1]), "estado_molde": m.get('estado'),
                                "pendiente_aprobacion": m.get('estado') not in ('aprobado', 'publicado'),
                                "altura_m": alt, "plantilla": v23.get('plantilla') or fj.get('plantilla'),
                                "armature": fj.get('armature') or f"ESQ_{d.name}", "huesos": fj.get('huesos_nombres') or list((fj.get('huesos') or {}).keys()) if isinstance(fj.get('huesos'), dict) else fj.get('huesos_nombres', []),
                                "ficha": str(d / ficha['path']) if ficha else None,
                                "historial": {k: hrec.get(k) for k in ('aplicar', 'cambio', 'en_base', 'variante_ref', 'variante_aprobada', 'faltante_variante', 'fallback', 'ocultar', 'material', 'gap', 'codigo')}})
        sj, sjf = sujeto_kimodo(leer_adn(d, d.name), v23.get('plantilla') or fj.get('plantilla')); E['personajes'][-1].update(sujeto_kimodo=sj, sujeto_fuente=sjf)
    if any(x.get('motivo') == 'VARIANTE_NO_APROBADA' for x in E['faltantes']) and exigir and not a.permitir_faltantes:
        json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
        print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "VARIANTE_NO_APROBADA", "faltantes": E['faltantes']}, ensure_ascii=False)); sys.exit(5)
    if E['faltantes'] and not a.permitir_faltantes:
        json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
        print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "MOLDE_FALTANTE", "faltantes": E['faltantes']}, ensure_ascii=False)); sys.exit(3)
    # escenario
    eid = D.get('escenario_id'); de = bib / 'escenarios' / str(eid); me = json.load(open(de / 'meta.json')) if (de / 'meta.json').exists() else {}
    be = ultima(me, 'blend')
    if be and (de / be['path']).exists():
        dst = out / 'moldes' / f"escenario_{eid}.blend"
        hrec = aplicar_copia(bib, 'escenarios', str(eid), a.escena, de / be['path'], dst, E, exigir=exigir, linea=linea, flash=flash)
        if hrec.get('bloqueo'):
            E['faltantes'].append({"id": eid, "motivo": "VARIANTE_NO_APROBADA", "variante_ref": hrec.get('variante_ref'),
                                   "quien_arregla": "Ricardo (aprobar variante de historia o confirmar fallback placeholder)"})
            json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
            print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "VARIANTE_NO_APROBADA", "id": eid}, ensure_ascii=False)); sys.exit(5)
        E['historial'].append(hrec)
        E['escenario'] = {"id": eid, "blend": f"moldes/escenario_{eid}.blend", "origen": hrec.get('origen_usado') or str(de / be['path']),
                          "fuente": "biblioteca (fábrica)", "estado": me.get('estado'), "sha256": hrec.get('sha256') or sha(dst),
                          "historial": {k: hrec.get(k) for k in ('aplicar', 'cambio', 'en_base', 'variante_ref', 'variante_aprobada', 'faltante_variante', 'fallback', 'ocultar', 'material', 'gap', 'codigo')}}
    else:
        taller = cad / 'ramas/moldes' / str(eid) / 'molde.blend'
        if a.permitir_escenario_taller and taller.exists():
            dst = out / 'moldes' / f"escenario_{eid}.blend"; shutil.copy2(taller, dst)
            E['escenario'] = {"id": eid, "blend": f"moldes/escenario_{eid}.blend", "origen": str(taller), "fuente": "molde del taller (gris) — la fábrica aún no publicó el blend",
                              "estado": me.get('estado', 'sin_meta'), "sha256": sha(dst)}
            E['avisos'].append("ESCENARIO_DE_TALLER: la biblioteca no tiene blend del escenario; se usa el molde del taller sin modificarlo")
        else:
            E['faltantes'].append({"id": eid, "motivo": "MOLDE_ESCENARIO_FALTANTE", "quien_arregla": "fábrica de escenarios"})
            json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
            print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "MOLDE_ESCENARIO_FALTANTE"})); sys.exit(4)
    # storyboard + cámara + 2B
    for k, rel in [('storyboard', f'cubos/SB/esc_{a.escena}.json'), ('camara_v2', f'cubos/SB/blender/esc_{a.escena}_camara_v2_altura.json'),
                   ('camara_v1', f'cubos/SB/blender/esc_{a.escena}_camara.json'), ('programa_2b', f'cubos/2B/esc_{a.escena}.json')]:
        f = cad / rel
        if f.exists(): shutil.copy2(f, out / Path(rel).name.replace(f'esc_{a.escena}', k)); E[k] = Path(rel).name.replace(f'esc_{a.escena}', k)
        else: E[k] = None
    import camara_vigente as CVIG
    if E.get('camara_v2'):
        ok_v2, motivo_v2 = CVIG.v2_es_vigente(
            out / E['camara_v2'],
            path_v1=(out / E['camara_v1']) if E.get('camara_v1') else None,
            path_sb=(out / E['storyboard']) if E.get('storyboard') else None,
        )
        if not ok_v2:
            E['avisos'].append(
                f"CAMARA_V2_NO_VIGENTE ({motivo_v2}): se usa la v1 del SB; el archivo v2 no se borra"
            )
            E['camara_v2_omitida'] = E['camara_v2']
            E['camara_v2_omitida_motivo'] = motivo_v2
            E['camara_v2'] = None
    if not E['camara_v2']:
        if not any(str(a).startswith('CAMARA_V2_NO_VIGENTE') for a in (E.get('avisos') or [])):
            E['avisos'].append('SIN_CAMARA_V2_ALTURA: se usa la v1 del SB')
    # objetos y props (Ricardo t1027u): lo que pide la escena, copiado de la biblioteca (nunca se modifica)
    sb = json.load(open(out / E['storyboard'])) if E.get('storyboard') else {}
    pjs = {p['id']: p['bib'] for p in E['personajes']}; bib2pid = {v: k for k, v in pjs.items()}
    idx = indice_objetos(bib); E['objetos'] = []
    for b, info in sorted(objetos_pedidos(D, sb, pjs, idx).items()):
        cand = [x for x in idx if any(b == c or b.startswith(c + '-') or c.startswith(b + '-') for c in x['claves'])]
        cand.sort(key=lambda x: (b not in x['claves'], x['tipo'] != 'objetos_usuario'))
        if not cand:
            E['avisos'].append(f"OBJETO_SIN_MOLDE: {b} (lo pide {sorted(info['fuentes'])}; quien_arregla: fábrica de objetos)"); continue
        x = cand[0]; d = x['dir']; m = x['meta']
        if m.get('estado') not in ok_est + ('falta_receta',):
            E['avisos'].append(f"OBJETO_ESTADO: {b} -> {d.name} estado {m.get('estado')} (no se usa)"); continue
        dst = out / 'moldes' / f"objeto_{d.name}.blend"
        hrec = aplicar_copia(bib, x['tipo'], d.name, a.escena, d / x['blend']['path'], dst, E, exigir=exigir, linea=linea, flash=flash)
        if hrec.get('bloqueo'):
            E['faltantes'].append({"id": d.name, "motivo": "VARIANTE_NO_APROBADA", "variante_ref": hrec.get('variante_ref'),
                                   "quien_arregla": "Ricardo (aprobar variante de historia o confirmar fallback placeholder)"})
            if exigir and not a.permitir_faltantes:
                json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
                print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "VARIANTE_NO_APROBADA", "id": d.name}, ensure_ascii=False)); sys.exit(5)
            continue
        E['historial'].append(hrec)
        if m.get('estado') == 'falta_receta': E['avisos'].append(f"OBJETO_PROVISIONAL: {b} -> {d.name} es una caja provisional (falta_receta en la fábrica); se usa igual para que el prop exista")
        alto = (m.get('v2_3d') or {}).get('alto_m_medido')
        port = bib2pid.get(x['sello'].get('dueno')) or (next((ac for ac in info['actores'] if ac in pjs), None) if (alto is not None and float(alto) <= 0.3) else None)   # sin dueño: solo lo pequeño de mano/cara lo lleva quien actúa con él
        adn = leer_adn(None, d.name); hu, hm = hueso_de(x['sello'], adn)
        E['objetos'].append({"pedido": b, "id": d.name, "tipo": x['tipo'], "blend": f"moldes/{dst.name}", "origen": hrec.get('origen_usado') or str(d / x['blend']['path']),
                             "sha256": hrec.get('sha256') or sha(dst), "estado": m.get('estado'), "fuentes": sorted(info['fuentes']), "portador": port,
                             "hueso": hu if port else None, "hueso_fuente": hm if port else None,
                             "subclase": x['sello'].get('subclase'), "alto_m": ((m.get('v2_3d') or {}).get('alto_m_medido')),
                             "historial": {k: hrec.get(k) for k in ('aplicar', 'cambio', 'en_base', 'variante_ref', 'variante_aprobada', 'faltante_variante', 'fallback', 'ocultar', 'material', 'gap', 'codigo')}})
    # activos con historial vigente que la escena no pidió explícitamente (p. ej. un muro ya dañado del escenario)
    ya = {o['id'] for o in E['objetos']} | {p['bib'] for p in E['personajes']} | {((E.get('escenario') or {}).get('id'))}
    for pieza in HH.piezas_con_historial(bib):
        if pieza['id'] in ya:
            continue
        est = HH.resolver(bib, pieza['tipo'], pieza['id'], escena=a.escena, linea_temporal=linea, escena_flashback=flash, gap_hereda=True)
        if est.get('en_base') and not est.get('gap') and est.get('cambio') in (None, 'reparar'):
            continue
        # cargar el molde (base o variante) para que el daño persista
        idxp = [x for x in idx if x['dir'].name == pieza['id'] and x['tipo'] == pieza['tipo']]
        d = bib / pieza['tipo'] / pieza['id']
        mp = d / 'meta.json'
        if not mp.is_file():
            continue
        m = json.load(open(mp)); bl = ultima(m, 'blend')
        if not bl or not (d / bl['path']).is_file():
            E['avisos'].append(f"HISTORIAL_SIN_MOLDE: {pieza['id']} tiene estado {est.get('cambio')} pero no hay blend")
            continue
        dst = out / 'moldes' / f"{'escenario' if pieza['tipo']=='escenarios' else 'objeto'}_{d.name}.blend"
        if dst.exists():
            continue
        hrec = aplicar_copia(bib, pieza['tipo'], d.name, a.escena, d / bl['path'], dst, E, exigir=exigir, linea=linea, flash=flash)
        if hrec.get('bloqueo') and exigir and not a.permitir_faltantes:
            E['faltantes'].append({"id": d.name, "motivo": "VARIANTE_NO_APROBADA", "variante_ref": hrec.get('variante_ref')})
            json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
            print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "VARIANTE_NO_APROBADA", "id": d.name}, ensure_ascii=False)); sys.exit(5)
        E['historial'].append(hrec)
        if pieza['tipo'] in ('objetos', 'objetos_usuario'):
            E['objetos'].append({"pedido": d.name, "id": d.name, "tipo": pieza['tipo'], "blend": f"moldes/{dst.name}",
                                 "origen": hrec.get('origen_usado') or str(d / bl['path']), "sha256": hrec.get('sha256'),
                                 "estado": m.get('estado'), "fuentes": ["historial"], "portador": None, "hueso": None,
                                 "historial": {k: hrec.get(k) for k in ('aplicar', 'cambio', 'en_base', 'variante_ref', 'variante_aprobada', 'faltante_variante', 'fallback', 'ocultar', 'material', 'gap', 'codigo')}})
    json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
    print('RESULT_PREPARAR', json.dumps({"estado": "OK", "personajes": [p['id'] for p in E['personajes']], "faltantes": E['faltantes'],
                                         "escenario": E['escenario']['fuente'], "N": N,
                                         "objetos": [o['id'] + ('->' + o['portador'] + ':' + o['hueso'] if o['portador'] else '') for o in E.get('objetos', [])],
                                         "historial": [{"id": h.get('id'), "aplicar": h.get('aplicar'), "cambio": h.get('cambio'),
                                                        "variante_ref": h.get('variante_ref'), "faltante": h.get('faltante_variante'),
                                                        "fallback": h.get('fallback'), "gap": h.get('gap')} for h in E.get('historial', []) if not h.get('en_base') or h.get('cambio') or h.get('gap')]},
                                       ensure_ascii=False))

if __name__ == '__main__': main()
