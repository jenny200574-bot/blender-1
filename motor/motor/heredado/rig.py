"""Esqueleto real en Blender 5.2.3 (huesos de largo fijo) desde esqueleto_adn + poses por ÁNGULOS.
Convención de ángulos (grados) por articulación [flex, abd, giro]:
 flex+: hombro/cadera/codo/mano adelante; rodilla = flexión (la pierna va atrás); columna/pecho/cuello/cabeza = inclinar adelante; pie = punta arriba.
 abd+: separar del cuerpo hacia su lado (L a la izquierda, R a la derecha); en columna/cabeza = inclinar a la derecha; clavícula = subir hombro.
 giro+: girar a la izquierda (visto desde arriba) en columna/cuello/cabeza.
 'raiz': [pitch adelante+, roll derecha+, 0] gira todo el cuerpo sobre la pelvis (tendido = pitch -90 boca arriba / roll 90 de lado).
Los signos de cada hueso se CALIBRAN solos al crear el rig (sirve para cualquier proporción/partes extra)."""
import bpy, math
from mathutils import Vector, Matrix, Euler, Quaternion
import esqueleto_adn as EA
ESPERA = {"flex": {"muslo": "+y", "brazo": "+y", "antebrazo": "+y", "mano": "+y", "pierna": "-y", "columna": "+y", "pecho": "+y", "cuello": "+y", "cabeza": "+y",
                   "pie": "+z", "clavicula": "+y", "oreja": "+y", "ala": "+y", "cola": "-z"},
          "abd": {"clavicula": "+z", "columna": "+x", "pecho": "+x", "cuello": "+x", "cabeza": "+x", "cola": "+x"}}
def _vec(s): return {"+x": Vector((1, 0, 0)), "-x": Vector((-1, 0, 0)), "+y": Vector((0, 1, 0)), "-y": Vector((0, -1, 0)), "+z": Vector((0, 0, 1)), "-z": Vector((0, 0, -1))}[s]
def crear(pid, p, colores, col=None):
    col = col or bpy.context.scene.collection; B = EA.huesos(p); pel = B[0]["cabeza"][2]
    ad = bpy.data.armatures.new(f"{pid}_arm"); A = bpy.data.objects.new(pid, ad); col.objects.link(A)
    bpy.context.view_layer.objects.active = A; bpy.ops.object.mode_set(mode="EDIT")
    for b in B:
        e = ad.edit_bones.new(b["nombre"]); e.head = Vector(b["cabeza"]) - Vector((0, 0, pel)); e.tail = Vector(b["cola"]) - Vector((0, 0, pel))
        d = (e.tail - e.head).normalized(); e.align_roll(Vector((0, 0, 1)) if abs(d.z) < 0.7 else Vector((0, 1, 0)))
        if b["padre"]: e.parent = ad.edit_bones[b["padre"]]; e.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    A["altura_m"] = p["altura_m"]; A["pelvis_m"] = pel; A["spec"] = str(p)
    for pb in A.pose.bones: pb.rotation_mode = "XYZ"
    # calibración automática de signos
    sig = {}
    for b in B:
        pb = A.pose.bones[b["nombre"]]; g = b["grupo"]; lado = b["nombre"][-1] if b["nombre"][-2:] in ("_L", "_R") else ""
        s = [1, 1, 1]
        for k, ax in (("flex", 0), ("abd", 2)):
            want = ESPERA[k].get(g)
            if k == "abd" and not want: want = {"L": "-x", "R": "+x"}.get(lado, "+x")
            if not want: continue
            bpy.context.view_layer.update(); t0 = (A.matrix_world @ pb.tail).copy()
            e = [0, 0, 0]; e[ax] = math.radians(20); pb.rotation_euler = e; bpy.context.view_layer.update(); t1 = (A.matrix_world @ pb.tail).copy(); pb.rotation_euler = (0, 0, 0)
            s[ax] = 1 if (t1 - t0).dot(_vec(want)) >= 0 else -1
        # giro: el eje X local del hueso debe ir de +x hacia +y
        bpy.context.view_layer.update(); x0 = (A.matrix_world.to_3x3() @ pb.matrix.to_3x3() @ Vector((1, 0, 0)))
        pb.rotation_euler = (0, math.radians(20), 0); bpy.context.view_layer.update(); x1 = (A.matrix_world.to_3x3() @ pb.matrix.to_3x3() @ Vector((1, 0, 0))); pb.rotation_euler = (0, 0, 0)
        s[1] = 1 if x0.cross(x1).z >= 0 else -1
        sig[b["nombre"]] = s
    A["signos"] = str(sig); A["_sig"] = sig
    # cuerpo: cápsulas emparentadas a cada hueso (BONE)
    for b in B:
        n = b["nombre"]; g = b["grupo"]; L = (Vector(b["cola"]) - Vector(b["cabeza"])).length; r = b["radio"]
        c = colores.get(n, colores.get(g, colores.get("_")))
        if c is None:raise ValueError("FALTA color ADN/01: "+n)
        m = bpy.data.materials.get(f"{pid}_{g}") or _mat(f"{pid}_{g}_{n[-1]}", c)
        if g == "cabeza":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12); o = bpy.context.object; o.scale = (r * 0.95, r * 1.05, L * 0.55)
            bpy.ops.object.transform_apply(scale=True)
            from cargar_modulo_motor import cargar as cargar_modulo_motor
            for v, co in zip(o.data.vertices, cargar_modulo_motor('malla_cabeza').desplazar_cabeza([tuple(v.co) for v in o.data.vertices], L)): v.co = co
            off = Vector((0, L * 0.48, 0))
        elif g == "pie":
            bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.scale = (r * 2.2, L * 1.05, r * 1.6); bpy.ops.object.transform_apply(scale=True); off = Vector((0, L * 0.45, 0))
        else:
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=L, vertices=14); o = bpy.context.object
            o.rotation_euler = (math.radians(90), 0, 0); bpy.ops.object.transform_apply(rotation=True); off = Vector((0, L / 2, 0))
            bpy.ops.object.modifier_add(type="BEVEL"); o.modifiers[-1].width = r * 0.6; o.modifiers[-1].segments = 3
            if g in ("muslo", "brazo", "pierna", "antebrazo", "columna", "pelvis", "pecho"):
                bpy.ops.mesh.primitive_uv_sphere_add(radius=r * 1.02, segments=12, ring_count=8); j = bpy.context.object; j.data.materials.append(m)
                for cc in j.users_collection: cc.objects.unlink(j)
                col.objects.link(j); j.parent = A; j.parent_type = "BONE"; j.parent_bone = n; j.matrix_parent_inverse = Matrix(); j.location = Vector((0, -L, 0)); j.name = f"{pid}_art_{n}"
        o.name = f"{pid}_malla_{n}"; o.data.materials.append(m)
        for cc in o.users_collection: cc.objects.unlink(o)
        col.objects.link(o); o.parent = A; o.parent_type = "BONE"; o.parent_bone = n; o.matrix_parent_inverse = Matrix()
        o.location = off - Vector((0, L, 0))    # BONE parent: origen en la COLA del hueso, eje Y a lo largo
    return A
