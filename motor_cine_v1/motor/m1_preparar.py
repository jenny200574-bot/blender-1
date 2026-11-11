"""m1_preparar — motor unificado v1 [10-nov-2026]. Corre en 213 (python3, sin Blender).
Junta TODO lo que el motor necesita para una escena, sin crear nada:
  - 01 de la escena (cubos/01/esc_N.json), storyboard (cubos/SB/esc_N.json) y cámara v2 con altura_m (cubos/SB/blender/esc_N_camara_v2_altura.json)
  - moldes de personaje publicados en la biblioteca (/opt/myia-biblioteca/<canal>/personajes/<id>/meta.json -> última versión 'blend')
  - molde de escenario publicado (biblioteca escenarios/<id>); si la fábrica aún no lo publicó, se usa el molde del taller
    (ramas/moldes/<id>/molde.blend) SOLO si --permitir_escenario_taller, y se marca en el reporte.
  - programa 2B de Argon si existe (cubos/2B/esc_N.json) — opcional.
Si falta un molde de personaje: STOP «MOLDE_FALTANTE» (o, con --permitir_faltantes, se reporta y ese personaje no sale).
Nunca modifica moldes: los copia (sha256 verificado) a la carpeta de la corrida."""
import json, argparse, shutil, hashlib, sys, re
from pathlib import Path
from datetime import datetime

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

