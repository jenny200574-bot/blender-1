"""sentarse_exacto (Blender 5.2.3, código propio MYIA).
Encaja un clip de mocap de sentarse (CMU 13_01 ya retargeteado a Valentina + foot-lock, lab/tests/t6_13_01.blend)
a un asiento REAL: la cadera (punto de apoyo = parte baja de cadera/muslos) cae en el ancla del objeto
(altura y posición del asiento salen del objeto, no se inventan) y los pies siguen en el piso.
Método: (1) transformación rígida constante (giro en Z + traslación XY) para poner el apoyo del clip sobre el ancla
y mirando hacia el rumbo del ancla; (2) desplazamiento vertical dz = z_asiento - z_apoyo_clip, mezclado con
w(f) = suavizado( (h_pie - h_cadera(f)) / (h_pie - h_sentada) ) -> 0 de pie, 1 sentada; (3) IK de 2 huesos en las
piernas con objetivos = pies del clip (piso) para que el dz no levante ni hunda los pies; (4) horneado visual.
Contrato del ancla (lo entrega la fábrica de objetos): {"tipo":"sentarse","pos":[x,y,z_tope_asiento],"rumbo_deg":a,"huella_m":[ancho,fondo]}
Uso: blender -b t6_13_01.blend -P sentarse_exacto.py -- --alto 0.28 --tipo silla --out dir --tag x --guardar nueva.blend"""
import bpy, sys, json, math, argparse, os
from mathutils import Vector, Matrix, Euler

def args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--alto', type=float, required=True); ap.add_argument('--tipo', default='silla')
    ap.add_argument('--pos', default='1.0,0.5'); ap.add_argument('--rumbo', type=float, default=-90.0)
    ap.add_argument('--out', required=True); ap.add_argument('--tag', required=True); ap.add_argument('--guardar', default=None)
    ap.add_argument('--render', type=int, default=1)
    return ap.parse_args(sys.argv[sys.argv.index('--') + 1:])

a = args(); os.makedirs(a.out, exist_ok=True)
sc = bpy.context.scene; T = bpy.data.objects['ESQ_gdc-valentina']
for o in list(bpy.data.objects):
    if o.name in ('Plane',) or o.type == 'CAMERA' and o.name == 'CAM': pass
F = list(range(sc.frame_start, sc.frame_end + 1))
APOYO = [o for o in T.children if o.type == 'MESH' and any(k in o.name for k in ('cadera_mesh', 'muslo_L', 'muslo_R'))]
PIES = (('pie_L', 'tibia_L'), ('pie_R', 'tibia_R'))

def apoyo_punto():
    """punto de apoyo al sentarse (glúteos): z = mínimo de la pieza de cadera y de la parte PROXIMAL de los muslos
    (vértices a menos de 35% del largo del fémur desde la cadera); xy = cadera. No usa la rodilla: así el IK de piernas
    no cambia la medida."""
    dg = bpy.context.evaluated_depsgraph_get(); zmin = 9
    for o in APOYO:
        oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world
        if 'muslo' in o.name:
            lado = o.name[-1]; pb = T.pose.bones[f'femur_{lado}']
            hd = T.matrix_world @ pb.head; L = pb.length * T.matrix_world.to_scale()[0]
            zs = [(mw @ v.co).z for v in me.vertices if ((mw @ v.co) - hd).length < 0.35 * L + 0.04]
        else:
            zs = [(mw @ v.co).z for v in me.vertices]
        if zs: zmin = min(zmin, min(zs))
        oe.to_mesh_clear()
    h = T.matrix_world @ T.pose.bones['cadera'].head
    return Vector((h.x, h.y, zmin)), h

def frente():
    """dirección a la que mira (xy): de la cadera hacia el punto medio de las rodillas (sentada los muslos apuntan al frente)."""
    mw = T.matrix_world; h = mw @ T.pose.bones['cadera'].head
    k = (mw @ T.pose.bones['tibia_L'].head + mw @ T.pose.bones['tibia_R'].head) / 2
    d = k - h; d.z = 0; return d.normalized()

def muestrear():
    S = []
    for f in F:
        sc.frame_set(f); c, h = apoyo_punto()
        pies = {p: (T.matrix_world @ T.pose.bones[p].head).copy() for p, _ in PIES}
        puntas = {p: (T.matrix_world @ T.pose.bones[p].tail).copy() for p, _ in PIES}
        tob = {p: (T.matrix_world @ T.pose.bones[t].tail).copy() for p, t in PIES}
        rot = {p: (T.matrix_world @ T.pose.bones[p].matrix).to_quaternion() for p, _ in PIES}
        S.append({"c": c, "h": h, "fr": frente(), "pies": pies, "puntas": puntas, "tob": tob, "rot": rot})
    return S

