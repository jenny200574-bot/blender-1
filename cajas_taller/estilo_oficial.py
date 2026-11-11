# -*- coding: utf-8 -*-
"""MYIA · Taller n8n · SELLO DE ESTILO POR CANAL (v2 · 2-nov-2026, America/Bogota). GRATIS, sin red, sin IA.

v1 (31-oct) copiaba UNA imagen global (FIJOS_TALLER/estilo/ESTILO_OFICIAL_CANAL.png) a CUALQUIER canal: así un canal nuevo
recibía el estilo de Génesis. v2: cada canal tiene su PROPIO sello, fijado UNA vez desde su style_fijo aprobado en la app
(nombre, descripcion_en, negativo, paleta e IMAGEN SUBIDA Y APROBADA por el usuario en «Validador de estilo»). Los pasos lo
CONSULTAN; nadie lo reescribe a mano. Versionado: si cambia la imagen o el texto aprobado, sale una versión nueva.

  Sello:   FIJOS_TALLER/estilo/<canal>/sello.json  +  ESTILO_CANAL_v<N>.<ext>   (versiones viejas quedan en la carpeta)
  Cubo:    cubo_fijo/canales/<canal>.json  y  cubo_fijo/estilo/<id_estilo>.json  (los generan el sello; los lee «cubo_fijo ensamblar»)

Reglas:
  · Sin imagen aprobada propia → NO se usa la de otro canal: sello de TEXTO + aviso «falta imagen de estilo aprobada» (ok=true).
  · La imagen global vieja (ESTILO_OFICIAL_CANAL.png) solo se acepta para el canal que la aprobó (LEGADO_GLOBAL = Génesis).
  · fijar escribe style_fijo.imagen = imagen del sello (ruta absoluta) SOLO si la imagen salió del propio canal.

Uso (entrada restringida n8ntaller):
  paso00_cadena estilo fijar --canal CID --ok
  paso00_cadena estilo leer  --canal CID
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, shutil, sqlite3, sys
from pathlib import Path

CAJAS = Path("/opt/myia-taller-n8n/cajas")
RAIZ = CAJAS / "FIJOS_TALLER" / "estilo"
FIJO = RAIZ / "ESTILO_OFICIAL_CANAL.png"            # v1 global: SOLO legado del canal que la aprobó
LEGADO_GLOBAL = {"cn-gnesis-digital-el-de-ed178619"}
STUDIO_DB = Path("/opt/myia-staging-arreglos-20261026/demo_chat/estudio/web/data/studio.db")
MEDIA = Path("/opt/myia-staging-arreglos-20261026/demo_chat/estudio/media")
MEDIA_ESTILO = MEDIA / "estilo"
CUBO = CAJAS / "cubo_fijo"
VERSION_PROGRAMA = "estilo_oficial v2 (sello por canal, 2-nov-2026)"
ID = re.compile(r"^[A-Za-z0-9._-]{3,80}$")
AVISO_SIN_IMG = "falta imagen de estilo aprobada"


def _ahora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _wj(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + ".tmp")
    t.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(t, p)


def _rj(p: Path, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


def _canal(canal: str, rw: bool = False):
    con = sqlite3.connect(str(STUDIO_DB)) if rw else sqlite3.connect(f"file:{STUDIO_DB}?mode=ro", uri=True)
    row = con.execute("SELECT data, name FROM channels WHERE id=?", (canal,)).fetchone() if _tiene_name(con) else \
        (lambda r: (r[0], None) if r else None)(con.execute("SELECT data FROM channels WHERE id=?", (canal,)).fetchone())
    if not row:
        con.close(); return None, None, None
    data = json.loads(row[0]) if isinstance(row[0], str) else (row[0] or {})
    return con, data, row[1]


def _tiene_name(con) -> bool:
    return any(c[1] == "name" for c in con.execute("PRAGMA table_info(channels)"))


def _resolver(img: str):
    """style_fijo.imagen de la app (relativa a media/, p. ej. 'estilo/<cid>-estilo.png') o absoluta → Path o None."""
    if not img:
        return None
    p = Path(img)
    if not p.is_absolute():
        p = MEDIA / img.lstrip("/")
        if not p.is_file() and img.startswith("media/"):
            p = MEDIA / img[len("media/"):]
    return p if p.is_file() else None


def _slug(canal: str) -> str:
    m = re.match(r"^cn-(.+?)-[0-9a-f]{6,}$", canal)
    s = (m.group(1) if m else canal).replace("-", "_")
    return ("estilo_" + s)[:60]


def _dir(canal: str) -> Path:
    return RAIZ / canal


def _sello_actual(canal: str):
    return _rj(_dir(canal) / "sello.json")


def _origen_imagen(canal: str, sf: dict):
    """(Path|None, origen_txt, avisos). Nunca devuelve la imagen de OTRO canal."""
    av = []
    img = (sf or {}).get("imagen") or ""
    d = _dir(canal)
    if img:
        p = _resolver(img)
        if p is None:
            av.append(f"style_fijo.imagen no existe en disco: {img}")
        else:
            rp = p.resolve()
            if rp == FIJO.resolve():
                if canal in LEGADO_GLOBAL:
                    return p, "legado v1: muestra global aprobada por este canal (se migra a su carpeta propia)", av
                av.append("style_fijo.imagen apunta a la muestra GLOBAL de otro canal (ESTILO_OFICIAL_CANAL.png): NO se usa")
            elif str(rp).startswith(str(RAIZ.resolve()) + "/") and not str(rp).startswith(str(d.resolve()) + "/"):
                av.append(f"style_fijo.imagen apunta al sello de OTRO canal ({img}): NO se usa")
            else:
                return p, f"imagen aprobada del canal en la app ({img})", av
    espejo = MEDIA_ESTILO / f"{canal}-estilo.png"
    if espejo.is_file() and not img:
        av.append(f"hay una imagen subida ({espejo.name}) pero NO está aprobada: aprobar en Validador de estilo")
    return None, None, av


def _texto(sf: dict) -> dict:
    return {k: sf.get(k) for k in ("nombre", "descripcion_en", "negativo", "paleta_en", "base", "nota_imagen") if sf.get(k) not in (None, "", [])}


def _cubo(canal: str, nombre_canal, sf: dict, sello: dict) -> dict:
    """Genera cubo_fijo/canales/<canal>.json y la entrada de estilo del canal (la lee «cubo_fijo ensamblar»)."""
    escritos = []
    cv = CUBO / "canales" / f"{canal}.json"
    if CUBO.is_dir():
        _wj(cv, {"schema": "myia.canal_vars/v1", "canal": canal, "nombre": nombre_canal or canal,
                 "estilo_canal": sf.get("nombre") or "", "estilo_base": sf.get("base") or "",
                 "estilo_aprobado": bool(sf.get("aprobado")), "estilo_descripcion_en": sf.get("descripcion_en") or "",
                 "estilo_negativo": sf.get("negativo") or "", "estilo_paleta": sf.get("paleta_en") or None,
                 "estilo_imagen": sello.get("imagen"), "estilo_imagen_sha256": sello.get("imagen_sha256"),
                 "sello": str(_dir(canal) / "sello.json"), "sello_version": sello.get("version"),
                 "fuente": "generado por el sello de estilo del canal (estilo_oficial v2) desde studio.db style_fijo aprobado",
                 "fecha": _ahora(), "por": "estilo_oficial v2"})
        escritos.append(str(cv))
        ed = CUBO / "estilo"
        ent, f_ent = None, None
        for f in sorted(ed.glob("*.json")):
            e = _rj(f, {}) or {}
            if e.get("canal") == canal or canal in (e.get("ids_canal") or []) or e.get("sello_canal") == canal:
                ent, f_ent = e, f; break
        if ent is None and canal in LEGADO_GLOBAL and (ed / "estilo_genesis.json").is_file():
            ent, f_ent = _rj(ed / "estilo_genesis.json", {}), ed / "estilo_genesis.json"
        if ent is None:
            ent, f_ent = {"id": _slug(canal), "version": 1}, ed / f"{_slug(canal)}.json"
        viejo = ent.get("canal")
        if viejo and viejo != canal:
            ent.setdefault("ids_canal", [])
            if viejo not in ent["ids_canal"]: ent["ids_canal"].append(viejo)
        ent.update({"clase": "estilo", "clase_adn": "estilo", "canal": canal, "nombre": sf.get("nombre"),
                    "imagen_ref": sello.get("imagen"), "hoja_ref": sello.get("imagen"), "imagen_sha256": sello.get("imagen_sha256"),
                    "descripcion_en": sf.get("descripcion_en"), "negativo": sf.get("negativo"),
                    "sello_canal": canal, "sello_archivo": str(_dir(canal) / "sello.json"), "sello_version": sello.get("version"),
                    "actualizado": _ahora(), "origen": "estilo_oficial v2 (sello del canal)"})
        ent.setdefault("sellado", False)
        _wj(f_ent, ent); escritos.append(str(f_ent))
    return {"escritos": escritos}


def dimension_de(sf: dict | None, sello: dict | None = None) -> dict:
    """t310u (Ricardo, 2-nov-2026) — GENÉRICO: dimensión del estilo del CANAL («2D» o «3D») para los Maestros (p. ej. Maestro 02 Fase 1).
    1) style_fijo.dimension del canal (si la app la trae: «2D»/«3D»);
    2) si no, se lee del estilo aprobado del canal (nombre + descripcion_en del sello o del style_fijo; NO del negativo):
       «3D», «CGI», «render 3D», «Pixar» → 3D; si no → 2D.
    Nada amarrado a un canal."""
    sf = sf or {}; sello = sello or {}
    d = str(sf.get("dimension") or sello.get("dimension") or "").strip().upper()
    if d in ("2D", "3D"): return {"dimension": d, "fuente": "style_fijo.dimension del canal"}
    t = " ".join(str(x.get(k) or "") for x in (sello, sf) for k in ("nombre", "descripcion_en"))
    if re.search(r"\b3D\b|\bCGI\b|\bPixar\b|3D render|render 3D", t, re.I):
        return {"dimension": "3D", "fuente": "deducido del estilo aprobado del canal (nombre/descripcion_en)"}
    return {"dimension": "2D", "fuente": "deducido del estilo aprobado del canal (sin señal de 3D)"}


def dimension(canal: str) -> dict:
    """Solo lectura. Dimensión del estilo del canal (ver dimension_de)."""
    sf = {}
    try:
        con, data, _ = _canal(canal)
        if con is not None:
            con.close(); sf = data.get("style_fijo") if isinstance(data.get("style_fijo"), dict) else {}
    except Exception:
        sf = {}
    return dict(dimension_de(sf, _sello_actual(canal) or {}), canal=canal)


def leer(canal: str) -> dict:
    """Solo lectura: sello del canal, imagen, sha, ficha. US$0."""
    if not STUDIO_DB.is_file():
        return {"ok": False, "accion": "estilo leer", "error": f"no está studio.db en {STUDIO_DB}"}
    con, data, _ = _canal(canal)
    if con is None:
        return {"ok": False, "accion": "estilo leer", "error": f"canal no encontrado: {canal}"}
    con.close()
    sf = data.get("style_fijo") if isinstance(data.get("style_fijo"), dict) else {}
    s = _sello_actual(canal) or {}
    av = []
    if not sf or not sf.get("aprobado"): av.append("el canal no tiene style_fijo aprobado")
    if not s: av.append("el canal aún no tiene sello de estilo: correr «estilo fijar --canal … --ok»")
    img = s.get("imagen")
    existe = bool(img) and Path(img).is_file()
    if s and not img: av.append(AVISO_SIN_IMG)
    if img and existe and s.get("imagen_sha256") and _sha(Path(img)) != s["imagen_sha256"]:
        av.append("la imagen del sello cambió en disco (sha distinto): sello ROTO, no usar hasta re-fijar")
    sfi = (sf or {}).get("imagen") or ""
    if sfi and img and Path(sfi).is_absolute() and Path(sfi).resolve() != Path(img).resolve():
        av.append(f"style_fijo.imagen de la ficha ({sfi}) no es la del sello ({img})")
    return {"ok": True, "accion": "estilo leer", "canal": canal, "sello": s or None, "sello_archivo": str(_dir(canal) / "sello.json"),
            "imagen_ruta": img or None, "imagen_existe": existe, "style_fijo_imagen": sfi, "sha256": s.get("imagen_sha256") or "",
            "texto_sellado": bool(s.get("descripcion_en")), "dimension": dimension_de(sf, s), "usd": 0, "programa": VERSION_PROGRAMA,
            "resumen": ("sello de estilo del canal con imagen" if existe else "sello de estilo del canal SOLO TEXTO (" + AVISO_SIN_IMG + ")") if s else "sin sello",
            "avisos": av}


def fijar(canal: str, origen: Path | None = None) -> dict:
    """Fija (o confirma) el sello de estilo del canal desde su style_fijo aprobado. Versiona si cambió. US$0."""
    if not ID.match(canal or ""):
        return {"ok": False, "accion": "estilo fijar", "error": "canal inválido"}
    con, data, nombre_canal = _canal(canal, rw=True)
    if con is None:
        return {"ok": False, "accion": "estilo fijar", "error": f"canal no encontrado: {canal}"}
    try:
        sf = dict(data.get("style_fijo") or {})
        if not sf.get("aprobado") or not sf.get("descripcion_en"):
            return {"ok": False, "accion": "estilo fijar", "error": "el canal no tiene style_fijo aprobado (texto); no se toca"}
        avisos = []
        if origen:
            o = Path(origen)
            if not o.is_file():
                return {"ok": False, "accion": "estilo fijar", "error": f"--origen no existe: {o}"}
            if o.resolve() == FIJO.resolve() and canal not in LEGADO_GLOBAL:
                return {"ok": False, "accion": "estilo fijar", "error": "--origen es la muestra global de otro canal: no se usa"}
            src, de = o, f"--origen {o} (puesto por una persona)"
        else:
            src, de, av = _origen_imagen(canal, sf); avisos += av
        d = _dir(canal); d.mkdir(parents=True, exist_ok=True)
        prev = _sello_actual(canal) or {}
        texto = _texto(sf)
        texto_sha = hashlib.sha256(json.dumps(texto, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        img, img_sha = None, None
        if src is not None:
            img_sha = _sha(src)
            if prev.get("imagen_sha256") == img_sha and prev.get("imagen") and Path(prev["imagen"]).is_file():
                img = prev["imagen"]
            else:
                v = int(prev.get("version") or 0) + 1
                img = str(d / f"ESTILO_CANAL_v{v}{src.suffix.lower() or '.png'}")
                shutil.copy2(src, img)
        else:
            avisos.append(AVISO_SIN_IMG + ": el sello queda SOLO TEXTO; no se usa la imagen de ningún otro canal. "
                          "Sube y aprueba la imagen en la app (Configuración del canal → Validador de estilo) y vuelve a fijar.")
        cambio = (img_sha != prev.get("imagen_sha256")) or (texto_sha != prev.get("texto_sha256"))
        if prev and not cambio:
            sello = prev
        else:
            if prev:
                v_old = prev.get("version") or 1
                _wj(d / f"sello_v{v_old}.json", prev)
            sello = {"schema": "myia.sello_estilo/v1", "canal": canal, "canal_nombre": nombre_canal,
                     "version": int(prev.get("version") or 0) + 1, **texto, "texto_sha256": texto_sha,
                     "imagen": img, "imagen_sha256": img_sha, "imagen_origen": de,
                     "estado": "imagen+texto" if img else "solo_texto (" + AVISO_SIN_IMG + ")",
                     "fijado": _ahora(), "programa": VERSION_PROGRAMA,
                     "regla": "FIJO: los pasos lo consultan; no se edita a mano. Cambia solo si cambia el style_fijo aprobado en la app."}
            _wj(d / "sello.json", sello)
        antes = sf.get("imagen") or ""
        if img and antes != img:
            sf["imagen"] = img
            sf["imagen_sello"] = {"version": sello["version"], "sha256": img_sha, "origen": de, "cuando": _ahora()}
            data["style_fijo"] = sf
            con.execute("UPDATE channels SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), canal))
            con.commit()
        cubo = _cubo(canal, nombre_canal, sf, sello)
    finally:
        con.close()
    return {"ok": True, "accion": "estilo fijar", "canal": canal, "sello_archivo": str(_dir(canal) / "sello.json"),
            "sello_version": sello.get("version"), "nuevo": bool(cambio or not prev), "estado": sello.get("estado"),
            "imagen_ruta": img, "imagen_existe": bool(img) and Path(img).is_file(), "sha256": img_sha or "",
            "style_fijo_imagen": sf.get("imagen") or "", "style_fijo_imagen_antes": antes, "cubo": cubo,
            "usd": 0, "programa": VERSION_PROGRAMA,
            "resumen": ("sello de estilo del canal fijado (imagen + texto)" if img else "sello de estilo SOLO TEXTO: " + AVISO_SIN_IMG),
            "avisos": avisos}


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    ap = argparse.ArgumentParser(prog="estilo")
    ap.add_argument("accion", choices=["fijar", "leer"])
    ap.add_argument("--canal", required=True)
    ap.add_argument("--ok", action="store_true", help="obligatorio para fijar (confirma escritura)")
    ap.add_argument("--origen", default=None, help="ruta de una imagen PROPIA del canal (solo fijar; nunca la de otro canal)")
    a = ap.parse_args(argv)
    if a.accion == "leer":
        return leer(a.canal)
    if not a.ok:
        return {"ok": False, "accion": "estilo fijar", "error": "falta --ok (confirma que se escribe en la ficha)"}
    return fijar(a.canal, Path(a.origen) if a.origen else None)


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if r.get("ok") else 1)
