# -*- coding: utf-8 -*-
"""Biblioteca persistente por canal. Nunca borra: solo añade versiones."""
from __future__ import annotations
import hashlib, json, shutil, time
from pathlib import Path
from datetime import datetime, timezone

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

class Biblioteca:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "_comun" / "recetas_star_aprendidas").mkdir(parents=True, exist_ok=True)
        if not (self.root / "_comun" / "indice.json").exists():
            self._save(self.root / "_comun" / "indice.json", {"schema": "bib_comun_v1", "entries": []})

    def _save(self, p: Path, d):
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".parcial")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)

    def canal_dir(self, canal: str) -> Path:
        d = self.root / canal
        d.mkdir(parents=True, exist_ok=True)
        idx = d / "indice.json"
        if not idx.exists():
            self._save(idx, {"schema": "bib_canal_v1", "canal": canal, "entries": [], "updated_at": now_iso()})
        return d

    def pieza_dir(self, canal: str, tipo: str, pid: str) -> Path:
        assert tipo in ("personajes", "objetos", "objetos_usuario", "escenarios")
        d = self.canal_dir(canal) / tipo / pid
        for sub in ("adn", "corpus", "receta", "ficha_esqueleto", "poses", "blend", "renders", "recibos", "inventario_4a1"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        meta = d / "meta.json"
        if not meta.exists():
            self._save(meta, {
                "schema": "pieza_meta_v1", "canal": canal, "tipo": tipo, "id": pid,
                "estado": "nuevo", "versiones": [], "actual": None,
                "approval_ref": None, "gasto_usd_acum": 0, "created_at": now_iso(),
            })
        return d

    def leer_meta(self, canal, tipo, pid):
        p = self.pieza_dir(canal, tipo, pid) / "meta.json"
        return json.loads(p.read_text(encoding="utf-8"))

    def buscar_aprobado(self, canal, tipo, pid):
        meta = self.leer_meta(canal, tipo, pid)
        if meta.get("estado") == "aprobado" and meta.get("actual"):
            return meta
        # genérico en _comun (solo objetos/recetas)
        if tipo in ("objetos", "objetos_usuario"):
            comun = self.root / "_comun" / "recetas_star_aprendidas" / f"{pid}.json"
            if comun.is_file():
                return {"estado": "aprobado_comun", "path": str(comun), "gasto_usd": 0}
        return None

    def registrar_version(self, canal, tipo, pid, kind: str, path: Path, notas=None):
        d = self.pieza_dir(canal, tipo, pid)
        meta = self.leer_meta(canal, tipo, pid)
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None
        ver = {
            "n": len(meta["versiones"]) + 1,
            "kind": kind,
            "path": str(Path(path).relative_to(d)) if str(path).startswith(str(d)) else str(path),
            "sha256": sha,
            "at": now_iso(),
            "notas": notas or {},
        }
        meta["versiones"].append(ver)
        meta["actual"] = ver
        meta["updated_at"] = now_iso()
        if kind in ("blend", "receta", "ficha_esqueleto") and meta.get("estado") in ("nuevo", "listo_parcial", "esperando_argon"):
            meta["estado"] = "listo_parcial"
        self._save(d / "meta.json", meta)
        # índice canal
        idx_p = self.canal_dir(canal) / "indice.json"
        idx = json.loads(idx_p.read_text(encoding="utf-8"))
        key =[REDACTED]
        entries = [e for e in idx.get("entries", []) if e.get("key") != key]
        entries.append({"key": key, "tipo": tipo, "id": pid, "estado": meta["estado"], "updated_at": meta["updated_at"]})
        idx["entries"] = entries
        idx["updated_at"] = now_iso()
        self._save(idx_p, idx)
        return meta

    def importar_recetas_comun(self, src_dir: Path):
        src = Path(src_dir)
        dest = self.root / "_comun" / "recetas_star_aprendidas"
        n = 0
        if not src.exists():
            return 0
        for f in list(src.glob("*.json")) + list((src / "recetas").glob("*.json") if (src / "recetas").exists() else []):
            if f.name in ("catalogo.json", "indice.json", "alias_objeto_n8n.json"):
                continue
            shutil.copy2(f, dest / f.name)
            n += 1
        return n
