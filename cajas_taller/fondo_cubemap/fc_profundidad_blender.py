"""FC coherencia (inmi 2-nov t472u) · GRATIS, sin red. Profundidad por ray_cast sobre el clon SIN personajes.
blender -b fondo_sin_personajes.blend --python fc_profundidad_blender.py -- --cubo DIR_CUBO [--tomas DIR_CON_camaras.json] [--res 256] [--escala 0.25]
Escribe DIR_CUBO/prof/cubo_<K>.npy (distancia al origen por cara) y DIR_CUBO/prof/toma_<id>.npy (distancia desde la cámara de la toma)."""
import bpy, sys, json, os, argparse, numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser(); ap.add_argument('--cubo', required=True); ap.add_argument('--tomas', default='')
ap.add_argument('--res', type=int, default=256); ap.add_argument('--escala', type=float, default=0.25); ap.add_argument('--solo', default='')
a = ap.parse_args(argv)
S = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); LEJOS = 1000.0
P = os.path.join(a.cubo, 'prof'); os.makedirs(P, exist_ok=True)

def lanzar(o, D):
    out = np.full(len(D), LEJOS, np.float32); O = Vector(o)
    for i, d in enumerate(D):
        h, loc, *_ = S.ray_cast(dg, O, Vector(d))
        if h: out[i] = (loc - O).length
    return out

caras = json.load(open(os.path.join(a.cubo, 'caras.json'))); o = caras['origen']; N = a.res
for k, c in caras['caras'].items():
    f = os.path.join(P, f'cubo_{k}.npy')
    if os.path.isfile(f): continue
    u = ((np.arange(N) + 0.5) / N) * 2 - 1; U, V = np.meshgrid(u, -u)
    D = np.array(c['adelante'])[None, None] + U[..., None] * np.array(c['derecha']) + V[..., None] * np.array(c['arriba'])
    np.save(f, lanzar(o, D.reshape(-1, 3)).reshape(N, N))
if a.tomas:
    solo = set(x for x in a.solo.split(',') if x)
    for t in json.load(open(os.path.join(a.tomas, 'camaras.json')))['tomas']:
        if t.get('tipo') != 'PERSP' or (solo and t['toma'] not in solo): continue
        f = os.path.join(P, f"toma_{t['toma']}.npy")
        if os.path.isfile(f): continue
        W, H = max(8, int(t['W'] * a.escala)), max(8, int(t['H'] * a.escala)); M = np.array(t['matriz'])
        fl = t['lente_mm']; fit = t['sensor_fit']
        if fit == 'VERTICAL' or (fit == 'AUTO' and H > W): sh = t['sensor_h'] if fit == 'VERTICAL' else t['sensor_w']; sw = sh * W / H
        else: sw = t['sensor_w']; sh = sw * H / W
        big = max(sw, sh)
        xs = ((np.arange(W) + 0.5) / W - 0.5) * sw + t['shift'][0] * big; ys = (0.5 - (np.arange(H) + 0.5) / H) * sh + t['shift'][1] * big
        X, Y = np.meshgrid(xs, ys); d = np.stack([X, Y, -np.full_like(X, fl)], -1) @ M[:3, :3].T
        d = d / np.linalg.norm(d, axis=-1, keepdims=True)
        np.save(f, lanzar(M[:3, 3], d.reshape(-1, 3)).reshape(H, W))
print('FC_JSON ' + json.dumps({'ok': True, 'prof': P}))
