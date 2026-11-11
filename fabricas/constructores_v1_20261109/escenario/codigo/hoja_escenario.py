# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · genérico] HOJA de aprobación de un escenario: 5 vistas de construir_render.py + resumen de validación.
Uso: python3 hoja_escenario.py --escenario ID --modo star --datos DIR --renders DIR/renders --salida HOJA.png  (PIL, US$0)"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser()
for k in ('--escenario', '--datos', '--renders', '--salida'): ap.add_argument(k, required=True)
ap.add_argument('--modo', default='star'); a = ap.parse_args()
def f(s):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)
    except Exception: return ImageFont.load_default()
VIS = ['cenital_sin_techo', 'vista_a', 'vista_b', 'vista_c', 'vista_d']
R = Path(a.renders); v = json.loads((Path(a.datos) / f'validacion_{a.modo}.json').read_text())
nst = sum(1 for i in v['info'] if i.get('fid') and 'FALTA' not in (i.get('forma') or ''))
TW, TH = 800, 450
g = Image.new('RGB', (2 * TW + 30, 120 + 3 * (TH + 40)), 'white'); d = ImageDraw.Draw(g)
d.text((15, 12), f'{a.escenario} — {a.modo.upper()} — {v["objetos"]} objetos, {nst} con forma Star', fill='black', font=f(28))
d.text((15, 56), f'avisos {len(v["problemas"])} · apoyos corregidos {len(v["correcciones_apoyo"])} · sostenidos no dibujados {len(v["sostenidos_no_dibujados"])}', fill=(60, 60, 60), font=f(18))
for k, n in enumerate(VIS):
    p = R / f'{a.modo}_{n}.png'
    if not p.exists(): continue
    im = Image.open(p).convert('RGB'); im.thumbnail((TW, TH))
    x, y = 10 + (k % 2) * (TW + 10), 100 + (k // 2) * (TH + 40)
    d.text((x + 5, y), n, fill='black', font=f(20)); g.paste(im, (x, y + 30))
g.save(a.salida); print(a.salida)
