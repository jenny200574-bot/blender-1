"""escala_adn (Blender 5.2.3, código propio MYIA).
Regla: la altura del ADN (altura_m) es la ÚNICA que vale. El molde de fábrica NO se toca: se carga (append) en una
ESCENA NUEVA, se mide en pose de reposo (suela -> punto más alto de la malla del personaje) y:
  SI falta altura_m en el ADN               -> STOP  FALTA_DATO
  SI las fuentes de altura del ADN no coinciden (±2%) -> STOP  CONFLICTO_ALTURA (no se escoge una)
  SI |H/altura_m - 1| <= 0.02               -> no se escala (OK)
  SI NO -> escala UNIFORME k = altura_m/H al armature, se APLICA la escala conservando el parent BONE de las piezas,
          se vuelve a medir; SI sigue fuera de ±2% -> STOP  ESCALA_FALLIDA
Prueba de seguridad: se posan huesos (giros conocidos) y se compara la malla aplicada contra la referencia
(armature escalado sin aplicar): error máx en metros.
Uso: blender -b --factory-startup -P escala_adn.py -- --molde m.blend --id <personaje> --biblio biblioteca_personajes.json
     [--adn_txt adn_personaje.txt] [--ficha ficha.json] --salida nueva.blend --reporte r.json"""
import bpy, json, sys, re, math, argparse, os
from mathutils import Vector, Euler

TOL = 0.02

def alturas_adn(pid, biblio, adn_txt=None, ficha=None):
    fuentes = {}
    b = json.load(open(biblio))
    p = next((x for x in b.get("personajes", []) if x.get("id") == pid or pid in x.get("ids_mapa", [])), None)
    if p is not None and p.get("altura_m") is not None:
        fuentes["biblioteca_personajes.altura_m"] = float(p["altura_m"])
    if adn_txt and os.path.exists(adn_txt):
        t = open(adn_txt, encoding="utf-8").read()
        m = re.search(r"[Ee]statura[^:\n]*:\**\s*([0-9]+(?:[.,][0-9]+)?)\s*(cm|m)\b", t)
        if m:
            v = float(m.group(1).replace(",", ".")); fuentes["adn_personaje.txt"] = v / 100 if m.group(2) == "cm" else v
    if ficha and os.path.exists(ficha):
        f = json.load(open(ficha))
        if f.get("altura_m") is not None: fuentes["ficha_esqueleto.altura_m (copia, no fuente)"] = float(f["altura_m"])
    return fuentes, p

def decidir_altura(fuentes):
    reales = {k: v for k, v in fuentes.items() if "copia" not in k}
    if not reales: return None, "FALTA_DATO"
    vals = list(reales.values()); ref = vals[0]
    if any(abs(v / ref - 1) > TOL for v in vals): return None, "CONFLICTO_ALTURA"
    return ref, "OK"

def cargar_molde(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    sc = bpy.context.scene
    for o in dst.objects:
        if o is not None: sc.collection.objects.link(o)
    arms = [o for o in sc.objects if o.type == 'ARMATURE']
    if len(arms) != 1: raise SystemExit(f"STOP MOLDE_INVALIDO: {len(arms)} armatures")
    return arms[0]

def piezas(A):
    return [o for o in A.children_recursive if o.type == 'MESH']

def medir(A):
    A.data.pose_position = 'REST'; bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); zs = []; xs = []
    for o in piezas(A):
        oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world
        for v in me.vertices:
            w = mw @ v.co; zs.append(w.z); xs.append(w)
        oe.to_mesh_clear()
    A.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    return max(zs) - min(zs), min(zs), max(zs)

def snapshot(A):
    dg = bpy.context.evaluated_depsgraph_get(); out = {}
    for o in piezas(A):
        oe = o.evaluated_get(dg); me = oe.to_mesh(); out[o.name] = [oe.matrix_world @ v.co for v in me.vertices]; oe.to_mesh_clear()
    return out

POSE_TEST = {"femur_L": (0.6, 0, 0.2), "tibia_L": (-0.9, 0, 0), "brazo_R": (0, 0.4, 0.8), "cabeza": (0.2, 0.3, 0), "cadera": (0, 0, 0.5)}
def posar(A, on):
    for n, r in POSE_TEST.items():
        if n in A.pose.bones:
            pb = A.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler(r if on else (0, 0, 0))
    bpy.context.view_layer.update()

