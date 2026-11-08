# -*- coding: utf-8 -*-
"""Fuente de movimiento Kimodo (generador) para la escalera de respaldo — universal.

Camino: BVH (o JSON de retarget ya pulido) -> pulir_mocap (+ SciPy vs revisor) ->
retarget al esqueleto del personaje -> el revisor elige si aprueba (misma métrica
que CMU/Argon). No fuerza por nombre de tramo ni de personaje.

Interruptor: motor/mocap_kimodo.off  →  apagado (escalera idéntica al original).
Sin el .off → el escalón Kimodo participa como un paso más de la escalera.

Biblioteca local: mocap/kimodo_lib/*.json (retarget ya listo) y mocap/kimodo_lib/*.bvh.
"""
from __future__ import annotations

import copy
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MOCAP = AQUI / "mocap"
LIB = MOCAP / "kimodo_lib"
B = "/home/box/apps/blender-5.2.3-linux-x64/blender"


def activo() -> bool:
    import movimiento_natural as MN
    return MN.activo("mocap_kimodo")


def ahora() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def listar_candidatos(lib: Path | None = None) -> list[dict]:
    """Lista candidatos universales (cualquier .json retarget o .bvh en la lib)."""
    root = Path(lib or LIB)
    out = []
    if not root.exists():
        return out
    for p in sorted(root.glob("rt_*.json")) + sorted(root.glob("*.json")):
        if p.name.endswith(".scipy_report.json"):
            continue
        out.append({"tipo": "retarget_json", "path": p, "id": p.stem})
    for p in sorted(root.glob("*.bvh")):
        out.append({"tipo": "bvh", "path": p, "id": p.stem})
    # dedupe by id preferring json
    seen = set()
    uniq = []
    for c in out:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        uniq.append(c)
    return uniq


def _inyectar_retarget(cat: dict, rt: dict, pid: str, mov: str, tag: str) -> str:
    """Inserta poses/fases del retarget como movimiento candidato. Nombre = mov + _kimodo_ + tag."""
    nm = f"{mov}_kimodo_{tag}"
    for n, p in rt["poses"].items():
        cat["poses"][n] = {
            **p,
            "origen": f"kimodo/{tag} retarget a {pid}",
            "fecha": ahora(),
        }
    base = cat["movimientos"].get(mov, {})
    cat["movimientos"][nm] = {
        "descripcion": f"{base.get('descripcion', mov)} (Kimodo {tag})",
        "fases": rt["fases"],
        "objetivos": base.get("objetivos", []),
        "excepciones": {},
        "temblor_deg": base.get("temblor_deg", 0),
        "fisica": base.get("fisica"),
        "origen": "kimodo",
        "fuente": {
            "generador": "kimodo",
            "tag": tag,
            "licencia": "uso según licencia del generador/BVH de origen",
            "cuadros_bvh": rt.get("cuadros_bvh"),
        },
        "validado": False,
        "fecha": ahora(),
        "escena": base.get("escena"),
    }
    return nm


def preparar_candidato(
    cand: dict,
    pid: str,
    mov: str,
    trab: Path,
    *,
    pulir: bool = True,
    scipy: bool = True,
) -> Path | None:
    """Devuelve path a JSON retarget listo (tras pulido opcional). Universal."""
    trab = Path(trab)
    trab.mkdir(parents=True, exist_ok=True)
    tag = cand["id"]
    if cand["tipo"] == "retarget_json":
        src = Path(cand["path"])
        dst = trab / f"rt_{tag}.json"
        shutil.copy(src, dst)
    else:
        # BVH -> retarget Blender
        bvh = Path(cand["path"])
        # optional polish BVH first
        bvh_use = bvh
        if pulir:
            sys.path.insert(0, str(MOCAP))
            try:
                import pulir_mocap as PM  # noqa: WPS440

                polished = trab / f"{tag}_pulido.bvh"
                # footlock+smooth if module allows
                if PM.activo():
                    # always allow explicit polish when Kimodo step runs
                    try:
                        PM.polish_bvh(bvh, polished, do_smooth=True, do_footlock=True)
                        bvh_use = polished
                    except Exception as e:
                        (trab / f"pulir_bvh_{tag}.err").write_text(str(e))
                        raise RuntimeError('Pulida obligatoria falló') from e
                else:
                    raise RuntimeError('Pulida apagada por .off')
            except Exception as e:
                (trab / f"import_pulir_{tag}.err").write_text(str(e))
                raise RuntimeError("No se permite candidato sin pulida") from e
        dst = trab / f"rt_{tag}.json"
        r = subprocess.run(
            [B, "-b", "-P", str(MOCAP / "bvh_retarget.py"), "--", str(bvh_use), pid, str(dst), "14"],
            capture_output=True,
            text=True,
            timeout=900,
        )
        (trab / f"retarget_{tag}.log").write_text((r.stdout or "")[-2000:] + "\n" + (r.stderr or "")[-2000:])
        if not dst.exists():
            return None

    # Post-retarget angle polish + SciPy vs reviewer (si no hay .off de esos pasos)
    if pulir:
        sys.path.insert(0, str(MOCAP))
        try:
            import pulir_mocap as PM

            ang = trab / f"rt_{tag}_ang.json"
            try:
                PM.polish_retarget_json(dst, ang, margin_deg=8.0)
                dst = ang
            except Exception as e:
                (trab / f"pulir_ang_{tag}.err").write_text(str(e))
        except Exception as e:
            (trab / f"import_pulir2_{tag}.err").write_text(str(e))
    if scipy:
        sys.path.insert(0, str(MOCAP))
        try:
            import pulir_mocap as PM

            if PM.scipy_activo():
                sci = trab / f"rt_{tag}_scipy.json"
                rep = PM.optimize_retarget_vs_revisor(dst, sci, personaje=pid)
                if rep.get("ok") and sci.exists():
                    dst = sci
                json.dump(rep, open(trab / f"scipy_{tag}.json", "w"), ensure_ascii=False, indent=2)
        except Exception as e:
            (trab / f"scipy_{tag}.err").write_text(str(e))
    return dst


