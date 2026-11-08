#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pulido universal de mocap BVH (COPY del motor v9).

Suaviza la trayectoria de la raíz (anti-aceleración) y ancla pies/manos en
contacto para reducir resbale. Pensado para cualquier BVH/personaje: umbrales
relativos a la altura del personaje, sin valores fijos de Kael.

Partes adaptadas de código Apache-2.0 de NVIDIA:
  - kimodo/ardy motion_rep/smooth_root.py  (TrajectorySmoother ADMM + smooth_signal)
  - ardy/motion_rep/feet.py               (heurística altura+velocidad de contacto)
SPDX-License-Identifier: Apache-2.0 (porciones NVIDIA) + uso en motor Argon.

Interruptor: crear ``pulir_mocap.off`` junto a este archivo (o en motor/) para
indicar que el pipeline NO debe aplicarlo automáticamente. Este script se puede
llamar igual a mano para experimentos.

Paso final opcional SciPy/revisor: ``optimize_retarget_vs_revisor`` (Blender FK).
Interruptor propio: ``pulir_mocap_scipy.off``.

Uso:
  python3 pulir_mocap.py entrada.bvh salida.bvh [--smooth] [--footlock]
      [--margin 0.06] [--npz opc.npz] [--hands] [--report json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
MOTOR = AQUI.parent
OFF = AQUI / "pulir_mocap.off"
if not OFF.exists():
    OFF = MOTOR / "pulir_mocap.off"


def activo() -> bool:
    """True si el pulido está permitido (no existe pulir_mocap.off)."""
    return not OFF.exists()


# ---------------------------------------------------------------------------
# ADMM TrajectorySmoother — adaptado de NVIDIA kimodo/ardy smooth_root.py
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
# ---------------------------------------------------------------------------
from scipy import sparse
from scipy.sparse.linalg import splu


class TrajectorySmoother:
    """Minimiza aceleración con márgenes por cuadro (ADMM). Ver docstring NVIDIA."""

    def __init__(self, margins, pos_weight=0.0, loop=False, admm_iters=100, alpha_overrelax=1.0, circle_project=False):
        self.pos_weight = pos_weight
        self.admm_iters = admm_iters
        self.alpha_overrelax = alpha_overrelax
        self.circle_project = circle_project
        N = len(margins)
        self.margin_vals = np.asarray(margins, dtype=np.float64)
        a_data, a_rows, a_cols = [], [], []
        for i in range(1, N - 1):
            a_data.extend([-1.0, 2.0, -1.0])
            a_rows.extend([i, i, i])
            a_cols.extend([i - 1, i, i + 1])
        if loop:
            a_data.extend([-1.0, 2.0, -1.0]); a_rows.extend([0, 0, 0]); a_cols.extend([N - 1, 0, 1])
            a_data.extend([-1.0, 2.0, -1.0]); a_rows.extend([N - 1, N - 1, N - 1]); a_cols.extend([N - 2, N - 1, 0])
        A = sparse.csr_matrix((a_data, (a_rows, a_cols)), shape=(N, N))
        I = sparse.eye(N)
        M = pos_weight * I + A.T @ A
        diag_max = max(abs(M.diagonal())) if N else 1.0
        self.admm_stepsize = 0.25 * np.sqrt(diag_max)
        M = M + self.admm_stepsize * I
        self.system_lu = splu(M.tocsc())

    def smooth(self, targets, x0):
        x_target = targets.copy()
        x = x0.copy()
        z = np.zeros_like(x)
        u = np.zeros_like(x)
        for _ in range(self.admm_iters):
            self._z_update(z, x, x_target, u)
            u[:] += self.alpha_overrelax * (x - z)
            r = self.pos_weight * x_target + self.admm_stepsize * (z - u)
            x[:] = self.system_lu.solve(r)
        return x

    def _z_update(self, z, x, z_t, u):
        z[:] = x + u - z_t
        norms = np.linalg.norm(z, axis=1)
        mask = norms > self.margin_vals
        if np.any(mask):
            z[mask] *= (self.margin_vals[mask] / norms[mask])[:, None]
        z[:] += z_t
        if self.circle_project:
            z[:] = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-6)


