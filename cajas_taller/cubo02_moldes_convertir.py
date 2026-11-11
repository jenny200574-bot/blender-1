"""PISTA INMI (2026-10-29): orden 87 — conversión UNIVERSAL de los moldes de toma del CUBO 02 (copia de taller de
pruebas_o84/hibrido_convertir.py, orden 84). Usa el pase ID plano de cubo02_moldes_blender.py: cada píxel cuyo color coincide (±TOL)
con la paleta de la config (personajes, accesorios, piel, nuca, cielo) se pinta con ese color EXACTO; el resto es el set en gris
difuminado. Arma la hoja 2×N (2 columnas, N filas) con la maqueta de la hoja de Ako (márgenes y calles blancas).
Cambio de la orden 87: el tamaño del panel sale del formato del canal (no siempre 16:9). US$0, sin red."""
import json
import numpy as np
from PIL import Image, ImageFilter, ImageOps

TOL = 4


def rgb(h): h = str(h).lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def paleta(cfg):
    """[(etiqueta, rgb)] en orden de prioridad. ValueError si dos colores están demasiado cerca o si uno es gris."""
    P = []
    for p in cfg['personajes']:
        P.append((p['id'], rgb(p['color_molde'])))
        for a in p.get('accesorios', []): P.append((f"{p['id']}:{a['nombre']}", rgb(a['color'])))
    C = cfg['colores_molde']; P += [('piel', rgb(C['piel'])), ('nuca', rgb(C['nuca']))]
    if C.get('cielo'): P.append(('cielo', rgb(C['cielo'])))
    vistos = {}
    for e, c in P:
        for e2, c2 in vistos.items():
            if c != c2 and max(abs(a - b) for a, b in zip(c, c2)) <= 3 * TOL: raise ValueError(f'paleta ambigua: {e} y {e2}')
        vistos.setdefault(e, c)
    for e, c in P:
        if max(c) - min(c) < 12 and e not in ('nuca',): raise ValueError(f'color de paleta gris (se confunde con el set): {e}')
    return P


def hoja(paneles, filas, W, Hh, gut=24, marg=48):
    """Misma maqueta que la hoja de Ako (myia_tiras_servicio.hoja), con el tamaño de panel del canal."""
    ancho = 2 * W + gut
    alto_f = [Hh if f == 2 else int(ancho * Hh / W) for f in filas]
    S = Image.new('RGB', (ancho + 2 * marg, sum(alto_f) + gut * (len(filas) - 1) + 2 * marg), 'white')
    y, i = marg, 0
    for f, hf in zip(filas, alto_f):
        if f == 1:
            S.paste(paneles[i].resize((ancho, hf)), (marg, y)); i += 1
        else:
            for c in range(2):
                if i < len(paneles): S.paste(paneles[i], (marg + c * (W + gut), y)); i += 1
        y += hf + gut
    return S


def geometria(n_paneles, W, Hh, gut=24, marg=48):
    """Cajas (x0, y0, x1, y1) de cada panel en la hoja 2×N (para cortar la tira pintada en el mismo orden)."""
    out = []
    for i in range(n_paneles):
        f, c = divmod(i, 2); x0 = marg + c * (W + gut); y0 = marg + f * (Hh + gut); out.append((x0, y0, x0 + W, y0 + Hh))
    return out


def convertir(cfg, crudos, D, ids, panel=(1280, 720), nombre=None):
    """crudos = carpeta de cubo02_moldes_blender (sombreado/ e id/); D = salida. Devuelve (ruta_hoja, stats)."""
    from pathlib import Path
    D = Path(D); D.mkdir(parents=True, exist_ok=True); P = paleta(cfg); stats = {}; paneles = []; W, Hh = panel
    for n in ids:
        sh = Image.open(f'{crudos}/sombreado/{n}.png').convert('RGB').resize((W, Hh), Image.LANCZOS)
        idm = np.asarray(Image.open(f'{crudos}/id/{n}.png').convert('RGB').resize((W, Hh), Image.NEAREST)).astype(int)
        G = ImageOps.grayscale(sh).filter(ImageFilter.GaussianBlur(3)).point(lambda x: int(40 + x * .7))
        O = np.asarray(G.convert('RGB')).copy(); st = {}
        for e, c in P:
            m = (np.abs(idm - np.array(c)).max(2) <= TOL)
            O[m] = c; st[e] = round(float(m.mean()), 4)
        im = Image.fromarray(O.astype('uint8')); im.save(D / f'{n}.png'); paneles.append(im); stats[n] = st
    filas = [2] * ((len(ids) + 1) // 2)
    S = hoja(paneles, filas, W, Hh); f = D / (nombre or f'hoja_moldes_2x{len(filas)}.png'); S.save(f)
    (D / 'cobertura_paleta.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    return str(f), stats
