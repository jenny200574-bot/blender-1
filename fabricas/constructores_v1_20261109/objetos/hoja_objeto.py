# -*- coding: utf-8 -*-
"""Hoja PNG de un objeto (PIL, US$0): 4 vistas + alto medido vs ADN/4a2. Uso: python3 hoja_objeto.py --dir OUT --id ID --alto-ref M --fuente TXT"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument('--dir', required=True); ap.add_argument('--id', required=True); ap.add_argument('--alto-ref', type=float); ap.add_argument('--fuente', default='')
a = ap.parse_args(); D = Path(a.dir); m = json.load(open(D / 'medida.json'))
def f(s):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)
    except Exception: return ImageFont.load_default()
H = Image.new('RGB', (1280, 420), 'white'); d = ImageDraw.Draw(H)
dif = (m['alto_m'] / a.alto_ref - 1) * 100 if a.alto_ref else None
d.text((12, 8), f"{a.id} — molde de objeto · alto medido {m['alto_m']} m" + (f" · referencia {a.alto_ref} m ({dif:+.2f} %)" if dif is not None else ''), fill='black', font=f(20))
d.text((12, 36), f"ancho {m['ancho_m']} m · fondo {m['fondo_m']} m · mallas {m['n_mallas']} · Blender {m['blender']} · {a.fuente}"[:150], fill='black', font=f(14))
for i, n in enumerate(['frente', 'perfil', 'tres_cuartos', 'arriba']):
    p = D / 'renders' / f'{a.id}_{n}.png'
    if p.is_file(): H.paste(Image.open(p).convert('RGB').resize((310, 310)), (10 + i * 318, 62)); d.text((14 + i * 318, 376), n, fill='black', font=f(14))
H.save(D / 'renders' / f'HOJA_{a.id}.png'); print('HOJA_OK')
