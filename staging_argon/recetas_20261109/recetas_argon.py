"""Registro FIJO + tope de catálogo + recotización + envío único: 4 recetas (receta_objetos_faltantes_v1) y Piquito
(investigacion_personaje_v1_corpus). Staging 213. No imprime credenciales. Sin reintentos."""
import sys, json, hashlib, datetime, shutil, traceback
from pathlib import Path
R = '/opt/myia-staging-arreglos-20261026/repo'
sys.path[:0] = [R, R + '/web']
import myia_argon as A, myia_fijo_prompt as FP, precios_myia as PR
W = Path(__file__).resolve().parent
M, NIVEL, MAXO, TOPE_TOTAL = 'gemini-4-argon', 'HIGH', 65536, 3.43
CASOS = json.loads((W / 'casos.json').read_text(encoding='utf-8'))
AUT = ('Ricardo 9-nov-2026 13:09 COT: «Registra los prompts y lanza las 4 recetas y Piquito con salida completa 65.536, '
       'máximo US$3,43». Grok Bot.')
sha = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()
def out(d): print(json.dumps(d, ensure_ascii=False), flush=True)
def texto(c): return (W / CASOS[c]['archivo']).read_text(encoding='utf-8')
def fijo(c): return json.loads((W / CASOS[c]['fijo']).read_text(encoding='utf-8'))
def est(c): return A.estimar(len(texto(c)), MAXO, modelo=M)
TOPES = {'receta_objetos_faltantes_v1': max(v['cotizado'] for k, v in CASOS.items() if k.startswith('G')),
         'investigacion_personaje_v1_corpus': CASOS['piquito']['cotizado']}

cmd = sys.argv[1]
if cmd == 'estado':
    out({'guard': FP.encendido(), 'ledger': str(A.ledger()), 'cred_ok': bool(A.credencial()), 'raiz': str(FP.raiz()),
         'aprobadores': list(FP.F.aprobadores()), 'ya': {p: FP.carpeta(p).exists() for p in TOPES},
         'topes': {p: (PR.cargar().get('topes_paso') or {}).get(p) for p in TOPES}})
elif cmd == 'tope':
    f = PR.ARCHIVO; viejo = f.read_text(encoding='utf-8'); d = json.loads(viejo)
    if json.dumps(d, ensure_ascii=False, indent=2) + ('\n' if viejo.endswith('\n') else '') != viejo:
        out({'error': 'el formato de precios_myia.json no se reproduce: no lo toco'}); sys.exit(2)
    tp = d['topes_paso']; puestos = {}
    for p, usd in TOPES.items():
        if p in tp: puestos[p] = 'ya existía, no se cambia'; continue
        tp[p] = {'tramos': [{'vigente_desde': '2026-11-09', 'usd': usd}],
                 'fuente': f'{AUT} Tope = la cotización oficial por consulta (myia_argon.estimar, max_out 65536, peor caso) '
                           f'del 9-nov-2026: US${usd}. 1 intento, sin reintentos. Desde el 1-dic el precio sube y la consulta ya no cabe.'}
        puestos[p] = usd
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    resp = Path('/opt/myia-staging-arreglos-20261026/respaldos') / f'precios_myia.json.antes_recetas_{ts}'
    shutil.copy2(f, resp)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + ('\n' if viejo.endswith('\n') else ''), encoding='utf-8')
    out({'respaldo': str(resp), 'puestos': puestos, 'lee': {p: PR.tope_paso(p, A.hoy()) for p in TOPES}})
elif cmd == 'registrar':
    hechos = set()
    for c in CASOS:
        fj = fijo(c); p = fj['paso']
        if p in hechos: continue
        hechos.add(p)
        nota = f'{AUT} sha256 total {FP.sha_total(fj["partes"])}; {M} {NIVEL} max_out {MAXO} max_rondas 1; fragmentos {len(fj["fragmentos"])}.'
        try:
            out({'paso': p, 'registrado': FP.registrar(p, fj, 'Ricardo', nota=nota)})
        except Exception as e:
            out({'paso': p, 'error': type(e).__name__, 'detalle': str(e)})
elif cmd == 'cotizar':
    r = {c: {'est': est(c), 'cotizado': CASOS[c]['cotizado'], 'tope_catalogo': PR.tope_paso(CASOS[c]['paso'], A.hoy())['usd']} for c in CASOS}
    out({'hoy': str(A.hoy()), 'precio': A.precio(M), 'casos': r, 'total': round(sum(x['est'] for x in r.values()), 4)})
elif cmd == 'enviar':
    for c in (sys.argv[2:] or list(CASOS)):
        res = W / f'res_{c}.json'
        if res.exists() and json.loads(res.read_text()).get('enviado'):
            out({'caso': c, 'omitido': 'ya enviado antes (no se repite)'}); continue
        t = texto(c); e = est(c); total = round(sum(est(x) for x in CASOS), 4)
        tope = PR.tope_paso(CASOS[c]['paso'], A.hoy())['usd']
        if total > TOPE_TOTAL + 1e-9 or e > CASOS[c]['cotizado'] + 1e-9 or e > tope + 1e-9:
            r = {'caso': c, 'enviado': False, 'motivo': f'est {e} cotizado {CASOS[c]["cotizado"]} tope {tope} total {total}'}
            res.write_text(json.dumps(r, ensure_ascii=False)); out(r); continue
        id_ = f'receta-{c}-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') if c != 'piquito' else \
              'investigacion-piquito-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        sal = W / 'respuestas' / f'{c}.json'
        try:
            r = A.llamar(id_, t, str(sal), e, f'{c} — {AUT}', modelo=M, nivel=NIVEL, max_out=MAXO, json_out=True,
                         fijo=fijo(c), cotizacion=A.cotizacion(e, M), ok_usd=e, tope_usd=min(tope, CASOS[c]['cotizado']))
            r = {'caso': c, 'enviado': True, 'id': id_, 'est': e, 'usd_real': r['usd'], 'fin': str(r['fin']),
                 'tokens_entrada': r['tokens_entrada'], 'tokens_salida': r['tokens_salida'], 'salida': str(sal)}
        except Exception as ex:
            r = {'caso': c, 'enviado': 'error', 'id': id_, 'error': type(ex).__name__, 'detalle': str(ex)[:1500]}
        res.write_text(json.dumps(r, ensure_ascii=False)); out(r)
