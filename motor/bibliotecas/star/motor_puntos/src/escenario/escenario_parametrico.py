"""Construye el escenario desde JSON: fórmula + tamaño + puntos nombrados + huesos c∈[0,1].
Premisa STAR_HOJA_HUESOS expandida a muebles (puerta.bisagra, silla.giro, cortina, colchón, lámpara).
Solo objetos de la descripción. Molde AABB = referencia de ubicación; se oculta al reemplazar.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import bpy
    from mathutils import Vector, Euler
except ImportError:
    bpy = None  # type: ignore


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _mat(name: str, rgba=(0.55, 0.55, 0.57, 1.0)):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = False
    m.diffuse_color = rgba
    return m


def _cube(name: str, loc, size_xyz, color=(0.55, 0.55, 0.57, 1.0)):
    # crear en origen; dimensions exactas; luego ubicar — evita hornear world en verts
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.0, 0.0))
    o = bpy.context.object
    o.name = name
    o.dimensions = (float(size_xyz[0]), float(size_xyz[1]), float(size_xyz[2]))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = loc
    o.color = color
    o.data.materials.append(_mat(f"mat_{name}", color))
    return o


def _cyl(name: str, loc, r, h, color=(0.55, 0.55, 0.57, 1.0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(0.0, 0.0, 0.0))
    o = bpy.context.object
    o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = (loc[0], loc[1], loc[2] + h / 2)
    o.color = color
    o.data.materials.append(_mat(f"mat_{name}", color))
    return o


def _empty(name: str, loc, empty_type="PLAIN_AXES", size=0.12):
    e = bpy.data.objects.get(name)
    if e is None:
        e = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(e)
    e.empty_display_type = empty_type
    e.empty_display_size = size
    e.location = loc
    return e


def hide_molde(names: List[str]) -> List[str]:
    hidden = []
    for o in list(bpy.data.objects):
        nl = o.name.lower()
        for n in names:
            if not n:
                continue
            if n.lower() in nl or nl in n.lower():
                o.hide_render = True
                o.hide_viewport = True
                # also clear from BVH consideration by renaming prefix
                if not o.name.startswith("MOLDE_HIDE_"):
                    o.name = "MOLDE_HIDE_" + o.name
                hidden.append(o.name)
                break
    return hidden


def build_object(spec: dict) -> Dict[str, Any]:
    oid = spec["id"]
    forma = spec.get("forma") or "caja"
    tam = spec.get("tamano_m") or {}
    pos = spec.get("pos_m") or [0, 0, 0]
    rot_z = float(spec.get("rot_z_deg") or 0)
    color = (0.52, 0.53, 0.55, 1.0)
    if oid == "silla":
        color = (0.35, 0.38, 0.42, 1.0)
    elif oid.startswith("puerta"):
        color = (0.45, 0.32, 0.22, 1.0)
    elif oid == "cama" or oid == "colchon" or "colchon" in oid:
        color = (0.40, 0.45, 0.55, 1.0)
    elif oid == "alfombra":
        color = (0.45, 0.30, 0.28, 1.0)
    elif oid == "piso":
        color = (0.62, 0.60, 0.55, 1.0)

    meshes = []
    # Special compound: silla = asiento + respaldo + base (NOT solid 0→1.05)
    if oid == "silla":
        # Silla giratoria ergonómica de escritorio (por defecto si FALTA número en descripción):
        # asiento_alto≈0.45, ancho≈0.50, fondo≈0.50, respaldo DETRÁS (−Y si mira escritorio +Y),
        # columna central, base 5 patas + ruedas. Medidas típicas marcadas 'por defecto'.
        asiento_z = float(tam.get("asiento_alto") or 0.45)
        w = float(tam.get("ancho") or 0.50)
        d = float(tam.get("fondo") or 0.50)
        root = _empty(f"param_{oid}_root", (pos[0], pos[1], 0.0), "SPHERE", 0.08)
        seat_h = 0.08  # cojín visible (tope = asiento_z)
        seat = _cube(f"param_{oid}_asiento", (0.0, 0.0, asiento_z - seat_h / 2),
                     (w * 0.95, d * 0.90, seat_h), (0.22, 0.28, 0.38, 1))
        # RESPALDO detrás (−Y): Kael mira +Y al escritorio; lumbar + panel
        back = _cube(f"param_{oid}_respaldo", (0.0, -d * 0.42, asiento_z + 0.32),
                     (w * 0.78, 0.07, 0.55), (0.22, 0.28, 0.38, 1))
        lumbar = _cube(f"param_{oid}_lumbar", (0.0, -d * 0.36, asiento_z + 0.12),
                       (w * 0.55, 0.06, 0.14), (0.18, 0.22, 0.30, 1))
        ped = _cyl(f"param_{oid}_pedestal", (0.0, 0.0, 0.05), 0.04, asiento_z - 0.14,
                   (0.40, 0.40, 0.42, 1))
        meshes = [seat, back, lumbar, ped]
        leg_r = float(tam.get("pata_radio") or 0.28)
        wheel_r = float(tam.get("rueda_radio") or 0.04)
        for i in range(5):
            ang = i * (2.0 * math.pi / 5.0)
            ex, ey = math.cos(ang) * leg_r, math.sin(ang) * leg_r
            arm = _cube(f"param_{oid}_pata_{i}", (ex * 0.5, ey * 0.5, 0.055),
                        (leg_r * 0.92, 0.055, 0.045), (0.32, 0.32, 0.34, 1))
            arm.rotation_euler[2] = ang
            wheel = _cyl(f"param_{oid}_rueda_{i}", (ex, ey, 0.0), wheel_r, wheel_r * 1.4,
                         (0.12, 0.12, 0.13, 1))
            meshes.extend([arm, wheel])
        hub = _cyl(f"param_{oid}_base_hub", (0.0, 0.0, 0.02), 0.06, 0.06, (0.32, 0.32, 0.34, 1))
        meshes.append(hub)
        for m in meshes:
            m.parent = root
            m.matrix_parent_inverse.identity()
        if rot_z:
            root.rotation_euler[2] = math.radians(rot_z)
    elif oid == "cama":
        # frame + mattress top surface (separable for hundimiento)
        w = float(tam.get("ancho") or 1.1)
        d = float(tam.get("fondo") or 1.9)
        h = float(tam.get("alto") or 0.55)
        frame = _cube(f"param_{oid}_marco", (pos[0], pos[1], h * 0.35), (w, d, h * 0.7), (0.40, 0.30, 0.22, 1))
        colchon = _cube(f"param_{oid}_colchon", (pos[0], pos[1], h - 0.05), (w * 0.95, d * 0.95, 0.12),
                        (0.55, 0.58, 0.65, 1))
        meshes = [frame, colchon]
    elif oid == "puerta_principal" or oid == "puerta_bano":
        # bisagra en borde −X; hoja en coords LOCALES (como silla) para que c rote de verdad
        w = float(tam.get("ancho") or 0.9)
        h = float(tam.get("alto") or 2.1)
        th = float(tam.get("fondo") or 0.05)
        hinge = _empty(f"param_{oid}_hinge", (pos[0] - w / 2, pos[1], h / 2), "SINGLE_ARROW", 0.2)
        # hoja: centro a +w/2 en local X desde bisagra; grosor en Y
        door = _cube(f"param_{oid}_hoja", (w / 2, 0.0, 0.0), (w, th, h), color)
        door.parent = hinge
        door.matrix_parent_inverse.identity()
        if rot_z:
            hinge.rotation_euler[2] = math.radians(rot_z)
        meshes = [door]
    elif oid == "cortina":
        # v4: tela continua que se dobla — cadena de huesos (como hoja), segmentos
        # solapados (~8%) mismo material: no se separan en paneles visibles.
        w = float(tam.get("ancho") or 1.65)
        h = float(tam.get("alto") or 1.45)
        n = max(3, len(spec.get("huesos") or []) or 5)
        panels = []
        root = _empty(f"param_{oid}_root", (pos[0], pos[1], pos[2] + h), "PLAIN_AXES", 0.1)
        prev = root
        seg = h / n
        cloth = (0.48, 0.42, 0.55, 1.0)
        for i in range(n):
            bone = _empty(f"param_{oid}_hueso_{i}", (0.0, 0.0, 0.0), "SINGLE_ARROW", 0.08)
            if i == 0:
                bone.location = (0.0, 0.0, 0.0)
            else:
                bone.location = (0.0, 0.0, -seg)
            bone.parent = prev
            bone.matrix_parent_inverse.identity()
            # solape vertical 8% → tela continua sin huecos entre segmentos
            p = _cube(f"param_{oid}_tela_{i}", (0.0, 0.0, -seg * 0.5),
                      (0.03, w * 0.92, seg * 1.08), cloth)
            p.parent = bone
            p.matrix_parent_inverse.identity()
            panels.append(p)
            prev = bone
        meshes = panels
    elif oid == "lampara":
        base = _cyl(f"param_{oid}_base", (pos[0], pos[1], pos[2]), 0.06, 0.04, color)
        a1 = _empty(f"param_{oid}_art1", (pos[0], pos[1], pos[2] + 0.05), "SINGLE_ARROW", 0.1)
        arm1 = _cube(f"param_{oid}_arm1", (pos[0], pos[1], pos[2] + 0.22), (0.03, 0.03, 0.35), color)
        arm1.parent = a1
        arm1.matrix_parent_inverse = a1.matrix_world.inverted()
        a2 = _empty(f"param_{oid}_art2", (pos[0], pos[1], pos[2] + 0.40), "SINGLE_ARROW", 0.08)
        a2.parent = a1
        head = _cube(f"param_{oid}_cabeza", (pos[0] + 0.15, pos[1], pos[2] + 0.45), (0.12, 0.08, 0.06),
                     (0.7, 0.65, 0.3, 1))
        head.parent = a2
        head.matrix_parent_inverse = a2.matrix_world.inverted()
        meshes = [base, arm1, head]
    elif forma == "cilindro":
        r = float(tam.get("r") or 0.1)
        h = float(tam.get("alto") or 0.3)
        meshes = [_cyl(f"param_{oid}", pos, r, h, color)]
    elif forma == "plano":
        w = float(tam.get("ancho") or 1)
        d = float(tam.get("fondo") or 1)
        h = float(tam.get("alto") or 0.02)
        meshes = [_cube(f"param_{oid}", (pos[0], pos[1], pos[2] + h / 2), (w, d, h), color)]
    else:
        w = float(tam.get("ancho") or 0.5)
        d = float(tam.get("fondo") or 0.5)
        h = float(tam.get("alto") or 0.5)
        meshes = [_cube(f"param_{oid}", (pos[0], pos[1], pos[2] + h / 2), (w, d, h), color)]
        if rot_z and meshes:
            meshes[0].rotation_euler[2] = math.radians(rot_z)

    # Named points as empties (world coords from JSON)
    puntos_objs = {}
    for pname, pdata in (spec.get("puntos") or {}).items():
        xyz = pdata.get("xyz") if isinstance(pdata, dict) else pdata
        if not xyz:
            continue
        e = _empty(pname, tuple(xyz), "PLAIN_AXES", 0.1)
        puntos_objs[pname] = e

    return {"id": oid, "meshes": [m.name for m in meshes], "puntos": list(puntos_objs.keys()),
            "huesos": spec.get("huesos") or []}


def apply_param(c: float, bone_spec: dict, obj_name_hint: str = ""):
    """Aplica c∈[0,1] a un hueso/empty según spec (rotación, traslación, color o intensidad)."""
    c = max(0.0, min(1.0, float(c)))
    bid = bone_spec.get("id") or ""

    # --- v4: intensidad de luz (c0/c1 sin deg/m) ---
    if bid == "luz.intensidad" or (bone_spec.get("param") == "encendida" and bid.startswith("luz.")):
        c0 = float(bone_spec.get("c0") if bone_spec.get("c0") is not None else 1.0)
        c1 = float(bone_spec.get("c1") if bone_spec.get("c1") is not None else 0.0)
        val = c0 + (c1 - c0) * c
        # marcador + empty de control
        for nm in ("param_iluminacion", "param_luz_intensidad", "luz.intensidad"):
            o = bpy.data.objects.get(nm)
            if o is None and nm == "param_luz_intensidad":
                o = _empty("param_luz_intensidad", (2.5, 3.0, 2.7), "PLAIN_AXES", 0.05)
            if o is not None:
                o["intensidad"] = float(val)
                o["c"] = float(c)
                o.color = (0.9 * val + 0.05, 0.85 * val + 0.05, 0.55 * val + 0.05, 1.0)
                if o.type == "MESH" and o.data.materials:
                    o.data.materials[0].diffuse_color = o.color
        for L in bpy.data.lights:
            if "_base_energy" not in L:
                L["_base_energy"] = float(L.energy)
            L.energy = float(L["_base_energy"]) * max(0.05, float(val))
        # atenúa world si existe
        w = bpy.context.scene.world
        if w is not None and hasattr(w, "node_tree") and w.node_tree:
            for node in w.node_tree.nodes:
                if node.type == "BACKGROUND":
                    if "_base_str" not in w:
                        w["_base_str"] = float(node.inputs[1].default_value)
                    node.inputs[1].default_value = float(w["_base_str"]) * max(0.08, float(val))
        return True

    # --- v4: encendido / corriente por color (monitor, computador, cables) ---
    if bid.endswith(".encendido") or bid.endswith(".corriente") or (
        bone_spec.get("param") in ("encendida", "corriente_azul") and "c0_deg" not in bone_spec and "c0_m" not in bone_spec
        and bid != "luz.intensidad"
    ):
        oid = bid.split(".")[0]
        candidates = [f"param_{oid}", oid, f"param_{oid}_tela_0"]
        o = None
        for n in candidates:
            o = bpy.data.objects.get(n)
            if o:
                break
        if o is None:
            return False
        col0 = bone_spec.get("color_c0") or [0.08, 0.08, 0.10, 1.0]
        col1 = bone_spec.get("color_c1") or [0.12, 0.75, 0.95, 1.0]
        rgba = tuple(float(col0[i]) + (float(col1[i]) - float(col0[i])) * c for i in range(4))
        o.color = rgba
        if o.type == "MESH" and o.data.materials:
            o.data.materials[0].diffuse_color = rgba
        o["c"] = float(c)
        return True

    # find empty
    candidates = [bid, f"param_{bid}", bid.replace(".", "_")]
    # door hinge mapping
    if bid == "puerta.bisagra":
        candidates = ["param_puerta_principal_hinge", "puerta.bisagra"] + candidates
    if bid == "puerta_bano.bisagra":
        candidates = ["param_puerta_bano_hinge"] + candidates
    if bid.startswith("cortina.hueso"):
        i = bid.split("_")[-1]
        candidates = [f"param_cortina_hueso_{i}"] + candidates
    if bid.startswith("lampara.articulacion"):
        n = "1" if "1" in bid else "2"
        candidates = [f"param_lampara_art{n}"] + candidates
    if bid == "silla.giro":
        candidates = ["param_silla_root", "silla.giro"] + candidates
    if bid == "colchon.hundimiento":
        candidates = ["param_cama_colchon"] + candidates
    o = None
    for n in candidates:
        o = bpy.data.objects.get(n)
        if o:
            break
    if o is None:
        return False
    eje = (bone_spec.get("eje") or "z").lower()
    axis = {"x": 0, "y": 1, "z": 2}.get(eje, 2)
    if "c0_deg" in bone_spec or "c1_deg" in bone_spec:
        a0 = float(bone_spec.get("c0_deg") or 0)
        a1 = float(bone_spec.get("c1_deg") or 0)
        ang = math.radians(a0 + (a1 - a0) * c)
        o.rotation_mode = "XYZ"
        o.rotation_euler[axis] = ang
    elif "c0_m" in bone_spec or "c1_m" in bone_spec:
        m0 = float(bone_spec.get("c0_m") or 0)
        m1 = float(bone_spec.get("c1_m") or 0)
        delta = m0 + (m1 - m0) * c
        # store base if needed
        base_key = f"_base_{axis}"
        if base_key not in o:
            o[base_key] = float(o.location[axis])
        o.location[axis] = float(o[base_key]) + delta
    return True


def build_scene(doc: dict, hide_replaced: bool = True) -> dict:
    assert bpy is not None
    report = {"hidden": [], "built": [], "puntos": [], "huesos": []}
    to_hide = []
    for spec in doc.get("objetos") or []:
        rm = spec.get("reemplaza_molde")
        if rm:
            to_hide.append(rm)
        # also hide by common name fragments for silla/cama etc
        if spec["id"] == "silla":
            to_hide += ["silla-ergonomica", "silla_ergonomica", "silla ergonom"]
        if spec["id"] == "cama":
            to_hide += ["cama-individual", "cama_individual"]
        if spec["id"] == "escritorio":
            to_hide += ["escritorio-muebles", "obj-escritorio"]
        if spec["id"] == "columna":
            to_hide += ["Columna del techo"]
    if hide_replaced:
        report["hidden"] = hide_molde(to_hide)

    for spec in doc.get("objetos") or []:
        try:
            info = build_object(spec)
            report["built"].append(info["id"])
            report["puntos"].extend(info["puntos"])
            for h in info["huesos"]:
                report["huesos"].append({"objeto": info["id"], **h})
        except Exception as ex:
            report.setdefault("errores", []).append(f"{spec.get('id')}: {ex}")
    # Tag floor objects for piso()
    for nm in ("param_piso", "param_alfombra"):
        o = bpy.data.objects.get(nm)
        if o:
            o["es_suelo"] = 1
    return report


def punto_world(name: str) -> Optional[Tuple[float, float, float]]:
    o = bpy.data.objects.get(name)
    if o is None:
        return None
    loc = o.matrix_world.translation
    return (float(loc.x), float(loc.y), float(loc.z))
