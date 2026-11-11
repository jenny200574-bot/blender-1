"""FC · coherencia entre cubos (inmi 2-nov-2026, Ricardo t472u/t473u). TODO GRATIS (numpy/Blender, sin red).
Problema: la proyección de entorno NO tiene paralaje -> (a) salto T3→T4 al cambiar de cubo A→B, (b) tomas cercanas en
dirección parecida (T1/T2, T4/T5) salen casi iguales porque el fondo es el mismo «pegado al infinito», (c) el estilo se
desvía entre cubos pintados por separado.
Arreglo:
  agrupar      cámaras -> grupos por distancia; 1 cubo por grupo (origen = cámara medoide, válida para --origen);
               si TODAS caben en «umbral_compartido» del centroide -> 1 solo cubo compartido.
  profundidad  (Blender) distancia por ray_cast en el clon SIN personajes, para cada cubo y cada toma.
  reproyectar  por toma: punto 3D real = cámara + t·rayo; se colorea mirando ese punto DESDE el origen del cubo
               (con prueba de oclusión). Así cualquier cubo sirve a cualquier toma con paralaje correcto y, si dos cubos
               ven el mismo punto, ven el MISMO color -> se acaba el salto. Huecos (zonas que ningún cubo ve) se
               rellenan con el método viejo (al infinito) y se reportan en %.
  equirect     6 caras <-> 1 panorama 360 equirectangular (2:1). Pintar 1 sola imagen evita costuras entre caras.
               (NO arregla el paralaje: sigue siendo un solo punto de vista; combinar con reproyectar.)
  estilo       al pintar varios cubos, la cara F del PRIMER cubo pintado es la referencia de estilo de todos los demás."""
import json, math
from pathlib import Path
import numpy as np

CARAS = ['F', 'B', 'L', 'R', 'U', 'D']
LEJOS = 999.0


# ---------------- 1) agrupar cámaras ----------------
def camaras_unicas(tomas):
    v = {}
    for t in tomas:
        if t.get('tipo') != 'PERSP': continue
        M = np.array(t['matriz']); v.setdefault(t['camara'], {'camara': t['camara'], 'pos': M[:3, 3].tolist(), 'mira': (-M[:3, 2]).tolist(), 'tomas': []})['tomas'].append(t['toma'])
    return list(v.values())


def agrupar(tomas, umbral=3.0, umbral_compartido=2.5, dist_fondo=6.0, dup_m=1.0, dup_grados=12.0):
    """Enlace simple: dos cámaras a <= umbral m quedan en el mismo grupo. Error de paralaje estimado = atan(d/dist_fondo)."""
    cs = camaras_unicas(tomas); n = len(cs); P = np.array([c['pos'] for c in cs]); pad = list(range(n))
    def raiz(i):
        while pad[i] != i: pad[i] = pad[pad[i]]; i = pad[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if np.linalg.norm(P[i] - P[j]) <= umbral: pad[raiz(i)] = raiz(j)
    g = {}
    for i in range(n): g.setdefault(raiz(i), []).append(i)
    par = lambda d: round(math.degrees(math.atan2(d, dist_fondo)), 1)
    grupos = []
    for k, idx in enumerate(sorted(g.values(), key=lambda x: -len(x))):
        C = P[idx].mean(0); med = min(idx, key=lambda i: np.linalg.norm(P[i] - C))
        grupos.append({'grupo': f'g{k+1}', 'origen_camara': cs[med]['camara'], 'origen': P[med].round(3).tolist(), 'centroide': C.round(3).tolist(),
                       'camaras': [cs[i]['camara'] for i in idx], 'radio_m': round(float(max(np.linalg.norm(P[i] - P[med]) for i in idx)), 2),
                       'paralaje_max_grados': par(max(np.linalg.norm(P[i] - P[med]) for i in idx))})
    Cg = P.mean(0); rmax = float(max(np.linalg.norm(P - Cg, axis=1))) if n else 0
    dups = []
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.linalg.norm(P[i] - P[j])); a = math.degrees(math.acos(max(-1, min(1, float(np.dot(cs[i]['mira'], cs[j]['mira']) / (np.linalg.norm(cs[i]['mira']) * np.linalg.norm(cs[j]['mira'])))))))
            if d <= dup_m and a <= dup_grados: dups.append({'camaras': [cs[i]['camara'], cs[j]['camara']], 'dist_m': round(d, 2), 'angulo_grados': round(a, 1), 'aviso': 'casi duplicadas: mover/rotar una o fusionar tomas (FC no puede inventar diferencia)'})
            elif a <= dup_grados and d > dup_m: dups.append({'camaras': [cs[i]['camara'], cs[j]['camara']], 'dist_m': round(d, 2), 'angulo_grados': round(a, 1), 'aviso': 'misma dirección, distinta posición: SIN paralaje salen casi iguales -> usar «reproyectar»'})
    compartido = rmax <= umbral_compartido
    return {'umbral_m': umbral, 'umbral_compartido_m': umbral_compartido, 'dist_fondo_m': dist_fondo, 'centroide_escena': Cg.round(3).tolist(),
            'radio_desde_centroide_m': round(rmax, 2), 'decision': 'un_cubo_compartido' if compartido else ('un_cubo_por_grupo' if len(grupos) > 1 else 'un_cubo'),
            'grupos': grupos if not compartido else [{'grupo': 'g1', 'origen_camara': None, 'origen': Cg.round(3).tolist(), 'camaras': [c['camara'] for c in cs], 'radio_m': round(rmax, 2), 'paralaje_max_grados': par(rmax)}],
            'camaras': cs, 'avisos_tomas': dups,
            'recomendacion': 'pintar 1 cubo por grupo con estilo bloqueado (ref = cara F del primero) y usar «reproyectar» para TODAS las tomas'}