R = {"contrato": "reporte_sentarse_v1", "clip": "CMU 13_01 (retarget Mwni + foot-lock, t6_13_01.blend)", "blender": bpy.app.version_string}
S0 = muestrear()
hz = [s["h"].z for s in S0]; hseat = min(hz)
sent = [i for i, s in enumerate(S0) if s["h"].z <= hseat + 0.02]
# fases sentada (tramos contiguos)
fases = []
for i in sent:
    if fases and i == fases[-1][1] + 1: fases[-1][1] = i
    else: fases.append([i, i])
fases = [x for x in fases if x[1] - x[0] >= 10]
alto_cad = sorted(hz)[int(len(hz) * 0.8)]
R["clip"] += f"; fases sentada (cuadros) {[[F[x], F[y]] for x, y in fases]}"
i0, i1 = fases[0]
cz = sum(S0[i]["c"].z for i in range(i0, i1 + 1)) / (i1 - i0 + 1)
cxy = sum((S0[i]["c"] for i in range(i0, i1 + 1)), Vector()) / (i1 - i0 + 1)
fr = sum((S0[i]["fr"] for i in range(i0, i1 + 1)), Vector()).normalized()
R["clip_natural"] = {"apoyo_z_sentada_m": round(cz, 4), "cadera_z_sentada_m": round(hseat, 4), "cadera_z_de_pie_m": round(alto_cad, 4)}

# --- asiento de prueba (lo haría la fábrica de objetos): caja + ancla en propiedad personalizada
px, py = map(float, a.pos.split(',')); rum = math.radians(a.rumbo)
ancho, fondo = (0.32, 0.30) if a.tipo == 'silla' else (0.9, 0.6)
bpy.ops.mesh.primitive_cube_add(size=1); seat = bpy.context.object; seat.name = f'{a.tipo}_prueba'
seat.scale = (ancho, fondo, a.alto); seat.location = (px, py, a.alto / 2); seat.rotation_euler = (0, 0, rum + math.pi / 2)
m = bpy.data.materials.new('asiento'); m.diffuse_color = (0.55, 0.35, 0.2, 1) if a.tipo == 'silla' else (0.4, 0.5, 0.8, 1); seat.data.materials.append(m)
fdir = Vector((math.cos(rum), math.sin(rum), 0))
if a.tipo == 'silla':   # respaldo detrás del asiento
    bpy.ops.mesh.primitive_cube_add(size=1); bk = bpy.context.object; bk.name = 'silla_prueba_respaldo'
    bk.scale = (ancho, 0.04, 0.35); bk.rotation_euler = seat.rotation_euler
    bk.location = Vector((px, py, a.alto + 0.175)) - fdir * (fondo / 2 + 0.02); bk.data.materials.append(m)
ancla = {"tipo": "sentarse", "pos": [round(px - fdir.x * 0.03, 4), round(py - fdir.y * 0.03, 4), round(a.alto, 4)], "rumbo_deg": a.rumbo,
         "huella_m": [ancho, fondo], "nota": "objeto de PRUEBA del laboratorio (no es de fábrica)"}
seat["ancla_sentarse"] = json.dumps(ancla); R["ancla"] = ancla
A = Vector(ancla["pos"])

