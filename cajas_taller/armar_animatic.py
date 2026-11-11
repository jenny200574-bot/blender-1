# -*- coding: utf-8 -*-
"""MYIA · Taller n8n · animatic gratis (sin IA) — programa de imágenes (31-oct-2026, America/Bogota).

Port de programa_imagenes/animatic/armar_animatic.py.
GRATIS, sin red, sin IA. Requiere ffmpeg en el PATH del host (n8ntaller).

Uso (entrada restringida n8ntaller — sin barras en los args):
  paso00_cadena animatic armar --canal CID --capitulo N [--escena 10] [--sin-caption]
  paso00_cadena animatic leer  --canal CID --capitulo N [--escena 10]

Convención en disco (por capítulo):
  <cap>/cubos/animatic/esc_<N>/plan.json     (opcional; tomas con imagen relativa o absoluta)
  <cap>/cubos/animatic/esc_<N>/*.png|jpg…    (pinturas ordenadas si no hay plan)
  <cap>/cubos/animatic/esc_<N>/entrada_star.json  (opcional; tomas[].t de Star)
  Salida: <cap>/cubos/animatic/esc_<N>/ANIMATIC.mp4

Duraciones: de plan.json; si faltan, de Star entrada.json → tomas[].t (fin-inicio).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 1920, 1080
DEFAULT_FPS = 24
DEFAULT_XFADE = 0.4
DEFAULT_ZOOM = 1.05  # max 5% push-in
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TRABAJO = Path("/opt/myia-taller-n8n/trabajo/paso00_cadena")
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def _ffprobe_dur(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def load_plan(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tomas" in data:
        items = data["tomas"]
    elif isinstance(data, list):
        items = data
    else:
        raise SystemExit(f"JSON inválido en {path}: se espera lista o {{tomas:[...]}}")
    base = path.parent
    out = []
    for i, it in enumerate(items):
        img = it.get("imagen") or it.get("image")
        seg = it.get("segundos")
        if seg is None:
            seg = it.get("duration") or it.get("duracion")
        etiq = it.get("etiqueta") or it.get("label") or f"toma {i+1}"
        if not img or seg is None:
            raise SystemExit(f"Item {i} necesita imagen y segundos: {it}")
        p = Path(img)
        if not p.is_file():
            p2 = base / img
            if p2.is_file():
                p = p2
            else:
                raise SystemExit(f"No existe la imagen: {img}")
        out.append({"imagen": str(p.resolve()), "segundos": float(seg), "etiqueta": str(etiq)})
    if not out:
        raise SystemExit("Plan vacío")
    return out


def make_clip(
    imagen: str,
    segundos: float,
    etiqueta: str,
    out_path: Path,
    fps: int,
    zoom_end: float,
    with_caption: bool,
) -> None:
    n_frames = max(1, int(round(segundos * fps)))
    if n_frames == 1:
        z_expr = f"min({zoom_end},1)"
    else:
        z_expr = f"min({zoom_end},1+({zoom_end}-1)*on/{n_frames - 1})"
    vf_parts = [
        f"scale={W}:{H}:force_original_aspect_ratio=increase",
        f"crop={W}:{H}",
        (
            f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={W}x{H}:fps={fps}"
        ),
    ]
    if with_caption and etiqueta:
        safe = (
            etiqueta.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\%")
        )
        font = FONT if Path(FONT).is_file() else ""
        font_arg = f"fontfile={font}:" if font else ""
        vf_parts.append(
            f"drawtext={font_arg}text='{safe}'"
            f":fontsize=28:fontcolor=white@0.92"
            f":borderw=2:bordercolor=black@0.55"
            f":x=36:y=h-th-28"
        )
    vf = ",".join(vf_parts)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", imagen,
        "-vf", vf,
        "-frames:v", str(n_frames),
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_path),
    ]
    run(cmd)


def concat_xfade(clips: list[Path], durations: list[float], out_path: Path, xfade: float, fps: int) -> float:
    if len(clips) == 1:
        shutil.copy(clips[0], out_path)
        return durations[0]
    inputs = []
    for c in clips:
        inputs.extend(["-i", str(c)])
    filters = []
    offset = durations[0] - xfade
    if offset < 0:
        raise SystemExit(f"xfade {xfade}s >= duración de la primera toma {durations[0]}s")
    filters.append(
        f"[0:v][1:v]xfade=transition=fade:duration={xfade}:offset={offset:.6f}[v01]"
    )
    last = "v01"
    for i in range(2, len(clips)):
        acc = sum(durations[:i]) - (i - 1) * xfade
        offset_i = acc - xfade
        if offset_i < 0:
            raise SystemExit(f"xfade {xfade}s demasiado largo para toma {i}")
        out_lab = f"v0{i}"
        filters.append(
            f"[{last}][{i}:v]xfade=transition=fade:duration={xfade}:offset={offset_i:.6f}[{out_lab}]"
        )
        last = out_lab
    total = sum(durations) - (len(clips) - 1) * xfade
    filter_complex = ";".join(filters)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{last}]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-movflags", "+faststart",
        "-an",
        str(out_path),
    ]
    run(cmd)
    return total


def build(
    plan: list[dict],
    salida: Path,
    fps: int = DEFAULT_FPS,
    xfade: float = DEFAULT_XFADE,
    zoom_end: float = DEFAULT_ZOOM,
    with_caption: bool = True,
) -> float:
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="animatic_") as tmp:
        tmp_p = Path(tmp)
        clips = []
        durs = []
        for i, it in enumerate(plan):
            clip = tmp_p / f"clip_{i:02d}.mp4"
            make_clip(
                it["imagen"],
                it["segundos"],
                it["etiqueta"],
                clip,
                fps=fps,
                zoom_end=zoom_end,
                with_caption=with_caption,
            )
            clips.append(clip)
            durs.append(it["segundos"])
        total = concat_xfade(clips, durs, salida, xfade=xfade, fps=fps)
    return total


def contact_sheet(plan: list[dict], out_png: Path, cell_h: int = 360) -> None:
    from PIL import Image, ImageDraw, ImageFont
    imgs = []
    for it in plan:
        im = Image.open(it["imagen"]).convert("RGB")
        ratio = cell_h / im.height
        w = int(round(im.width * ratio))
        imgs.append(im.resize((w, cell_h), Image.Resampling.LANCZOS))
    gap = 8
    label_h = 36
    total_w = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
    sheet = Image.new("RGB", (total_w, cell_h + label_h), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(FONT, 22)
    except Exception:
        font = ImageFont.load_default()
    x = 0
    for im, it in zip(imgs, plan):
        sheet.paste(im, (x, 0))
        draw.text((x + 8, cell_h + 6), it["etiqueta"], fill=(240, 240, 240), font=font)
        x += im.width + gap
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)


# ---- taller helpers ----

def _cap_dir(canal: str, capitulo: str) -> Path:
    root = TRABAJO / canal
    if not root.is_dir():
        raise FileNotFoundError(f"no está el canal en trabajo: {root}")
    try:
        n = int(str(capitulo).lstrip("0") or "0")
    except ValueError:
        n = 1
    pref = f"cap{n:02d}_"
    cands = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith(pref))
    if not cands:
        # also accept exact cap01
        cands = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith(f"cap{capitulo}"))
    if not cands:
        raise FileNotFoundError(f"no hay carpeta de capítulo {capitulo} bajo {root}")
    return cands[0]


def _esc_dir(cap: Path, escena: int | str) -> Path:
    try:
        n = int(str(escena))
    except ValueError:
        n = escena
    return cap / "cubos" / "animatic" / f"esc_{n}"


def _star_durations(cap: Path, esc_dir: Path, escena: int, n_needed: int) -> list[float]:
    """Leer tomas[].t de Star; devolver duraciones (fin-inicio) para las primeras n_needed tomas."""
    candidatos = [
        esc_dir / "entrada_star.json",
        esc_dir / "entrada.json",
        cap / "cubos" / "02" / "molde_o109" / f"esc_{escena}" / "entrada.json",
        cap / "cubos" / "02" / "video_o112" / f"esc_{escena}" / "entrada.json",
    ]
    # búsqueda amplia bajo el cap
    for p in cap.rglob("entrada.json"):
        if f"esc_{escena}" in str(p) or f"/esc{escena}/" in str(p).replace("_", ""):
            candidatos.append(p)
    seen = set()
    for p in candidatos:
        rp = str(p)
        if rp in seen or not p.is_file():
            continue
        seen.add(rp)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        tomas = data.get("tomas") if isinstance(data, dict) else None
        if not isinstance(tomas, list) or not tomas:
            continue
        durs = []
        for t in tomas:
            if not isinstance(t, dict):
                continue
            win = t.get("t")
            if isinstance(win, (list, tuple)) and len(win) >= 2:
                durs.append(float(win[1]) - float(win[0]))
            elif "segundos" in t:
                durs.append(float(t["segundos"]))
        if len(durs) >= n_needed:
            return durs[:n_needed]
        if durs:
            # pad with last
            while len(durs) < n_needed:
                durs.append(durs[-1])
            return durs
    return []


def _list_pinturas(esc_dir: Path) -> list[Path]:
    skip_pref = ("CONTACTO", "ANIMATIC", "plan_usado")
    files = []
    for p in esc_dir.iterdir():
        if not p.is_file() or p.suffix.lower() not in IMG_EXT:
            continue
        if p.name.upper().startswith(skip_pref):
            continue
        # solo pinturas con id numérico al inicio (179_....png)
        if not re.match(r"^\d+", p.name):
            continue
        files.append(p)
    def key(p: Path):
        m = re.match(r"^(\d+)", p.name)
        return (0, int(m.group(1)), p.name) if m else (1, 0, p.name)
    return sorted(files, key=key)


def _plan_desde_carpeta(cap: Path, esc_dir: Path, escena: int) -> tuple[list[dict], list[str]]:
    avisos = []
    plan_path = esc_dir / "plan.json"
    if plan_path.is_file():
        return load_plan(plan_path), avisos
    pinturas = _list_pinturas(esc_dir)
    if not pinturas:
        raise FileNotFoundError(f"sin plan.json ni pinturas en {esc_dir}")
    durs = _star_durations(cap, esc_dir, escena, len(pinturas))
    if not durs:
        avisos.append("sin Star entrada.json; se usan 5 s por toma")
        durs = [5.0] * len(pinturas)
    elif len(durs) < len(pinturas):
        avisos.append(f"Star trae {len(durs)} tomas; sobran pinturas")
        while len(durs) < len(pinturas):
            durs.append(durs[-1])
    plan = []
    for i, (img, seg) in enumerate(zip(pinturas, durs)):
        # etiqueta: intenta número de pintura del nombre
        m = re.match(r"^(\d+)", img.name)
        num = m.group(1) if m else str(i + 1)
        plan.append({
            "imagen": str(img.resolve()),
            "segundos": float(seg),
            "etiqueta": f"toma {i+1} · pintura {num}",
        })
    return plan, avisos


def _ffmpeg_ok() -> tuple[bool, str]:
    p = shutil.which("ffmpeg")
    if not p:
        return False, "ffmpeg no está en PATH"
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        ver = (r.stdout or "").splitlines()[0] if r.stdout else p
        return True, ver[:120]
    except Exception as e:
        return False, f"ffmpeg falla: {type(e).__name__}"


def armar(canal: str, capitulo: str, escena: str | None, sin_caption: bool) -> dict:
    ok_ff, ff_info = _ffmpeg_ok()
    if not ok_ff:
        return {"ok": False, "accion": "animatic armar", "error": ff_info, "usd": 0}
    try:
        cap = _cap_dir(canal, capitulo)
    except FileNotFoundError as e:
        return {"ok": False, "accion": "animatic armar", "error": str(e), "usd": 0}

    if escena is not None:
        escenas = [int(escena)]
    else:
        root = cap / "cubos" / "animatic"
        if not root.is_dir():
            return {
                "ok": True, "accion": "animatic armar", "canal": canal, "capitulo": capitulo,
                "usd": 0, "animatics": [], "avisos": [f"no hay carpeta {root}; nada que armar"],
                "resumen": "sin escenas listas",
            }
        escenas = []
        for p in sorted(root.iterdir()):
            m = re.match(r"^esc_(\d+)$", p.name)
            if m and p.is_dir():
                escenas.append(int(m.group(1)))
        if not escenas:
            return {
                "ok": True, "accion": "animatic armar", "canal": canal, "capitulo": capitulo,
                "usd": 0, "animatics": [], "avisos": ["cubos/animatic sin esc_N"],
                "resumen": "sin escenas listas",
            }

    resultados = []
    avisos_g = [f"ffmpeg: {ff_info}"]
    for esc in escenas:
        esc_dir = _esc_dir(cap, esc)
        esc_dir.mkdir(parents=True, exist_ok=True)
        try:
            plan, avisos = _plan_desde_carpeta(cap, esc_dir, esc)
        except Exception as e:
            avisos_g.append(f"esc_{esc}: {type(e).__name__}: {e}")
            resultados.append({"escena": esc, "ok": False, "error": str(e)[:300]})
            continue
        salida = esc_dir / "ANIMATIC.mp4"
        try:
            total = build(
                plan, salida,
                fps=DEFAULT_FPS, xfade=DEFAULT_XFADE, zoom_end=DEFAULT_ZOOM,
                with_caption=not sin_caption,
            )
            # contact sheet gratis
            try:
                contact_sheet(plan, esc_dir / "CONTACTO.png")
            except Exception as e:
                avisos.append(f"contact sheet: {type(e).__name__}")
            # guardar plan usado
            plan_out = {
                "escena": f"esc_{esc}",
                "fuente_duraciones": "plan.json o Star tomas[].t",
                "tomas": [
                    {"imagen": Path(t["imagen"]).name, "segundos": t["segundos"], "etiqueta": t["etiqueta"]}
                    for t in plan
                ],
            }
            (esc_dir / "plan_usado.json").write_text(
                json.dumps(plan_out, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            real = _ffprobe_dur(salida) if salida.is_file() else total
            resultados.append({
                "escena": esc,
                "ok": True,
                "mp4": str(salida),
                "bytes": salida.stat().st_size if salida.is_file() else 0,
                "tomas": len(plan),
                "duracion_plan_s": round(total, 3),
                "duracion_ffprobe_s": round(real, 3),
                "avisos": avisos,
            })
        except Exception as e:
            avisos_g.append(f"esc_{esc} build: {type(e).__name__}: {e}")
            resultados.append({"escena": esc, "ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"})

    ok_any = any(r.get("ok") for r in resultados)
    # si se pidió una escena concreta y falló → ok False; si loop vacío de fallos con --escena
    if escena is not None and resultados and not resultados[0].get("ok"):
        return {
            "ok": False, "accion": "animatic armar", "canal": canal, "capitulo": capitulo,
            "escena": int(escena), "usd": 0, "animatics": resultados, "avisos": avisos_g,
            "error": resultados[0].get("error") or "falló el animatic",
            "resumen": "falló",
        }
    return {
        "ok": True if (ok_any or not resultados) else False,
        "accion": "animatic armar",
        "canal": canal,
        "capitulo": capitulo,
        "usd": 0,
        "animatics": resultados,
        "avisos": avisos_g,
        "resumen": f"{sum(1 for r in resultados if r.get('ok'))} animatic(s) listos",
        "ffmpeg": ff_info,
    }


def leer(canal: str, capitulo: str, escena: str | None) -> dict:
    try:
        cap = _cap_dir(canal, capitulo)
    except FileNotFoundError as e:
        return {"ok": False, "accion": "animatic leer", "error": str(e), "usd": 0}
    root = cap / "cubos" / "animatic"
    items = []
    if not root.is_dir():
        return {
            "ok": True, "accion": "animatic leer", "canal": canal, "capitulo": capitulo,
            "usd": 0, "animatics": [], "avisos": [f"no existe {root}"],
        }
    dirs = []
    if escena is not None:
        dirs = [_esc_dir(cap, int(escena))]
    else:
        dirs = sorted(p for p in root.iterdir() if p.is_dir() and re.match(r"^esc_\d+$", p.name))
    for d in dirs:
        mp4 = d / "ANIMATIC.mp4"
        row = {
            "escena": d.name,
            "dir": str(d),
            "mp4_existe": mp4.is_file(),
            "mp4": str(mp4) if mp4.is_file() else "",
            "bytes": mp4.stat().st_size if mp4.is_file() else 0,
            "pinturas": [p.name for p in _list_pinturas(d)],
            "plan_json": (d / "plan.json").is_file(),
        }
        if mp4.is_file():
            try:
                row["duracion_ffprobe_s"] = round(_ffprobe_dur(mp4), 3)
            except Exception:
                pass
        items.append(row)
    return {
        "ok": True, "accion": "animatic leer", "canal": canal, "capitulo": capitulo,
        "usd": 0, "animatics": items, "resumen": f"{sum(1 for i in items if i['mp4_existe'])} MP4 en disco",
    }


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    ap = argparse.ArgumentParser(prog="animatic")
    ap.add_argument("accion", choices=["armar", "leer"])
    ap.add_argument("--canal", required=True)
    ap.add_argument("--capitulo", required=True)
    ap.add_argument("--escena", default=None, help="número de escena (ej. 10); si falta, todas las esc_N listas")
    ap.add_argument("--sin-caption", action="store_true")
    a = ap.parse_args(argv)
    if a.accion == "leer":
        return leer(a.canal, a.capitulo, a.escena)
    return armar(a.canal, a.capitulo, a.escena, a.sin_caption)


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if r.get("ok") else 1)
