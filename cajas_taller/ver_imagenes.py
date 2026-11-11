"""Caja «ver» (orden 66): SOLO LECTURA, GRATIS, sin red. Devuelve las imágenes de un capítulo para verlas en n8n.

Uso (por la entrada SSH restringida):
  paso00_cadena ver moldes  --canal <canal> --capitulo <N|ep-…> [--solo id1,id2] [--tipos planta,cam,luz] [--ancho 1280] [--formato jpg|png]
  paso00_cadena ver pintura --canal <canal> --capitulo <N|ep-…> [--solo id1,id2] [--ancho 1280] [--formato jpg|png]
  paso00_cadena ver galeria <cubo> --canal <canal> --capitulo <N|ep-…>   (orden 70: miniaturas agrupadas para el nodo HTML; ver galeria_n8n.py)
  paso00_cadena ver cubo <01|03|04|05|06|07|08|09|10|14> --canal <canal> --capitulo <N|ep-…> [--escena 3,8]   (orden 74: ver paso01_cubos.py)

- moldes  = renders de Blender de 4a2/4a3: ramas/moldes/<escenario>/planta.png, cam_*.png (y luz_*.png si se pide).
- pintura = imágenes de 4a5: ramas/imagenes/4a5/*.png (bases, vistas y variantes).
Sirve para cualquier canal: solo lee la carpeta del capítulo. No escribe nada, no llama a ningún servicio.
Salida: una línea JSON {ok, imagenes:[{escenario, tipo, nombre, archivo, ancho, alto, ancho_original, alto_original, mime, b64}], …}.
Las imágenes se achican a --ancho (por defecto 1280 px; 0 = tamaño original) y van en JPG calidad 88 para que n8n las cargue rápido
(--formato png = PNG sin pérdida, el archivo original si no se achica). El original en el servidor no se toca.
Tope de salida ~45 MB: si se pasa, se cortan y se avisa (usar --solo).
"""
import argparse, base64, io, json, re
from pathlib import Path

TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
TOPE_BYTES = 45 * 1024 * 1024

def carpeta(canal, capitulo):
    b = TRABAJO / canal
    if not re.fullmatch(r'[A-Za-z0-9._-]+', canal or '') or not b.is_dir(): return None
    ds = sorted(b.glob(f'cap{int(capitulo):02d}_*')) if str(capitulo).isdigit() else sorted(b.glob(f'cap*_{capitulo}'))
    return ds[0] if ds else None

def _num(p):
    m = re.match(r'(?:cam|luz)_(\d+)', p.stem); return int(m.group(1)) if m else 0

def _img(f, ancho, formato):
    """Lee y (si hace falta) achica. formato jpg (liviano, por defecto) o png (sin pérdida)."""
    from PIL import Image
    im = Image.open(f); w0, h0 = im.size
    if ancho and w0 > ancho:
        im = im.resize((ancho, max(1, round(h0 * ancho / w0))), Image.LANCZOS)
    w, h = im.size
    if formato == 'png' and (w, h) == (w0, h0):
        return f.read_bytes(), w, h, w0, h0, 'image/png', 'png'
    buf = io.BytesIO()
    if formato == 'png':
        im.save(buf, 'PNG', optimize=True); return buf.getvalue(), w, h, w0, h0, 'image/png', 'png'
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); fondo = Image.new('RGB', im.size, (255, 255, 255)); fondo.paste(im, mask=im.split()[-1]); im = fondo
    elif im.mode != 'RGB': im = im.convert('RGB')
    im.save(buf, 'JPEG', quality=88, optimize=True); return buf.getvalue(), w, h, w0, h0, 'image/jpeg', 'jpg'

def lista_moldes(D, solo, tipos):
    out = []
    base = D / 'ramas' / 'moldes'
    if not base.is_dir(): return out, 'no hay ramas/moldes (falta correr 4a2)'
    for d in sorted(x for x in base.iterdir() if x.is_dir()):
        if solo and d.name not in solo: continue
        cams = {}
        try:
            ej = json.loads((d / 'escenario.json').read_text(encoding='utf-8'))
            nombre = ej.get('nombre') or d.name
            for i, c in enumerate(ej.get('camaras_sugeridas') or [], 1):
                cams[i] = f"esc {c.get('escena', '?')} · {c.get('lente_mm', '?')} mm · {str(c.get('posicion', ''))[:120]}"
        except Exception:
            nombre = d.name
        if 'planta' in tipos and (d / 'planta.png').is_file():
            out.append((d.name, nombre, 'planta', 'Planta (vista desde arriba)', d / 'planta.png'))
        if 'cam' in tipos:
            for f in sorted(d.glob('cam_*.png'), key=_num):
                out.append((d.name, nombre, 'camara', f'Cámara {f.stem}' + (f' — {cams[_num(f)]}' if _num(f) in cams else ''), f))
        if 'luz' in tipos:
            for f in sorted(d.glob('luz_*.png'), key=_num):
                out.append((d.name, nombre, 'luz', f'Luz {f.stem}', f))
    return out, None