def _mat(n, c):
    m = bpy.data.materials.new(n); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*c[:3], 1); b.inputs["Roughness"].default_value = 0.55
    if len(c) > 3 and c[3] > 0: b.inputs["Emission Color"].default_value = (*c[:3], 1); b.inputs["Emission Strength"].default_value = c[3]
    return m
def aplicar(A, ang):
    """ang: {'hueso': [flex, abd, giro]} (+ 'raiz'). Huesos sin dato = reposo."""
    sig = A["_sig"].to_dict() if hasattr(A["_sig"], "to_dict") else A["_sig"]
    for pb in A.pose.bones:
        v = ang.get(pb.name, [0, 0, 0]); s = sig[pb.name]
        pb.rotation_euler = (math.radians(v[0]) * s[0], math.radians(v[2]) * s[1], math.radians(v[1]) * s[2])
def puntos_cuerpo(A):
    """Puntos con nombre del personaje en mundo (para apuntar/mirar/agarrar): pid.pecho, pid.cabeza, pid.mano_R..."""
    bpy.context.view_layer.update(); M = A.matrix_world; P = {}
    for pb in A.pose.bones:
        P[pb.name] = M @ pb.tail; P[pb.name + "_ini"] = M @ pb.head
    P["pecho_c"] = (M @ A.pose.bones["pecho"].head + M @ A.pose.bones["pecho"].tail) / 2
    return P
def suelo(A, radios):
    """Min z de la superficie del cuerpo (cabezas/colas de hueso menos su radio)."""
    bpy.context.view_layer.update(); M = A.matrix_world; z = 1e9; quien = None
    for pb in A.pose.bones:
        r = radios[pb.name]
        for nm, p in (("ini", M @ pb.head), ("fin", M @ pb.tail)):
            zz = p.z - (r if pb.name.split("_")[0] not in ("pie",) else 0.0)
            if zz < z: z, quien = zz, (pb.name, nm, p.copy())
    return z, quien
def largos(A):
    bpy.context.view_layer.update(); M = A.matrix_world
    return {pb.name: ((M @ pb.tail) - (M @ pb.head)).length for pb in A.pose.bones}