# ---------------- muestreo de cubo / equirect ----------------
def muestrear_cubo(caras, imgs, d):
    """d: (...,3) direcciones mundo -> color (...,3) y cara elegida."""
    sh = d.shape[:-1]; d = d.reshape(-1, 3); out = np.zeros((len(d), imgs['F'].shape[-1] if imgs['F'].ndim == 3 else 1), np.float32); mejor = np.full(len(d), -np.inf)
    for k in CARAS:
        Fw, Up, Rt = (np.array(caras[k][x], float) for x in ('adelante', 'arriba', 'derecha'))
        z = d @ Fw; m = (z > mejor) & (z > 0)
        if not m.any(): continue
        mejor = np.where(m, z, mejor); im = imgs[k]; N = im.shape[0]
        if im.ndim == 2: im = im[..., None]
        u = (d[m] @ Rt) / z[m]; v = (d[m] @ Up) / z[m]
        px = np.clip((u + 1) / 2 * N - 0.5, 0, N - 1); py = np.clip((1 - v) / 2 * N - 0.5, 0, N - 1)
        x0 = np.floor(px).astype(int); y0 = np.floor(py).astype(int); x1 = np.minimum(x0 + 1, N - 1); y1 = np.minimum(y0 + 1, N - 1)
        ax = (px - x0)[:, None]; ay = (py - y0)[:, None]
        out[m] = im[y0, x0] * (1 - ax) * (1 - ay) + im[y0, x1] * ax * (1 - ay) + im[y1, x0] * (1 - ax) * ay + im[y1, x1] * ax * ay
    return out.reshape(sh + (out.shape[-1],))


def _dirs_equirect(W, H):
    lon = ((np.arange(W) + 0.5) / W) * 2 * np.pi - np.pi; lat = np.pi / 2 - ((np.arange(H) + 0.5) / H) * np.pi
    LO, LA = np.meshgrid(lon, lat)   # lon 0 = +Y (cara F), +lon hacia +X (cara R); Z arriba
    return np.stack([np.cos(LA) * np.sin(LO), np.cos(LA) * np.cos(LO), np.sin(LA)], -1)