def lista_pintura(D, solo):
    out = []
    base = D / 'ramas' / 'imagenes' / '4a5'
    if not base.is_dir(): return out, 'no hay ramas/imagenes/4a5 (falta pintar en 4a5)'
    for f in sorted(base.glob('*.png')):
        eid = f.stem.split('__')[0]
        if solo and eid not in solo: continue
        resto = f.stem[len(eid):].lstrip('_')
        tipo = 'base' if not resto else ('vista' if re.fullmatch(r'vista\d+', resto) else 'variante')
        info = ''
        try:
            j = json.loads(f.with_suffix('.json').read_text(encoding='utf-8'))
            info = str(j.get('nombre') or j.get('escenario_nombre') or '')
        except Exception: pass
        out.append((eid, info or eid, tipo, f'{tipo.capitalize()} · {f.stem}', f))
    return out, None

def main(argv):
    if argv and argv[0] == 'galeria':   # PISTA INMI (2026-10-29): orden 70 — galería de miniaturas para n8n (todos los cubos con imágenes o videos)
        import galeria_n8n
        return galeria_n8n.main(argv[1:])
    if argv and argv[0] == 'cubo':      # PISTA INMI (2026-10-29): orden 74 — cubos 01–14 «ajustes Argon» (gratis, solo cotizan/calculan; ver paso01_cubos.py).
        import paso01_cubos             # PISTA INMI (2026-10-29): va por «ver» para no tocar paso00_cadena.py/entrada_ssh.sh durante la prueba pagada 4c2; luego, acción propia «cubos».
        return paso01_cubos.main(argv[1:])
    ap = argparse.ArgumentParser(prog='ver')
    ap.add_argument('que', choices=['moldes', 'pintura'])
    ap.add_argument('--canal', required=True)
    ap.add_argument('--capitulo', required=True)
    ap.add_argument('--solo', default='')
    ap.add_argument('--tipos', default='planta,cam')
    ap.add_argument('--ancho', type=int, default=1280)
    ap.add_argument('--formato', choices=['jpg', 'png'], default='jpg')
    a = ap.parse_args(argv)
    D = carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'caja': 'ver', 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    solo = {x for x in a.solo.split(',') if x}
    tipos = {x.strip() for x in a.tipos.split(',') if x.strip()}
    if a.que == 'moldes': lst, aviso = lista_moldes(D, solo, tipos)
    else: lst, aviso = lista_pintura(D, solo)
    imgs, total, cortadas, fallos = [], 0, [], []
    for eid, nombre, tipo, etiqueta, f in lst:
        try: data, w, h, w0, h0, mime, ext = _img(f, max(0, a.ancho), a.formato)
        except Exception as e: fallos.append(f'{f.name}: {type(e).__name__}'); continue
        if total + len(data) > TOPE_BYTES: cortadas.append(f'{eid}/{f.name}'); continue
        total += len(data)
        imgs.append({'escenario': eid, 'escenario_nombre': nombre, 'tipo': tipo, 'nombre': etiqueta,
                     'archivo': (f'{eid}__{f.stem}' if a.que == 'moldes' else f.stem) + '.' + ext, 'ruta': str(f.relative_to(D)),
                     'ancho': w, 'alto': h, 'ancho_original': w0, 'alto_original': h0, 'mime': mime,
                     'b64': base64.b64encode(data).decode()})
    esc = sorted({i['escenario'] for i in imgs})
    res = f'{len(imgs)} imágenes de {len(esc)} escenarios ({a.que})' + (f'; {len(cortadas)} no entraron por tamaño (usa --solo)' if cortadas else '') + (f'; aviso: {aviso}' if aviso else '')
    return {'ok': True, 'caja': 'ver', 'que': a.que, 'gratis': True, 'solo_lectura': True, 'carpeta': str(D), 'escenarios': esc,
            'cuantas': len(imgs), 'bytes': total, 'cortadas': cortadas, 'fallos': fallos, 'aviso': aviso, 'resumen': res, 'imagenes': imgs}
