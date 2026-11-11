"""Registro FIJO + tope de catálogo + recotización + envío único: 8 lotes de poses clave (poses_clave_movimientos_v1).
Staging 213. No imprime credenciales. Sin reintentos. Uno a la vez; nunca pasa de TOPE_TOTAL."""
import sys, json, hashlib, datetime, shutil
from pathlib import Path
R = '/opt/myia-staging-arreglos-20261026/repo'
sys.path[:0] = [R, R + '/web']
import myia_argon as A, myia_fijo_prompt as FP, precios_myia as PR
W = Path(__file__).resolve().parent
M, NIVEL, MAXO, TOPE_TOTAL = 'gemini-4-argon', 'HIGH', 65536, 5.94
CASOS = json.loads((W / 'casos.json').read_text(encoding='utf-8'))
PASO = 'poses_clave_movimientos_v1'
AUT = ('Ricardo 9-nov-2026 14:15 COT: «Registra el prompt de poses y lanza las 8 tandas, máximo US$5,94». Grok Bot.')
def out(d): print(json.dumps(d, ensure_ascii=False), flush=True)
def texto(c): return (W / CASOS[c]['archivo']).read_text(encoding='utf-8')
FIJO = json.loads((W / 'fijo_poses.json').read_text(encoding='utf-8'))
def est(c): return A.estimar(len(texto(c)), MAXO, modelo=M)
TOPE_PASO = max(v['cotizado'] for v in CASOS.values())
cmd = sys.argv[1]
if cmd == 'estado':
    out({'guard': FP.encendido(), 'ledger': str(A.ledger()), 'cred_ok': bool(A.credencial()), 'raiz': str(FP.raiz()),
         'aprobadores': list(FP.F.aprobadores()), 'ya': FP.carpeta(PASO).exists(),
         'tope': (PR.cargar().get('topes_paso') or {}).get(PASO), 'gastado_ledger': A.gastado() if hasattr(A, 'gastado') else None})
elif cmd == 'tope':
    f = PR.ARCHIVO; viejo = f.read_text(encoding='utf-8'); d = json.loads(viejo)
    if json.dumps(d, ensure_ascii=False, indent=2) + ('\n' if viejo.endswith('\n') else '') != viejo:
        out({'error': 'el formato de precios_myia.json no se reproduce: no lo toco'}); sys.exit(2)
    tp = d['topes_paso']
    if PASO in tp: out({'tope': 'ya existía, no se cambia', 'lee': PR.tope_paso(PASO, A.hoy())}); sys.exit(0)
    tp[PASO] = {'tramos': [{'vigente_desde': '2026-11-09', 'usd': TOPE_PASO}],
                'fuente': f'{AUT} Tope = la mayor cotización oficial por lote (myia_argon.estimar, max_out 65536, peor caso) del 9-nov-2026: '
                          f'US${TOPE_PASO}. 8 lotes, 1 intento cada uno, sin reintentos. Desde el 1-dic el precio sube y el lote ya no cabe.'}
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    resp = Path('/opt/myia-staging-arreglos-20261026/respaldos') / f'precios_myia.json.antes_poses_{ts}'
    shutil.copy2(f, resp)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + ('\n' if viejo.endswith('\n') else ''), encoding='utf-8')
    out({'respaldo': str(resp), 'puesto': TOPE_PASO, 'lee': PR.tope_paso(PASO, A.hoy())})
elif cmd == 'registrar':
    nota = f'{AUT} sha256 total {FP.sha_total(FIJO["partes"])}; {M} {NIVEL} max_out {MAXO} max_rondas 1; fragmentos {len(FIJO["fragmentos"])}.'
    try: out({'paso': PASO, 'registrado': FP.registrar(PASO, FIJO, 'Ricardo', nota=nota)})
    except Exception as e: out({'paso': PASO, 'error': type(e).__name__, 'detalle': str(e)})
elif cmd == 'cotizar':
    r = {c: {'est': est(c), 'cotizado': v['cotizado'], 'sha_ok': hashlib.sha256(texto(c).encode()).hexdigest() == v['sha256_texto']} for c, v in CASOS.items()}
    out({'hoy': str(A.hoy()), 'precio': A.precio(M), 'tope_catalogo': PR.tope_paso(PASO, A.hoy())['usd'], 'casos': r,
         'total': round(sum(x['est'] for x in r.values()), 4)})
elif cmd == 'enviar':
    (W / 'respuestas').mkdir(exist_ok=True)
    ests = {c: est(c) for c in CASOS}; total = round(sum(ests.values()), 4)
    tope = PR.tope_paso(PASO, A.hoy())['usd']
    malos = {c: (e, CASOS[c]['cotizado']) for c, e in ests.items() if e > CASOS[c]['cotizado'] + 1e-9 or e > tope + 1e-9}
    if total > TOPE_TOTAL + 1e-9 or malos:
        out({'PARADO': True, 'total': total, 'tope_total': TOPE_TOTAL, 'lotes_sobre_cotizacion': malos}); sys.exit(3)
    gastado = 0.0
    for c in CASOS:
        res = W / f'res_{c}.json'
        if res.exists():
            r0 = json.loads(res.read_text())
            if r0.get('enviado'): gastado += float(r0.get('usd_real') or ests[c]); out({'caso': c, 'omitido': 'ya enviado antes (no se repite)'}); continue
        pendientes = [x for x in CASOS if not (W / f'res_{x}.json').exists()]
        if gastado + sum(ests[x] for x in pendientes) > TOPE_TOTAL + 1e-9:
            r = {'caso': c, 'enviado': False, 'motivo': f'gastado {gastado:.4f} + peor caso pendiente pasaría US${TOPE_TOTAL}'}
            res.write_text(json.dumps(r, ensure_ascii=False)); out(r); continue
        id_ = f'poses-{c}-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        sal = W / 'respuestas' / f'{c}.json'; e = ests[c]
        try:
            r = A.llamar(id_, texto(c), str(sal), e, f'{c} — {AUT}', modelo=M, nivel=NIVEL, max_out=MAXO, json_out=True,
                         fijo=FIJO, cotizacion=A.cotizacion(e, M), ok_usd=e, tope_usd=min(tope, CASOS[c]['cotizado']))
            r = {'caso': c, 'enviado': True, 'id': id_, 'est': e, 'usd_real': r['usd'], 'fin': str(r['fin']),
                 'tokens_entrada': r['tokens_entrada'], 'tokens_salida': r['tokens_salida'], 'salida': str(sal)}
            gastado += float(r['usd_real'])
        except Exception as ex:
            r = {'caso': c, 'enviado': 'error', 'id': id_, 'error': type(ex).__name__, 'detalle': str(ex)[:1500]}
            gastado += e   # posible cobro: se cuenta el peor caso
        r['gastado_acumulado_usd'] = round(gastado, 4)
        res.write_text(json.dumps(r, ensure_ascii=False)); out(r)
