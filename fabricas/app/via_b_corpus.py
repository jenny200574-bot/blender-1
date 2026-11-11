# -*- coding: utf-8 -*-
"""Vía B GRATIS: Wikipedia/fuentes públicas → corpus con citas literales. Sin Argon, sin API key de pago."""
from __future__ import annotations
import hashlib, json, re, time, urllib.parse, urllib.request
from pathlib import Path

UA = "MYIA-FabricasCorpus/1.0 (taller; +https://local; corpus-only)"
TIMEOUT = 20

def _get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()

def wiki_summary(title: str, lang: str = "es") -> dict | None:
    q = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{q}"
    try:
        st, raw = _get(url)
        if st != 200:
            return None
        d = json.loads(raw.decode("utf-8", errors="replace"))
        if d.get("type") == "disambiguation":
            return None
        extract = (d.get("extract") or "").strip()
        if len(extract) < 40:
            return None
        return {
            "id": f"wiki_{lang}_{d.get('titles',{}).get('canonical') or title}",
            "titulo": d.get("title") or title,
            "url": d.get("content_urls", {}).get("desktop", {}).get("page") or url,
            "texto": extract,
            "origen": "wikipedia_rest_summary",
            "lang": lang,
        }
    except Exception as e:
        return {"error": str(e), "titulo": title, "lang": lang}

def buscar_terminos(terminos: list[str], langs=("es", "en")) -> list[dict]:
    out, seen = [], set()
    for t in terminos:
        t = (t or "").strip()
        if not t:
            continue
        for lang in langs:
            hit = wiki_summary(t, lang)
            if not hit or hit.get("error") or not hit.get("texto"):
                continue
            key =[REDACTED]
            if key in seen:
                continue
            seen.add(key)
            hit["sha256"] = hashlib.sha256(hit["texto"].encode()).hexdigest()
            # cita literal corta (para revisor)
            cita = hit["texto"][:240].rsplit(" ", 1)[0]
            hit["cita_literal"] = cita
            out.append(hit)
            time.sleep(0.15)  # cortesía
    return out

def armar_corpus(pieza_id: str, terminos: list[str], dest: Path) -> dict:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "fuentes").mkdir(exist_ok=True)
    plan = {"pieza_id": pieza_id, "terminos": terminos, "via": "B_wikipedia", "gasto_usd": 0}
    (dest / "plan_busqueda.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    fuentes = buscar_terminos(terminos)
    entries = []
    for i, f in enumerate(fuentes):
        fn = dest / "fuentes" / f"{i:02d}_{re.sub(r'[^a-zA-Z0-9_-]+','_', f.get('id','x'))[:60]}.txt"
        body = f"TITULO: {f.get('titulo')}\nURL: {f.get('url')}\nSHA256: {f.get('sha256')}\n\n{f.get('texto')}\n"
        fn.write_text(body, encoding="utf-8")
        entries.append({
            "id": f.get("id"), "titulo": f.get("titulo"), "url": f.get("url"),
            "sha256": f.get("sha256"), "cita": f.get("cita_literal"),
            "archivo": str(fn.name), "origen": f.get("origen"), "lang": f.get("lang"),
        })
    corpus = {
        "schema": "corpus_via_b/v1",
        "pieza_id": pieza_id,
        "gasto_usd": 0,
        "n_fuentes": len(entries),
        "fuentes": entries,
        "terminos": terminos,
    }
    (dest / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding="utf-8")
    return corpus
