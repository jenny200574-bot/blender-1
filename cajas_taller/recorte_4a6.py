"""recorte_4a6.py — t445 (Ricardo «corrije y aplica»): recorte AUTOMÁTICO de los escenarios pintados (4a5). GRATIS, sin IA, sin red.
Convención (sin preguntar a nadie):
  - Formato = el del canal (channels.data.aspect, p. ej. «16:9»); si el canal no lo trae, 16:9.
  - Tamaño = la calidad de video del canal (channels.data.quality: 720p → 1280×720, 1080p → 1920×1080); si no hay, se conserva el alto original.
  - Encuadre = CENTRADO: 4a5 pinta sobre la cámara del molde de Blender (ya encuadrada para la escena), así que solo se recorta el sobrante
    simétrico para llegar a la proporción exacta; nunca se cambia el punto de vista. Si la imagen ya tiene la proporción, solo se escala.
  - Nunca toca la imagen de 4a5. Salida: ramas/imagenes/4a6/<mismo nombre>.png + ramas/recorte_4a6.json (origen, sha, caja de recorte).
  - Idempotente: si el recorte ya existe para el mismo sha de origen y misma convención, no se rehace.
"""
import hashlib, json, re
from pathlib import Path

ALTOS = {"480p": 480, "720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160, "4k": 2160}


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def formato_canal(canal):
    aspect, quality, fuente = "16:9", None, "por defecto (el canal no trae aspect)"
    try:
        import estilo_taller as ET
        d = ET.canal_datos(canal) or {}
        def buscar(o, k):
            if isinstance(o, dict):
                if isinstance(o.get(k), str): return o[k]
                for v in o.values():
                    r = buscar(v, k)
                    if r: return r
            return None
        a = buscar(d, "aspect"); q = buscar(d, "quality")
        if a and re.match(r"^\d+:\d+$", a): aspect, fuente = a, "channels.data.aspect"
        quality = q
    except Exception as exc:
        fuente = f"por defecto ({type(exc).__name__})"
    w, h = (int(x) for x in aspect.split(":"))
    alto = ALTOS.get(str(quality or "").lower())
    return {"aspect": aspect, "ratio": w / h, "alto": alto, "quality": quality, "fuente": fuente}


def recortar(D, canal):
    from PIL import Image
    D = Path(D); src = D / "ramas" / "imagenes" / "4a5"; dst = D / "ramas" / "imagenes" / "4a6"
    man_f = D / "ramas" / "recorte_4a6.json"
    prev = {}
    if man_f.is_file():
        try: prev = {x["origen"]: x for x in json.loads(man_f.read_text(encoding="utf-8")).get("recortes", [])}
        except Exception: prev = {}
    F = formato_canal(canal)
    conv = f"centrado|{F['aspect']}|{F['alto']}"
    out, hechos, saltados = [], 0, 0
    if not src.is_dir():
        return {"ok": True, "recortes": 0, "aviso": "4a5 aún no tiene imágenes", "formato": F}
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.glob("*.png")):
        sh = _sha(p); o = dst / p.name; pv = prev.get(str(p))
        if pv and pv.get("sha_origen") == sh and pv.get("convencion") == conv and o.is_file():
            out.append(pv); saltados += 1; continue
        im = Image.open(p); W, H = im.size
        if abs(W / H - F["ratio"]) < 1e-3: box = (0, 0, W, H)
        elif W / H > F["ratio"]:
            nw = round(H * F["ratio"]); x = (W - nw) // 2; box = (x, 0, x + nw, H)
        else:
            nh = round(W / F["ratio"]); y = (H - nh) // 2; box = (0, y, W, y + nh)
        c = im.crop(box)
        if F["alto"] and c.size[1] != F["alto"]:
            c = c.resize((round(F["alto"] * F["ratio"]), F["alto"]), Image.LANCZOS)
        c.save(o)
        out.append({"origen": str(p), "sha_origen": sh, "salida": str(o), "sha_salida": _sha(o), "tam_origen": [W, H],
                    "caja": list(box), "tam_salida": list(c.size), "convencion": conv})
        hechos += 1
    man = {"schema": "myia.recorte_4a6.v1", "canal": canal, "formato": F, "convencion": "centrado; proporción y tamaño del canal; origen intacto",
           "recortes": out}
    man_f.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "recortes": len(out), "nuevos": hechos, "ya_estaban": saltados, "formato": F, "manifiesto": str(man_f), "carpeta": str(dst)}
