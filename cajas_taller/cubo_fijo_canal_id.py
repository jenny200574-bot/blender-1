#!/usr/bin/env python3
"""cubo_fijo_canal_id — GRATIS, sin red. Genérico para cualquier canal (t528u, Ricardo 2-nov-2026).
Fichas viejas de cubo_fijo cuyo «canal» es un apodo (p. ej. semillas de Ako) y no un id real «cn-…»:
  - agrega «canal_id» con el id real SOLO si el apodo casa con UN único canal de cubo_fijo/canales/*.json
    (por nombre o id, sin tildes). Si casa con 0 o con varios, no toca nada y lo reporta.
  - si la ficha no tiene «nombre», lo deriva del id (guiones → espacios) y lo marca nombre_origen=derivado_del_id.
  - NO cambia «canal» (los flujos que usan el apodo siguen igual), no cambia versión ni sello.
Por defecto solo muestra (seco). --aplicar escribe, con respaldo previo en --respaldo DIR.
Uso: cubo_fijo_canal_id.py [--clases objetos_pj,poderes] [--aplicar --respaldo DIR]"""
import json, re, sys, glob, shutil, unicodedata, argparse, time, os
from pathlib import Path
R = Path('/opt/myia-taller-n8n/cajas/cubo_fijo')
def n(s):
    s = unicodedata.normalize('NFD', str(s or '').lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()
def canales():
    out = []
    for p in sorted((R / 'canales').glob('*.json')):
        d = json.loads(p.read_text(encoding='utf-8')); cid = d.get('canal') or p.stem
        if cid.startswith('cn-'): out.append((cid, f"{n(d.get('nombre'))} {n(cid)}"))
    return out
def resolver(apodo, cs):
    a = n(apodo)
    if not a: return None, 'apodo vacío'
    hits = [cid for cid, txt in cs if re.search(rf'(^| ){re.escape(a)}( |$)', txt)]
    return (hits[0], None) if len(hits) == 1 else (None, f'casa con {len(hits)} canales')
def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument('--clases', default='objetos_pj,poderes'); ap.add_argument('--aplicar', action='store_true'); ap.add_argument('--respaldo')
    a = ap.parse_args(argv); cs = canales(); res = {'ok': True, 'aplicado': a.aplicar, 'cambios': [], 'sin_resolver': []}
    if a.aplicar and not a.respaldo: return {'ok': False, 'error': 'falta --respaldo'}
    for cl in a.clases.split(','):
        for p in sorted((R / cl).glob('*.json')):
            d = json.loads(p.read_text(encoding='utf-8')); c = d.get('canal')
            if not c or str(c).startswith('cn-'): continue
            cid, por_que = resolver(c, cs)
            if d.get('canal_id', '').startswith('cn-'): cid = cid or d['canal_id']
            if not cid: res['sin_resolver'].append({'ficha': f'{cl}/{p.name}', 'canal': c, 'motivo': por_que}); continue
            nuevo = dict(d); cambios = []
            if nuevo.get('canal_id') != cid: nuevo['canal_id'] = cid; cambios.append(f'canal_id={cid}')
            if not nuevo.get('nombre'):
                nuevo['nombre'] = re.sub(r'[_-]+', ' ', d['id']).strip().capitalize(); nuevo['nombre_origen'] = 'derivado_del_id'; cambios.append(f"nombre={nuevo['nombre']}")
            if not cambios: continue
            res['cambios'].append({'ficha': f'{cl}/{p.name}', 'cambios': cambios})
            if a.aplicar:
                dst = Path(a.respaldo) / cl; dst.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dst / p.name)
                tmp = str(p) + '.tmp'; json.dump(nuevo, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, p)
                with open(R / 'historial.jsonl', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'op': 'canal_id', 'ficha': f'{cl}/{p.name}', 'cambios': cambios,
                                        'por': 't528u (Ricardo): fichas viejas con apodo de canal', 'respaldo': str(dst / p.name)}, ensure_ascii=False) + '\n')
    return res
if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False, indent=1))