def smooth_signal(x, margins, pos_weight=0.0, alpha_overrelax=1.8, admm_iters=500, circle_project=False):
    """Multiresolución + ADMM (NVIDIA smooth_root.smooth_signal). x: (T, D)."""
    x = np.asarray(x, dtype=np.float64)
    margins = np.asarray(margins, dtype=np.float64)
    x_smoothed = np.zeros_like(x)
    x_smoothed[:] = x.mean(axis=0, keepdims=True)
    levels = int(math.floor(math.log2(max(len(x), 2))))
    levels = max(levels - 4, 1)
    stepsize = 2 ** levels
    while True:
        smoother = TrajectorySmoother(
            margins=margins[::stepsize],
            pos_weight=pos_weight,
            alpha_overrelax=alpha_overrelax,
            admm_iters=admm_iters,
            circle_project=circle_project,
        )
        x_smoothed[::stepsize] = smoother.smooth(x[::stepsize], x_smoothed[::stepsize])
        next_stepsize = stepsize // 2
        num_steps = len(x_smoothed[::stepsize])
        num_interleaved = len(x_smoothed[next_stepsize::stepsize])
        if num_interleaved == num_steps:
            x_smoothed[next_stepsize::stepsize][-1] = (
                x_smoothed[::stepsize][-1] + (x_smoothed[::stepsize][-1] - x_smoothed[::stepsize][-2]) / 2
            )
            num_interleaved -= 1
        if num_interleaved > 0:
            x_smoothed[next_stepsize::stepsize][:num_interleaved] = (
                x_smoothed[::stepsize][:-1] + x_smoothed[::stepsize][1:]
            ) / 2
        if stepsize == 1:
            break
        stepsize //= 2
    return x_smoothed


def smooth_root_xz(hips_xyz: np.ndarray, margin_m: float = 0.06, pos_weight: float = 0.0) -> np.ndarray:
    """Suaviza XZ de la cadera; conserva Y. hips en metros (T,3) Y-up."""
    out = hips_xyz.copy()
    xz = hips_xyz[:, [0, 2]]
    margins = np.full(len(hips_xyz), float(margin_m))
    sm = smooth_signal(xz, margins, pos_weight=pos_weight)
    out[:, 0] = sm[:, 0]
    out[:, 2] = sm[:, 1]
    return out


