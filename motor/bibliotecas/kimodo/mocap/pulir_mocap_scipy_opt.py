# -*- coding: utf-8 -*-
"""Optimiza poses de un JSON de retarget contra el costo del revisor (fuera + Z apoyo).

Corre bajo Blender. Usa descenso por coordenadas (pasos finitos visibles) + SciPy
Powell opcional. Misma idea que LIBRERIAS_MOTOR poc_scipy_pose_cd.py, pero sobre
secuencia de claves mocap y sin huesos/apoyos fijos de Kael.

Uso (vía pulir_mocap.optimize_retarget_vs_revisor o a mano):
  blender -b -P pulir_mocap_scipy_opt.py -- config.json
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
from pathlib import Path

CFG_PATH = Path(sys.argv[sys.argv.index("--") + 1])
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))

MOTOR = Path(CFG["motor"])
TARGET = Path(CFG.get("target_blender") or "/workspace/LIBRERIAS_MOTOR_20261104/target_blender")
sys.path.insert(0, str(MOTOR))
if TARGET.exists():
    sys.path.insert(0, str(TARGET))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
import esqueleto_adn as EA  # noqa: E402
import rig  # noqa: E402
import movimiento_natural as MN  # noqa: E402

try:
    from scipy.optimize import minimize as scipy_minimize

    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False
    scipy_minimize = None

ADN_MAP = {
    "kael": "ADN_kael_sin_mochila.md",
    "alien": "ADN_alien_guardian.md",
    "novia": "ADN_novia_cardigan.md",
}
COL = {"_": (0.55, 0.5, 0.45)}


def _grupo(h: str) -> str:
    return h.split("_")[0]


def _clamp_ang(ang: dict) -> dict:
    a = copy.deepcopy(ang)
    for h, ejes in list(a.items()):
        if h == "raiz":
            continue
        lim = EA.LIMITES.get(_grupo(h))
        if not lim:
            continue
        for i in range(min(3, len(ejes))):
            lo, hi = lim[i]
            ejes[i] = max(lo, min(hi, float(ejes[i])))
    return a


def _punto(A, h: str):
    pb = A.pose.bones[h]
    pt = pb.head if h.startswith("pierna") else pb.tail
    return A.matrix_world @ pt


def _apply(A, rad, ang):
    a = _clamp_ang(ang)
    rig.aplicar(A, a)
    p, r, _ = a.get("raiz", [0, 0, 0])
    A.rotation_euler = (math.radians(-p), math.radians(r), 0.0)
    A.location = (0, 0, 0)
    bpy.context.view_layer.update()
    z, _ = rig.suelo(A, rad)
    A.location.z -= z
    bpy.context.view_layer.update()
    return a


def _medir(A, rad, ang, apoyos):
    _apply(A, rad, ang)
    com = MN.centro_masa(A, rad)
    apo = {h: _punto(A, h) for h in apoyos if h in A.pose.bones}
    pts = MN.puntos_contacto(A, rad, 0.06, apo if apo else None)
    fuera = float(MN.distancia_fuera(com, pts))
    ez = 0.0
    for h in apoyos:
        if h not in A.pose.bones:
            continue
        pp = _punto(A, h)
        r0 = 0.0 if h.startswith("pie") else rad.get(h, 0.04)
        ez += (pp.z - r0) ** 2
    return fuera, ez, (com.x, com.y, com.z)


def _dofs_from_pose(ang: dict, apoyos: list) -> list[tuple[str, int]]:
    """DOFs universales: tronco + raíces de extremidad + ejes útiles; sin pies plantados en giro raro."""
    prefer = []
    order = [
        ("raiz", 0),
        ("raiz", 1),
        ("columna", 0),
        ("columna", 1),
        ("pecho", 0),
        ("pecho", 1),
        ("muslo_L", 0),
        ("muslo_L", 1),
        ("muslo_R", 0),
        ("muslo_R", 1),
        ("pierna_L", 0),
        ("pierna_R", 0),
        ("brazo_L", 0),
        ("brazo_L", 1),
        ("brazo_R", 0),
        ("brazo_R", 1),
        ("antebrazo_L", 0),
        ("antebrazo_R", 0),
    ]
    for h, e in order:
        if h in ang:
            prefer.append((h, e))
    # si faltan, añadir cualquier hueso no-pie con ejes 0/1
    have = set(prefer)
    for h in ang:
        if h.startswith("pie") or h.startswith("mano") or h in ("cabeza", "cuello"):
            continue
        for e in (0, 1):
            if (h, e) not in have:
                prefer.append((h, e))
                have.add((h, e))
    return prefer


def _cost(A, rad, ang, ang0, apoyos, max_dev_deg: float):
    fuera, ez, _ = _medir(A, rad, ang, apoyos)
    # Costo alineado al revisor: umbral ~0.02–0.06 m, fuera fuerte
    c = 5000.0 * max(0.0, fuera - 0.02) ** 2 + 800.0 * fuera ** 2 + 2000.0 * ez
    # Fidelidad a la pose mocap (universal, grados)
    dev = 0.0
    n = 0
    for h, v0 in ang0.items():
        v = ang.get(h, v0)
        for i in range(3):
            d = float(v[i]) - float(v0[i])
            dev += d * d
            n += 1
            if abs(d) > max_dev_deg:
                c += 50.0 * (abs(d) - max_dev_deg) ** 2
    c += 0.15 * (dev / max(1, n))
    return c, fuera, ez


def _coord_descent(A, rad, ang, ang0, apoyos, dofs, max_dev_deg, pasos=None):
    if pasos is None:
        pasos = [8.0, 4.0, 2.0, 1.0, 0.5]
    c0, f0, e0 = _cost(A, rad, ang, ang0, apoyos, max_dev_deg)
    evals = 1
    for paso in pasos:
        mejoro = True
        while mejoro:
            mejoro = False
            for h, eje in dofs:
                ang.setdefault(h, [0.0, 0.0, 0.0])
                v0 = float(ang[h][eje])
                # no alejarse más de max_dev_deg del original
                lo = float(ang0.get(h, ang[h])[eje]) - max_dev_deg
                hi = float(ang0.get(h, ang[h])[eje]) + max_dev_deg
                best = v0
                bestc = c0
                for s in (-1.0, 1.0):
                    cand = v0 + s * paso
                    if cand < lo or cand > hi:
                        continue
                    ang[h][eje] = cand
                    c, f, ez = _cost(A, rad, ang, ang0, apoyos, max_dev_deg)
                    evals += 1
                    if c < bestc - 1e-6:
                        bestc = c
                        best = cand
                        mejoro = True
                ang[h][eje] = best
                c0 = bestc
    c1, f1, e1 = _cost(A, rad, ang, ang0, apoyos, max_dev_deg)
    return ang, {"costo": c1, "fuera": f1, "ez": e1, "evals": evals, "fuera0": f0, "ez0": e0}


def _scipy_powell(A, rad, ang, ang0, apoyos, dofs, max_dev_deg, maxiter=40):
    if not HAS_SCIPY or not dofs:
        return ang, {"usado": False}
    x0 = np.array([float(ang.get(h, [0, 0, 0])[e]) for h, e in dofs], dtype=np.float64)
    bounds = []
    for h, e in dofs:
        base = float(ang0.get(h, ang.get(h, [0, 0, 0]))[e])
        bounds.append((base - max_dev_deg, base + max_dev_deg))

    def fun(x):
        a = copy.deepcopy(ang)
        for i, (h, e) in enumerate(dofs):
            a.setdefault(h, [0.0, 0.0, 0.0])
            a[h][e] = float(x[i])
        c, _, _ = _cost(A, rad, a, ang0, apoyos, max_dev_deg)
        return c

    res = scipy_minimize(fun, x0, method="Powell", bounds=bounds, options={"maxiter": maxiter, "xtol": 0.05, "ftol": 1e-4})
    a = copy.deepcopy(ang)
    for i, (h, e) in enumerate(dofs):
        a.setdefault(h, [0.0, 0.0, 0.0])
        a[h][e] = float(res.x[i])
    return a, {"usado": True, "success": bool(res.success), "nfev": int(getattr(res, "nfev", 0)), "fun": float(res.fun)}


def main():
    t0 = time.time()
    data = json.loads(Path(CFG["src"]).read_text(encoding="utf-8"))
    pid = CFG.get("personaje") or data.get("personaje") or "kael"
    if isinstance(pid, str) and "/" in pid:
        pid = Path(pid).stem.split("_")[0]
    # personaje en retarget suele ser "kael"
    if pid not in ADN_MAP:
        # intentar deducir
        for k in ADN_MAP:
            if k in str(data.get("personaje", "")).lower() or k in Path(CFG["src"]).stem.lower():
                pid = k
                break
        else:
            pid = "kael"

    adn_path = Path(CFG["adn_md"]) if CFG.get("adn_md") else (MOTOR / "adn" / ADN_MAP[pid])
    perfil = EA.leer_adn(adn_path.read_text(encoding="utf-8"), pid)
    rad = {b["nombre"]: b["radio"] for b in EA.huesos(perfil)}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    A = rig.crear(pid, perfil, COL)

    poses = data["poses"]
    fases = {f["pose"]: f for f in data.get("fases", []) if isinstance(f, dict) and "pose" in f}
    max_dev = float(CFG.get("max_dev_deg", 18.0))
    per_pose = []
    n_mejoradas = 0

    names = list(poses.keys())

    def _apoyos_of(name, pose):
        fase = fases.get(name, {})
        apoyos = list(pose.get("apoyos") or fase.get("apoyos") or [])
        if not apoyos:
            apoyos = [h for h in ("pie_L", "pie_R", "mano_L", "mano_R") if h in A.pose.bones]
        return apoyos

    def _opt_one(name, pose, force=False):
        nonlocal n_mejoradas
        ang0 = {h: list(map(float, v)) for h, v in pose["angulos"].items()}
        ang = copy.deepcopy(ang0)
        apoyos = _apoyos_of(name, pose)
        dofs = _dofs_from_pose(ang, apoyos)
        f_before, ez_before, _ = _medir(A, rad, ang, apoyos)
        md = max_dev
        if f_before > 0.1:
            md = max(md, 28.0)
        if (not force) and f_before <= 0.025 and ez_before <= 0.003:
            per_pose.append({"pose": name, "skip": True, "fuera": f_before})
            return False
        ang, info_cd = _coord_descent(A, rad, ang, ang0, apoyos, dofs, md)
        info_sp = {"usado": False}
        if info_cd["fuera"] > 0.02:
            ang2, info_sp = _scipy_powell(A, rad, ang, ang0, apoyos, dofs, md, maxiter=60)
            c2, f2, e2 = _cost(A, rad, ang2, ang0, apoyos, md)
            if f2 <= info_cd["fuera"] + 1e-6 and c2 <= info_cd["costo"] + 1e-6:
                ang = ang2
                info_cd = {
                    "costo": c2,
                    "fuera": f2,
                    "ez": e2,
                    "evals": info_cd["evals"] + info_sp.get("nfev", 0),
                    "fuera0": info_cd["fuera0"],
                    "ez0": info_cd["ez0"],
                }
        pose["angulos"] = {h: [round(float(x), 2) for x in v] for h, v in ang.items()}
        if info_cd["fuera"] < f_before - 1e-4:
            n_mejoradas += 1
        per_pose.append(
            {
                "pose": name,
                "apoyos": apoyos,
                "fuera_antes": round(f_before, 4),
                "fuera_despues": round(info_cd["fuera"], 4),
                "ez_antes": round(ez_before, 5),
                "ez_despues": round(info_cd["ez"], 5),
                "evals": info_cd["evals"],
                "max_dev": md,
                "scipy": info_sp,
            }
        )
        return True

    # 1) optimizar cada clave
    for name in names:
        _opt_one(name, poses[name], force=False)

    # 2) si el punto medio entre claves consecutivas sigue fuera, re-optimizar ambas con force
    for i in range(len(names) - 1):
        n0, n1 = names[i], names[i + 1]
        a0 = poses[n0]["angulos"]
        a1 = poses[n1]["angulos"]
        mid = {}
        bones = set(a0) | set(a1)
        for h in bones:
            v0 = a0.get(h, [0, 0, 0])
            v1 = a1.get(h, [0, 0, 0])
            mid[h] = [(float(v0[j]) + float(v1[j])) * 0.5 for j in range(3)]
        apoyos = list(dict.fromkeys(_apoyos_of(n0, poses[n0]) + _apoyos_of(n1, poses[n1])))
        fmid, _, _ = _medir(A, rad, mid, apoyos)
        if fmid > 0.04:
            _opt_one(n0, poses[n0], force=True)
            _opt_one(n1, poses[n1], force=True)

    dst = Path(CFG["dst"])
    dst.parent.mkdir(parents=True, exist_ok=True)
    data["_pulir_mocap_scipy"] = {
        "personaje": pid,
        "has_scipy": HAS_SCIPY,
        "max_dev_deg": max_dev,
        "n_mejoradas": n_mejoradas,
        "tiempo_s": round(time.time() - t0, 2),
    }
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    report = {
        "ok": True,
        "src": CFG["src"],
        "dst": str(dst),
        "personaje": pid,
        "has_scipy": HAS_SCIPY,
        "n_mejoradas": n_mejoradas,
        "per_pose": per_pose,
        "tiempo_s": round(time.time() - t0, 2),
    }
    Path(str(dst) + ".scipy_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SCIPY_OPT_OK", dst, "mejoradas", n_mejoradas, "t", report["tiempo_s"])


if __name__ == "__main__":
    main()
