"""Compara dos salidas de correr_etapa11_sintetica.py (por ejemplo instalada contra parchada).

  python3 comparar_salidas.py SALIDA_A SALIDA_B

Exige igualdad exacta de auditoria_4g/camara_v2.json (salvo 'interruptores', que
nombra la bandera nueva) y de todas las claves horneadas de la cámara. Código 0 si son iguales.
"""
import json
import sys
from pathlib import Path


def cargar(salida):
    salida = Path(salida)
    rep = json.loads((salida / 'auditoria_4g' / 'camara_v2.json').read_text(encoding='utf-8'))
    rep.pop('interruptores', None)
    claves = json.loads((salida / 'camara_claves.json').read_text(encoding='utf-8'))
    return rep, claves


def diferencias(a, b, ruta='', out=None, tope=20):
    out = [] if out is None else out
    if len(out) >= tope:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(ruta + '/' + str(k) + ' solo en ' + ('B' if k not in a else 'A'))
            else:
                diferencias(a[k], b[k], ruta + '/' + str(k), out, tope)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(ruta + ' largo %d != %d' % (len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diferencias(x, y, ruta + '[%d]' % i, out, tope)
    elif a != b:
        out.append(ruta + ': %r != %r' % (a, b))
    return out


def main(argv):
    ra, ca = cargar(argv[0])
    rb, cb = cargar(argv[1])
    dif = diferencias(ra, rb, 'camara_v2') + diferencias(ca, cb, 'claves')
    print(json.dumps({'iguales': not dif, 'claves_camara': len(ca), 'puntos': sum(len(v) for v in ca.values()), 'diferencias': dif}, ensure_ascii=False))
    return 0 if not dif else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
