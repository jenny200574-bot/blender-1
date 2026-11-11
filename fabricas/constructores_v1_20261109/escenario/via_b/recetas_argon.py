# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · genérico, 10-nov-2026] Vía B + Argon para los objetos FALTA de CUALQUIER escenario
(antes: faltantes.py / armar_recetas.py / procesar_respuestas.py fijos a esc-habitacion). Sin IA aquí: Argon lo llama el
servicio (app/argon_fabrica.py, con ledger y topes).
  preparar: plan_<esc>.json + validacion_star.json → fichas de faltantes (caja en ejes del objeto, apoyo, colores, ADN del
            cubo si existe) en grupos de ≤ N → corpus GRATIS (Wikipedia, recolector) → PROMPT_RECETA_<g>.md (plantilla fija).
  revisar:  respuestas/<g>.json → ancla_tubos → revisor_recetas.py (esquema, caja, apoyo, flotantes, paleta, citas literales)
            → recetas_validas.json (solo APTAS) + REVISION.json.
Uso: python3 recetas_argon.py preparar --datos D --escenario E --salida S [--adn-dir DIR] [--por-grupo N]
     python3 recetas_argon.py revisar --salida S"""
import argparse, json, re, sys, hashlib
from datetime import datetime
from pathlib import Path
B = Path(__file__).resolve().parent
sys.path[:0] = [str(B.parent / 'codigo'), str(B)]
import datos_via_b as DV

_ADN_CACHE = {}
def _canal_de(datos):
    """canal = carpeta de la biblioteca: <bib>/<canal>/escenarios/<id>/datos/vNNN (sin canal fijo en el código)."""
    ps = Path(str(datos)).resolve().parts
    return ps[ps.index('escenarios') - 1] if 'escenarios' in ps and ps.index('escenarios') > 0 else None
def _adn_ids(adn_dir, corto, canal):
    """ADN sellados del canal cuyo id es '<prefijo del canal>-<corto>' (o '<corto>'): el prefijo sale de los datos, no del código."""
    if not adn_dir or not Path(adn_dir).is_dir(): return []
    if adn_dir not in _ADN_CACHE:
        m = {}
        for f in Path(adn_dir).glob('*_ako.json'):
            try: m[f.name[:-9]] = json.loads(f.read_text(encoding='utf-8')).get('canal')
            except Exception: m[f.name[:-9]] = None
        _ADN_CACHE[adn_dir] = m
    m = _ADN_CACHE[adn_dir]
    c = [i for i, cn in m.items() if (i == corto or (i.endswith('-' + corto) and re.fullmatch(r'[a-z0-9]{2,6}-', i[:-len(corto)])))
         and (canal is None or cn in (None, canal))]
    return sorted(c, key=lambda i: (i != corto, i))   # el último gana en _fichas: con prefijo del canal manda (como antes)

def _fichas(datos, esc, adn_dir):
    sys.argv = [sys.argv[0], '--datos', str(datos), '--escenario', esc]
    from ensamblar import dims_locales
    plan = json.loads((Path(datos) / f'plan_{esc}.json').read_text(encoding='utf-8'))
    vf = Path(datos) / 'validacion_star.json'
    sost = {s['id'] for s in json.loads(vf.read_text())['sostenidos_no_dibujados']} if vf.is_file() else set()
    por, excl = {}, {}
    for it in plan['objetos']:
        if it.get('fid'): continue
        k = it.get('oid') or it['id']
        ex, mot = DV.excluye_de_receta(it)
        if ex: excl[k] = mot; continue
        por.setdefault(k, []).append(it)
    fichas = []
    for k, its in por.items():
        it = its[0]; w, d, h = [round(v, 4) for v in dims_locales(it)]
        apoyo = 'en_mano' if all(i['id'] in sost for i in its) else it['apoyo']
        apoyo = DV.norma_apoyo(apoyo)
        f = {'objeto_id': k, 'nombre': it.get('nombre') or k, 'caja_m': {'ancho': w, 'fondo': d, 'alto': h},
             'material_4a1': it.get('material'), 'color_4a1': it.get('color_txt'), 'colores_usados': it.get('colores'),
             'apoyo': apoyo, 'donde': [{'escenas': i.get('escenas'), 'junto_a': i.get('junto_a'), 'pared': i.get('pared')} for i in its],
             'nota': it.get('nota')}
        cand = _adn_ids(adn_dir, re.sub(r'^(obj|amb-[a-z]+-[a-z]+)-', '', k), _canal_de(datos))
        for c in cand:
            p = Path(adn_dir) / f'{c}_ako.json' if adn_dir else None
            if p and p.is_file():
                try: t = json.loads(p.read_text(encoding='utf-8')); f['adn_texto'] = json.dumps(t, ensure_ascii=False)[:6000]
                except Exception: f['adn_texto'] = p.read_text(encoding='utf-8')[:6000]
                f['adn_id'] = c
        fichas.append({x: v for x, v in f.items() if v not in (None, '', [], {})})
    return fichas, excl

def _consultas(f):
    """Consulta GRATIS por objeto: nombre corto (sin prefijos) y, de respaldo, la primera palabra; la fuente debe nombrarla."""
    n = re.sub(r'^(amb-[a-z0-9-]+-|obj-)', '', f['objeto_id']).replace('-', ' ')
    n = re.sub(r'\b(\d+|al|de|del|la|el|derecha|izquierda|interior|familiar|pared|pequen[oa])\b', ' ', n).strip()
    w = n.split()[0] if n.split() else n
    raiz = w[:max(4, len(w) - 2)]
    return [{'fuente': 'wikipedia', 'q': n, 'n': 1, 'idioma': 'es', 'requiere': [raiz]},
            {'fuente': 'wikipedia', 'q': w, 'n': 1, 'idioma': 'es', 'requiere': [raiz]}]

def preparar(a):
    import recolector as R, formas_detalle as FD
    R.MAX_CHARS_FUENTE = 5000; R.MAX_CHARS_CORPUS = 30000
    import time as _t, urllib.error as _ue
    _get0 = R._get
    def _get_cortes(url, timeout=25):   # Wikipedia gratis: ritmo cortés y espera ante su 429 (no es Argon, no cuesta)
        for k in range(4):
            _t.sleep(1.5)
            try: return _get0(url, timeout)
            except _ue.HTTPError as e:
                if e.code != 429 or k == 3: raise
                _t.sleep(15 * (k + 1))
    R._get = _get_cortes
    S = Path(a.salida); (S / 'prompts').mkdir(parents=True, exist_ok=True); (S / 'corpus').mkdir(exist_ok=True); (S / 'respuestas').mkdir(exist_ok=True)
    fichas, excl = _fichas(a.datos, a.escenario, a.adn_dir)
    plantilla = (B / 'esquemas/PLANTILLA_receta_objetos_v1.md').read_text(encoding='utf-8')
    esquema = DV.inyectar_enum_apoyo(json.loads((B / 'esquemas/recetas_objetos_v1.schema.json').read_text(encoding='utf-8')))
    d = FD.__doc__; partes = d[d.index('Partes que puede pedir'):d.index('OPERACIONES (cambios')].strip()
    fija = (plantilla.replace('{{PARTES}}', partes)
                     .replace('{{APOYOS}}', DV.texto_apoyos())
                     .replace('{{ESQUEMA}}', json.dumps(esquema, ensure_ascii=False, separators=(',', ':'))))
    grupos = {}
    lotes = DV.armar_grupos(fichas, por_grupo=a.por_grupo)
    for i, fs in enumerate(lotes):
        g = f'G{i + 1}_{a.escenario}'
        corpus = R.recolectar({'caso': g, 'consultas': [c for f in fs for c in _consultas(f)]})
        txt = (fija.replace('{{GRUPO}}', g).replace('{{OBJETOS}}', json.dumps(fs, ensure_ascii=False, indent=1))
                   .replace('{{FECHA}}', datetime.now().strftime('%Y-%m-%d')).replace('{{CORPUS}}', R_texto(corpus)))
        (S / 'prompts' / f'PROMPT_RECETA_{g}.md').write_text(txt, encoding='utf-8')
        (S / 'prompts' / f'FICHAS_{g}.json').write_text(json.dumps(fs, ensure_ascii=False, indent=1), encoding='utf-8')
        (S / 'corpus' / f'corpus_{g}.json').write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding='utf-8')
        grupos[g] = {'objetos': [f['objeto_id'] for f in fs], 'caracteres': len(txt), 'sha256': hashlib.sha256(txt.encode()).hexdigest(),
                     'fuentes': [(x['id'], x['titulo'], x['url']) for x in corpus['fuentes']]}
    r = {'escenario': a.escenario, 'n_faltantes': len(fichas), 'excluidos': excl, 'grupos': grupos, 'gasto_usd': 0}
    (S / 'grupos.json').write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'faltantes': len(fichas), 'grupos': {g: (v['caracteres'], len(v['objetos'])) for g, v in grupos.items()}}, ensure_ascii=False))

def R_texto(corpus):
    return '\n\n'.join(f'### {f["id"]} | {f["titulo"]} | {f["url"]} | {f["licencia"]}\n{f["texto"]}' for f in corpus['fuentes']) or '(sin fuentes: usa solo la ficha y deducciones explícitas)'

def revisar(a):
    import revisor_recetas as RV, ancla_tubos as AT
    S = Path(a.salida); G = json.loads((S / 'grupos.json').read_text(encoding='utf-8'))
    prev = S / 'recetas_validas.json'
    validas = json.loads(prev.read_text(encoding='utf-8')) if prev.is_file() else {}
    inf = {}
    for g in G['grupos']:
        f = S / 'respuestas' / f'{g}.json'
        if not f.is_file(): inf[g] = {'estado': 'sin respuesta'}; continue
        fichas = json.loads((S / 'prompts' / f'FICHAS_{g}.json').read_text(encoding='utf-8'))
        corpus = json.loads((S / 'corpus' / f'corpus_{g}.json').read_text(encoding='utf-8'))
        t = f.read_text(encoding='utf-8').strip()
        resp, aviso = DV.cargar_respuesta(t)
        if resp is None: inf[g] = {'estado': 'JSON roto', 'error': (aviso or '')[:200]}; continue
        resp, anclas = AT.aplicar(resp)
        fx = {x['objeto_id']: x for x in fichas}; por = {}
        for r in resp.get('recetas', []) if isinstance(resp, dict) else []:
            oid = r.get('objeto_id') if isinstance(r, dict) else None
            if oid not in fx: por[str(oid)] = {'apta': False, 'errores': ['objeto no pedido']}; continue
            e1 = RV.esquema(r, RV.ESQUEMA['properties']['recetas']['items'], f'$.{oid}')
            e2, a2, _ = RV.revisar_receta(r, fx[oid], corpus) if not e1 else ([], [], None)
            por[oid] = {'apta': not (e1 or e2), 'errores': (e1 + e2)[:20], 'avisos': a2[:10]}
            if not (e1 or e2): validas[oid] = r
        inf[g] = {'aptas': [k for k, v in por.items() if v['apta']], 'rechazadas': {k: v['errores'][:6] for k, v in por.items() if not v['apta']}, 'anclas': list(anclas)}
        if aviso: inf[g]['aviso'] = aviso
        if resp.get('_salvadas_de_truncada'): inf[g]['salvadas_de_truncada'] = [r.get('objeto_id') for r in resp.get('recetas') or []]
    prev.write_text(json.dumps(validas, ensure_ascii=False, indent=1), encoding='utf-8')
    (S / 'REVISION.json').write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'validas': len(validas), 'por_grupo': {g: len(v.get('aptas', [])) for g, v in inf.items()}}, ensure_ascii=False))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('modo', choices=['preparar', 'revisar']); ap.add_argument('--datos'); ap.add_argument('--escenario')
    ap.add_argument('--salida', required=True); ap.add_argument('--adn-dir'); ap.add_argument('--por-grupo', type=int, default=None, help='tope de objetos por grupo; si no se pasa, sale de esquemas/grupos_recetas.json')
    a = ap.parse_args(); preparar(a) if a.modo == 'preparar' else revisar(a)
