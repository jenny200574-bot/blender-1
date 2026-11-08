"""F1: pases Depth / Normal / Mist por cuadro (EEVEE Blender 5.2).

Interruptor: motor/pases_mapas.off
Si existe el .off, activo()=False y el render Combined es exactamente como antes.

Cuando está activo, el render escribe OPEN_EXR_MULTILAYER (Combined+Depth+Normal+Mist)
por cuadro y luego se extraen PNG + MP4 24fps yuv420p.
"""
from __future__ import annotations

from pathlib import Path

AQUI = Path(__file__).resolve().parent


def activo() -> bool:
    import movimiento_natural as MN
    return MN.activo("pases_mapas")


def configurar(scene, out_dir: Path) -> Path:
    """Activa pases Z/Normal/Mist y arma File Output EXR multilayer (Blender 5.2 API).

    Devuelve el directorio de EXR. El caller debe fijar `fo.file_name` por cuadro
    vía `set_frame_name(scene, frame)` o actualizar scene["_pases_fo"].file_name.
    """
    import bpy
    out_dir = Path(out_dir)
    exr_dir = out_dir / "exr"
    exr_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("depth", "normal", "mist", "combined"):
        (out_dir / sub).mkdir(exist_ok=True)

    vl = scene.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_normal = True
    vl.use_pass_mist = True

    if scene.world is not None and hasattr(scene.world, "mist_settings"):
        ms = scene.world.mist_settings
        ms.use_mist = True
        ms.start = 0.5
        ms.depth = 40.0

    # Blender 5: compositing_node_group + File Output solo OPEN_EXR_MULTILAYER
    tree = scene.compositing_node_group
    if tree is None:
        tree = bpy.data.node_groups.new("MYIA_PasesComp", "CompositorNodeTree")
        scene.compositing_node_group = tree
    tree.nodes.clear()
    # limpia interface de salidas previas
    try:
        for item in list(tree.interface.items_tree):
            tree.interface.remove(item)
    except Exception:
        pass

    rl = tree.nodes.new("CompositorNodeRLayers")
    fo = tree.nodes.new("CompositorNodeOutputFile")
    fo.directory = str(exr_dir) + "/"
    fo.format.file_format = "OPEN_EXR_MULTILAYER"
    fo.format.color_depth = "32"
    try:
        fo.format.exr_codec = "ZIP"
    except Exception:
        pass
    fo.file_name = "f0001"
    items = fo.file_output_items
    items.clear()
    items.new(socket_type="RGBA", name="Image")
    items.new(socket_type="FLOAT", name="Depth")
    items.new(socket_type="VECTOR", name="Normal")
    items.new(socket_type="FLOAT", name="Mist")
    links = tree.links
    for nm in ("Image", "Depth", "Normal", "Mist"):
        s, d = rl.outputs.get(nm), fo.inputs.get(nm)
        if s and d:
            links.new(s, d)
    # salida del grupo (requerida en Blender 5)
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    go = tree.nodes.new("NodeGroupOutput")
    if rl.outputs.get("Image") and go.inputs:
        links.new(rl.outputs["Image"], go.inputs[0])

    scene.render.use_compositing = True
    scene["_pases_fo"] = fo.name  # referencia por nombre del nodo
    scene["_pases_tree"] = tree.name
    return exr_dir


def set_frame_name(scene, frame: int) -> None:
    """Actualiza el nombre del EXR del File Output para este cuadro."""
    import bpy
    tname = scene.get("_pases_tree")
    foname = scene.get("_pases_fo")
    if not tname or not foname:
        return
    tree = bpy.data.node_groups.get(tname)
    if not tree:
        return
    fo = tree.nodes.get(foname)
    if fo is not None:
        fo.file_name = f"f{int(frame):04d}"



def restaurar_png(scene) -> None:
    """Tras los pases, deja el scene listo para PNG Combined (por si hace falta)."""
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"


def _norm_depth(arr, lo=None, hi=None):
    import numpy as np
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 3:
        a = a[..., 0]
    # Filtrar infinitos / valores absurdos de EEVEE Z
    finite = np.isfinite(a) & (a > 0) & (a < 1e6)
    if not finite.any():
        return np.zeros_like(a, dtype=np.uint8)
    vals = a[finite]
    if lo is None:
        lo = float(np.percentile(vals, 2))
    if hi is None:
        hi = float(np.percentile(vals, 98))
    if hi <= lo:
        hi = lo + 1.0
    out = np.zeros_like(a, dtype=np.float32)
    out[finite] = (a[finite] - lo) / (hi - lo)
    out = np.clip(out, 0, 1)
    # cerca = claro
    out = 1.0 - out
    return (out * 255).astype("uint8"), float(lo), float(hi)


def _norm_normal(arr):
    import numpy as np
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 2:
        a = np.stack([a, a, a], axis=-1)
    if a.shape[-1] > 3:
        a = a[..., :3]
    # Blender normals ≈ [-1,1] → [0,1]
    a = (a + 1.0) * 0.5
    a = np.clip(a, 0, 1)
    return (a * 255).astype("uint8")


def _norm_mist(arr):
    import numpy as np
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 3:
        a = a[..., 0]
    a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0)
    a = np.clip(a, 0, 1)
    return (a * 255).astype("uint8")