# ---------------------------------------------------------------------------
# BVH I/O mínimo (canales Root/Hips posición)
# ---------------------------------------------------------------------------
def _parse_bvh(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    motion_i = next(i for i, l in enumerate(lines) if l.strip() == "MOTION")
    hier = lines[:motion_i]
    # channel layout
    groups = []  # (joint_name, n, names, offset_in_frame)
    name = None
    offset = 0
    for l in hier:
        s = l.strip()
        if s.startswith("ROOT") or s.startswith("JOINT"):
            name = s.split()[1]
        elif s.startswith("CHANNELS"):
            parts = s.split()
            n = int(parts[1])
            ch = parts[2:]
            groups.append({"joint": name, "n": n, "ch": ch, "off": offset})
            offset += n
    n_frames = int(lines[motion_i + 1].split()[1])
    frame_time = float(lines[motion_i + 2].split()[2])
    frames = []
    for l in lines[motion_i + 3 : motion_i + 3 + n_frames]:
        if not l.strip():
            continue
        frames.append([float(x) for x in l.split()])
    frames = np.asarray(frames, dtype=np.float64)
    return {"hier": hier, "groups": groups, "n_frames": n_frames, "frame_time": frame_time, "frames": frames, "motion_i": motion_i, "raw_lines": lines}


def _find_pos_joint(groups, prefer=("Hips", "hips", "Root", "root", "pelvis", "Pelvis")):
    """Junta con Xposition Yposition Zposition; preferir Hips si Root está fijo en 0."""
    candidates = []
    for g in groups:
        if "Xposition" in g["ch"] and "Yposition" in g["ch"] and "Zposition" in g["ch"]:
            candidates.append(g)
    if not candidates:
        raise RuntimeError("BVH sin canales de posición")
    # Prefer joint whose position actually moves
    by_name = {c["joint"]: c for c in candidates}
    for p in prefer:
        if p in by_name:
            return by_name[p]
    return candidates[0]


def _hips_xyz_meters(bvh, unit_scale: float | None = None):
    """Devuelve (T,3) en metros Y-up y el factor cm→m usado."""
    g = _find_pos_joint(bvh["groups"])
    # Si hay Root y Hips, medir cuál se mueve
    moving = []
    for cand in bvh["groups"]:
        if "Xposition" not in cand["ch"]:
            continue
        ix = cand["off"] + cand["ch"].index("Xposition")
        iy = cand["off"] + cand["ch"].index("Yposition")
        iz = cand["off"] + cand["ch"].index("Zposition")
        pos = bvh["frames"][:, [ix, iy, iz]]
        span = float(np.linalg.norm(pos.max(0) - pos.min(0)))
        moving.append((span, cand, pos))
    moving.sort(key=lambda x: -x[0])
    span, g, pos = moving[0]
    # Auto unit: si altura Y max > 3, asumir cm
    if unit_scale is None:
        yspan = float(pos[:, 1].max() - pos[:, 1].min())
        ymax = float(np.abs(pos[:, 1]).max())
        unit_scale = 0.01 if (ymax > 3.0 or yspan > 3.0) else 1.0
    return pos * unit_scale, g, unit_scale


def _write_bvh(bvh, frames_new: np.ndarray, out: Path):
    lines = list(bvh["hier"]) + [
        "MOTION",
        f"Frames: {len(frames_new)}",
        f"Frame Time: {bvh['frame_time']}",
    ]
    for row in frames_new:
        lines.append(" ".join(f"{v:.6f}" for v in row))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Contacto pies/manos — heurística NVIDIA feet.py (altura + velocidad)
# ---------------------------------------------------------------------------
def detect_contacts_from_positions(
    positions: np.ndarray,
    dt: float,
    vel_thres: float,
    height_thresh: float,
) -> np.ndarray:
    """positions (T, J, 3) Y-up metros. Devuelve (T, J) bool contacto."""
    vel = np.zeros_like(positions)
    vel[1:] = (positions[1:] - positions[:-1]) / max(dt, 1e-6)
    vel[0] = vel[1] if len(vel) > 1 else 0
    speed = np.linalg.norm(vel, axis=-1)
    height = positions[..., 1]
    return (speed < vel_thres) & (height < height_thresh)


def foot_lock_root_shift(
    hips: np.ndarray,
    ee_pos: np.ndarray,
    contacts: np.ndarray,
) -> np.ndarray:
    """Ancla horizontales de efectores en contacto desplazando la raíz XZ.

    hips (T,3), ee_pos (T,E,3), contacts (T,E). Universal: no asume personaje.
    En un segmento de contacto, el ancla es la posición XZ del primer cuadro.
    """
    out = hips.copy()
    T, E, _ = ee_pos.shape
    # Corrección acumulada aplicada a la cadera (y por tanto a todo el cuerpo)
    for e in range(E):
        t = 0
        while t < T:
            if not contacts[t, e]:
                t += 1
                continue
            t0 = t
            while t < T and contacts[t, e]:
                t += 1
            t1 = t  # exclusive
            anchor = ee_pos[t0, e, [0, 2]].copy()
            for i in range(t0, t1):
                cur = ee_pos[i, e, [0, 2]] + (out[i, [0, 2]] - hips[i, [0, 2]])
                # ee_pos ya es mundo del crudo; tras shift de hips la ee se mueve igual
                shift = anchor - (ee_pos[i, e, [0, 2]] + (out[i, [0, 2]] - hips[i, [0, 2]]))
                # Recalcular: mundo_nuevo = ee_crudo + (hips_nuevo - hips_crudo)
                # Queremos mundo_nuevo_xz = anchor → hips_nuevo_xz = hips_crudo_xz + anchor - ee_crudo_xz
                # Si varios EE, promediar al final por cuadro
                pass
    # Por cuadro: promedio de shifts pedidos por EE en contacto
    for i in range(T):
        shifts = []
        for e in range(E):
            if contacts[i, e]:
                # ancla del segmento
                # buscar inicio de segmento
                t0 = i
                while t0 > 0 and contacts[t0 - 1, e]:
                    t0 -= 1
                anchor = ee_pos[t0, e, [0, 2]]
                shifts.append(anchor - ee_pos[i, e, [0, 2]])
        if shifts:
            sh = np.mean(shifts, axis=0)
            out[i, 0] = hips[i, 0] + sh[0]
            out[i, 2] = hips[i, 2] + sh[1]
    return out


def _ee_from_npz(npz_path: Path):
    """Si el npz Kimodo/ARDY trae posed_joints + foot_contacts, úsalos."""
    d = np.load(npz_path)
    keys = set(d.keys())
    out = {}
    if "root_positions" in keys:
        out["root"] = np.asarray(d["root_positions"], dtype=np.float64)
    if "smooth_root_pos" in keys:
        out["smooth_root"] = np.asarray(d["smooth_root_pos"], dtype=np.float64)
    if "posed_joints" in keys:
        out["posed"] = np.asarray(d["posed_joints"], dtype=np.float64)
    if "foot_contacts" in keys:
        out["fc"] = np.asarray(d["foot_contacts"])
    return out


def _guess_ee_indices(posed: np.ndarray) -> list[int]:
    """Elige hasta 6 articulaciones más bajas (pies/manos candidatos) de forma universal."""
    # mediana de altura en el clip
    med_y = np.median(posed[:, :, 1], axis=0)
    idx = np.argsort(med_y)[:6]
    return idx.tolist()


def polish_bvh(
    src: Path,
    dst: Path,
    *,
    do_smooth: bool = True,
    do_footlock: bool = True,
    margin_m: float = 0.06,
    pos_weight: float = 0.0,
    npz: Path | None = None,
    use_npz_smooth: bool = False,
    use_npz_contacts: bool = False,
    hands: bool = True,
    vel_factor: float = 0.15,
    height_factor: float = 0.12,
) -> dict:
    """Aplica pulido y escribe BVH. Devuelve reporte con desviaciones."""
    bvh = _parse_bvh(src)
    hips_m, g, scale = _hips_xyz_meters(bvh)
    dt = float(bvh["frame_time"])
    hips_new = hips_m.copy()
    report = {
        "src": str(src),
        "dst": str(dst),
        "n_frames": int(len(hips_m)),
        "dt": dt,
        "unit_scale": scale,
        "joint": g["joint"],
        "smooth": do_smooth,
        "footlock": do_footlock,
        "margin_m": margin_m,
        "pos_weight": pos_weight,
        "npz": str(npz) if npz else None,
        "license_note": "smooth_root/feet heuristics adapted from NVIDIA kimodo/ardy (Apache-2.0)",
    }

    npz_data = _ee_from_npz(npz) if npz and Path(npz).exists() else {}

    if do_smooth:
        if use_npz_smooth and "smooth_root" in npz_data:
            sr = npz_data["smooth_root"]
            # alinear longitud
            n = min(len(hips_new), len(sr))
            hips_new[:n, 0] = sr[:n, 0]
            hips_new[:n, 2] = sr[:n, 2]
            # Y se conserva del original (como get_smooth_root_pos)
            report["smooth_source"] = "npz.smooth_root_pos"
        else:
            hips_new = smooth_root_xz(hips_new, margin_m=margin_m, pos_weight=pos_weight)
            report["smooth_source"] = "admm_local"

    ee_pos = None
    contacts = None
    if do_footlock:
        if use_npz_contacts and "posed" in npz_data and "fc" in npz_data:
            posed = npz_data["posed"]
            fc = npz_data["fc"].astype(bool)
            # Si ya vienen pocos EE (<=8), usarlos en orden; si no, elegir los más bajos
            if posed.shape[1] <= 8:
                idxs = list(range(posed.shape[1]))
            else:
                idxs = _guess_ee_indices(posed)
            ee_pos = posed[:, idxs, :]
            if fc.ndim == 2 and fc.shape[1] == len(idxs):
                contacts = fc
            elif fc.ndim == 2 and fc.shape[1] >= len(idxs):
                contacts = fc[:, : len(idxs)]
            else:
                contacts = None
            report["ee_source"] = "npz.posed_joints"
            report["contact_source"] = "npz.foot_contacts" if contacts is not None else "detect"
        if ee_pos is None:
            # Sin npz: no tenemos FK aquí; footlock se omite salvo que el caller
            # pase posiciones. Señalamos en reporte.
            report["footlock_applied"] = False
            report["footlock_skip"] = "sin FK/npz: usar pulir_mocap_blender.py o --npz"
        else:
            # Umbrales relativos a altura del personaje
            height = float(np.percentile(ee_pos[:, :, 1], 95) - np.percentile(ee_pos[:, :, 1], 5))
            # mejor: altura de cadera
            char_h = float(np.percentile(hips_m[:, 1], 95))
            char_h = max(char_h, 0.5)
            vel_thres = vel_factor * char_h  # m/s relativo (factor * altura ≈ umbral)
            # feet.py usa umbrales absolutos; nosotros escalamos con altura
            # vel típica NVIDIA ~0.1-0.3 m/s; height ~0.05-0.15 m
            vel_thres = max(0.08, min(0.35, vel_factor * 1.0))  # cap razonable en m/s
            height_thresh = max(0.04, min(0.20, height_factor * char_h))
            if contacts is None:
                contacts = detect_contacts_from_positions(ee_pos, dt, vel_thres, height_thresh)
            # Si contacts es (T, K) con K!=E, recortar
            E = ee_pos.shape[1]
            if contacts.shape[1] > E:
                contacts = contacts[:, :E]
            elif contacts.shape[1] < E:
                # pad with detection for missing
                det = detect_contacts_from_positions(ee_pos, dt, vel_thres, height_thresh)
                c2 = det.copy()
                c2[:, : contacts.shape[1]] = contacts
                contacts = c2
            hips_before_fl = hips_new.copy()
            hips_new = foot_lock_root_shift(hips_before_fl, ee_pos[: len(hips_new)], contacts[: len(hips_new)])
            report["footlock_applied"] = True
            report["vel_thres"] = vel_thres
            report["height_thresh"] = height_thresh
            report["contact_rate"] = contacts.mean(axis=0).tolist()

    # Desviación de raíz
    report["root_shift_mean_m"] = float(np.linalg.norm(hips_new - hips_m, axis=-1).mean())
    report["root_shift_max_m"] = float(np.linalg.norm(hips_new - hips_m, axis=-1).max())

    # Escribir de vuelta en unidades del BVH
    frames = bvh["frames"].copy()
    ix = g["off"] + g["ch"].index("Xposition")
    iy = g["off"] + g["ch"].index("Yposition")
    iz = g["off"] + g["ch"].index("Zposition")
    frames[:, ix] = hips_new[:, 0] / scale
    frames[:, iy] = hips_new[:, 1] / scale
    frames[:, iz] = hips_new[:, 2] / scale
    dst.parent.mkdir(parents=True, exist_ok=True)
    _write_bvh(bvh, frames, dst)
    report["ok"] = True
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description="Pulir BVH (smooth root + foot lock)")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--smooth", action="store_true")
    p.add_argument("--footlock", action="store_true")
    p.add_argument("--margin", type=float, default=0.06)
    p.add_argument("--pos-weight", type=float, default=0.0)
    p.add_argument("--npz", default=None)
    p.add_argument("--use-npz-smooth", action="store_true")
    p.add_argument("--use-npz-contacts", action="store_true")
    p.add_argument("--hands", action="store_true", default=True)
    p.add_argument("--report", default=None)
    p.add_argument("--force", action="store_true", help="Ignorar pulir_mocap.off")
    args = p.parse_args(argv)
    if not args.force and not activo():
        print("PULIR_OFF: existe pulir_mocap.off (usa --force para forzar)")
        sys.exit(2)
    if not args.smooth and not args.footlock:
        args.smooth = True
        args.footlock = True
    rep = polish_bvh(
        Path(args.src),
        Path(args.dst),
        do_smooth=args.smooth,
        do_footlock=args.footlock,
        margin_m=args.margin,
        pos_weight=args.pos_weight,
        npz=Path(args.npz) if args.npz else None,
        use_npz_smooth=args.use_npz_smooth,
        use_npz_contacts=args.use_npz_contacts,
        hands=args.hands,
    )
    if args.report:
        Path(args.report).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PULIR_OK", json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Post-retarget: suavizar trayectorias angulares (universal, márgenes en grados)
