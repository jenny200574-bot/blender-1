# -*- coding: utf-8 -*-
"""Workers gratis: biblioteca primero → vía B corpus → (Argon apagado)."""
from __future__ import annotations
import json, shutil, traceback
from pathlib import Path
from biblioteca import Biblioteca, now_iso
from via_b_corpus import armar_corpus

def prefijo_canal(bib, canal, cfg=None):
    """Prefijo de ids del canal (p. ej. 'gdc-'), sacado de los datos del canal: ids ya publicados en la biblioteca y ADN
    sellados del cubo con ese canal. Si la mayoría (>=60 %, >=2 ids) comparte '<2-6 letras>-', ese es el prefijo; si no, ''."""
    import collections, re as _re
    ids = []
    try:
        cd = bib.canal_dir(canal)
        for t in ("personajes", "objetos", "objetos_usuario"):
            if (cd / t).is_dir(): ids += [x.name for x in (cd / t).iterdir() if x.is_dir()]
    except Exception: pass
    try:
        adn = Path(((cfg or {}).get("constructores") or {}).get("cubo_fijo_raiz") or "") / "adn"
        if adn.is_dir():
            for f in adn.glob("*_ako.json"):
                try:
                    if json.loads(f.read_text(encoding="utf-8")).get("canal") == canal: ids.append(f.name[:-9])
                except Exception: pass
    except Exception: pass
    pre = [m.group(1) for m in (_re.match(r"^([a-z0-9]{2,6}-)", i) for i in ids) if m]
    if len(ids) < 2 or not pre: return ""
    p, n = collections.Counter(pre).most_common(1)[0]
    return p if n >= 0.6 * len(ids) else ""

def sin_prefijo(txt, pref):
    return txt[len(pref):] if pref and txt.startswith(pref) else txt

def _terminos_objeto(payload, pref=""):
    nombre = payload.get("nombre") or payload.get("id") or ""
    terms = [sin_prefijo(nombre, pref).replace("-", " "), "objeto", "juguete"]
    extra = payload.get("terminos_busqueda") or []
    return [t for t in terms + list(extra) if t]

def _terminos_personaje(payload, pref=""):
    nombre = payload.get("nombre") or payload.get("id") or ""
    anatomy = payload.get("anatomy") or payload.get("especie") or "esqueleto"
    return [sin_prefijo(nombre, pref).replace("-", " "), anatomy, "huesos", "esqueleto animal"]

def _terminos_escenario(payload, pref=""):
    # sin lugar por defecto: el nombre/id del escenario manda; términos extra solo si el pedido los trae
    nombre = payload.get("nombre") or payload.get("id") or ""
    terms = [sin_prefijo(nombre, "esc-").replace("-", " "), "mobiliario"] + list(payload.get("terminos_busqueda") or [])
    return [t for t in terms if t]

