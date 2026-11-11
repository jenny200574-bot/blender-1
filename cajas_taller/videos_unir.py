#!/usr/bin/env python3
"""videos_unir.py (10-nov-2026, Ricardo t1032u): une en orden las escenas de un capítulo.
Uso vía entrada_ssh.sh: «videos_unir b64.<payload>».
Payload JSON: {canal, capitulo, modo?, escenas:[{escena, video}], salida?}
Gratis: solo ffmpeg local. No llama a Argon ni GPU.
Si falta algún video, modo es cotizar, o la lista está vacía: no une, gasto_usd 0."""
import base64, json, os, re, subprocess, sys, tempfile
from pathlib import Path

RAICES = (
    "/opt/myia-motor-unificado/",
    "/opt/myia-taller-n8n/trabajo/",
    "/opt/myia-biblioteca/",
)
SALIDA_RAIZ = Path("/opt/myia-taller-n8n/trabajo/paso00_cadena")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")


def out(d):
    print(json.dumps(d, ensure_ascii=False))
    sys.exit(0)


def b64_payload(token):
    if not token.startswith("b64."):
        raise ValueError("falta b64.")
    s = token[4:]
    return json.loads(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode("utf-8"))


def bajo_raiz(p: Path) -> bool:
    try:
        rp = p.resolve()
    except Exception:
        return False
    s = str(rp)
    return any(s == r.rstrip("/") or s.startswith(r) for r in RAICES)


def main(argv):
    if len(argv) != 1:
        out({"ok": False, "error": "uso: videos_unir b64.<payload>", "gasto_usd": 0, "unido": False})
    try:
        p = b64_payload(argv[0])
    except Exception as e:
        out({"ok": False, "error": f"payload ilegible: {type(e).__name__}", "gasto_usd": 0, "unido": False})
    canal = str(p.get("canal") or "")
    cap = str(p.get("capitulo") or "")
    if not ID.match(canal) or not ID.match(cap):
        out({"ok": False, "error": "canal o capítulo no válido", "gasto_usd": 0, "unido": False})
    modo = str(p.get("modo") or "cotizar").strip().lower()
    tope = float(p.get("tope_usd") or 0)
    escenas = p.get("escenas") or []
    if not isinstance(escenas, list):
        out({"ok": False, "error": "escenas debe ser una lista", "gasto_usd": 0, "unido": False})

    def clave(e):
        try:
            return int(str(e.get("escena")))
        except Exception:
            return 10**9

    escenas = sorted([e for e in escenas if isinstance(e, dict)], key=clave)
    faltan = []
    rutas = []
    for e in escenas:
        vid = e.get("video") or e.get("ruta") or ""
        if not vid:
            faltan.append({"escena": e.get("escena"), "motivo": "sin video"})
            continue
        path = Path(str(vid))
        if not bajo_raiz(path) or not path.is_file() or path.suffix.lower() != ".mp4":
            faltan.append({"escena": e.get("escena"), "motivo": "ruta no permitida o no es mp4", "video": str(vid)[:200]})
            continue
        rutas.append({"escena": e.get("escena"), "video": str(path.resolve())})

    if modo in ("cotizar",) or tope <= 0 and modo not in ("real", "pagar"):
        out({
            "ok": True, "unido": False, "gasto_usd": 0, "seco": True,
            "motivo": "modo cotizar o tope 0: no se une, solo se informa",
            "canal": canal, "capitulo": cap, "n_listas": len(escenas),
            "n_con_video": len(rutas), "faltan": faltan,
            "orden": [x["escena"] for x in rutas],
        })
    if not rutas or faltan:
        out({
            "ok": False, "unido": False, "gasto_usd": 0,
            "error": "faltan videos para unir el capítulo entero",
            "canal": canal, "capitulo": cap, "n_con_video": len(rutas), "faltan": faltan,
        })

    dest_dir = SALIDA_RAIZ / canal / f"cap{cap}" / "union"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "capitulo_unido.mp4"
    lista = dest_dir / "lista_ffmpeg.txt"
    lista.write_text("".join(f"file '{x['video']}'\n" for x in rutas), encoding="utf-8")
    cmd = [
        "/usr/bin/ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(lista), "-c", "copy", str(dest),
    ]
    try:
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        out({"ok": False, "unido": False, "gasto_usd": 0, "error": f"ffmpeg: {type(e).__name__}"})
    if pr.returncode != 0 or not dest.is_file():
        err = (pr.stderr or pr.stdout or "")[-400:]
        out({"ok": False, "unido": False, "gasto_usd": 0, "error": "ffmpeg falló", "detalle": err})
    out({
        "ok": True, "unido": True, "gasto_usd": 0,
        "canal": canal, "capitulo": cap,
        "video": str(dest), "bytes": dest.stat().st_size,
        "orden": [x["escena"] for x in rutas], "n": len(rutas),
    })


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except SystemExit:
        raise
    except Exception as e:
        out({"ok": False, "unido": False, "gasto_usd": 0, "error": f"fallo interno: {type(e).__name__}: {e}"})
