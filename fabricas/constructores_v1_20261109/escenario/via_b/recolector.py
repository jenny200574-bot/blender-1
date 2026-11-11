# -*- coding: utf-8 -*-
"""Recolector de fuentes ABIERTAS (sin IA, sin costo) para la investigación de Argon.

Busca y descarga textos de fuentes con API pública y licencia que permite guardar:
  - Wikipedia (en/es) — Action API, texto plano (CC BY-SA 4.0).
  - Europe PMC — resúmenes de artículos científicos (anatomía, biomecánica, veterinaria).
Cada fuente queda en el CORPUS con id estable (F01, F02…), url, título, licencia, fecha de descarga (Bogotá),
sha256 del texto y el texto recortado. Argon recibe el corpus como parte VARIABLE del prompt y debe citar
`fuente_id` + `cita` literal; verificador_citas.py comprueba que la cita está en el texto guardado.
No usa Grounding con Google Search (ver DISENO_ARGON_INTERNET.md §1.4: términos de almacenamiento)."""
from __future__ import annotations
import datetime, hashlib, json, re, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

UA = 'MYIA-Fabricas/0.1 (investigacion anatomica; contacto: operador MYIA) python-urllib'
MAX_CHARS_FUENTE = 12000      # recorte por fuente (controla el costo de entrada)
MAX_CHARS_CORPUS = 90000      # tope del corpus (~30K tokens a 3 caracteres/token)
BOG = ZoneInfo('America/Bogota')


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def wikipedia(consulta, idioma='en', n=2):
    base = f'https://{idioma}.wikipedia.org/w/api.php'
    q = urllib.parse.urlencode({'action': 'query', 'list': 'search', 'srsearch': consulta, 'srlimit': n,
                                'format': 'json', 'formatversion': 2})
    out = []
    for hit in _get(f'{base}?{q}').get('query', {}).get('search', []):
        t = hit['title']
        q2 = urllib.parse.urlencode({'action': 'query', 'prop': 'extracts|info', 'explaintext': 1, 'inprop': 'url',
                                     'titles': t, 'format': 'json', 'formatversion': 2, 'redirects': 1})
        p = _get(f'{base}?{q2}')['query']['pages'][0]
        txt = p.get('extract') or ''
        if txt.strip():
            out.append({'origen': f'wikipedia-{idioma}', 'titulo': p['title'], 'url': p.get('fullurl'),
                        'licencia': 'CC BY-SA 4.0 (Wikipedia)', 'texto': txt})
        time.sleep(0.5)
    return out


def europepmc(consulta, n=3):
    q = urllib.parse.urlencode({'query': f'({consulta}) AND HAS_ABSTRACT:y', 'format': 'json', 'pageSize': n,
                                'resultType': 'core'})
    out = []
    for r in _get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?{q}').get('resultList', {}).get('result', []):
        import html as _h
        abs_ = re.sub(r'<[^>]+>', ' ', _h.unescape(r.get('abstractText') or '')).strip()
        if not abs_:
            continue
        doi = r.get('doi')
        url = f'https://doi.org/{doi}' if doi else f'https://europepmc.org/article/{r.get("source")}/{r.get("id")}'
        out.append({'origen': 'europepmc', 'titulo': re.sub(r'<[^>]+>', '', __import__('html').unescape(r.get('title') or '')), 'url': url,
                    'licencia': r.get('license') or 'resumen (derechos del editor; se guarda solo para citar)',
                    'referencia': f'{r.get("authorString","")} {r.get("pubYear","")}. {r.get("journalInfo",{}).get("journal",{}).get("title","")}',
                    'texto': abs_})
    return out


def recolectar(plan):
    """plan = {'caso': str, 'consultas': [{'fuente': 'wikipedia'|'europepmc', 'q': str, 'idioma'?: 'en'|'es', 'n'?: int}]}"""
    fuentes, vistos, total, descartes = [], set(), 0, []
    for c in plan['consultas']:
        try:
            res = wikipedia(c['q'], c.get('idioma', 'en'), c.get('n', 2)) if c['fuente'] == 'wikipedia' else europepmc(c['q'], c.get('n', 3))
        except Exception as e:
            fuentes.append({'error': f'{c["fuente"]}: {type(e).__name__}: {e}', 'consulta': c['q']}); continue
        debe = [w.lower() for w in c.get('debe', [])]
        for r in res:
            if r['url'] in vistos:
                continue
            blob = (r['titulo'] + ' ' + r['texto'][:4000]).lower()
            req = [w.lower() for w in c.get('requiere', [])]
            if (req and not any(w in blob for w in req)) or (debe and sum(w in blob for w in debe) < c.get('min_debe', 2)):
                descartes.append({'consulta': c['q'], 'titulo': r['titulo'], 'url': r['url'], 'motivo': 'no pasa filtro de relevancia'})
                continue
            vistos.add(r['url'])
            t = r['texto'][:MAX_CHARS_FUENTE]
            if total + len(t) > MAX_CHARS_CORPUS:
                t = t[:max(0, MAX_CHARS_CORPUS - total)]
            if not t:
                break
            total += len(t)
            r.update(texto=t, consulta=c['q'], sha256=hashlib.sha256(t.encode()).hexdigest(),
                     descargado=datetime.datetime.now(BOG).isoformat(timespec='seconds'))
            fuentes.append(r)
    ok = [f for f in fuentes if 'error' not in f]
    for i, f in enumerate(ok, 1):
        f['id'] = f'F{i:02d}'
    return {'schema': 'corpus_investigacion/v1', 'caso': plan['caso'], 'creado': datetime.datetime.now(BOG).isoformat(timespec='seconds'),
            'caracteres': total, 'fuentes': ok, 'descartes': descartes, 'errores': [f for f in fuentes if 'error' in f]}


def corpus_a_texto(corpus):
    """Bloque VARIABLE que va dentro del prompt (fuente exacta: el archivo del corpus con su sha256)."""
    partes = []
    for f in corpus['fuentes']:
        partes.append(f'### {f["id"]} | {f["titulo"]} | {f["url"]} | {f["licencia"]}\n{f["texto"]}')
    return '\n\n'.join(partes)


if __name__ == '__main__':
    plan = json.load(open(sys.argv[1], encoding='utf-8'))
    c = recolectar(plan)
    json.dump(c, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'fuentes': [(f['id'], f['origen'], f['titulo'], len(f['texto'])) for f in c['fuentes']],
                      'caracteres': c['caracteres'], 'descartes': len(c['descartes']), 'errores': c['errores']}, ensure_ascii=False, indent=1))