# ---------------------------------------------------------------------------
def smooth_angle_track(values: np.ndarray, margin_deg: float = 8.0, pos_weight: float = 0.05) -> np.ndarray:
    """Suaviza una secuencia (T,) o (T,D) de ángulos en grados con ADMM.
    Los ángulos se tratan como R^n local (sin unwrap 360) — suficiente entre claves cercanas.
    """
    v = np.asarray(values, dtype=np.float64)
    if v.ndim == 1:
        v = v[:, None]
        squeeze = True
    else:
        squeeze = False
    T = len(v)
    if T < 3:
        return values
    margins = np.full(T, float(margin_deg))
    # Pin first and last tightly to preserve start/end pose
    margins[0] = 0.0
    margins[-1] = 0.0
    out = smooth_signal(v, margins, pos_weight=pos_weight, admm_iters=300)
    return out[:, 0] if squeeze else out


def polish_retarget_json(
    src_json: Path,
    dst_json: Path,
    *,
    margin_deg: float = 8.0,
    bones: list[str] | None = None,
    pos_weight: float = 0.05,
) -> dict:
    """Suaviza ángulos entre claves del JSON de retarget. No toca el BVH.

    Universal: mismos márgenes en grados para cualquier personaje/BVH.
    """
    data = json.loads(Path(src_json).read_text(encoding="utf-8"))
    poses = data["poses"]
    names = list(poses.keys())
    if not names:
        raise RuntimeError("sin poses")
    # orden temporal = orden de inserción del retarget
    bone_set = set()
    for p in poses.values():
        bone_set |= set(p["angulos"].keys())
    if bones:
        bone_set &= set(bones)
    tracks = {b: [] for b in bone_set}
    for n in names:
        ang = poses[n]["angulos"]
        for b in bone_set:
            tracks[b].append(list(ang.get(b, [0, 0, 0])))
    report = {"src": str(src_json), "dst": str(dst_json), "margin_deg": margin_deg, "n_keys": len(names), "bones": sorted(bone_set)}
    diffs = []
    for b, seq in tracks.items():
        arr = np.asarray(seq, dtype=np.float64)  # (T,3)
        sm = smooth_angle_track(arr, margin_deg=margin_deg, pos_weight=pos_weight)
        diffs.append(np.abs(sm - arr).mean())
        for i, n in enumerate(names):
            poses[n]["angulos"][b] = [round(float(x), 2) for x in sm[i]]
    report["ang_change_mean_deg"] = float(np.mean(diffs)) if diffs else 0.0
    # fases intactas (tiempos/apoyos)
    Path(dst_json).parent.mkdir(parents=True, exist_ok=True)
    Path(dst_json).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    report["ok"] = True
    return report

