# -*- coding: utf-8 -*-
"""Workers gratis: biblioteca primero → vía B corpus → (Argon apagado)."""
from __future__ import annotations
import json, shutil, traceback
from pathlib import Path
from biblioteca import Biblioteca, now_iso
from via_b_corpus import armar_corpus

def _terminos_objeto(payload):
    nombre = payload.get("nombre") or payload.get("id") or ""
    terms = [nombre.replace("gdc-", "").replace("-", " "), "objeto", "juguete"]
    extra = payload.get("terminos_busqueda") or []
    return [t for t in terms + list(extra) if t]

def _terminos_personaje(payload):
    nombre = payload.get("nombre") or payload.get("id") or ""
    anatomy = payload.get("anatomy") or payload.get("especie") or "esqueleto"
    return [nombre.replace("gdc-", "").replace("-", " "), anatomy, "huesos", "esqueleto animal"]

def _terminos_escenario(payload):
    nombre = payload.get("nombre") or payload.get("id") or "habitacion"
    return [nombre.replace("esc-", "").replace("-", " "), "mobiliario", "habitación infantil"]

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
        if kind == "personaje":
            terms = _terminos_personaje(job["payload"])
        elif kind == "escenario":
            terms = _terminos_escenario(job["payload"])
        else:
            terms = _terminos_objeto(job["payload"])
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
            needle = pid.replace("gdc-", "").replace("-", "_")
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
