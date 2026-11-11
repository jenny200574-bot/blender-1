#!/usr/bin/env python3
"""paso00_objetos_faltantes — revisión GRATIS y de solo lectura (sin red, sin Argon).
Compara, para un capítulo ya corrido en el paso 00, lo que el canal YA tiene o declaró
(cubo_fijo/objetos_pj + poderes del canal, material_cliente objeto_portado/acompanante,
overrides) y lo que el guion usa (objetos que se levantan, disparan, guardan, sacan...)
contra los objetos que Argon dejó en base.json (catalogo_oficial) y objetos.json.
Uso: paso00_cadena ver objetos --canal <canal_id> --capitulo <N|ep-…>
Genérico: no conoce ningún canal ni objeto."""
import json, re, sys, glob, sqlite3, unicodedata
from pathlib import Path
CUBO = Path('/opt/myia-taller-n8n/cajas/cubo_fijo')
TRAB = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
DB = '/opt/myia-staging-arreglos-20261026/demo_chat/estudio/web/data/studio.db'
VERBOS = (r'levanta|levantan|saca|sacan|guarda|guardan|dispara|disparan|lanza|lanzan|sostiene|sostienen|toma|toman|agarra|agarran|'
          r'apunta|apuntan|empuña|blande|blanden|usa|usan|activa|activan|enciende|encienden|abre|abren|muestra|muestran|carga|cargan|'
          r'tiene|tienen|lleva|llevan|mira|baja|bajan|suelta|sueltan|recoge|recogen|entrega|entregan|rompe|rompen')
DET = r'(?:su|sus|el|la|los|las|un|una|unos|unas|del|al)'
NOSON = set(('mano manos dedo dedos dedito cabeza ojos boca brazo brazos pie pies cara voz mirada vuelta paso pausa momento turno hora '
              'aire pantalla escena puerta video puntito').split())   # partes del cuerpo y palabras que no son objetos
def n(s):
    s = unicodedata.normalize('NFD', str(s or '').lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]+', ' ', s)
def toks(s): return {t for t in n(s).split() if len(t) > 3 and t not in {'para', 'como', 'esta', 'este', 'nuevo', 'canal', 'objeto'}}
def guion(canal, ep, D):
    f = D / 'pedidos' / 'base.txt'
    if f.is_file():
        t = f.read_text(encoding='utf-8'); m = re.search(r'=== GUION_COMPLETO ===\n(.*)\n=== FIN GUION ===', t, re.S)
        if m: return m.group(1), str(f)
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    r = c.execute('SELECT guion FROM myia_capitulo_guion WHERE episode_id=? AND channel_id=? ORDER BY canonico DESC, updated_at DESC LIMIT 1', (ep, canal)).fetchone()
    return (r[0], 'studio.db myia_capitulo_guion') if r and r[0] else ('', 'sin guion')
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='ver objetos'); ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True)
    a = ap.parse_args(argv); canal = a.canal
    if not re.fullmatch(r'cn-[a-z0-9-]+', canal) or not re.fullmatch(r'(ep-[a-z0-9]+|\d{1,3})', a.capitulo): return {'ok': False, 'error': 'canal o capítulo no válido'}
    patron = f'cap*_{a.capitulo}' if a.capitulo.startswith('ep-') else f'cap{int(a.capitulo):02d}_ep-*'
    D = next(iter(sorted((TRAB / canal).glob(patron))), None)
    if not D or not (D / 'respuestas' / 'base.json').is_file(): return {'ok': False, 'error': 'ese capítulo no tiene BASE (caja 4) corrida'}
    ep = D.name.split('_', 1)[1]
    base = json.loads((D / 'respuestas' / 'base.json').read_text())
    objs = json.loads((D / 'respuestas' / 'objetos.json').read_text()) if (D / 'respuestas' / 'objetos.json').is_file() else {}
    cat = base.get('catalogo_oficial', {}).get('objetos', [])
    pers = [p.get('nombre', '') for p in base.get('catalogo_oficial', {}).get('personajes', [])]
    texto_argon = n(json.dumps(cat, ensure_ascii=False) + json.dumps(objs.get('objetos', []), ensure_ascii=False))
    tok_argon = set(texto_argon.split())
    g, gsrc = guion(canal, ep, D)
    out = {'ok': True, 'canal': canal, 'capitulo': ep, 'guion_de': gsrc, 'objetos_argon': len(cat), 'faltan_del_canal': [], 'faltan_del_guion': [], 'notas': []}
    # 1) lo que el canal ya tiene (cubo fijo) o declaró (material_cliente)
    fijos = []
    for k in ('objetos_pj', 'poderes'):
        for p in sorted(glob.glob(str(CUBO / k / '*.json'))):
            d = json.load(open(p))
            if canal in (d.get('canal'), d.get('canal_id')): fijos.append({'fuente': f'cubo_fijo/{k}/{Path(p).name}', 'nombre': d.get('nombre') or d.get('id'), 'clase': d.get('clase') or k, 'portador': d.get('portador') or d.get('dueno')})
            elif d.get('canal') and not str(d.get('canal')).startswith('cn-') and not str(d.get('canal_id') or '').startswith('cn-'):
                out['notas'].append(f"cubo_fijo/{k}/{Path(p).name}: canal «{d.get('canal')}» no es un id de canal (cn-…); no se casa con ningún canal")
    try:
        c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
        cd = json.loads(c.execute('SELECT data FROM channels WHERE id=?', (canal,)).fetchone()[0] or '{}')
        for x in ((cd.get('material_cliente') or {}).get('separacion_tipos') or []):
            if x.get('tipo') in ('objeto_portado', 'objeto') and x.get('nombre'):
                fijos.append({'fuente': 'channels.data.material_cliente', 'nombre': x['nombre'], 'clase': x['tipo'], 'portador': x.get('portador')})
    except Exception as e: out['notas'].append(f'material_cliente no leído: {e}')
    for f in fijos:
        t = toks(f['nombre']); cab = next(iter([w for w in n(f['nombre']).split() if w in t]), ''); en_g = sorted(w for w in t if w in set(n(g).split()))
        hit = sorted(t & tok_argon)
        if not hit:
            out['faltan_del_canal'].append(dict(f, palabras_en_guion=en_g, nota='ni el nombre ni sus palabras salen en los objetos de Argon'))
        elif cab and cab not in tok_argon:
            out['faltan_del_canal'].append(dict(f, palabras_en_guion=en_g, coincide_solo=hit, sustantivo=cab, nota='su sustantivo principal no sale: quedó fundido con otro objeto o renombrado'))
    # 2) lo que el guion usa con un verbo de manipulación y no salió
    vistos = set()
    for m in re.finditer(rf'\b(?:{VERBOS})\s+{DET}\s+((?:[A-ZÁÉÍÓÚÑ]?[a-záéíóúñü]+)(?:\s+(?:de|del)\s+[A-ZÁÉÍÓÚÑ]?[a-záéíóúñü]+|\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+)?)', g):
        fr = m.group(1); k = n(fr).strip(); cab = k.split()[0] if k else ''
        if not cab or cab in NOSON or k in vistos or any(n(p).strip() == k for p in pers) or len(cab) < 4: continue
        vistos.add(k)
        if not (toks(fr) & tok_argon):
            ini = max(0, m.start() - 40); out['faltan_del_guion'].append({'palabra': fr, 'frase': g[ini:m.end() + 20].replace('\n', ' ')})
    out['resumen'] = f"{len(out['faltan_del_canal'])} del canal y {len(out['faltan_del_guion'])} del guion para revisar (no se agrega nada a mano)"
    return out
if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False, indent=1))