# --- SCIPY_REVIEWER_OPT ---


# ---------------------------------------------------------------------------
# Paso final SciPy / descenso por coordenadas contra reglas del revisor
# Interruptor propio: pulir_mocap_scipy.off (junto a este archivo o en motor/)
# ---------------------------------------------------------------------------
OFF_SCIPY = AQUI / "pulir_mocap_scipy.off"
if not OFF_SCIPY.exists():
    OFF_SCIPY = MOTOR / "pulir_mocap_scipy.off"


def scipy_activo() -> bool:
    """True si el paso SciPy/revisor está permitido (no existe pulir_mocap_scipy.off)."""
    return not OFF_SCIPY.exists()


def optimize_retarget_vs_revisor(
    src_json: Path,
    dst_json: Path,
    *,
    adn_md: Path | None = None,
    personaje: str | None = None,
    max_dev_deg: float = 18.0,
    blender_bin: str = "/home/box/apps/blender-5.2.3-linux-x64/blender",
    timeout_s: int = 900,
) -> dict:
    """Optimiza ángulos de un JSON de retarget contra el costo del revisor (fuera/apoyo).

    Corre bajo Blender (FK real del motor). Si existe pulir_mocap_scipy.off, no hace nada
    y copia src→dst con ok=False, motivo=off.
    Universal: DOFs = huesos presentes en las poses; límites = EA.LIMITES por grupo.
    """
    import subprocess
    import tempfile

    src_json, dst_json = Path(src_json), Path(dst_json)
    if not scipy_activo():
        dst_json.parent.mkdir(parents=True, exist_ok=True)
        dst_json.write_text(src_json.read_text(encoding="utf-8"), encoding="utf-8")
        return {"ok": False, "motivo": "pulir_mocap_scipy.off", "src": str(src_json), "dst": str(dst_json)}

    opt_py = AQUI / "pulir_mocap_scipy_opt.py"
    if not opt_py.exists():
        raise FileNotFoundError(f"falta {opt_py}")

    cfg = {
        "src": str(src_json),
        "dst": str(dst_json),
        "motor": str(MOTOR),
        "adn_md": str(adn_md) if adn_md else None,
        "personaje": personaje,
        "max_dev_deg": float(max_dev_deg),
        "target_blender": "/workspace/LIBRERIAS_MOTOR_20261104/target_blender",
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(cfg, f)
        cfg_path = f.name
    cmd = [blender_bin, "-b", "-P", str(opt_py), "--", cfg_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    report_path = Path(str(dst_json) + ".scipy_report.json")
    report = {"ok": False, "returncode": r.returncode, "stdout_tail": (r.stdout or "")[-2000:], "stderr_tail": (r.stderr or "")[-2000:]}
    if report_path.exists():
        try:
            report.update(json.loads(report_path.read_text(encoding="utf-8")))
        except Exception as e:
            report["report_read_error"] = str(e)
    report["cfg"] = cfg
    return report


