"""hacer_hoja.py — [constructores_v1_20261109] HOJA de aprobación de un molde de personaje (genérico). US$0, sin IA.
Uso: python3 hacer_hoja.py --informe X_informe.json --medida medida.json --salida HOJA_X.png [--altura-adn 1.12]
(Antes: buscaba *_informe.json en una carpeta fija del prototipo.)"""
import sys, json, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument('--informe', required=True); ap.add_argument('--medida'); ap.add_argument('--salida', required=True)
ap.add_argument('--altura-adn', type=float); a = ap.parse_args()
def font(n):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        try: return ImageFont.truetype(p, n)
        except Exception: pass
    try: return ImageFont.load_default(size=n)
    except Exception: return ImageFont.load_default()
inf = Path(a.informe); d = json.loads(inf.read_text())
med = json.loads(Path(a.medida).read_text()) if a.medida and Path(a.medida).exists() else {}
items = [(k, p if Path(p).exists() else str(inf.parent / Path(p).name)) for k, p in d['renders'].items()]
W = 400; cols = 4; rows = (len(items) + cols - 1) // cols
hoja = Image.new('RGB', (cols * W, rows * (W + 34) + 96), 'white'); dr = ImageDraw.Draw(hoja)
tipo = (d.get('origen') or {}).get('tipo')
orig = {'argon': 'FICHA DE ARGON', 'plantilla': 'FICHA AUTOMÁTICA DESDE ADN (plantilla, sin IA)'}.get(tipo, 'FICHA MANUAL (NO Argon)')
dr.text((10, 10), f"{d['id']} — {orig} · validación {'APTA' if d['validacion']['apta'] else 'RECHAZADA'} · prueba de pose {d['resultado']}", fill='black', font=font(20))
lin2 = f"huesos {d.get('n_huesos')} · piezas {d.get('n_objetos')} · Blender {d.get('blender')} · {'GPU' if d.get('gpu') else 'CPU'}"
if med: lin2 += f" · altura medida {med.get('altura_medida_m')} m"
if a.altura_adn: lin2 += f" · ADN {a.altura_adn} m ({(med.get('altura_medida_m', 0) / a.altura_adn - 1) * 100:+.2f} %)" if med else f" · ADN {a.altura_adn} m"
dr.text((10, 44), lin2, fill='black', font=font(18))
for i, (k, p) in enumerate(items):
    im = Image.open(p).convert('RGB').resize((W, W))
    x, y = (i % cols) * W, 96 + (i // cols) * (W + 34)
    hoja.paste(im, (x, y + 34)); dr.text((x + 8, y + 6), k + (' (rango)' if k.startswith('extremos') else ''), fill='black', font=font(14))
hoja.save(a.salida); print(a.salida)
