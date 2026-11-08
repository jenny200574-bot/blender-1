"""F3a — Revisor que usa mapas de profundidad (informativo, no bloquea).
Interruptor: revisor_mapas.off
Detecta flotación aproximada (pie vs piso en depth) y choques aproximados (solapes de profundidad).
Sin topes de fallo hasta que Ricardo los fije."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

def activo():
    import movimiento_natural as MN
    return MN.activo("revisor_mapas")

def _cargar_depth_png(path: Path):
    from PIL import Image
    im = Image.open(path).convert("L")
    return np.asarray(im, dtype=np.float32) / 255.0

def _cargar_normal_png(path: Path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    # de vuelta a [-1,1]
    return arr * 2.0 - 1.0

def analizar_frame(depth, normal=None, openpose_pts=None, umbral_flotar=0.04, umbral_choque=0.02):
    """depth: array HxW en 0..1 (cerca=0 o cerca=bajo según meta; aquí asumimos normalización 0 cerca / 1 lejos
    tras nuestra conversión percentil donde 0=lo cercano).
    openpose_pts: lista de puntos con u,v de tobillos para muestrear depth del pie.
    Devuelve dict informativo."""
    h, w = depth.shape[:2]
    info = {"flotar_candidato": False, "choque_candidato": False, "detalle": {}}
    # Flotar: si hay tobillos, comparar depth del tobillo vs depth del piso debajo (píxel un poco más abajo en imagen)
    if openpose_pts:
        tobillos = [p for p in openpose_pts if p.get("nombre", "").endswith("ankle") and p.get("visible")]
        flot = []
        for p in tobillos:
            x = int(np.clip(p["u"] * (w - 1), 0, w - 1))
            y = int(np.clip((1 - p["v"]) * (h - 1), 0, h - 1))
            d_pie = float(depth[y, x])
            # piso: mirar unos píxeles más abajo (hacia el borde inferior) en la misma x
            y2 = min(h - 1, y + max(3, h // 40))
            d_piso = float(depth[y2, x])
            # si el pie está claramente más "lejos" (mayor depth normalizado) que el piso bajo él → sospecha flotar
            # (en nuestra PNG: 0=cerca percentil lo, 1=lejos). Pie flotando: depth pie < depth piso (más cerca cámara que el suelo proyectado) puede indicar hueco;
            # usamos diferencia absoluta grande como señal débil.
            delta = d_pie - d_piso
            flot.append({"tobillo": p["nombre"], "d_pie": round(d_pie, 4), "d_piso": round(d_piso, 4), "delta": round(delta, 4)})
        info["detalle"]["tobillos"] = flot
        # señal débil: delta muy negativo (pie mucho más cerca que la franja inferior) con umbral
        if any(t["delta"] < -umbral_flotar for t in flot):
            info["flotar_candidato"] = True
    # Choque aproximado: laplaciano de depth alto en zona de personaje (gradientes raros) — señal suave
    gy, gx = np.gradient(depth)
    grad = np.hypot(gx, gy)
    p99 = float(np.percentile(grad, 99))
    info["detalle"]["grad_depth_p99"] = round(p99, 4)
    if p99 > 0.35:  # umbral blando informativo
        info["choque_candidato"] = True
    if normal is not None:
        # normal Z media: si hay muchas normales horizontales "imposibles" en zona media — solo meta
        nz = normal[..., 2]
        info["detalle"]["normal_z_media"] = round(float(nz.mean()), 4)
    return info

def revisar_carpeta(out_dir: Path, frames, openpose_json_dir: Path | None = None):
    out_dir = Path(out_dir)
    ddir = out_dir / "depth"
    ndir = out_dir / "normal"
    res = {"activo": True, "bloquea": False, "nota": "informativo; Ricardo fijará topes", "frames": [],
           "flotar_n": 0, "choque_n": 0}
    for f in frames:
        dp = ddir / f"f{f:04d}.png"
        if not dp.exists():
            res["frames"].append({"frame": f, "ok": False, "error": "sin depth"})
            continue
        depth = _cargar_depth_png(dp)
        normal = _cargar_normal_png(ndir / f"f{f:04d}.png") if (ndir / f"f{f:04d}.png").exists() else None
        pts = None
        if openpose_json_dir:
            jf = Path(openpose_json_dir) / f"f{f:04d}.json"
            if jf.exists():
                data = json.loads(jf.read_text())
                pts = []
                for pj in (data.get("personajes") or {}).values():
                    pts.extend(pj.get("puntos") or [])
        info = analizar_frame(depth, normal, pts)
        info["frame"] = f
        info["ok"] = True
        res["frames"].append(info)
        res["flotar_n"] += int(info["flotar_candidato"])
        res["choque_n"] += int(info["choque_candidato"])
    (out_dir / "revisor_mapas.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return res