def extraer_exr(exr_path: Path, out_dir: Path, frame: int) -> dict:
    """Extrae Combined/Depth/Normal/Mist de un EXR multilayer a PNG."""
    import numpy as np
    from PIL import Image
    import OpenImageIO as oiio

    out_dir = Path(out_dir)
    exr_path = Path(exr_path)
    inp = oiio.ImageInput.open(str(exr_path))
    if inp is None:
        raise RuntimeError(f"no se abre EXR: {exr_path}")

    # Multilayer = subimages (Blender 5 File Output)
    nsub = inp.spec().get_int_attribute("oiio:subimages", 1) or 1
    mapas = {}
    for i in range(nsub):
        if i > 0 and not inp.seek_subimage(i, 0):
            break
        spec = inp.spec()
        name = (spec.get_string_attribute("name")
                or spec.get_string_attribute("oiio:subimagename")
                or (spec.channelnames[0].split(".")[0] if spec.channelnames else f"sub{i}"))
        pixels = inp.read_image(format=oiio.FLOAT)
        if pixels is None:
            continue
        arr = np.array(pixels).reshape(spec.height, spec.width, spec.nchannels)
        mapas[str(name).lower()] = arr
    inp.close()

    # Alias
    def pick(*keys):
        for k in keys:
            for mk, arr in mapas.items():
                if k in mk:
                    return arr
        return None

    combined = pick("image", "combined", "beauty", "rgba")
    depth = pick("depth", "z", "depth.z")
    normal = pick("normal", "normal.xyz")
    mist = pick("mist")

    tag = f"f{frame:04d}.png"
    rutas = {}
    if combined is not None:
        c = np.clip(combined[..., :3], 0, 1)
        Image.fromarray((c * 255).astype("uint8"), "RGB").save(out_dir / "combined" / tag)
        rutas["combined"] = str(out_dir / "combined" / tag)
    if depth is not None:
        d8, lo, hi = _norm_depth(depth)
        Image.fromarray(d8, "L").save(out_dir / "depth" / tag)
        rutas["depth"] = str(out_dir / "depth" / tag)
        rutas["depth_range"] = [lo, hi]
    if normal is not None:
        Image.fromarray(_norm_normal(normal), "RGB").save(out_dir / "normal" / tag)
        rutas["normal"] = str(out_dir / "normal" / tag)
    if mist is not None:
        Image.fromarray(_norm_mist(mist), "L").save(out_dir / "mist" / tag)
        rutas["mist"] = str(out_dir / "mist" / tag)
    return rutas


def postprocesar_exr_dir(exr_dir: Path, out_dir: Path) -> dict:
    """Recorre f####.exr (o *.exr) y genera PNG + MP4."""
    import re
    import subprocess
    exr_dir = Path(exr_dir)
    out_dir = Path(out_dir)
    files = sorted(exr_dir.glob("*.exr"))
    resumen = {"frames": [], "videos": {}}
    for fp in files:
        m = re.search(r"(\d{3,5})", fp.stem)
        fr = int(m.group(1)) if m else len(resumen["frames"]) + 1
        try:
            r = extraer_exr(fp, out_dir, fr)
            r["frame"] = fr
            r["exr"] = str(fp)
            resumen["frames"].append(r)
        except Exception as e:
            resumen["frames"].append({"frame": fr, "error": str(e), "exr": str(fp)})

    def mp4(subdir, name):
        d = out_dir / subdir
        pngs = sorted(d.glob("f*.png"))
        if not pngs:
            return None
        dest = out_dir / name
        cmd = [
            "ffmpeg", "-y", "-framerate", "24",
            "-i", str(d / "f%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            str(dest),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and dest.exists():
            return str(dest)
        # fallback concat if numbering gaps
        lst = out_dir / f"_{subdir}_list.txt"
        lst.write_text("".join(f"file '{x}'\n" for x in pngs))
        cmd2 = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-r", "24",
            "-i", str(lst),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            str(dest),
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True)
        return str(dest) if dest.exists() else None

    for sub, name in (("depth", "depth.mp4"), ("normal", "normal.mp4"),
                       ("mist", "mist.mp4"), ("combined", "combined_pases.mp4")):
        v = mp4(sub, name)
        if v:
            resumen["videos"][sub] = v
    (out_dir / "resumen_pases.json").write_text(
        __import__("json").dumps(resumen, indent=2, ensure_ascii=False)
    )
    return resumen


def hoja_contacto_pases(out_dir: Path, frames=(1, 8, 16, 24), dest=None) -> Path | None:
    """Hoja con Combined | Depth | Normal | Mist en N cuadros."""
    from PIL import Image
    out_dir = Path(out_dir)
    dest = Path(dest) if dest else out_dir / "hoja_contacto_pases.png"
    filas = []
    for fr in frames:
        tag = f"f{fr:04d}.png"
        imgs = []
        for sub in ("combined", "depth", "normal", "mist"):
            fp = out_dir / sub / tag
            if not fp.exists():
                # buscar cualquiera cercano
                cand = sorted((out_dir / sub).glob("f*.png"))
                fp = cand[min(len(cand) - 1, max(0, fr - 1))] if cand else None
            if fp and Path(fp).exists():
                im = Image.open(fp).convert("RGB")
                imgs.append(im)
        if len(imgs) >= 2:
            # uniform size
            w, h = imgs[0].size
            imgs = [im.resize((w, h)) for im in imgs]
            row = Image.new("RGB", (w * len(imgs), h))
            for i, im in enumerate(imgs):
                row.paste(im, (i * w, 0))
            filas.append(row)
    if not filas:
        return None
    W = max(r.size[0] for r in filas)
    H = sum(r.size[1] for r in filas)
    sheet = Image.new("RGB", (W, H), (20, 20, 20))
    y = 0
    for r in filas:
        sheet.paste(r, (0, y))
        y += r.size[1]
    sheet.save(dest)
    return dest
