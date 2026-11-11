"""pies_bloqueo — el foot-lock APROBADO (Ricardo t995u «perfecto no le hagas más»), extraído SIN CAMBIOS de
kimodo/fix_pies_y_video.py::strong_foot_lock (lab/kimodo_prueba_20261109/revision):
  detección de apoyo (thr_z 0.025, thr_v 0.15, histéresis ×1.9/×2.5, min_seg 3, borde 6 con peso cuadrático),
  pie primario por antigüedad de contacto, plantado de raíz con crossfade HALF=4 en los cambios de pie, contactos Kimodo si hay.
Única adaptación de ENTRADA (no del algoritmo): z del pie medida SOBRE EL PISO REAL bajo el pie (raycast al molde de escenario)
y la raíz base es la trayectoria planificada por cuadro (lista) en vez de una posición fija. fps 24 como el aprobado."""
import math
from mathutils import Vector

def strong_foot_lock_plan(tips0, n, kim=None, thr_z=0.025, thr_v=0.15, min_seg=3, borde=6, fps=24):
    info = {}; st = {}
    for p in tips0:
        tip = tips0[p]
        z = [t.z for t in tip]; zmin = sorted(z)[max(0, n // 12)]
        v = [0.0] + [math.hypot(tip[i].x - tip[i - 1].x, tip[i].y - tip[i - 1].y) * fps for i in range(1, n)]
        base = [(z[i] - zmin < thr_z) and (v[i] < thr_v) for i in range(n)]
        hyst = [False] * n; planted = False
        for i in range(n):
            if not planted:
                if base[i]: planted = True
            else:
                if (z[i] - zmin > thr_z * 1.9) or (v[i] > thr_v * 2.5): planted = False
            hyst[i] = planted
        if kim is not None and p in kim:
            near = [z[i] - zmin < thr_z * 2.0 for i in range(n)]
            st[p] = [bool(hyst[i] or (kim[p][i] and near[i])) for i in range(n)]
        else:
            st[p] = hyst
        info[p] = {"zmin": round(float(zmin), 4)}
    locks = {p: [None] * n for p in tips0}; w = {p: [0.0] * n for p in tips0}
    for p in tips0:
        segs = []; i = 0
        while i < n:
            if st[p][i]:
                j = i
                while j + 1 < n and st[p][j + 1]: j += 1
                if j - i + 1 >= min_seg: segs.append((i, j))
                i = j + 1
            else: i += 1
        for (a, b) in segs:
            xs = sorted(tips0[p][k].x for k in range(a, b + 1)); ys = sorted(tips0[p][k].y for k in range(a, b + 1))
            Lxy = Vector((xs[len(xs) // 2], ys[len(ys) // 2], 0.0))
            for f in range(max(0, a - borde), min(n, b + borde + 1)):
                if f < a: wf = (1 - (a - f) / (borde + 1)) ** 2
                elif f > b: wf = (1 - (f - b) / (borde + 1)) ** 2
                else: wf = 1.0
                if wf >= w[p][f]: w[p][f] = wf; locks[p][f] = Lxy
        info[p]["apoyos"] = len(segs); info[p]["cuadros_bloqueados"] = int(sum(1 for x in w[p] if x >= 0.999)); info[p]["contact_frames"] = int(sum(st[p]))
    age = {p: [0] * n for p in tips0}
    for p in tips0:
        for i in range(n):
            age[p][i] = (age[p][i - 1] + 1) if i > 0 and w[p][i] >= 0.999 and w[p][i - 1] >= 0.999 else (1 if w[p][i] >= 0.999 else 0)
    primary = [None] * n
    for i in range(n):
        full = [p for p in tips0 if w[p][i] >= 0.999]
        if len(full) == 1: primary[i] = full[0]
        elif len(full) >= 2: primary[i] = max(full, key=lambda p: age[p][i])
        else:
            soft = [p for p in tips0 if w[p][i] > 0.05]
            if soft: primary[i] = max(soft, key=lambda p: w[p][i])
    HALF = 4
    def foot_delta(p, i):
        if p is None or locks[p][i] is None: return Vector((0, 0, 0))
        dxy = locks[p][i] - tips0[p][i]; return Vector((dxy.x, dxy.y, 0.0)) * w[p][i]
    raw = [foot_delta(primary[i], i) for i in range(n)]
    changes = [i for i in range(1, n) if primary[i] != primary[i - 1] and primary[i] and primary[i - 1]]
    delta = [r.copy() for r in raw]
    for c in changes:
        a = max(0, c - HALF); b = min(n - 1, c + HALF)
        for i in range(a, b + 1):
            tt = (i - a) / (b - a) if b > a else 1.0; tt = tt * tt * (3 - 2 * tt)
            p0 = primary[c - 1]; p1 = primary[c]
            delta[i] = foot_delta(p0, i).lerp(foot_delta(p1, i), tt)
    info["crossfade_half"] = HALF; info["primary_changes"] = len(changes)
    info["method"] = "primary_foot_root_plant+crossfade4+kimodo_contacts (aprobado, sin cambios)"
    info["primary_lock_frames"] = int(sum(1 for i in range(n) if primary[i] and w[primary[i]][i] >= 0.999))
    return delta, w, primary, info
