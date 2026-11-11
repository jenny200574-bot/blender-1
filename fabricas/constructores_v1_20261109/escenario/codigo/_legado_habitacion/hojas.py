# -*- coding: utf-8 -*-
"""Hojas de comparación (PIL). 1) comparativa cajas vs Star (5 vistas) con el molde n8n original arriba. 2) hoja interior Star."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json
B = Path(__file__).resolve().parents[1]; R = B / 'renders'; O = B / 'hojas'; O.mkdir(exist_ok=True)
N8N = Path('/workspace/fabricas/datos_n8n/escenario')
VIS = [('cenital_sin_techo', 'Cenital sin techo'), ('desde_puerta', 'Desde la puerta'), ('hacia_cama', 'Hacia la cama'),
       ('hacia_ventana', 'Hacia la ventana'), ('esquina_armario', 'Esquina del armario')]
def f(s): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', s)
TW, TH = 800, 450
def tile(p, w=TW, h=TH):
    im = Image.open(p).convert('RGB'); im.thumbnail((w, h)); c = Image.new('RGB', (w, h), (40, 40, 40)); c.paste(im, ((w - im.width) // 2, (h - im.height) // 2)); return c
vs = json.loads((B / 'datos/validacion_star.json').read_text()); vc = json.loads((B / 'datos/validacion_cajas.json').read_text())
nst = sum(1 for i in vs['info'] if i['fid'] and 'FALTA' not in i['forma'])
cab = 150; fila = TH + 40
hoja = Image.new('RGB', (2 * TW + 30, cab + fila * (len(VIS) + 1) + 20), 'white'); d = ImageDraw.Draw(hoja)
d.text((15, 12), 'esc-habitacion (Los Guardianes, cap01) — molde de cajas vs biblioteca Star (283 formas)', fill='black', font=f(30))
d.text((15, 56), f'Mismo cuarto, luz y cámaras. Star: {nst} objetos con forma Star, faltantes = cajas translúcidas; '
       f'{len(vs["sostenidos_no_dibujados"])} props en mano/volando no se dibujan.', fill=(60, 60, 60), font=f(18))
d.text((15, 84), f'Validación — cajas: {len(vc["problemas"])} avisos (5 objetos enterrados en la caja de la cama/estantería). '
       f'Star: {len(vs["problemas"])} avisos, {len(vs["correcciones_apoyo"])} apoyos corregidos.', fill=(60, 60, 60), font=f(18))
d.text((15, 112), 'Fila 0 = molde n8n actual (4a2) de referencia: cam_01_esc1.png y planta.png', fill=(120, 40, 40), font=f(18))
y = cab
d.text((15, y), 'n8n 4a2 (molde actual)  cam_01_esc1', fill='black', font=f(20)); d.text((TW + 30, y), 'n8n 4a2  planta.png', fill='black', font=f(20))
hoja.paste(tile(N8N / 'cam_01_esc1.png'), (10, y + 32)); hoja.paste(tile(N8N / 'planta.png'), (TW + 20, y + 32)); y += fila
for k, (n, t) in enumerate(VIS):
    d.text((15, y), f'{t} — MOLDE DE CAJAS', fill='black', font=f(20)); d.text((TW + 30, y), f'{t} — STAR', fill=(0, 90, 0), font=f(20))
    hoja.paste(tile(R / f'cajas_{n}.png'), (10, y + 32)); hoja.paste(tile(R / f'star_{n}.png'), (TW + 20, y + 32)); y += fila
hoja.save(O / '01_COMPARATIVA_cajas_vs_star.png'); hoja.convert('RGB').resize((hoja.width // 2, hoja.height // 2)).save(O / '01_COMPARATIVA_cajas_vs_star_mini.jpg', quality=88)
# interior Star grande
g = Image.new('RGB', (2 * 1280 + 30, 3 * 760 + 80), 'white'); d = ImageDraw.Draw(g)
d.text((15, 15), 'esc-habitacion — STAR — vistas interiores (1280×720, EEVEE CPU)', fill='black', font=f(32))
for k, (n, t) in enumerate(VIS):
    x, yy = 10 + (k % 2) * 1290, 70 + (k // 2) * 760
    d.text((x + 5, yy), t, fill='black', font=f(24)); g.paste(Image.open(R / f'star_{n}.png').convert('RGB'), (x, yy + 34))
g.save(O / '02_STAR_interiores.png')
print('ok')