def paso_escalera(
    *,
    pid: str,
    mov: str,
    cat0: Path,
    asig0: Path,
    trab: Path,
    validar_fn,
    puntaje_fn,
    clave_fn,
    max_cand: int = 4,
    log: dict | None = None,
):
    """Escalón Kimodo: prueba candidatos, el revisor elige el mejor que apruebe.

    validar_fn(cat, asig, tag) -> (RV, tramos)
    Devuelve (cat, asig, mov_final, metricas, cand_id) o None.
    """
    if not activo():
        if log is not None:
            log.setdefault("pasos", []).append({"escalon": "kimodo", "omitido": True, "motivo": "mocap_kimodo.off"})
        return None

    cands = listar_candidatos()[:max_cand]
    entrada = {"escalon": "kimodo", "candidatos": [c["id"] for c in cands], "resultados": {}}
    if log is not None:
        log.setdefault("pasos", []).append(entrada)

    res = []
    for cand in cands:
        rt_path = preparar_candidato(cand, pid, mov, Path(trab) / f"kimodo_{cand['id']}")
        if not rt_path or not rt_path.exists():
            entrada["resultados"][cand["id"]] = {"error": "sin retarget"}
            continue
        rt = json.load(open(rt_path))
        C = json.load(open(cat0))
        nm = _inyectar_retarget(C, rt, pid, mov, cand["id"])
        cf = Path(trab) / f"cat_kimodo_{cand['id']}.json"
        json.dump(C, open(cf, "w"), ensure_ascii=False)
        A = json.load(open(asig0))
        for x in A:
            if x.get("personaje") == pid and x.get("movimiento") == mov:
                x["movimiento"] = nm
        af = Path(trab) / f"asig_kimodo_{cand['id']}.json"
        json.dump(A, open(af, "w"), ensure_ascii=False)
        rv, T = validar_fn(cf, af, f"kimodo_{cand['id']}")
        m = T.get(f"{pid}:{nm}", {"aprobado": False, "error": "armado falló", "cuadros_fuera": 99, "saltitos": 9, "resbale_max_cm": 99, "acel_com_max_m_s2": 99})
        entrada["resultados"][cand["id"]] = m
        res.append((puntaje_fn(m), bool(m.get("aprobado")), cf, af, nm, m, cand["id"]))

    ok = sorted([r for r in res if r[1]], key=lambda r: r[0])
    if ok:
        best = ok[0]
        return best[2], best[3], best[4], best[5], best[6]
    if res:
        # no aprobado: devolver el de menor puntaje para info (no aprobar)
        best = sorted(res, key=lambda r: r[0])[0]
        entrada["mejor_no_aprobado"] = {"id": best[6], "metricas": best[5], "movimiento": best[4]}
    return None


def aplicar_retarget_a_catalogo(
    cat_path: Path,
    asig_path: Path,
    rt_path: Path,
    pid: str,
    mov: str,
    tag: str,
    *,
    reemplazar_nombre: bool = False,
) -> tuple[Path, Path, str]:
    """Utilidad de prueba: escribe cat/asig con el candidato Kimodo inyectado.

    Si reemplazar_nombre=True, el movimiento se guarda con el mismo nombre `mov`
    (sustituye el contenido) — útil para armar la escena completa sin cambiar la asignación.
    """
    C = json.load(open(cat_path))
    rt = json.load(open(rt_path))
    if reemplazar_nombre:
        for n, p in rt["poses"].items():
            C["poses"][n] = {**p, "origen": f"kimodo/{tag}", "fecha": ahora()}
        base = C["movimientos"][mov]
        C["movimientos"][mov] = {
            **base,
            "fases": rt["fases"],
            "origen": "kimodo",
            "fuente": {"generador": "kimodo", "tag": tag},
            "validado": False,
            "fecha": ahora(),
            "descripcion": f"{base.get('descripcion', mov)} [Kimodo {tag}]",
        }
        nm = mov
        A = json.load(open(asig_path))
    else:
        nm = _inyectar_retarget(C, rt, pid, mov, tag)
        A = json.load(open(asig_path))
        for x in A:
            if x.get("personaje") == pid and x.get("movimiento") == mov:
                x["movimiento"] = nm
    out_c = Path(cat_path)
    out_a = Path(asig_path)
    json.dump(C, open(out_c, "w"), ensure_ascii=False, indent=1)
    json.dump(A, open(out_a, "w"), ensure_ascii=False, indent=1)
    return out_c, out_a, nm