def objetos_pedidos(D, sb, pjs):
    """objetos que pide la escena: 01 (acciones[].objeto) + storyboard (director_imagen.objetos) + props portados de los personajes."""
    ped = {}
    for a in D.get('acciones', []):
        b = base_obj(a.get('objeto')); b = b if re.match(r'^obj-[a-z0-9-]+$', b) else ''
        if b: ped.setdefault(b, {"fuentes": set(), "actores": []})["fuentes"].add('01')
        if b and a.get('actor') and a['actor'] not in ped[b]['actores']: ped[b]['actores'].append(a['actor'])
    for v in (sb or {}).get('vinetas', []):
        for o in ((v.get('director_imagen') or {}).get('objetos') or []):
            b = base_obj(o.get('nombre') if isinstance(o, dict) else o)
            if b and re.match(r'^obj-[a-z0-9-]+$', b):   # solo ids; los nombres libres del SB los resuelve el escenario
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
            claves =[REDACTED]
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cadena', required=True, help='carpeta del capítulo en paso00_cadena')
    ap.add_argument('--escena', required=True); ap.add_argument('--biblioteca', required=True)
    ap.add_argument('--corrida', required=True); ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--permitir_faltantes', action='store_true'); ap.add_argument('--permitir_escenario_taller', action='store_true')
    ap.add_argument('--solo_estado_aprobado', action='store_true')
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
         "faltantes": [], "avisos": [], "escenario": None}
    for p in D['personajes']:
        pid = p['id']; E['segmentos_01'][pid] = p.get('segmentos', [])
        d, m = buscar_molde(bib, pid)
        blend = ultima(m, 'blend') if m else None
        if not d or not blend or not (d / blend['path']).exists() or m.get('estado') not in ok_est:
            E['faltantes'].append({"id": pid, "motivo": "MOLDE_FALTANTE" if not blend else f"estado {m.get('estado')}",
                                   "biblioteca": str(d) if d else None, "quien_arregla": "fábrica de personajes"}); continue
        src = d / blend['path']; dst = out / 'moldes' / f"{d.name}.blend"; shutil.copy2(src, dst)
        ficha = ultima(m, 'ficha_esqueleto'); fj = json.load(open(d / ficha['path'])) if ficha else {}
        v23 = m.get('v2_3d') or {}
        alt = (m.get('altura_v2') or {}).get('altura_adn_m') or v23.get('altura_m_adn') or alturas.get(pid) or fj.get('altura_m')
        E['personajes'].append({"id": pid, "bib": d.name, "blend": f"moldes/{d.name}.blend", "blend_origen": str(src), "sha256": sha(dst),
                                "version": (v23.get('version') or blend['path'].split('/')[1]), "estado_molde": m.get('estado'),
                                "pendiente_aprobacion": m.get('estado') not in ('aprobado', 'publicado'),
                                "altura_m": alt, "plantilla": v23.get('plantilla') or fj.get('plantilla'),
                                "armature": fj.get('armature') or f"ESQ_{d.name}", "huesos": fj.get('huesos_nombres') or list((fj.get('huesos') or {}).keys()) if isinstance(fj.get('huesos'), dict) else fj.get('huesos_nombres', []),
                                "ficha": str(d / ficha['path']) if ficha else None})
        sj, sjf = sujeto_kimodo(leer_adn(d, d.name), v23.get('plantilla') or fj.get('plantilla')); E['personajes'][-1].update(sujeto_kimodo=sj, sujeto_fuente=sjf)
    if E['faltantes'] and not a.permitir_faltantes:
        json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
        print('RESULT_PREPARAR', json.dumps({"estado": "STOP", "motivo": "MOLDE_FALTANTE", "faltantes": E['faltantes']}, ensure_ascii=False)); sys.exit(3)
    # escenario
    eid = D.get('escenario_id'); de = bib / 'escenarios' / str(eid); me = json.load(open(de / 'meta.json')) if (de / 'meta.json').exists() else {}
    be = ultima(me, 'blend')
    if be and (de / be['path']).exists():
        dst = out / 'moldes' / f"escenario_{eid}.blend"; shutil.copy2(de / be['path'], dst)
        E['escenario'] = {"id": eid, "blend": f"moldes/escenario_{eid}.blend", "origen": str(de / be['path']), "fuente": "biblioteca (fábrica)", "estado": me.get('estado'), "sha256": sha(dst)}
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
    if not E['camara_v2']: E['avisos'].append('SIN_CAMARA_V2_ALTURA: se usa la v1 del SB')
    # objetos y props (Ricardo t1027u): lo que pide la escena, copiado de la biblioteca (nunca se modifica)
    sb = json.load(open(out / E['storyboard'])) if E.get('storyboard') else {}
    pjs = {p['id']: p['bib'] for p in E['personajes']}; bib2pid = {v: k for k, v in pjs.items()}
    idx = indice_objetos(bib); E['objetos'] = []
    for b, info in sorted(objetos_pedidos(D, sb, pjs).items()):
        cand = [x for x in idx if any(b == c or b.startswith(c + '-') or c.startswith(b + '-') for c in x['claves'])]
        cand.sort(key=lambda x: (b not in x['claves'], x['tipo'] != 'objetos_usuario'))
        if not cand:
            E['avisos'].append(f"OBJETO_SIN_MOLDE: {b} (lo pide {sorted(info['fuentes'])}; quien_arregla: fábrica de objetos)"); continue
        x = cand[0]; d = x['dir']; m = x['meta']
        if m.get('estado') not in ok_est + ('falta_receta',):
            E['avisos'].append(f"OBJETO_ESTADO: {b} -> {d.name} estado {m.get('estado')} (no se usa)"); continue
        dst = out / 'moldes' / f"objeto_{d.name}.blend"; shutil.copy2(d / x['blend']['path'], dst)
        if m.get('estado') == 'falta_receta': E['avisos'].append(f"OBJETO_PROVISIONAL: {b} -> {d.name} es una caja provisional (falta_receta en la fábrica); se usa igual para que el prop exista")
        alto = (m.get('v2_3d') or {}).get('alto_m_medido')
        port = bib2pid.get(x['sello'].get('dueno')) or (next((a for a in info['actores'] if a in pjs), None) if (alto is not None and float(alto) <= 0.3) else None)   # sin dueño: solo lo pequeño de mano/cara lo lleva quien actúa con él
        adn = leer_adn(None, d.name); hu, hm = hueso_de(x['sello'], adn)
        E['objetos'].append({"pedido": b, "id": d.name, "tipo": x['tipo'], "blend": f"moldes/{dst.name}", "origen": str(d / x['blend']['path']),
                             "sha256": sha(dst), "estado": m.get('estado'), "fuentes": sorted(info['fuentes']), "portador": port,
                             "hueso": hu if port else None, "hueso_fuente": hm if port else None,
                             "subclase": x['sello'].get('subclase'), "alto_m": ((m.get('v2_3d') or {}).get('alto_m_medido'))})
    json.dump(E, open(out / 'entrada_motor.json', 'w'), indent=1, ensure_ascii=False)
    print('RESULT_PREPARAR', json.dumps({"estado": "OK", "personajes": [p['id'] for p in E['personajes']], "faltantes": E['faltantes'],
                                         "escenario": E['escenario']['fuente'], "N": N,
                                         "objetos": [o['id'] + ('->' + o['portador'] + ':' + o['hueso'] if o['portador'] else '') for o in E.get('objetos', [])]}, ensure_ascii=False))

if __name__ == '__main__': main()
