# -*- coding: utf-8 -*-
"""Validación SIN IA de una investigación de Argon (investigacion/v1) contra su CORPUS.
- cada dato origen=fuente: fuente_id existe en el corpus y la cita (8–300 caracteres) está LITERAL en su texto
  (comparación sin mayúsculas ni espacios repetidos);
- origen=hoja: campo_hoja existe en el ADN; origen=deduccion: deriva_de apunta a claves existentes;
- URLs: todas las del corpus responden (HEAD/GET 2xx/3xx) — opcional (--red);
- porcentaje de datos con fuente; personaje: catálogo ≥60 movimientos con nombres únicos.
Sale con código 0 si APTA, 1 si RECHAZADA."""
from __future__ import annotations
import json, re, sys, unicodedata, urllib.error, urllib.request

def _n(s):
    s = unicodedata.normalize('NFKC', s or '').lower()
    return re.sub(r'\s+', ' ', s).strip()

class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def url_viva(u, timeout=20):
    """2xx/3xx = viva. Para https://doi.org/… basta que doi.org redirija (el DOI existe): muchas editoriales
    responden 403 a programas aunque la página exista."""
    if u.startswith('https://doi.org/'):
        try:
            op = urllib.request.build_opener(_SinRedireccion)
            op.open(urllib.request.Request(u, method='HEAD', headers={'User-Agent': 'MYIA-Fabricas/0.1 verificador'}), timeout=timeout)
            return True
        except urllib.error.HTTPError as e:
            return 300 <= e.code < 400
        except Exception:
            return False
    try:
        req = urllib.request.Request(u, method='GET', headers={'User-Agent': 'MYIA-Fabricas/0.1 verificador'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False

def verificar(inv, corpus, adn=None, red=False, min_movimientos=60):
    err, avisos = [], []
    fx = {f['id']: _n(f['texto']) for f in corpus.get('fuentes', [])}
    claves =[REDACTED]
    n_f = 0
    for d in inv.get('datos', []):
        k, o = d.get('clave'), d.get('origen')
        if o == 'fuente':
            fid, cita = d.get('fuente_id'), d.get('cita') or ''
            if fid not in fx:
                err.append(f'E_FUENTE {k}: fuente_id {fid!r} no está en el corpus'); continue
            if not (8 <= len(cita) <= 300):
                err.append(f'E_CITA_LARGO {k}: cita de {len(cita)} caracteres'); continue
            if _n(cita) not in fx[fid]:
                err.append(f'E_CITA {k}: la cita no está literal en {fid}: {cita[:80]!r}'); continue
            n_f += 1
        elif o == 'hoja':
            if adn is not None and d.get('campo_hoja') not in adn:
                err.append(f'E_HOJA {k}: campo {d.get("campo_hoja")!r} no está en el ADN')
        elif o == 'deduccion':
            falt = [x for x in d.get('deriva_de') or [] if x not in claves]
            if not d.get('deriva_de') or falt:
                err.append(f'E_DEDUCCION {k}: deriva_de vacío o con claves inexistentes {falt}')
        else:
            err.append(f'E_ORIGEN {k}: origen {o!r}')
    tot = len(inv.get('datos', []))
    if tot and n_f / tot < 0.3:
        avisos.append(f'A_POCAS_FUENTES: solo {n_f}/{tot} datos con cita de fuente')
    if inv.get('tipo') == 'personaje':
        cat = (inv.get('payload') or {}).get('catalogo_movimientos') or []
        nombres = [m.get('nombre') for m in cat]
        if len(cat) < min_movimientos:
            err.append(f'E_MOVIMIENTOS: {len(cat)} < {min_movimientos}')
        if len(set(nombres)) != len(nombres):
            err.append('E_MOVIMIENTOS_REPETIDOS')
    if red:
        for f in corpus.get('fuentes', []):
            if not url_viva(f['url']):
                err.append(f'E_URL {f["id"]}: no responde {f["url"]}')
    return {'apta': not err, 'errores': err, 'avisos': avisos, 'datos': tot, 'con_fuente': n_f}

if __name__ == '__main__':
    inv = json.load(open(sys.argv[1], encoding='utf-8')); corpus = json.load(open(sys.argv[2], encoding='utf-8'))
    adn = json.load(open(sys.argv[3], encoding='utf-8')) if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    r = verificar(inv, corpus, adn, red='--red' in sys.argv)
    print(json.dumps(r, ensure_ascii=False, indent=1)); sys.exit(0 if r['apta'] else 1)
