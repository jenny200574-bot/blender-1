"""Retarget de captura de movimiento libre (CMU BVH, uso libre) al ESQUELETO ADAPTABLE del personaje (v9).
blender -b -P mocap/bvh_retarget.py -- archivo.bvh personaje salida.json [n_claves] [modo: levantarse|todo]
Por cada clave: copia la DIRECCIÓN de cada segmento del actor real (no sus largos) al esqueleto del ADN, dentro de los límites articulares;
la raíz copia la orientación de la pelvis (rumbo normalizado al final). Devuelve poses + movimiento (fases con tiempos reales del actor y apoyos)."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
AQUI = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(AQUI))
import rig, esqueleto_adn as EA
A_ = sys.argv[sys.argv.index("--") + 1:]; BVH, PID, OUTF = A_[0], A_[1], A_[2]; K = int(A_[3]) if len(A_) > 3 else 12; MODO = A_[4] if len(A_) > 4 else "levantarse"
ADN = {"kael": "ADN_kael_sin_mochila.md", "alien": "ADN_alien_guardian.md", "novia": "ADN_novia_cardigan.md"}
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_anim.bvh(filepath=BVH, axis_forward="-Z", axis_up="Y", rotate_mode="NATIVE", update_scene_fps=False, update_scene_duration=True)
M = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]; sc = bpy.context.scene; f0, f1 = int(M.animation_data.action.frame_range[0]), int(M.animation_data.action.frame_range[1])
def J(n): pb = M.pose.bones[n]; return M.matrix_world @ pb.head
def JT(n): pb = M.pose.bones[n]; return M.matrix_world @ pb.tail
MAP = {"columna": ("LowerBack", "Spine1"), "pecho": ("Spine1", "Neck"), "cuello": ("Neck", "Head"), "cabeza": ("Head", "@Head"),
       **{f"brazo_{s}": (f"{L}Arm", f"{L}ForeArm") for s, L in (("L", "Left"), ("R", "Right"))}, **{f"antebrazo_{s}": (f"{L}ForeArm", f"{L}Hand") for s, L in (("L", "Left"), ("R", "Right"))},
       **{f"muslo_{s}": (f"{L}UpLeg", f"{L}Leg") for s, L in (("L", "Left"), ("R", "Right"))}, **{f"pierna_{s}": (f"{L}Leg", f"{L}Foot") for s, L in (("L", "Left"), ("R", "Right"))},
       **{f"pie_{s}": (f"{L}Foot", f"{L}ToeBase") for s, L in (("L", "Left"), ("R", "Right"))}}
def muestra(f):
    sc.frame_set(f); bpy.context.view_layer.update()
    P = {n: J(n).copy() for n in {x for ab in MAP.values() for x in ab if not x.startswith("@")} | {"Hips", "LeftUpLeg", "RightUpLeg", "Spine"}}; P["@Head"] = JT("Head").copy(); return P
alt = []
for f in range(f0, f1 + 1):
    sc.frame_set(f); bpy.context.view_layer.update(); alt.append(J("Head").z)
hmax = max(alt)
if MODO == "levantarse":   # tramo: desde el último cuadro con la cabeza baja hasta que queda de pie
    lo = [i for i, h in enumerate(alt) if h < 0.35 * hmax]; i0 = lo[len(lo) // 2] if lo else 0
    lo2 = [i for i in lo if i < next((j for j in range(len(alt)) if alt[j] > 0.93 * hmax and j > (lo[-1] if lo else 0)), len(alt) - 1)]
    i0 = lo2[-1] if lo2 else 0; i1 = min(len(alt) - 1, next((j for j in range(i0, len(alt)) if alt[j] > 0.97 * hmax), len(alt) - 1) + 24); i0 = max(0, i0 - 10)
else: i0, i1 = 0, len(alt) - 1
fr = [f0 + i0 + round((i1 - i0) * k / (K - 1)) for k in range(K)]
S = [muestra(f) for f in fr]
def marco(P):
    u = ((P["Spine"] - (P["LeftUpLeg"] + P["RightUpLeg"]) / 2)).normalized(); r = (P["RightUpLeg"] - P["LeftUpLeg"]); r = (r - u * r.dot(u)).normalized(); fw = u.cross(r)
    return Matrix((r, fw, u)).transposed()   # columnas: derecha, frente, arriba
Rf = marco(S[-1]); fwh = Vector((Rf.col[1].x, Rf.col[1].y, 0)).normalized(); yaw = math.atan2(-fwh.x, fwh.y); H = Matrix.Rotation(-yaw, 3, "Z")   # rumbo final → +Y
# esqueleto del personaje
p = EA.leer_adn((AQUI / "adn" / ADN[PID]).read_text(), PID); A = rig.crear(PID, p, {"_": (.5, .5, .5)}); HB = EA.huesos(p); RAD = {b["nombre"]: b["radio"] for b in HB}; GR = {b["nombre"]: b["grupo"] for b in HB}
ORD = ["columna", "pecho", "cuello", "cabeza", "muslo_L", "pierna_L", "pie_L", "muslo_R", "pierna_R", "pie_R", "brazo_L", "antebrazo_L", "brazo_R", "antebrazo_R"]
def dir_nuestro(n): pb = A.pose.bones[n]; return ((A.matrix_world @ pb.tail) - (A.matrix_world @ pb.head)).normalized()
POSES = {}; FASES = []; base = Path(BVH).stem; PREV = {}; PREV_HIJO = {}; ERR = []; E_PREV = None; EB = {}; LAMBDA = 2e-5
for k, P in enumerate(S):
    R = H @ marco(P); e = R.to_euler("XYZ", E_PREV) if E_PREV else R.to_euler("XYZ"); E_PREV = e.copy(); ang = {"raiz": [-math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)]}
    A.rotation_euler = (e.x, e.y, e.z); A.location = (0, 0, 0)
    for n in ORD:
        a, b = MAP[n]; dv = P[b] - P[a]
        if dv.length < 1e-4 and n == "pecho": dv = P["Head"] - P["Spine1"]
        tg = (H @ dv).normalized(); lim = EA.LIMITES[GR[n]]; best = (9, [0, 0, 0])
        dofs = 1 if n.startswith(("pierna", "antebrazo", "pie")) else 2
        prv = PREV.get(n)
        def ev(v):   # error de dirección + continuidad con la clave anterior (evita saltos entre soluciones equivalentes)
            ang[n] = v; rig.aplicar(A, ang); bpy.context.view_layer.update()
            return 1 - dir_nuestro(n).dot(tg) + (LAMBDA * sum((v[i] - prv[i]) ** 2 for i in range(2)) if prv else 0)
        if n.startswith(("pierna", "antebrazo")) and n in PREV_HIJO: pass
        step = [(lim[0][1] - lim[0][0]) / 8, (lim[1][1] - lim[1][0]) / 8]
        for fx in [lim[0][0] + i * step[0] for i in range(9)]:
            for ab in ([lim[1][0] + j * step[1] for j in range(9)] if dofs == 2 else [0]):
                c = ev([fx, ab, 0])
                if c < best[0]: best = (c, [fx, ab, 0])
        if prv:
            c = ev(list(prv))
            if c < best[0]: best = (c, list(prv))
        cur = best[1]; c = best[0]; s_ = [step[0] / 2, step[1] / 2]
        for _ in range(7):
            for i in range(dofs):
                for d in (s_[i], -s_[i]):
                    v = list(cur); v[i] = max(lim[i][0], min(lim[i][1], v[i] + d)); cc = ev(v)
                    if cc < c: c, cur = cc, v
            s_ = [x / 2 for x in s_]
        HIJO = {"muslo_L": "pierna_L", "muslo_R": "pierna_R", "brazo_L": "antebrazo_L", "brazo_R": "antebrazo_R"}.get(n)
        if HIJO:   # cadena: el giro del muslo/brazo orienta el plano de la rodilla/codo -> se resuelve junto con el hijo
            ah, bh = MAP[HIJO]; tgh = (H @ (P[bh] - P[ah])).normalized(); limh = EA.LIMITES[GR[HIJO]]
            def ev_h(v):
                ang[n] = v; mejor_h = (9, 0)
                for kf in [limh[0][0] + i * (limh[0][1] - limh[0][0]) / 12 for i in range(13)]:
                    ang[HIJO] = [kf, 0, 0]; rig.aplicar(A, ang); bpy.context.view_layer.update(); e_ = 1 - dir_nuestro(HIJO).dot(tgh)
                    if e_ < mejor_h[0]: mejor_h = (e_, kf)
                ang[HIJO] = [mejor_h[1], 0, 0]; rig.aplicar(A, ang); bpy.context.view_layer.update()
                return 1 - dir_nuestro(n).dot(tg) + mejor_h[0] + (LAMBDA * sum((v[i] - prv[i]) ** 2 for i in range(3)) if prv else 0), mejor_h[1]
            c, _ = ev_h(cur); s3 = [8, 8, 20]
            for g0 in [lim[2][0] + i * (lim[2][1] - lim[2][0]) / 6 for i in range(7)]:
                v = [cur[0], cur[1], g0]; cc, _ = ev_h(v)
                if cc < c: c, cur = cc, v
            for _ in range(6):
                for i in range(3):
                    for d in (s3[i], -s3[i]):
                        v = list(cur); v[i] = max(lim[i][0], min(lim[i][1], v[i] + d)); cc, _ = ev_h(v)
                        if cc < c: c, cur = cc, v
                s3 = [x / 2 for x in s3]
            _, kf = ev_h(cur); ang[n] = list(cur)
        PREV[n] = list(cur); EB.setdefault(n, []).append(round(math.degrees(math.acos(max(-1, min(1, dir_nuestro(n).dot(tg)))))));ERR.append(round(math.degrees(math.acos(max(-1, min(1, dir_nuestro(n).dot(tg))))), 1))
        ang[n] = [round(x, 1) for x in cur]; rig.aplicar(A, ang)
    bpy.context.view_layer.update(); z, _ = rig.suelo(A, RAD); A.location.z = -z; bpy.context.view_layer.update(); Mw = A.matrix_world
    ap = []
    for s_ in "LR":
        if (Mw @ A.pose.bones[f"mano_{s_}"].tail).z < 0.08: ap.append(f"mano_{s_}")
        if (Mw @ A.pose.bones[f"pierna_{s_}"].head).z - RAD[f"pierna_{s_}"] < 0.08: ap.append(f"pierna_{s_}")
        if min((Mw @ A.pose.bones[f"pie_{s_}"].tail).z, (Mw @ A.pose.bones[f"pie_{s_}"].head).z) < 0.1: ap.append(f"pie_{s_}")
    nm = f"mc_{base}_{PID}_k{k:02d}"; POSES[nm] = {"angulos": ang, "apoyos": ap}
    FASES.append({"pose": nm, "t_fin_frac": round(max(0.02, (fr[k] - fr[0]) / max(1, fr[-1] - fr[0])), 3), "apoyos": ap, "anclar_apoyo": True, "desplazamiento_m": 0.0})
json.dump({"error_por_hueso_deg": EB, "error_direccion_medio_deg": round(sum(ERR) / len(ERR), 1), "error_direccion_max_deg": max(ERR), "bvh": Path(BVH).name, "personaje": PID, "cuadros_bvh": [fr[0], fr[-1]], "fps_bvh": 120, "poses": POSES, "fases": FASES}, open(OUTF, "w"), ensure_ascii=False, indent=1)
print("RETARGET_OK", len(POSES), fr[0], fr[-1])
