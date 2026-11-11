"""kimodo_gen (pod GPU): genera TODOS los pedidos de la corrida con el CLI oficial de Kimodo (kimodo.scripts.generate.main),
con los MISMOS argumentos del lab aprobado (Ricardo t995u): --model soma --num_samples 1 --seed 7 --bvh --bvh_standard_tpose
--no-postprocess, TEXT_ENCODER_DEVICE=cpu. Única diferencia: el modelo se carga UNA vez para todos los pedidos (caché de load_model).
Uso: python3 kimodo_gen.py --corrida DIR   (lee DIR/kimodo/pedidos.json, escribe DIR/kimodo/<nombre>.bvh/.npz y gen.json)"""
import argparse, json, os, sys, time
ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); a = ap.parse_args()
K = f"{a.corrida}/kimodo"; P = json.load(open(f"{K}/pedidos.json"))
os.environ.setdefault('TEXT_ENCODER_DEVICE', 'cpu')
import kimodo.scripts.generate as G
_cache = {}
_orig = G.load_model
def load_cached(*x, **kw):
    k = repr((x, sorted(kw.items())))
    if k not in _cache: _cache[k] = _orig(*x, **kw)
    return _cache[k]
G.load_model = load_cached
res = {"pedidos": [], "inicio": time.strftime('%Y-%m-%dT%H:%M:%S')}
for p in P['pedidos']:
    t0 = time.time()
    sys.argv = ['kimodo_gen', p['prompt'], '--model', 'soma', '--duration', str(p['duracion_s']), '--constraints', f"{K}/{p['nombre']}.json",
                '--num_samples', '1', '--seed', '7', '--output', f"{K}/{p['nombre']}", '--bvh', '--bvh_standard_tpose', '--no-postprocess']
    try:
        G.main(); ok = os.path.isfile(f"{K}/{p['nombre']}.bvh") and os.path.isfile(f"{K}/{p['nombre']}.npz"); err = None
    except SystemExit as e: ok, err = False, f"SystemExit {e}"
    except Exception as e: ok, err = False, f"{type(e).__name__}: {e}"[:400]
    res['pedidos'].append({"nombre": p['nombre'], "ok": ok, "error": err, "s": round(time.time() - t0, 1)}); print('KIMODO', p['nombre'], ok, err, round(time.time() - t0, 1), flush=True)
json.dump(res, open(f"{K}/gen.json", 'w'), indent=1)
print('RESULT_KIMODO_GEN', json.dumps({"ok": sum(x['ok'] for x in res['pedidos']), "total": len(res['pedidos'])}))