def cubo_a_equirect(caras, imgs, W=2048):
    return muestrear_cubo(caras, imgs, _dirs_equirect(W, W // 2))


def muestrear_equirect(eq, d):
    d = d / np.linalg.norm(d, axis=-1, keepdims=True); H, W = eq.shape[:2]
    lon = np.arctan2(d[..., 0], d[..., 1]); lat = np.arcsin(np.clip(d[..., 2], -1, 1))
    px = ((lon + np.pi) / (2 * np.pi) * W - 0.5) % W; py = np.clip((np.pi / 2 - lat) / np.pi * H - 0.5, 0, H - 1)
    x0 = np.floor(px).astype(int) % W; x1 = (x0 + 1) % W; y0 = np.floor(py).astype(int); y1 = np.minimum(y0 + 1, H - 1)
    ax = (px - np.floor(px))[..., None]; ay = (py - y0)[..., None]
    return eq[y0, x0] * (1 - ax) * (1 - ay) + eq[y0, x1] * ax * (1 - ay) + eq[y1, x0] * (1 - ax) * ay + eq[y1, x1] * ax * ay


def equirect_a_cubo(caras, eq, N=1024):
    out = {}
    u = ((np.arange(N) + 0.5) / N) * 2 - 1; U, V = np.meshgrid(u, -u)
    for k in CARAS:
        c = caras[k]; D = np.array(c['adelante'])[None, None] + U[..., None] * np.array(c['derecha']) + V[..., None] * np.array(c['arriba'])
        out[k] = muestrear_equirect(eq, D)
    return out


# ---------------- 2) reproyección con profundidad ----------------
def rayos_toma(t, W=None, H=None):
    W = W or t['W']; H = H or t['H']; M = np.array(t['matriz'])
    f = t['lente_mm']; fit = t['sensor_fit']
    if fit == 'VERTICAL' or (fit == 'AUTO' and H > W): sh = t['sensor_h'] if fit == 'VERTICAL' else t['sensor_w']; sw = sh * W / H
    else: sw = t['sensor_w']; sh = sw * H / W
    big = max(sw, sh)
    xs = ((np.arange(W) + 0.5) / W - 0.5) * sw + t['shift'][0] * big; ys = (0.5 - (np.arange(H) + 0.5) / H) * sh + t['shift'][1] * big
    X, Y = np.meshgrid(xs, ys); d = np.stack([X, Y, -np.full_like(X, f)], -1) @ M[:3, :3].T
    return d / np.linalg.norm(d, axis=-1, keepdims=True), M[:3, 3]


def _subir(a, H, W):
    h, w = a.shape; yi = np.minimum((np.arange(H) * h / H).astype(int), h - 1); xi = np.minimum((np.arange(W) * w / W).astype(int), w - 1)
    return a[yi][:, xi]


def reproyectar_toma(t, cubos, prof_toma, tol=0.04):
    """cubos: lista [{'origen', 'caras', 'imgs', 'prof': {K: NxN}}] ordenada por preferencia (el más cercano primero).
    Devuelve imagen (H,W,3), % de píxeles de cada cubo y % de huecos (relleno al infinito)."""
    d, C = rayos_toma(t); H, W = d.shape[:2]; z = _subir(prof_toma, H, W)
    lejos = z >= LEJOS * 0.9; Pw = C + d * z[..., None]
    out = np.zeros((H, W, 3), np.float32); hecho = np.zeros((H, W), bool); stats = []
    for c in cubos:
        O = np.array(c['origen']); v = Pw - O; r = np.linalg.norm(v, axis=-1)
        zc = muestrear_cubo(c['caras'], c['prof'], v)[..., 0]
        vis = (~hecho) & (~lejos) & (r <= zc * (1 + tol) + 0.05)
        col = muestrear_cubo(c['caras'], c['imgs'], v); out[vis] = col[vis]; hecho |= vis; stats.append(round(100 * vis.mean(), 1))
    # cielo/lejos y huecos: dirección del rayo desde el cubo preferido (método viejo)
    resto = ~hecho
    if resto.any():
        col = muestrear_cubo(cubos[0]['caras'], cubos[0]['imgs'], d); out[resto] = col[resto]
    return out, {'pct_por_cubo': stats, 'pct_infinito': round(100 * (lejos & resto).mean(), 1), 'pct_hueco': round(100 * (resto & ~lejos).mean(), 1)}


def cargar_cubo(D, fuente='auto', N=None):
    from PIL import Image
    D = Path(D); cj = json.load(open(D / 'caras.json')); N = N or cj['res']
    src = fuente if fuente != 'auto' else ('pintado' if all((D / 'pintado' / f'{k}.png').is_file() for k in CARAS) else 'gris')
    imgs = {k: np.asarray(Image.open(D / src / f'{k}.png').convert('RGB').resize((N, N)), np.float32) for k in CARAS}
    prof = {k: np.load(D / 'prof' / f'cubo_{k}.npy')[..., None] for k in CARAS} if (D / 'prof' / 'cubo_F.npy').is_file() else None
    return {'dir': str(D), 'origen': cj['origen'], 'camara_origen': cj.get('camara_origen'), 'caras': cj['caras'], 'imgs': imgs, 'prof': prof, 'fuente': src}
