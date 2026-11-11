"""Registro FIJO + cotización + envío único de las fichas de esqueleto (staging 213). No imprime credenciales."""
import sys, json, hashlib, datetime, os, traceback
from pathlib import Path
R = '/opt/myia-staging-arreglos-20261026/repo'
sys.path[:0] = [R, R + '/web']
import myia_argon as A, myia_fijo_prompt as FP
W = Path(__file__).resolve().parent
M, NIVEL, MAXO, TOPE_TOTAL, TOPE_LLAMADA = 'gemini-4-argon', 'HIGH', 65536, 1.33, 0.75
CASOS = {'piquito': 'PROMPT_ARGON_piquito.md', 'perro': 'PROMPT_ARGON_perro.md'}
ESQ = (W / 'ficha_esqueleto_v1.schema.json').read_text(encoding='utf-8')
AUT = ('Ricardo 9-nov-2026 11:46 COT: «Autorizo registrar el prompt y enviar las dos consultas, máximo US$1,32»; '
       '11:54 COT: «Subo el tope a US$1,33, envía las dos tal cual». Grok Bot.')
sha = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()

def texto(c): return (W / CASOS[c]).read_text(encoding='utf-8')
def paso(c): return f'ficha_esqueleto_v1_{c}'
def fijo(c):
    t = texto(c)
    return {'paso': paso(c), 'partes': {'texto': t, 'esquema': ESQ, 'modelo': M, 'nivel': NIVEL, 'max_out': MAXO,
                                         'max_rondas': 1, 'json_out': True}, 'fragmentos': [t]}

def out(d): print(json.dumps(d, ensure_ascii=False))

cmd = sys.argv[1]
if cmd == 'estado':
    out({'guard': FP.encendido(), **FP.estado(), 'ledger': str(A.ledger()), 'cred_ok': bool(A.credencial())})
elif cmd == 'registrar':
    for c in CASOS:
        t = texto(c)
        nota = f'{AUT} texto sha256 {sha(t)}; esquema sha256 {sha(ESQ)}; {M} {NIVEL} max_out {MAXO} max_rondas 1.'
        try:
            f = FP.registrar(paso(c), fijo(c), 'Ricardo', nota=nota); out({'caso': c, 'registrado': f})
        except Exception as e:
            out({'caso': c, 'error': type(e).__name__, 'detalle': str(e)})
elif cmd == 'cotizar':
    r = {c: A.estimar(len(texto(c)), MAXO, modelo=M) for c in CASOS}
    out({'hoy': str(A.hoy()), 'precio': A.precio(M), **r, 'total': round(sum(r.values()), 4)})
elif cmd == 'enviar':
    c = sys.argv[2]
    t = texto(c)
    est = A.estimar(len(t), MAXO, modelo=M)
    otro = [x for x in CASOS if x != c][0]
    tot = round(est + A.estimar(len(texto(otro)), MAXO, modelo=M), 4)
    if tot > TOPE_TOTAL + 1e-9 or est > TOPE_LLAMADA + 1e-9:
        out({'caso': c, 'enviado': False, 'motivo': f'est {est} total {tot} pasa tope'}); sys.exit(2)
    cot = A.cotizacion(est, M)
    id_ = f'esqueleto-{c}-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    sal = W / 'respuestas' / f'{c}.json'
    try:
        FP.comprobar(fijo(c), t, M, NIVEL, MAXO, True, id_=id_, registro=A.ledger().parent / FP.REGISTRO)
        r = A.llamar(id_, t, str(sal), est, f'ficha esqueleto {c} — {AUT}', modelo=M, nivel=NIVEL, max_out=MAXO,
                     json_out=True, fijo=fijo(c), cotizacion=cot, ok_usd=est, tope_usd=TOPE_LLAMADA)
        out({'caso': c, 'enviado': True, 'id': id_, 'est': est, 'usd_real': r['usd'], 'fin': r['fin'],
             'tokens_entrada': r['tokens_entrada'], 'tokens_salida': r['tokens_salida'], 'salida': str(sal)})
    except Exception as e:
        out({'caso': c, 'id': id_, 'error': type(e).__name__, 'detalle': str(e)[:1500]})
