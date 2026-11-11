"""componer_revision (python3 + Pillow) — video de revisión GRANDE y claro (1920x1080) por cuadro:
  izquierda arriba : lo que ve la cámara del storyboard (render final GPU)
  derecha arriba   : vista amplia fija de todo el set (todos los personajes)
  derecha centro   : planta cenital (rutas A*+RVO2, separación, acople)
  derecha abajo    : [t1066u] vista LATERAL fija (si se pasa --lateral)
  izquierda abajo  : panel de texto: escena, cuadro, segundo, viñeta, objetivo, ángulo/movimiento del SB, modo de cada personaje,
                     resultado de la revisión.
Uso: python3 componer_revision.py --corrida DIR --final DIR --amplia DIR --planta DIR --out DIR [--paso 1]"""
import json, os, argparse, sys, traceback
def _salir_por_excepcion(typ, val, tb):
    print(''.join(traceback.format_exception(typ, val, tb)), flush=True)
    sys.exit(1)
sys.excepthook = _salir_por_excepcion
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser()
for k in ('--corrida', '--final', '--amplia', '--planta', '--out'): ap.add_argument(k, required=True)
ap.add_argument('--paso', type=int, default=1); ap.add_argument('--lateral', default='')
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
R = json.load(open(f'{a.corrida}/reporte_motor.json')); PL = json.load(open(f'{a.corrida}/plan.json')); E = json.load(open(f'{a.corrida}/entrada_motor.json'))
def _titulo(E):
    """título del video de revisión desde la entrada (canal y capítulo de la cadena), sin canal fijo en el código."""
    cad = str(E.get('cadena') or '').rstrip('/'); cap = os.path.basename(cad); canal = os.path.basename(os.path.dirname(cad))
    nom = canal
    for f in (f'/opt/myia-taller-n8n/cajas/cubo_fijo/canales/{canal}.json',):
        try: nom = json.load(open(f)).get('nombre') or canal
        except Exception: pass
    capn = cap.split('_')[0] if cap.startswith('cap') else cap
    return f"{nom} · {capn}" if nom or capn else 'revisión'
TITULO = _titulo(E)
tomas = R['pasos']['5_camara']['tomas']; rev = R['pasos']['6_revision']; N = R['N']; FPS = R['fps']
def fuente(s):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, s)
    try: return ImageFont.load_default(size=s)
    except TypeError: return ImageFont.load_default()
F1, F2, F3 = fuente(34), fuente(24), fuente(20)
corto = {pid: pid.split('-')[1] if pid.startswith('ch-') else pid for pid in PL['personajes']}
for f in range(1, N + 1, a.paso):
    C = Image.new('RGB', (1920, 1080), (18, 18, 22)); d = ImageDraw.Draw(C)
    def pegar(dirr, box, titulo):
        p = f'{dirr}/f{f:05d}.png'
        if os.path.exists(p):
            im = Image.open(p).convert('RGB').resize((box[2], box[3])); C.paste(im, (box[0], box[1]))
        d.rectangle([box[0], box[1], box[0] + box[2] - 1, box[1] + box[3] - 1], outline=(90, 90, 100), width=2)
        d.rectangle([box[0], box[1], box[0] + len(titulo) * 12 + 16, box[1] + 30], fill=(0, 0, 0)); d.text((box[0] + 8, box[1] + 3), titulo, font=F3, fill=(255, 230, 80))
    pegar(a.final, (0, 0, 1280, 720), 'CÁMARA DEL STORYBOARD (render final GPU)')
    pegar(a.amplia, (1280, 0, 640, 360), 'VISTA AMPLIA DE REVISIÓN')
    pegar(a.planta, (1280, 360, 640, 360), 'PLANTA (rutas A*+RVO2)')
    if a.lateral: pegar(a.lateral, (1280, 720, 640, 360), 'VISTA LATERAL DE REVISIÓN')
    t = next((x for x in tomas if x['frame_ini'] <= f <= x['frame_fin']), None)
    y = 735
    d.text((20, y), f"{TITULO} · escena {E['escena']} · cuadro {f}/{N} · {((f - 1) / FPS):5.2f} s", font=F1, fill=(255, 255, 255)); y += 48
    if t:
        d.text((20, y), f"Viñeta {t['vineta']}  objetivo {corto.get(t['objetivo'], t['objetivo'])}  ángulo {t['angulo']}  lado {t['lado']}  mov {'/'.join(str(m) for m in t['movimientos'])}  altura_m {t['altura_m']}", font=F2, fill=(160, 220, 255)); y += 36
        if t.get('sb3d'):
            s3 = t['sb3d']; d.text((20, y), f"SB después del 3D: plano {t.get('plano')} · lente {t.get('lente_mm')} mm · {s3.get('origen')} · validación {s3.get('estado')}", font=F3,
                                   fill=(140, 255, 160) if s3.get('estado') == 'OK' else (255, 170, 120)); y += 30
    x = 20
    for pid, fr in PL['personajes'].items():
        if x + 300 > 1280 and a.lateral: x = 20; y += 34
        m = fr[min(len(fr), f) - 1][4]; col = {'caminar': (120, 255, 120), 'girar': (255, 200, 90), 'oculto': (120, 120, 120), 'acoplado': (200, 160, 255)}.get(m, (230, 230, 230))
        ok = rev['personajes'].get(pid, {}).get('ok'); txt = f"{corto[pid]}: {m}{'' if ok is None else (' ✓' if ok else ' ✗')}"
        d.text((x, y), txt, font=F2, fill=col); x += 300
        if x > (1000 if a.lateral else 1700): x = 20; y += 34
    y += 40
    d.text((20, y), (f"Revisión gate: {'APROBADA' if rev.get('ok') else 'CON OBSERVACIONES (ver reporte_motor.json)'}" + ('' if a.lateral else ' · moldes de fábrica sin modificar · motor no crea geometría')), font=F3, fill=(255, 255, 255) if rev.get('ok') else (255, 170, 120))
    C.save(f'{a.out}/f{f:05d}.png')
print('RESULT_COMPONER', json.dumps({"cuadros": len(range(1, N + 1, a.paso))}))
