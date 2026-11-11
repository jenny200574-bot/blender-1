#!/usr/bin/env python3
"""Hojas de contacto de la biblioteca de formas (US$0, local). Lee salida_biblioteca/render_biblioteca/vista_<forma>.png y
render_estados/vista_<forma>__<estado>.png; escribe salida_biblioteca/hoja_biblioteca_NN.png (POR_HOJA por hoja) y hoja_estados.png."""
import glob, json, math, os, sys
from PIL import Image, ImageDraw, ImageFont
AQUI = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(AQUI, 'salida_biblioteca')
POR_HOJA, COLS, TW = 48, 8, 240
try: F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12); FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
except OSError: F = FB = ImageFont.load_default()
fichas = {f['id']: f for f in json.load(open(os.path.join(AQUI, 'biblioteca_formas.json'), encoding='utf-8'))['fichas']}

def hoja(items, titulo, ruta, cols=COLS):
    th = int(TW * 9 / 16) + 30; filas = math.ceil(len(items) / cols)
    im = Image.new('RGB', (cols * TW + 20, filas * th + 50), 'white'); d = ImageDraw.Draw(im); d.text((10, 12), titulo, fill='black', font=FB)
    for i, (png, et) in enumerate(items):
        x, y = 10 + (i % cols) * TW, 45 + (i // cols) * th
        t = Image.open(png).convert('RGB'); t.thumbnail((TW - 6, th - 30)); im.paste(t, (x, y)); d.text((x, y + th - 28), et[:34], fill='black', font=F)
    os.umask(0o077); im.save(ruta); os.chmod(ruta, 0o600); return ruta

def main():
    rb = sorted(glob.glob(os.path.join(S, 'render_biblioteca', 'vista_*.png')))
    rb = [p for p in rb if os.path.basename(p)[6:-4] in fichas]
    falta = sorted(set(fichas) - {os.path.basename(p)[6:-4] for p in rb})
    rb.sort(key=lambda p: (fichas[os.path.basename(p)[6:-4]]['categoria'], os.path.basename(p)))
    out = []
    n = math.ceil(len(rb) / POR_HOJA)
    for h in range(n):
        tr = rb[h * POR_HOJA:(h + 1) * POR_HOJA]
        items = [(p, f"{fichas[k]['categoria']}/{k}") for p in tr for k in [os.path.basename(p)[6:-4]]]
        out.append(hoja(items, f'Biblioteca de formas (código propio, US$0) — hoja {h + 1}/{n} — {len(fichas)} formas', os.path.join(S, f'hoja_biblioteca_{h + 1:02d}.png')))
    re_ = sorted(glob.glob(os.path.join(S, 'render_estados', 'vista_*__*.png')))
    items = [(p, os.path.basename(p)[6:-4].replace('__', ' · ')) for p in re_]
    out.append(hoja(items, f'Biblioteca — estados de muestra (intacto/roto/deformado/flotando/volcado): {len(items)} vistas', os.path.join(S, 'hoja_estados_biblioteca.png'), cols=8))
    print('\n'.join(out)); print('formas con vista', len(rb), 'sin vista', falta)
    return 0 if not falta else 4

if __name__ == '__main__':
    sys.exit(main())
