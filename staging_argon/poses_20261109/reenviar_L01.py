"""Reenvío ÚNICO de L01 (caminar/correr), autorizado por Ricardo 15:41 COT, máximo US$0,75. Mismo prompt y fijo registrados.
Sin reintentos: si existe res_..._REENVIO.json o la marca de intento, no hace nada."""
import sys, json, hashlib, datetime
from pathlib import Path
R = '/opt/myia-staging-arreglos-20261026/repo'; sys.path[:0] = [R, R + '/web']
import myia_argon as A, precios_myia as PR
W = Path(__file__).resolve().parent
C = 'polluelo_chibi_mascota_L01_de_08'; PASO = 'poses_clave_movimientos_v1'; M, NIVEL, MAXO, MAXIMO = 'gemini-4-argon', 'HIGH', 65536, 0.75
AUT = 'Ricardo 9-nov-2026 15:41 COT: «Sí, reenvía caminar y correr con máximo US$0,75». Reenvío único de L01. Grok Bot.'
def out(d): print(json.dumps(d, ensure_ascii=False), flush=True)
caso = json.loads((W / 'casos.json').read_text(encoding='utf-8'))[C]; FIJO = json.loads((W / 'fijo_poses.json').read_text(encoding='utf-8'))
res, marca = W / f'res_{C}_REENVIO.json', W / f'.intento_{C}_REENVIO'
if res.exists() or marca.exists(): out({'omitido': 'el reenvío ya se intentó; no se repite'}); sys.exit(0)
t = (W / caso['archivo']).read_text(encoding='utf-8')
e = A.estimar(len(t), MAXO, modelo=M); tope = PR.tope_paso(PASO, A.hoy())['usd']
if hashlib.sha256(t.encode()).hexdigest() != caso['sha256_texto'] or e > MAXIMO + 1e-9 or e > tope + 1e-9:
    r = {'caso': C, 'enviado': False, 'motivo': f'est {e} máximo {MAXIMO} tope {tope}'}; res.write_text(json.dumps(r, ensure_ascii=False)); out(r); sys.exit(3)
marca.write_text(datetime.datetime.now().isoformat())
id_ = f'poses-{C}-REENVIO-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'); sal = W / 'respuestas' / f'{C}.json'
try:
    x = A.llamar(id_, t, str(sal), e, f'{C} — {AUT}', modelo=M, nivel=NIVEL, max_out=MAXO, json_out=True,
                 fijo=FIJO, cotizacion=A.cotizacion(e, M), ok_usd=e, tope_usd=min(tope, MAXIMO))
    r = {'caso': C, 'enviado': True, 'id': id_, 'est': e, 'usd_real': x['usd'], 'fin': str(x['fin']),
         'tokens_entrada': x['tokens_entrada'], 'tokens_salida': x['tokens_salida'], 'salida': str(sal)}
except Exception as ex:
    r = {'caso': C, 'enviado': 'error', 'id': id_, 'est': e, 'error': type(ex).__name__, 'detalle': str(ex)[:1500]}
res.write_text(json.dumps(r, ensure_ascii=False)); out(r)
