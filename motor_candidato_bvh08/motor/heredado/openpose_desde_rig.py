"""F2 — Esqueleto OpenPose desde el rig (universal).
Interruptor: openpose.off
Lee mapa JSON por personaje (adn/mapas_openpose/mapa_openpose_<id>.json).
Si falta un hueso → punto null + aviso; no inventa. Manos/cara solo si el mapa las declara."""
from __future__ import annotations
import json, math, subprocess, shutil
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MAPAS = {}
def configurar_mapas(paths):
    global MAPAS
    MAPAS = {k: Path(v) for k,v in paths.items()}
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

# Colores OpenPose estándar (BGR→usamos RGB) por índice COCO 18
COLORES = [
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0),
    (85, 255, 0), (0, 255, 0), (0, 255, 85), (0, 255, 170), (0, 255, 255),
    (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255), (170, 0, 255),
    (255, 0, 255), (255, 0, 170), (255, 0, 85),
]
# Pares de huesos COCO 18
PARES = [(1, 2), (1, 5), (2, 3), (3, 4), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10),
         (1, 11), (11, 12), (12, 13), (1, 0), (0, 14), (14, 16), (0, 15), (15, 17)]

def activo():
    import movimiento_natural as MN
    return MN.activo("openpose")

def cargar_mapa(personaje_id: str):
    p = MAPAS.get(personaje_id)
    if p is None:return None, ["FALTA mapa entregado por paquete/ADN"]
    if not p.exists():
        return None, [f"sin mapa OpenPose para '{personaje_id}' ({p.name})"]
    return json.loads(p.read_text()), []

def _co_hueso(arm, nombre, parte):
    pb = arm.pose.bones.get(nombre)
    if pb is None:
        return None
    from mathutils import Vector
    M = arm.matrix_world
    if parte == "tail":
        return M @ pb.tail
    if parte == "head":
        return M @ pb.head
    if parte == "mid":
        return M @ ((pb.head + pb.tail) * 0.5)
    return M @ pb.head

def proyectar_personaje(sc, cam, arm, mapa, res_xy):
    """Devuelve lista de puntos {i, nombre, u, v, visible} y avisos."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    avisos = []
    pts = []
    puntos = mapa.get("puntos") or {}
    # ordenar por índice numérico del nombre "0_nose"
    items = []
    for k, spec in puntos.items():
        try:
            idx = int(k.split("_", 1)[0])
        except Exception:
            idx = len(items)
        items.append((idx, k, spec))
    items.sort()
    for idx, k, spec in items:
        if spec is None:
            pts.append({"i": idx, "nombre": k, "u": None, "v": None, "visible": False, "omitido": True})
            avisos.append(f"{k}: omitido (null en mapa)")
            continue
        h, parte = spec.get("hueso"), spec.get("parte", "head")
        if h not in arm.pose.bones:
            pts.append({"i": idx, "nombre": k, "u": None, "v": None, "visible": False, "omitido": True})
            avisos.append(f"{k}: hueso '{h}' no existe en el rig")
            continue
        co = _co_hueso(arm, h, parte)
        p = w2c(sc, cam, co)
        vis = (p.z > 0) and (0.0 <= p.x <= 1.0) and (0.0 <= p.y <= 1.0)
        pts.append({"i": idx, "nombre": k, "u": round(float(p.x), 5), "v": round(float(p.y), 5),
                    "visible": bool(vis), "omitido": False, "detras_camara": bool(p.z <= 0)})
    if not mapa.get("manos"):
        avisos.append("manos omitidas (mapa sin manos)")
    if not mapa.get("cara"):
        avisos.append("cara omitida salvo puntos declarados (mapa sin cara)")
    return pts, avisos

def pintar_png(pts, res_xy, path: Path, fondo=(0, 0, 0)):
    from PIL import Image, ImageDraw
    w, h = res_xy
    im = Image.new("RGB", (w, h), fondo)
    dr = ImageDraw.Draw(im)
    by_i = {p["i"]: p for p in pts}
    for a, b in PARES:
        pa, pb = by_i.get(a), by_i.get(b)
        if not pa or not pb: continue
        if pa.get("omitido") or pb.get("omitido"): continue
        if not pa.get("visible") or not pb.get("visible"): continue
        xa, ya = pa["u"] * w, (1 - pa["v"]) * h
        xb, yb = pb["u"] * w, (1 - pb["v"]) * h
        col = COLORES[a % len(COLORES)]
        dr.line([(xa, ya), (xb, yb)], fill=col, width=max(2, w // 256))
    for p in pts:
        if p.get("omitido") or not p.get("visible"): continue
        x, y = p["u"] * w, (1 - p["v"]) * h
        r = max(3, w // 128)
        col = COLORES[p["i"] % len(COLORES)]
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path

def exportar_cuadros(sc, cam, personajes, out_dir: Path, frames, res_xy=(1280, 720)):
    """personajes: dict id -> armature object.
    Escribe openpose/json/fXXXX.json y openpose/png/fXXXX.png (+ por personaje)."""
    import bpy
    out_dir = Path(out_dir)
    jdir = out_dir / "openpose" / "json"
    pdir = out_dir / "openpose" / "png"
    jdir.mkdir(parents=True, exist_ok=True)
    pdir.mkdir(parents=True, exist_ok=True)
    avisos_global = []
    mapas = {}
    for pid in personajes:
        m, av = cargar_mapa(pid)
        mapas[pid] = m
        avisos_global.extend([f"{pid}: {a}" for a in av])
        if m is None:
            avisos_global.append(f"{pid}: sin mapa, se omite")
    resumen = []
    for f in frames:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        frame_data = {"frame": f, "personajes": {}}
        # imagen combinada de todos
        todos_pts = []
        for pid, arm in personajes.items():
            m = mapas.get(pid)
            if not m:
                continue
            pts, av = proyectar_personaje(sc, cam, arm, m, res_xy)
            frame_data["personajes"][pid] = {"puntos": pts, "avisos": av}
            todos_pts.extend(pts)
            pintar_png(pts, res_xy, pdir / f"{pid}_f{f:04d}.png")
        (jdir / f"f{f:04d}.json").write_text(json.dumps(frame_data, ensure_ascii=False, indent=1))
        pintar_png(todos_pts, res_xy, pdir / f"f{f:04d}.png")
        resumen.append({"frame": f, "n_personajes": len(frame_data["personajes"])})
    meta = {"avisos": sorted(set(avisos_global)), "frames": resumen, "res": list(res_xy)}
    (out_dir / "openpose" / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta

def video_openpose(out_dir: Path, fps=24):
    out_dir = Path(out_dir)
    pngs = sorted((out_dir / "openpose" / "png").glob("f*.png"))
    if not pngs:
        return False
    mp4 = out_dir / "openpose" / "video_openpose.mp4"
    lst = mp4.with_suffix(".txt")
    with open(lst, "w") as fh:
        for p in pngs:
            fh.write(f"file '{p}'\n")
            fh.write(f"duration {1.0/fps}\n")
        fh.write(f"file '{pngs[-1]}'\n")
    r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-vf", f"fps={fps},format=yuv420p", "-r", str(fps), str(mp4)],
                       capture_output=True, text=True)
    return r.returncode == 0