def run_job(job: dict, cfg: dict, bib: Biblioteca) -> dict:
    tipo_map = {
        "personaje": "personajes",
        "escenario": "escenarios",
        "objeto": "objetos",
        "objeto_usuario": "objetos_usuario",
    }
    kind = job["kind"]
    tipo = tipo_map[kind]
    canal = job["payload"]["canal"]
    pid = job["payload"]["id"]
    d = bib.pieza_dir(canal, tipo, pid)
    job["log"] = job.get("log") or []
    job["gasto_usd"] = 0

    # 1) biblioteca primero
    hit = bib.buscar_aprobado(canal, tipo, pid)
    if hit and hit.get("estado") in ("aprobado", "aprobado_comun"):
        job["estado"] = "reusado"
        job["resultado"] = {"biblioteca": hit, "gasto_usd": 0}
        job["log"].append("reuso biblioteca US$0")
        return job

    # 2) vía B gratis (siempre, antes de Argon)
    if cfg.get("via_b_enabled", True):
        pref = prefijo_canal(bib, canal, cfg)
        if kind == "personaje":
            terms = _terminos_personaje(job["payload"], pref)
        elif kind == "escenario":
            terms = _terminos_escenario(job["payload"], pref)
        else:
            terms = _terminos_objeto(job["payload"], pref)
        job["log"].append(f"via_b terminos={terms}")
        try:
            corpus = armar_corpus(pid, terms, d / "corpus")
            bib.registrar_version(canal, tipo, pid, "corpus", d / "corpus" / "corpus.json",
                                  {"n_fuentes": corpus.get("n_fuentes"), "gasto_usd": 0})
            job["log"].append(f"corpus fuentes={corpus.get('n_fuentes')} US$0")
            job["corpus"] = {"n_fuentes": corpus.get("n_fuentes"), "path": str(d / "corpus" / "corpus.json")}
        except Exception as e:
            job["log"].append(f"via_b error: {e}")
            job["corpus"] = {"error": str(e)}

    # 3) construcción gratis según tipo
    if kind in ("objeto", "objeto_usuario"):
        # buscar receta aprendida / star por nombre
        rec_root = Path(cfg.get("recetas_aprendidas") or "")
        found = None
        if rec_root.exists():
            cand = list(rec_root.glob("*.json")) + list((rec_root / "recetas").glob("*.json") if (rec_root / "recetas").exists() else [])
            needle = sin_prefijo(pid, prefijo_canal(bib, canal, cfg)).replace("-", "_")
            for f in cand:
                if needle in f.stem or any(x in f.stem for x in needle.split("_") if len(x) > 3):
                    found = f
                    break
        if found:
            dest = d / "receta" / found.name
            shutil.copy2(found, dest)
            bib.registrar_version(canal, tipo, pid, "receta", dest, {"origen": "recetas_aprendidas", "gasto_usd": 0})
            meta = bib.leer_meta(canal, tipo, pid)
            meta["estado"] = "listo_parcial"
            bib._save(d / "meta.json", meta)
            job["estado"] = "listo_parcial"
            job["resultado"] = {"receta": str(dest), "gasto_usd": 0}
            job["log"].append(f"receta desde aprendidas: {found.name}")
            return job
        job["estado"] = "esperando_argon" if not cfg.get("argon_enabled") else "cotizar_argon"
        job["resultado"] = {"faltante": "receta", "argon_enabled": bool(cfg.get("argon_enabled")), "gasto_usd": 0}
        job["log"].append("sin receta local; Argon " + ("ON" if cfg.get("argon_enabled") else "OFF (default)"))
        return job

    if kind == "personaje":
        # si viene path de ficha/blend existente, copiar
        for key, sub in (("ficha_path", "ficha_esqueleto"), ("blend_path", "blend"), ("adn_path", "adn")):
            src = job["payload"].get(key)
            if src and Path(src).is_file():
                dest = d / sub / Path(src).name
                shutil.copy2(src, dest)
                bib.registrar_version(canal, tipo, pid, sub.rstrip("s") if False else sub, dest, {"gasto_usd": 0})
                job["log"].append(f"copiado {key}")
        meta = bib.leer_meta(canal, tipo, pid)
        if any((d / x).iterdir() for x in ("ficha_esqueleto", "blend", "adn") if (d / x).exists()):
            meta["estado"] = "listo_parcial"
            bib._save(d / "meta.json", meta)
            job["estado"] = "listo_parcial"
        else:
            job["estado"] = "esperando_argon" if not cfg.get("argon_enabled") else "cotizar_argon"
        job["resultado"] = {"dir": str(d), "gasto_usd": 0, "argon_enabled": bool(cfg.get("argon_enabled"))}
        return job

    if kind == "escenario":
        inv = job["payload"].get("inventario_path")
        if inv and Path(inv).is_file():
            dest = d / "inventario_4a1" / Path(inv).name
            shutil.copy2(inv, dest)
            bib.registrar_version(canal, tipo, pid, "inventario_4a1", dest, {"gasto_usd": 0})
        # marca listo_parcial: armado Blender Star queda para worker extendido (gratis CPU)
        meta = bib.leer_meta(canal, tipo, pid)
        meta["estado"] = "listo_parcial"
        bib._save(d / "meta.json", meta)
        job["estado"] = "listo_parcial"
        job["resultado"] = {"dir": str(d), "nota": "inv guardado; armado Star en cola CPU", "gasto_usd": 0}
        job["log"].append("escenario: inventario en bib; Argon OFF")
        return job

    job["estado"] = "error"
    job["error"] = "kind desconocido"
    return job