# --- (1) transformación rígida constante vía un Empty padre
yaw = math.atan2(fdir.y, fdir.x) - math.atan2(fr.y, fr.x)
raiz = bpy.data.objects.new('raiz_sentarse', None); sc.collection.objects.link(raiz)
Rz = Matrix.Rotation(yaw, 4, 'Z')
Mrig = Matrix.Translation(Vector((A.x, A.y, 0))) @ Rz @ Matrix.Translation(Vector((-cxy.x, -cxy.y, 0)))
raiz.matrix_world = Mrig
mw_T = T.matrix_world.copy(); T.parent = raiz; T.matrix_parent_inverse = Matrix.Identity(4); T.matrix_world = Mrig @ mw_T
bpy.context.view_layer.update()
dz = a.alto - cz
R["ajuste"] = {"giro_z_deg": round(math.degrees(yaw), 2), "dz_m": round(dz, 4)}
# pies objetivo = pies del clip ya movidos rígidamente (en el piso)
S1 = muestrear()
# --- (2) IK de piernas a los pies del clip (en el piso) + (3) dz por cuadro resuelto con las restricciones vivas
def suave(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
W = [suave((alto_cad - S0[i]["h"].z) / max(1e-6, alto_cad - (hseat + 0.01))) for i in range(len(F))]
emps = []
for p, tib in PIES:
    e = bpy.data.objects.new(f'IK_{p}', None); sc.collection.objects.link(e)
    pole = bpy.data.objects.new(f'POLE_{p}', None); sc.collection.objects.link(pole)
    rq = bpy.data.objects.new(f'ROT_{p}', None); sc.collection.objects.link(rq); rq.rotation_mode = 'QUATERNION'
    for i, f in enumerate(F):
        e.location = S1[i]["tob"][p]; e.keyframe_insert('location', frame=f)
        rq.rotation_quaternion = S1[i]["rot"][p]; rq.keyframe_insert('rotation_quaternion', frame=f)
        sc.frame_set(f); knee = T.matrix_world @ T.pose.bones[tib].head
        pole.location = knee + S1[i]["fr"] * 0.5; pole.keyframe_insert('location', frame=f)
    c = T.pose.bones[tib].constraints.new('IK'); c.target = e; c.pole_target = pole; c.chain_count = 2; c.pole_angle = -math.pi / 2
    cr = T.pose.bones[p].constraints.new('COPY_ROTATION'); cr.target = rq; cr.target_space = 'WORLD'; cr.owner_space = 'WORLD'
    emps += [e, pole, rq]
fase_de = {}
for x, y in fases:
    for i in range(x, y + 1): fase_de[i] = (x, y)
dzf = [W[i] * dz for i in range(len(F))]
it_log = []
for it in range(4):
    for i, f in enumerate(F):
        raiz.location = Mrig.translation + Vector((0, 0, dzf[i])); raiz.keyframe_insert('location', frame=f)
    corr = [0.0] * len(F)
    for i, f in enumerate(F):
        if W[i] < 0.5: continue
        sc.frame_set(f); c_, _ = apoyo_punto(); corr[i] = a.alto - c_.z
    # en sentada: corrección exacta; en transición: misma corrección que el cuadro sentado más cercano, escalada por W
    sent_idx = [i for i in range(len(F)) if W[i] >= 0.5]
    err = max(abs(corr[i]) for i in sent_idx if i in fase_de) if fase_de else 0
    it_log.append(round(err, 4))
    for i in range(len(F)):
        if W[i] >= 0.5: dzf[i] += corr[i] * W[i]
        elif W[i] > 0:
            j = min(sent_idx, key=lambda k: abs(k - i)); dzf[i] += corr[j] * W[i]
# suavizado gaussiano (sigma 3 cuadros) para no crear tirones de cadera (ACELERACION)
def gauss(v, sg=3.0):
    k = [math.exp(-0.5 * (j / sg) ** 2) for j in range(-9, 10)]; n = len(v); out = []
    for i in range(n):
        acc = wsum = 0.0
        for j, kw in zip(range(-9, 10), k):
            if 0 <= i + j < n: acc += v[i + j] * kw; wsum += kw
        out.append(acc / wsum)
    return out
dzf = gauss(dzf)
for i, f in enumerate(F):
    raiz.location = Mrig.translation + Vector((0, 0, dzf[i])); raiz.keyframe_insert('location', frame=f)
R["ajuste"]["iteraciones_error_apoyo_max_m"] = it_log
R["ajuste"]["dz_sentada_final_m"] = [round(min(dzf[x:y + 1]), 4) for x, y in fases]
for o in bpy.context.selected_objects: o.select_set(False)
T.select_set(True); bpy.context.view_layer.objects.active = T
bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(frame_start=F[0], frame_end=F[-1], only_selected=True, visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
for e in emps: bpy.data.objects.remove(e)

# --- (4) medidas
S2 = muestrear()
def err_fase(S, x0, x1):
    ez = [S[i]["c"].z - a.alto for i in range(x0, x1 + 1)]
    exy = [math.hypot(S[i]["c"].x - A.x, S[i]["c"].y - A.y) for i in range(x0, x1 + 1)]
    return {"z_err_medio_m": round(sum(ez) / len(ez), 4), "z_err_max_abs_m": round(max(abs(x) for x in ez), 4),
            "xy_err_medio_m": round(sum(exy) / len(exy), 4), "xy_err_max_m": round(max(exy), 4)}
R["cadera_en_asiento"] = {f"fase_{F[x]}_{F[y]}": err_fase(S2, x, y) for x, y in fases}
R["cadera_en_asiento_SIN_ajuste_clip_crudo"] = {f"fase_{F[x]}_{F[y]}": {"z_err_medio_m": round(sum(S0[i]["c"].z for i in range(x, y + 1)) / (y - x + 1) - a.alto, 4)} for x, y in fases}
def resbale(S):
    vs = []; zmin = 9; tgt = []
    for p, _ in PIES:
        z = [min(s["pies"][p].z, s["puntas"][p].z) for s in S]; zmin = min(zmin, min(z)); zr = sorted(z)[len(z) // 10]
        for i in range(1, len(S)):
            if z[i] - zr < 0.025 and z[i - 1] - zr < 0.025:
                d = S[i]["pies"][p] - S[i - 1]["pies"][p]; vs.append(math.hypot(d.x, d.y) * 24)
    vs.sort()
    return {"pie_apoyado_vel_mediana_m_s": round(vs[len(vs) // 2], 4), "pie_apoyado_vel_p90_m_s": round(vs[int(len(vs) * .9)], 4), "pie_z_min_m": round(zmin, 4)}
R["pies_antes_ajuste"] = resbale(S1); R["pies_despues"] = resbale(S2)
_ie = [((S2[i]["pies"][p] - S1[i]["pies"][p]).length, F[i], p) for i in range(len(F)) for p, _ in PIES]; _ie.sort(reverse=True)
R["ik_pie_error_peor"] = [[round(e, 4), f, p] for e, f, p in _ie[:3]]
R["ik_pie_error_mediana_m"] = round(_ie[len(_ie) // 2][0], 5)
R["ik_pie_error_max_m"] = round(max((S2[i]["pies"][p] - S1[i]["pies"][p]).length for i in range(len(F)) for p, _ in PIES), 4)
acc = [((S2[i + 1]["h"] - 2 * S2[i]["h"] + S2[i - 1]["h"]) * 576).length for i in range(1, len(F) - 1)]
R["acel_cadera_max_m_s2"] = round(max(acc), 2)
nan = sum(any(math.isnan(c) for c in s["h"]) for s in S2); R["nan"] = nan
# penetración del apoyo en el asiento (negativo = se hunde)
R["apoyo_bajo_asiento_min_m"] = min(R["cadera_en_asiento"][k]["z_err_medio_m"] for k in R["cadera_en_asiento"])
_sent = {i for x, y in fases for i in range(x, y + 1)}
R["ik_pie_error_max_sentada_m"] = round(max((S2[i]["pies"][p] - S1[i]["pies"][p]).length for i in _sent for p, _ in PIES), 4)
R["ik_pie_error_p99_m"] = round(_ie[int(len(_ie) * 0.01)][0], 4)
if R["ik_pie_error_max_sentada_m"] > 0.02:
    R["aviso"] = "ASIENTO_FUERA_DE_ALCANCE: con la cadera en el asiento los pies no llegan al piso (IK no alcanza). Hace falta otro clip (subirse / pies colgando) o receta de Argon; el motor no lo inventa."
ok = all(abs(v["z_err_medio_m"]) <= 0.01 and v["xy_err_medio_m"] <= 0.03 for v in R["cadera_en_asiento"].values()) and R["ik_pie_error_max_sentada_m"] <= 0.02 and R["pies_despues"]["pie_apoyado_vel_mediana_m_s"] <= 0.02 and nan == 0
R["estado"] = "OK" if ok else ("ASIENTO_FUERA_DE_ALCANCE" if R.get("aviso") else "REVISAR")
json.dump(R, open(f'{a.out}/reporte_sentarse_{a.tag}.json', 'w'), indent=1, ensure_ascii=False)
# --- render: tira lateral (workbench)
if a.render:
    cam = bpy.data.objects.get('camlab') or bpy.data.objects.new('camlab', bpy.data.cameras.new('camlab'))
    if cam.name not in sc.objects: sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.9
    side = Vector((-fdir.y, fdir.x, 0)); C0 = Vector((A.x, A.y, 0.55))
    cam.animation_data_clear(); cam.location = C0 + side * 5 + fdir * 0.0; cam.rotation_euler = (C0 - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x = 320; sc.render.resolution_y = 300
    for o in sc.objects:
        if o.type == 'ARMATURE': o.hide_render = True
    paths = []
    for f in F[::6]:
        sc.frame_set(f); sc.render.filepath = f'{a.out}/sent_{a.tag}_{f:04d}.png'; bpy.ops.render.render(write_still=True)
    R["render"] = f'{a.out}/sent_{a.tag}_*.png'
if a.guardar: bpy.ops.wm.save_as_mainfile(filepath=a.guardar, copy=True)
print("RESULT", json.dumps(R, ensure_ascii=False))