def escalar(A, k):
    """Escala uniforme k aplicada al esqueleto SIN romper el parent BONE:
    huesos (head/tail en espacio del armature) * k  y  matrix_parent_inverse_hijo' = S_k @ P.
    Demostración: con PB_k = S_k·PB·S_k⁻¹ y cola del hueso k·len, el mundo del hijo = S_k·PB·T(len)·P·L (igual que escalar el objeto).
    (bpy.ops.object.transform_apply en el armature NO sirve: probado, deja 2,1 cm de error y la altura en 1,099 m)."""
    from mathutils import Matrix
    for o in bpy.context.selected_objects: o.select_set(False)
    A.scale = (k, k, k); bpy.context.view_layer.update()
    posar(A, True); ref = snapshot(A); posar(A, False)
    A.scale = (1, 1, 1); bpy.context.view_layer.update()
    S = Matrix.Diagonal((k, k, k, 1.0))
    hijos = [o for o in A.children]                       # hijos directos (BONE u OBJECT)
    P = {o.name: o.matrix_parent_inverse.copy() for o in hijos}
    bpy.context.view_layer.objects.active = A; A.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in A.data.edit_bones:
        eb.head = eb.head * k; eb.tail = eb.tail * k
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in hijos: o.matrix_parent_inverse = S @ P[o.name]
    bpy.context.view_layer.update()
    posar(A, True); new = snapshot(A); posar(A, False)
    err = max((a - b).length for n in ref for a, b in zip(ref[n], new[n]))
    parent_ok = all(o.parent_type == 'BONE' and o.parent_bone for o in hijos if o.type == 'MESH')
    return {"metodo": "huesos*k + parent_inverse=S_k@P", "error_pose_prueba_max_m": round(err, 7), "parent_bone_conservado": parent_ok,
            "escala_armature_tras_aplicar": [round(x, 6) for x in A.scale], "huesos_pose_prueba": list(POSE_TEST)}

def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    ap = argparse.ArgumentParser()
    for k in ("--molde", "--id", "--biblio", "--adn_txt", "--ficha", "--salida", "--reporte", "--forzar_k"): ap.add_argument(k, default=None)
    a = ap.parse_args(argv)
    R = {"contrato": "reporte_escala_adn_v1", "id": a.id, "molde": a.molde, "blender": bpy.app.version_string,
         "molde_modificado": False, "tolerancia": TOL}
    fuentes, p = alturas_adn(a.id, a.biblio, a.adn_txt, a.ficha)
    R["fuentes_altura"] = fuentes; R["altura_fuente_nota"] = p and p.get("altura_fuente")
    alt, est = decidir_altura(fuentes); R["altura_adn_m"] = alt
    A = cargar_molde(a.molde); R["armature"] = A.name
    H0, z0, z1 = medir(A); R["antes"] = {"altura_m": round(H0, 4), "suela_z": round(z0, 4), "tope_z": round(z1, 4)}
    if est != "OK":
        R["estado"] = "STOP_" + est
        R["accion"] = "pedir a la fábrica / ADN: " + ("falta altura_m" if est == "FALTA_DATO" else "las fuentes de altura no coinciden; no se escoge una")
    else:
        dif = round(H0 / alt - 1, 4); R["antes"]["dif_vs_adn"] = dif
        if abs(dif) <= TOL and not a.forzar_k:
            R["estado"] = "OK_SIN_ESCALAR"; R["k"] = 1.0
        else:
            if a.forzar_k: alt = alt * float(a.forzar_k); R["PRUEBA_forzada"] = f"altura objetivo de prueba = ADN x {a.forzar_k} (solo para probar la escala; NO es el ADN)"; R["altura_objetivo_prueba_m"] = round(alt, 4)
            k = alt / H0; R["k"] = round(k, 6); R["aplicar"] = escalar(A, k)
            H1, z0b, z1b = medir(A); R["despues"] = {"altura_m": round(H1, 4), "suela_z": round(z0b, 4), "dif_vs_adn": round(H1 / alt - 1, 5)}
            R["estado"] = "OK_ESCALADO" if abs(H1 / alt - 1) <= 0.005 and R["aplicar"]["error_pose_prueba_max_m"] < 1e-4 else "STOP_ESCALA_FALLIDA"
        if a.salida:
            bpy.ops.wm.save_as_mainfile(filepath=a.salida); R["escena_nueva"] = a.salida
    if a.reporte: json.dump(R, open(a.reporte, "w"), indent=1, ensure_ascii=False)
    print("RESULT", json.dumps(R, ensure_ascii=False))

if __name__ == "__main__":
    main()
