# -*- coding: utf-8 -*-
"""Hojas después de las recetas de Argon: 03 comparativa antes (faltantes = cajas translúcidas) vs ahora (recetas aptas),
04 interiores con recetas, 05 recetas una por una con su estado del revisor."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json
B = Path(__file__).resolve().parents[1]; R = B / 'renders'; O = B / 'hojas'
VIS = [('cenital_sin_techo', 'Cenital sin techo'), ('desde_puerta', 'Desde la puerta'), ('hacia_cama', 'Hacia la cama'),
       ('hacia_ventana', 'Hacia la ventana'), ('esquina_armario', 'Esquina del armario')]
def f(s): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)
def fr(s): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', s)
TW, TH = 800, 450
def tile(p, w=TW, h=TH):
    im = Image.open(p).convert('RGB'); im.thumbnail((w, h)); c = Image.new('RGB', (w, h), (40, 40, 40)); c.paste(im, ((w - im.width) // 2, (h - im.height) // 2)); return c
rev = json.loads((B / 'via_b/respuestas/REVISION.json').read_text(encoding='utf-8'))
obj = {k: v for g in rev.values() for k, v in (g.get('por_objeto') or {}).items()}
ok = sum(v['apta'] for v in obj.values())
hoja = Image.new('RGB', (2 * TW + 30, 130 + (TH + 40) * len(VIS) + 10), 'white'); d = ImageDraw.Draw(hoja)
d.text((15, 12), 'esc-habitacion — ANTES (faltantes = cajas translúcidas) vs AHORA (recetas de Argon aptas)', fill='black', font=f(28))
d.text((15, 56), f'Recetas que pasaron el revisor sin IA: {ok} de {len(obj)}. Las rechazadas siguen como caja translúcida. '
       'Props en mano/volando no van en el set.', fill=(60, 60, 60), font=f(18))
y = 100
for n, t in VIS:
    d.text((15, y), f'{t} — ANTES', fill='black', font=f(20)); d.text((TW + 30, y), f'{t} — AHORA', fill=(0, 90, 0), font=f(20))
    hoja.paste(tile(R / f'star_{n}.png'), (10, y + 32)); hoja.paste(tile(R / f'star_recetas_{n}.png'), (TW + 20, y + 32)); y += TH + 40
hoja.save(O / '03_COMPARATIVA_antes_faltantes_vs_ahora_recetas.png')
g = Image.new('RGB', (2 * 1280 + 30, 3 * 760 + 80), 'white'); d = ImageDraw.Draw(g)
d.text((15, 15), 'esc-habitacion — STAR + recetas Argon — vistas interiores (1280×720)', fill='black', font=f(32))
for k, (n, t) in enumerate(VIS):
    x, yy = 10 + (k % 2) * 1290, 70 + (k // 2) * 760
    d.text((x + 5, yy), t, fill='black', font=f(24)); g.paste(Image.open(R / f'star_recetas_{n}.png').convert('RGB'), (x, yy + 34))
g.save(O / '04_STAR_recetas_interiores.png')
ids = list(obj); C = 5; S = 360; filas = (len(ids) + C - 1) // C
h = Image.new('RGB', (C * S + 20, 70 + filas * (S + 90)), 'white'); d = ImageDraw.Draw(h)
d.text((10, 10), 'Recetas de Argon (vía B), una por una — estado del revisor sin IA', fill='black', font=f(26))
for i, k in enumerate(ids):
    x, yy = 10 + (i % C) * S, 60 + (i // C) * (S + 90); v = obj[k]; p = R / 'recetas' / f'{k}.png'
    if v['apta'] and p.exists(): h.paste(Image.open(p).convert('RGB').resize((S - 10, S - 10)), (x, yy))
    else: d.rectangle([x, yy, x + S - 10, yy + S - 10], fill=(245, 225, 225))
    d.text((x, yy + S - 5), k.replace('amb-esc-habitacion-', ''), fill='black', font=f(16))
    d.text((x, yy + S + 16), 'APTA' if v['apta'] else 'RECHAZADA', fill=(0, 120, 0) if v['apta'] else (170, 0, 0), font=f(16))
    if not v['apta']:
        e = v['errores'][0] if v['errores'] else ''
        for j in range(3): d.text((x, yy + S + 36 + j * 16), e[j * 42:(j + 1) * 42], fill=(120, 0, 0), font=fr(13))
h.save(O / '05_RECETAS_una_por_una.png'); print('ok')
