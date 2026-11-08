# -*- coding: utf-8 -*-
"""
Motor genérico de fondos v2 — MYIA / Star.
Entrada: escenario_vivo_render.json (formula + ancla_z) + plan_tomas + estado_luces + materiales.
Salida: PNG por toma + .blend + informe FALTA + QC cámara.
Sin código de una escena concreta. Fórmulas desconocidas → FALTA.
US$0. Solo Blender local.
"""
from __future__ import annotations
import argparse, json, math, sys, random
from pathlib import Path

import bpy
from mathutils import Vector, Euler

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.worlds, bpy.data.curves):
        for b in list(coll):
            coll.remove(b)

def mat_pbr(name, base=(0.5,0.5,0.5), rough=0.5, metal=0.0, emit=None, emit_strength=0.0,
            transmission=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metal
    if transmission > 0:
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        elif "Transmission" in bsdf.inputs:
            bsdf.inputs["Transmission"].default_value = transmission
    if alpha < 1.0:
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    if emit and emit_strength > 0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emit_strength
        else:
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs["Color"].default_value = (*emit, 1.0)
            em.inputs["Strength"].default_value = emit_strength
            mix = nt.nodes.new("ShaderNodeAddShader")
            nt.links.new(bsdf.outputs["BSDF"], mix.inputs[0])
            nt.links.new(em.outputs["Emission"], mix.inputs[1])
            nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
            return m
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_glass(name="vidrio"):
    return mat_pbr(name, base=(0.85, 0.92, 1.0), rough=0.05, transmission=0.9, alpha=0.25)

def mat_from_catalog(formula, mats_cat, override_base=None, suffix=""):
    d = mats_cat.get(formula) or mats_cat.get("bbox") or {"base":[0.5,0.5,0.5],"rough":0.6,"nombre":"neutro"}
    base = tuple(override_base) if override_base else tuple(d.get("base") or [0.5,0.5,0.5])
    return mat_pbr(
        (d.get("nombre") or formula) + suffix,
        base=base,
        rough=float(d.get("rough", 0.5)),
        metal=float(d.get("metal", 0.0)),
        emit=d.get("emit"),
        emit_strength=float(d.get("emit_strength") or 0.0),
    ), d

def set_emission_strength(mat, strength, color=None):
    if not mat or not mat.node_tree:
        return
    nt = mat.node_tree
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            if "Emission Strength" in n.inputs:
                n.inputs["Emission Strength"].default_value = strength
            if color is not None and "Emission Color" in n.inputs:
                n.inputs["Emission Color"].default_value = (*color, 1.0)
        if n.type == "EMISSION":
            n.inputs["Strength"].default_value = strength
            if color is not None:
                n.inputs["Color"].default_value = (*color, 1.0)

def box(name, size, loc, mat, rot=(0,0,0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    o = bpy.context.active_object
    o.name = name
    o.dimensions = (float(size[0]), float(size[1]), float(size[2]))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = loc
    o.rotation_euler = rot
    if bevel > 0:
        mod = o.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = "ANGLE"
    if mat:
        o.data.materials.append(mat)
    return o

def cyl(name, r, h, loc, mat, verts=24, rot=(0,0,0)):
    """loc = center of cylinder."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, vertices=verts)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    if mat:
        o.data.materials.append(mat)
    return o

def cyl_base(name, r, h, loc_base, mat, verts=24, rot=(0,0,0)):
    """loc_base = bottom of cylinder (Z+ up)."""
    return cyl(name, r, h, (loc_base[0], loc_base[1], loc_base[2] + h/2), mat, verts, rot)

def plane(name, size_xy, loc, mat, rot=(0,0,0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0,0,0))
    o = bpy.context.active_object
    o.name = name
    o.dimensions = (float(size_xy[0]), float(size_xy[1]), 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = loc
    o.rotation_euler = rot
    if mat:
        o.data.materials.append(mat)
    return o

def look_at(obj, target):
    d = Vector(target) - Vector(obj.location)
    if d.length < 1e-6:
        return
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def center_from_ancla(spec):
    """Return world center of object bbox given ancla_z convention."""
    p = list(spec["pos_m"])
    s = list(spec["tamano_m"])
    ancla = spec.get("ancla_z") or "base"
    if ancla == "base":
        return [p[0], p[1], p[2] + s[2] / 2.0]
    if ancla == "habitacion_piso":
        return [p[0], p[1], s[2] / 2.0]  # walls/room: floor at 0, center at H/2
    if ancla == "plano":
        return [p[0], p[1], p[2] + s[2] / 2.0]
    return p  # centro

def base_pos_from_ancla(spec):
    """Return [x,y,z_base] for builders that grow upward from the bottom."""
    p = list(spec["pos_m"])
    s = list(spec["tamano_m"])
    ancla = spec.get("ancla_z") or "base"
    if ancla == "centro":
        return [p[0], p[1], p[2] - s[2] / 2.0]
    if ancla == "habitacion_piso":
        return [p[0], p[1], 0.0]
    return [p[0], p[1], p[2]]

# ---------------------------------------------------------------------------
REGISTRY = {}
LIGHT_HANDLES = {}
SKY_BUILT = False

def register(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco

@register("caja")
@register("bbox")
def f_caja(spec, mats_cat, report):
    mat, _ = mat_from_catalog(spec["formula"], mats_cat, suffix=f"_{spec['id']}")
    c = center_from_ancla(spec)
    return [box(spec["id"], spec["tamano_m"], c, mat, bevel=0.008)]

@register("cilindro")
def f_cil(spec, mats_cat, report):
    mat, _ = mat_from_catalog("cilindro", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = spec["pos_m"]
    r = max(s[0], s[1]) / 2
    if r < 1e-6:
        report["falta"].append(f"{spec['id']}: radio 0 → omitido")
        return []
    ancla = spec.get("ancla_z") or "base"
    if ancla == "base":
        return [cyl_base(spec["id"], r, s[2], p, mat)]
    return [cyl(spec["id"], r, s[2], center_from_ancla(spec), mat)]

@register("plano")
def f_plano(spec, mats_cat, report):
    mat, _ = mat_from_catalog("plano" if spec["id"] == "piso" or "piso" in spec["id"] or "calzada" in spec["id"]
                             else spec["formula"], mats_cat, suffix=f"_{spec['id']}")
    # wood floor variation for piso
    if "piso" in spec["id"] or "calzada" in spec["id"]:
        base = (0.48, 0.34, 0.20) if "piso" in spec["id"] else (0.35, 0.35, 0.36)
        mat = mat_pbr(f"suelo_{spec['id']}", base=base, rough=0.55)
    s = spec["tamano_m"]; p = spec["pos_m"]
    if s[2] < 0.05:
        o = plane(spec["id"], (s[0], s[1]), (p[0], p[1], p[2] + s[2]/2), mat)
        return [o]
    return [box(spec["id"], s, center_from_ancla(spec), mat, bevel=0.002)]

@register("punto")
def f_punto(spec, mats_cat, report):
    report["falta"].append(f"{spec['id']}: fórmula 'punto' es marcador lógico → omitido")
    return []

def _build_sky_outside_window(wall_x, cy, win_bottom, win_h, win_w, report):
    """Generic starry clear night sky plate + stars behind an opening."""
    global SKY_BUILT
    if SKY_BUILT:
        return []
    SKY_BUILT = True
    objs = []
    sky = mat_pbr("cielo_noche", base=(0.01, 0.015, 0.05), rough=1.0,
                  emit=(0.04, 0.06, 0.14), emit_strength=0.6)
    # vertical plate just outside wall (YZ plane)
    plate = box("cielo_exterior",
                (0.04, win_w * 1.6, win_h * 1.5),
                (wall_x + 0.55, cy, win_bottom + win_h / 2),
                sky)
    objs.append(plate)
    star_mat = mat_pbr("estrella", base=(1, 1, 0.9), rough=1,
                       emit=(1, 1, 0.9), emit_strength=14)
    rng = random.Random(42)
    for si in range(55):
        sy = cy + rng.uniform(-win_w * 0.7, win_w * 0.7)
        sz = win_bottom + rng.uniform(0.08, win_h * 0.95)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.012, 0.028),
                                            location=(wall_x + 0.5, sy, sz))
        so = bpy.context.active_object
        so.name = f"estrella_{si}"
        so.data.materials.append(star_mat)
        objs.append(so)
    report.setdefault("notas", []).append("cielo_nocturno: placa + estrellas emisivas (no HDRI)")
    return objs

@register("muros_caja_con_huecos")
def f_muros(spec, mats_cat, report):
    """4 paredes + techo. Huecos: paneles alrededor (no boolean frágil). ancla habitacion_piso."""
    mat, _ = mat_from_catalog("muros_caja_con_huecos", mats_cat)
    mat_techo = mat_pbr("techo", base=(0.88, 0.87, 0.84), rough=0.9)
    s = spec["tamano_m"]; p = spec["pos_m"]
    W, D, H = s
    # Room AABB: XY from center p, Z from 0 to H (habitacion_piso)
    cx, cy = p[0], p[1]
    x0, x1 = cx - W/2, cx + W/2
    y0, y1 = cy - D/2, cy + D/2
    thick = 0.08
    objs = []
    # front / back / left — solid
    objs.append(box(f"{spec['id']}_muro_frente", (W + thick*2, thick, H),
                    (cx, y0 - thick/2, H/2), mat, bevel=0.004))
    objs.append(box(f"{spec['id']}_muro_fondo", (W + thick*2, thick, H),
                    (cx, y1 + thick/2, H/2), mat, bevel=0.004))
    objs.append(box(f"{spec['id']}_muro_izq", (thick, D, H),
                    (x0 - thick/2, cy, H/2), mat, bevel=0.004))

    # right wall: cut opening with panels if hueco on 'der'
    huecos = spec.get("huecos") or []
    der_hueco = None
    for h in huecos:
        if h.get("pared") in ("der", "right", "+x", None) or True:
            # prefer explicit pared; if only one hueco assume der (MYIA habitación)
            if h.get("pared") in ("der", "right", "+x") or len(huecos) == 1:
                der_hueco = h
                break
    if der_hueco is None and huecos:
        der_hueco = huecos[0]

    if der_hueco:
        hp = der_hueco["pos_m"]; ht = der_hueco["tamano_m"]
        ancla_h = der_hueco.get("ancla_z") or "base"
        # Window size: ancho along Y, alto along Z, fondo = thickness
        vw, vh = ht[0], ht[2]  # ancho, alto
        if ancla_h == "base":
            win_bottom = hp[2]
        else:
            win_bottom = hp[2] - vh / 2
        win_top = win_bottom + vh
        win_cy = hp[1]
        win_y0 = win_cy - vw / 2
        win_y1 = win_cy + vw / 2
        # validate opening intersects right wall
        if abs(hp[0] - x1) > 0.5:
            report["dudas"].append(
                f"{spec['id']}: hueco ventana pos.x={hp[0]} lejos de muro_der x={x1} → DUDA (se recorta igual en muro_der)")
        # below
        if win_bottom > 0.02:
            objs.append(box(f"{spec['id']}_muro_der_bajo", (thick, D, win_bottom),
                            (x1 + thick/2, cy, win_bottom/2), mat, bevel=0.003))
        # above
        above_h = H - win_top
        if above_h > 0.02:
            objs.append(box(f"{spec['id']}_muro_der_alto", (thick, D, above_h),
                            (x1 + thick/2, cy, win_top + above_h/2), mat, bevel=0.003))
        # sides of opening
        if win_y0 > y0 + 0.02:
            objs.append(box(f"{spec['id']}_muro_der_y0", (thick, win_y0 - y0, vh),
                            (x1 + thick/2, (y0 + win_y0)/2, win_bottom + vh/2), mat, bevel=0.003))
        if win_y1 < y1 - 0.02:
            objs.append(box(f"{spec['id']}_muro_der_y1", (thick, y1 - win_y1, vh),
                            (x1 + thick/2, (win_y1 + y1)/2, win_bottom + vh/2), mat, bevel=0.003))
        if spec.get("cielo_nocturno"):
            objs.extend(_build_sky_outside_window(x1, win_cy, win_bottom, vh, vw, report))
    else:
        objs.append(box(f"{spec['id']}_muro_der", (thick, D, H),
                        (x1 + thick/2, cy, H/2), mat, bevel=0.004))
        if huecos:
            report["falta"].append(f"{spec['id']}: huecos presentes pero no se pudo ubicar pared")

    objs.append(box(f"{spec['id']}_techo", (W + thick*2, D + thick*2, thick),
                    (cx, cy, H + thick/2), mat_techo))
    return objs

@register("puerta_bisagra")
def f_puerta(spec, mats_cat, report):
    mat, _ = mat_from_catalog("puerta_bisagra", mats_cat, suffix=f"_{spec['id']}")
    mat_osc = mat_pbr(f"{spec['id']}_panel", base=(0.28, 0.18, 0.10), rough=0.48)
    metal, _ = mat_from_catalog("cilindro", mats_cat, suffix=f"_{spec['id']}_pomo")
    s = spec["tamano_m"]; p = spec["pos_m"]
    c = center_from_ancla(spec)
    leaf = box(spec["id"], (s[0], max(0.04, s[1]), s[2]), c, mat, bevel=0.008)
    panel = box(f"{spec['id']}_panel", (s[0]*0.7, 0.01, s[2]*0.55),
                (c[0], c[1] - max(0.04, s[1])*0.4, c[2] + s[2]*0.05), mat_osc, bevel=0.004)
    pomo = cyl(f"{spec['id']}_pomo", 0.025, 0.04,
               (c[0] + s[0]*0.35, c[1] - max(0.04, s[1]), c[2]), metal, rot=(math.radians(90), 0, 0))
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(p[0] - s[0]/2, p[1], p[2]))
    h = bpy.context.active_object
    h.name = f"{spec['id']}_bisagra"
    return [leaf, panel, pomo, h]

@register("ventana_marco_vidrio")
def f_ventana(spec, mats_cat, report):
    """Marco real (4 lados + travesaño) + vidrio transparente. ancla base = alféizar."""
    mat, _ = mat_from_catalog("ventana_marco_vidrio", mats_cat, suffix=f"_{spec['id']}")
    glass = mat_glass(f"{spec['id']}_vidrio")
    s = spec["tamano_m"]; p = spec["pos_m"]
    # Window sits on wall: ancho along Y, alto Z, fondo X thickness
    vw, vd, vh = s[0], max(0.05, s[1]), s[2]
    ancla = spec.get("ancla_z") or "base"
    if ancla == "base":
        cz = p[2] + vh / 2
    else:
        cz = p[2]
    cx, cy = p[0], p[1]
    fd = 0.06
    objs = [
        box(f"{spec['id']}_marco_izq", (fd, 0.05, vh), (cx, cy - vw/2, cz), mat, bevel=0.003),
        box(f"{spec['id']}_marco_der", (fd, 0.05, vh), (cx, cy + vw/2, cz), mat, bevel=0.003),
        box(f"{spec['id']}_marco_sup", (fd, vw, 0.05), (cx, cy, cz + vh/2), mat, bevel=0.003),
        box(f"{spec['id']}_marco_inf", (fd, vw, 0.05), (cx, cy, cz - vh/2), mat, bevel=0.003),
        box(f"{spec['id']}_travesano", (fd*0.8, vw, 0.03), (cx, cy, cz), mat, bevel=0.002),
        box(f"{spec['id']}_vidrio", (0.012, vw*0.92, vh*0.92), (cx - 0.02, cy, cz), glass),
    ]
    return objs

@register("cortina_enrollable")
def f_cortina(spec, mats_cat, report):
    mat, _ = mat_from_catalog("cortina_enrollable", mats_cat, suffix=f"_{spec['id']}")
    metal, _ = mat_from_catalog("cilindro", mats_cat, suffix=f"_{spec['id']}_riel")
    s = spec["tamano_m"]; p = spec["pos_m"]
    ancla = spec.get("ancla_z") or "base"
    if ancla == "base":
        top_z = p[2] + s[2] * 0.9
        hang_h = s[2] * 0.35
        hang_cz = top_z - hang_h / 2
    else:
        c = center_from_ancla(spec)
        top_z = c[2] + s[2] * 0.4
        hang_h = s[2] * 0.35
        hang_cz = top_z - hang_h / 2
    riel = cyl(f"{spec['id']}_riel", 0.035, s[0]*0.95, (p[0], p[1], top_z), metal,
               rot=(math.radians(90), 0, 0))
    tela = box(f"{spec['id']}_tela", (0.02, s[0]*0.9, hang_h), (p[0] - 0.02, p[1], hang_cz), mat, bevel=0.005)
    return [riel, tela]

@register("escritorio_patas")
def f_escritorio(spec, mats_cat, report):
    mat, _ = mat_from_catalog("escritorio_patas", mats_cat, suffix=f"_{spec['id']}")
    metal = mat_pbr(f"{spec['id']}_pata", base=(0.3, 0.31, 0.33), rough=0.35, metal=0.7)
    s = spec["tamano_m"]; p = spec["pos_m"]
    # base ancla: top at p[2]+s[2]
    top_h = 0.04
    top_z = p[2] + s[2] - top_h/2
    top = box(f"{spec['id']}_tablero", (s[0], s[1], top_h), (p[0], p[1], top_z), mat, bevel=0.01)
    faldon = box(f"{spec['id']}_faldon", (s[0]*0.95, 0.03, 0.08),
                 (p[0], p[1] - s[1]*0.35, p[2] + s[2] - 0.08), mat, bevel=0.004)
    # drawer block under right side
    cajon = box(f"{spec['id']}_cajon", (s[0]*0.35, s[1]*0.85, 0.18),
                (p[0] + s[0]*0.25, p[1], p[2] + s[2] - 0.18), mat, bevel=0.006)
    objs = [top, faldon, cajon]
    leg_w = 0.05
    hx, hy = s[0]*0.45, s[1]*0.40
    for i, (dx, dy) in enumerate([(-hx,-hy),(hx,-hy),(-hx,hy),(hx,hy)]):
        objs.append(box(f"{spec['id']}_pata_{i}", (leg_w, leg_w, s[2]-top_h),
                        (p[0]+dx, p[1]+dy, p[2] + (s[2]-top_h)/2), metal, bevel=0.003))
    return objs

@register("mesa_simple")
def f_mesa(spec, mats_cat, report):
    mat, _ = mat_from_catalog("mesa_simple", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    top_h = 0.04
    top = box(f"{spec['id']}_tablero", (s[0], s[1], top_h), (p[0], p[1], p[2]+s[2]-top_h/2), mat, bevel=0.008)
    objs = [top]
    for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        objs.append(cyl_base(f"{spec['id']}_pata_{dx}_{dy}", 0.025, s[2]-top_h,
                             (p[0]+dx*(s[0]/2-0.06), p[1]+dy*(s[1]/2-0.06), p[2]), mat))
    return objs

@register("silla_giratoria_ergonomica")
def f_silla(spec, mats_cat, report):
    mat, _ = mat_from_catalog("silla_giratoria_ergonomica", mats_cat, suffix=f"_{spec['id']}")
    metal = mat_pbr(f"{spec['id']}_metal", base=(0.35,0.36,0.38), rough=0.35, metal=0.7)
    s = spec["tamano_m"]; p = spec["pos_m"]
    asiento_z = 0.45
    w, d = s[0], s[1]
    objs = []
    objs.append(box(f"{spec['id']}_asiento", (w*0.95, d*0.9, 0.08), (p[0], p[1], asiento_z), mat, bevel=0.015))
    objs.append(box(f"{spec['id']}_espalda", (w*0.78, 0.07, 0.55), (p[0], p[1]-d*0.42, asiento_z+0.32), mat, bevel=0.012))
    objs.append(box(f"{spec['id']}_lumbar", (w*0.55, 0.06, 0.14), (p[0], p[1]-d*0.36, asiento_z+0.12), mat, bevel=0.01))
    for side, sx in (("L", -w*0.48), ("R", w*0.48)):
        objs.append(box(f"{spec['id']}_brazo_{side}", (0.04, d*0.55, 0.04), (p[0]+sx, p[1], asiento_z+0.12), metal, bevel=0.005))
    objs.append(cyl_base(f"{spec['id']}_columna", 0.035, asiento_z-0.12, (p[0], p[1], 0.08), metal))
    objs.append(cyl_base(f"{spec['id']}_hub", 0.06, 0.05, (p[0], p[1], 0.02), metal))
    leg_r = 0.28
    for i in range(5):
        ang = i * (2*math.pi/5)
        ex, ey = math.cos(ang)*leg_r, math.sin(ang)*leg_r
        arm = box(f"{spec['id']}_pata_{i}", (leg_r*0.92, 0.05, 0.04),
                  (p[0]+ex*0.5, p[1]+ey*0.5, 0.05), metal, bevel=0.003)
        arm.rotation_euler[2] = ang
        objs.append(arm)
        objs.append(cyl_base(f"{spec['id']}_rueda_{i}", 0.035, 0.045, (p[0]+ex, p[1]+ey, 0.0), metal, verts=12))
    return objs

@register("silla_simple")
def f_silla_simple(spec, mats_cat, report):
    mat, _ = mat_from_catalog("silla_simple", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    seat_z = min(0.45, s[2]*0.5)
    objs = [
        box(f"{spec['id']}_asiento", (s[0]*0.9, s[1]*0.9, 0.05), (p[0], p[1], p[2]+seat_z), mat, bevel=0.008),
        box(f"{spec['id']}_espalda", (s[0]*0.9, 0.05, s[2]*0.45), (p[0], p[1]-s[1]*0.4, p[2]+seat_z+s[2]*0.25), mat, bevel=0.006),
    ]
    for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        objs.append(cyl_base(f"{spec['id']}_pata_{dx}_{dy}", 0.02, seat_z,
                             (p[0]+dx*s[0]*0.35, p[1]+dy*s[1]*0.35, p[2]), mat))
    return objs

@register("cama_marco_colchon")
def f_cama(spec, mats_cat, report):
    mat, _ = mat_from_catalog("cama_marco_colchon", mats_cat, suffix=f"_{spec['id']}")
    cloth = mat_pbr(f"{spec['id']}_colchon", base=(0.75, 0.72, 0.68), rough=0.9)
    mat_cab = mat_pbr(f"{spec['id']}_cab", base=(0.28, 0.18, 0.10), rough=0.5)
    s = spec["tamano_m"]; p = spec["pos_m"]
    w, d, h = s
    frame = box(f"{spec['id']}_marco", (w, d, h*0.55), (p[0], p[1], p[2]+h*0.3), mat, bevel=0.01)
    cab = box(f"{spec['id']}_cabecero", (w, 0.05, h*0.7), (p[0], p[1]+d*0.48, p[2]+h*0.55), mat_cab, bevel=0.008)
    colchon = box(f"{spec['id']}_colchon", (w*0.95, d*0.92, 0.14), (p[0], p[1], p[2]+h-0.06), cloth, bevel=0.02)
    return [frame, cab, colchon]

@register("almohada_simple")
def f_almohada(spec, mats_cat, report):
    mat, _ = mat_from_catalog("almohada_simple", mats_cat, suffix=f"_{spec['id']}")
    return [box(spec["id"], spec["tamano_m"], center_from_ancla(spec), mat, bevel=0.03)]

@register("manta_simple")
def f_manta(spec, mats_cat, report):
    mat, _ = mat_from_catalog("manta_simple", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = spec["pos_m"]
    return [box(spec["id"], (s[0], s[1], max(0.04, s[2])), center_from_ancla(spec), mat, bevel=0.015)]

@register("armario_2puertas")
def f_armario(spec, mats_cat, report):
    mat, _ = mat_from_catalog("armario_2puertas", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    cuerpo = box(spec["id"], s, c, mat, bevel=0.008)
    seam = box(f"{spec['id']}_junta", (0.01, 0.02, s[2]*0.9),
               (c[0], c[1]-s[1]/2, c[2]), mat_pbr("junta", base=(0.2,0.15,0.1), rough=0.5))
    # handles
    metal = mat_pbr(f"{spec['id']}_pomo", base=(0.4,0.4,0.42), rough=0.3, metal=0.8)
    for dx in (-s[0]*0.15, s[0]*0.15):
        box(f"{spec['id']}_pomo_{dx}", (0.02, 0.02, 0.12),
            (c[0]+dx, c[1]-s[1]/2-0.01, c[2]), metal)
    return [cuerpo, seam]

@register("estanteria_abierta")
def f_estanteria(spec, mats_cat, report):
    mat, _ = mat_from_catalog("estanteria_abierta", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = spec["pos_m"]
    c = center_from_ancla(spec)
    thick = 0.025
    objs = [
        box(f"{spec['id']}_lat_izq", (thick, s[1], s[2]), (c[0]-s[0]/2+thick/2, c[1], c[2]), mat, bevel=0.003),
        box(f"{spec['id']}_lat_der", (thick, s[1], s[2]), (c[0]+s[0]/2-thick/2, c[1], c[2]), mat, bevel=0.003),
        box(f"{spec['id']}_fondo", (s[0], thick, s[2]), (c[0], c[1]+s[1]/2-thick/2, c[2]), mat, bevel=0.002),
    ]
    n = 4
    for i in range(n):
        z = p[2] + (i + 0.5) * (s[2] / n)
        objs.append(box(f"{spec['id']}_balda_{i}", (s[0]-2*thick, s[1]*0.95, thick), (c[0], c[1], z), mat, bevel=0.002))
    # items only if children listed in data — none here; leave empty shelves (no invent)
    return objs

@register("monitor_pantalla")
def f_monitor(spec, mats_cat, report):
    d = mats_cat.get("monitor_pantalla") or {}
    mat_body, _ = mat_from_catalog("monitor_pantalla", mats_cat, suffix=f"_{spec['id']}")
    emit_col = tuple(d.get("pantalla_emit") or [0.05, 0.85, 1.0])
    energy = float(d.get("pantalla_energy") or 8.0)
    mat_scr = mat_pbr(f"{spec['id']}_scr", base=(0.02,0.02,0.03), rough=0.2,
                      emit=emit_col, emit_strength=energy)
    s = spec["tamano_m"]; p = spec["pos_m"]
    # ancla base = bottom of stand on desk
    root_z = p[2]
    bezel = box(f"{spec['id']}_cuerpo", (s[0], max(0.04, s[1]), s[2]*0.9),
                (p[0], p[1], root_z + s[2]*0.55), mat_body, bevel=0.004)
    scr = box(f"{spec['id']}_pantalla", (s[0]*0.88, 0.008, s[2]*0.78),
              (p[0], p[1] - max(0.04, s[1])*0.55, root_z + s[2]*0.55), mat_scr)
    neck = box(f"{spec['id']}_cuello", (0.03, 0.03, 0.16),
               (p[0], p[1]+0.03, root_z + 0.12), mat_body, bevel=0.002)
    stand = box(f"{spec['id']}_pie", (s[0]*0.35, s[1]*1.2, 0.03),
                (p[0], p[1], root_z + 0.015), mat_body, bevel=0.004)
    # AREA light from screen (readable glow)
    bpy.ops.object.light_add(type="AREA", location=(p[0], p[1] - 0.12, root_z + s[2]*0.55))
    L = bpy.context.active_object
    L.name = f"{spec['id']}_luz"
    L.data.energy = float(d.get("area_light_energy") or 28.0)
    L.data.color = (0.35, 0.85, 1.0)
    L.data.shape = "RECTANGLE"
    L.data.size = s[0] * 0.8
    if hasattr(L.data, "size_y"):
        L.data.size_y = s[2] * 0.7
    L.rotation_euler = Euler((math.radians(-90), 0, 0), "XYZ")
    LIGHT_HANDLES[spec["id"]] = {
        "tipo": "monitor", "mats": [mat_scr], "energy_base": energy,
        "light": L, "light_energy_base": float(d.get("area_light_energy") or 28.0),
    }
    return [bezel, scr, neck, stand, L]

@register("torre_pc")
def f_torre(spec, mats_cat, report):
    mat, _ = mat_from_catalog("torre_pc", mats_cat, suffix=f"_{spec['id']}")
    c = center_from_ancla(spec)
    cuerpo = box(spec["id"], spec["tamano_m"], c, mat, bevel=0.006)
    led = mat_pbr(f"{spec['id']}_led", base=(0.1,0.5,1), rough=0.3, emit=(0.2,0.7,1), emit_strength=3)
    strip = box(f"{spec['id']}_led", (0.03, 0.005, 0.01),
                (c[0], c[1]-spec["tamano_m"][1]/2, spec["pos_m"][2]+0.08), led)
    return [cuerpo, strip]

@register("teclado_simple")
def f_teclado(spec, mats_cat, report):
    mat, _ = mat_from_catalog("teclado_simple", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    body = box(spec["id"], s, c, mat, bevel=0.003)
    objs = [body]
    mat_k = mat_pbr(f"{spec['id']}_tecla", base=(0.25,0.25,0.27), rough=0.5)
    for i in range(8):
        objs.append(box(f"{spec['id']}_tecla_{i}",
                        (0.035, 0.035, 0.008),
                        (c[0]-s[0]*0.35+i*0.05, c[1], c[2]+s[2]/2+0.005), mat_k))
    return objs

@register("cables_haz")
def f_cables(spec, mats_cat, report):
    d = mats_cat.get("cables_haz") or {}
    mat = mat_pbr(f"{spec['id']}_cable", base=tuple(d.get("base") or [0.18,0.18,0.2]), rough=0.55)
    emit_col = tuple(d.get("emit_on") or [0.05, 0.85, 1.0])
    s = spec["tamano_m"]; p = spec["pos_m"]
    objs = []
    for i, dx in enumerate((-0.12, -0.04, 0.04, 0.1)):
        # floor run
        o1 = cyl(f"{spec['id']}_suelo_{i}", 0.01, 0.32, (p[0]+dx, p[1], 0.02), mat, verts=10,
                 rot=(math.radians(90), 0, 0))
        # vertical up toward desk
        o2 = cyl_base(f"{spec['id']}_vert_{i}", 0.009, 0.7, (p[0]+dx, p[1]+0.12, 0.0), mat, verts=10)
        objs.extend([o1, o2])
    # point light for corriente (toggled by state)
    bpy.ops.object.light_add(type="POINT", location=(p[0], p[1], 0.35))
    L = bpy.context.active_object
    L.name = f"{spec['id']}_luz"
    L.data.energy = 0.0  # off until corriente
    L.data.color = (0.2, 0.85, 1.0)
    LIGHT_HANDLES[spec["id"]] = {
        "tipo": "cables", "mats": [mat], "emit_col": emit_col, "objs": objs,
        "light": L, "light_energy_base": float(d.get("point_light_energy") or 35.0),
    }
    report.setdefault("notas", []).append("cables: haz genérico suelo→escritorio (trazo exacto cable-a-cable FALTA en datos)")
    return objs + [L]

@register("lampara_arquitecto")
def f_lampara(spec, mats_cat, report):
    d = mats_cat.get("lampara_arquitecto") or {}
    mat, _ = mat_from_catalog("lampara_arquitecto", mats_cat, suffix=f"_{spec['id']}")
    plast = mat_pbr(f"{spec['id']}_cabeza", base=(0.15,0.15,0.16), rough=0.4)
    s = spec["tamano_m"]; p = spec["pos_m"]
    # base at pos (on desk)
    base = cyl_base(f"{spec['id']}_base", 0.06, 0.03, p, mat)
    arm1 = box(f"{spec['id']}_brazo1", (0.03, 0.03, 0.28), (p[0], p[1], p[2]+0.18), mat, bevel=0.002)
    arm2 = box(f"{spec['id']}_brazo2", (0.22, 0.03, 0.03), (p[0]+0.12, p[1], p[2]+0.35), mat, bevel=0.002)
    head = box(f"{spec['id']}_cabeza", (0.12, 0.08, 0.07), (p[0]+0.22, p[1], p[2]+0.32), plast, bevel=0.004)
    bpy.ops.object.light_add(type="SPOT", location=(p[0]+0.22, p[1], p[2]+0.30))
    L = bpy.context.active_object
    L.name = f"{spec['id']}_luz"
    L.data.energy = float(d.get("light_energy") or 18)
    L.data.color = (1.0, 0.92, 0.75)
    L.data.spot_size = math.radians(55)
    L.rotation_euler = Euler((math.radians(-50), 0, math.radians(30)), "XYZ")
    LIGHT_HANDLES[spec["id"]] = {"tipo": "lampara", "light": L, "energy_base": float(d.get("light_energy") or 18)}
    return [base, arm1, arm2, head, L]

@register("columna_estructural")
def f_columna(spec, mats_cat, report):
    mat, _ = mat_from_catalog("columna_estructural", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    # Verify column fits in room height — if data says H=2.8 from floor, OK
    o = box(spec["id"], s, c, mat, bevel=0.01)
    report.setdefault("notas", []).append(
        f"{spec['id']}: columna estructural según datos pos={spec['pos_m']} tam={s} (no inventada)")
    return [o]

@register("papelera_cilindro")
@register("papelera_calle")
def f_papelera(spec, mats_cat, report):
    key = "papelera_calle" if "calle" in (spec.get("formula") or "") or "publica" in spec["id"] else "papelera_cilindro"
    mat, _ = mat_from_catalog(key, mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    r = max(s[0], s[1]) / 2 or 0.14
    return [cyl_base(spec["id"], r, s[2], p, mat)]

@register("perchero_pie")
def f_perchero(spec, mats_cat, report):
    mat, _ = mat_from_catalog("perchero_pie", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    r_base = max(s[0], s[1]) / 2 or 0.18
    objs = [
        cyl_base(f"{spec['id']}_base", r_base*0.7, 0.03, p, mat),
        cyl_base(f"{spec['id']}_asta", 0.02, s[2]*0.95, (p[0], p[1], p[2]+0.03), mat),
    ]
    for i in range(4):
        ang = i * (math.pi/2)
        objs.append(cyl(f"{spec['id']}_gancho_{i}", 0.01, 0.12,
                        (p[0]+math.cos(ang)*0.08, p[1]+math.sin(ang)*0.08, p[2]+s[2]*0.85),
                        mat, verts=8, rot=(0, math.radians(90), ang)))
    return objs

@register("plafon_area")
def f_plafon(spec, mats_cat, report):
    d = mats_cat.get("plafon_area") or {}
    mat, _ = mat_from_catalog("plafon_area", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = spec["pos_m"]
    # plafón: pos is usually center of fixture near ceiling
    body = box(spec["id"], s, p, mat, bevel=0.01)
    bpy.ops.object.light_add(type="AREA", location=(p[0], p[1], p[2] - 0.06))
    L = bpy.context.active_object
    L.name = f"{spec['id']}_luz"
    L.data.energy = float(d.get("light_energy") or 350)
    L.data.color = tuple(d.get("light_color") or [1, 0.92, 0.75])
    L.data.size = max(s[0], s[1]) * 1.2
    L.data.shape = "RECTANGLE"
    if hasattr(L.data, "size_y"):
        L.data.size_y = max(min(s[0], s[1]) * 2, 0.4)
    L.rotation_euler = Euler((0, 0, 0), "XYZ")  # shines -Z by default for AREA? In Blender AREA shines -Z
    LIGHT_HANDLES[spec["id"]] = {
        "tipo": "plafon", "light": L, "energy_base": float(d.get("light_energy") or 95), "emit_base": float(d.get("emit_strength") or 1.8), "mat": mat,
    }
    return [body, L]

@register("bloque_edificio")
def f_edificio(spec, mats_cat, report):
    mat, _ = mat_from_catalog("bloque_edificio", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    cuerpo = box(spec["id"], s, c, mat, bevel=0.02)
    objs = [cuerpo]
    # facade windows grid (generic detail from size, not inventing props)
    win_mat = mat_pbr(f"{spec['id']}_ventanas", base=(0.15, 0.2, 0.28), rough=0.2,
                      emit=(0.4, 0.45, 0.35), emit_strength=0.8)
    n_x = max(2, int(s[0] / 3))
    n_z = max(2, int(s[2] / 3))
    for ix in range(n_x):
        for iz in range(n_z):
            wx = c[0] - s[0]/2 + (ix + 0.5) * (s[0] / n_x)
            wz = c[2] - s[2]/2 + (iz + 0.5) * (s[2] / n_z)
            objs.append(box(f"{spec['id']}_v_{ix}_{iz}",
                            (s[0]/n_x*0.45, 0.05, s[2]/n_z*0.45),
                            (wx, c[1] - s[1]/2 - 0.02, wz), win_mat))
    return objs

@register("muro_plano")
def f_muro_plano(spec, mats_cat, report):
    mat, _ = mat_from_catalog("muro_plano", mats_cat, suffix=f"_{spec['id']}")
    return [box(spec["id"], spec["tamano_m"], center_from_ancla(spec), mat, bevel=0.005)]

@register("arbol_simple")
def f_arbol(spec, mats_cat, report):
    mat, _ = mat_from_catalog("arbol_simple", mats_cat, suffix=f"_{spec['id']}")
    madera = mat_pbr(f"{spec['id']}_tronco", base=(0.3,0.2,0.1), rough=0.8)
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    tronco = cyl_base(f"{spec['id']}_tronco", max(0.05, s[0]*0.08), s[2]*0.45, p, madera)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=max(s[0], s[1])*0.35,
                                          location=(p[0], p[1], p[2]+s[2]*0.65))
    copa = bpy.context.active_object
    copa.name = f"{spec['id']}_copa"
    copa.data.materials.append(mat)
    return [tronco, copa]

@register("rack_servidores")
def f_rack(spec, mats_cat, report):
    mat, d = mat_from_catalog("rack_servidores", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    cuerpo = box(spec["id"], s, c, mat, bevel=0.005)
    led = mat_pbr(f"{spec['id']}_led", base=(0.1,0.3,1), rough=0.3,
                  emit=tuple(d.get("emit") or [0.1,0.4,1]), emit_strength=float(d.get("emit_strength") or 1.5))
    strip = box(f"{spec['id']}_led", (s[0]*0.9, 0.02, 0.03), (c[0], c[1]-s[1]/2, c[2]+s[2]*0.3), led)
    return [cuerpo, strip]

@register("farola_poste")
def f_farola(spec, mats_cat, report):
    d = mats_cat.get("farola_poste") or {}
    mat, _ = mat_from_catalog("farola_poste", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    r = max(0.04, min(s[0], s[1]) / 4)
    objs = [
        cyl_base(f"{spec['id']}_poste", r, s[2]*0.9, p, mat),
        box(f"{spec['id']}_brazo", (0.5, 0.05, 0.05), (p[0]+0.2, p[1], p[2]+s[2]*0.85), mat, bevel=0.005),
    ]
    lamp = mat_pbr(f"{spec['id']}_foco", base=(0.9,0.85,0.6), rough=0.3,
                   emit=(1,0.92,0.7), emit_strength=3)
    objs.append(box(f"{spec['id']}_foco", (0.15, 0.12, 0.08), (p[0]+0.4, p[1], p[2]+s[2]*0.82), lamp, bevel=0.01))
    bpy.ops.object.light_add(type="POINT", location=(p[0]+0.4, p[1], p[2]+s[2]*0.75))
    L = bpy.context.active_object
    L.name = f"{spec['id']}_luz"
    L.data.energy = float(d.get("light_energy") or 80)
    L.data.color = tuple(d.get("light_color") or [1, 0.92, 0.7])
    LIGHT_HANDLES[spec["id"]] = {"tipo": "farola", "light": L, "energy_base": float(d.get("light_energy") or 80)}
    return objs + [L]

@register("banco_calle")
def f_banco(spec, mats_cat, report):
    mat, _ = mat_from_catalog("banco_calle", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    objs = [
        box(f"{spec['id']}_asiento", (s[0], s[1], 0.06), (p[0], p[1], p[2]+s[2]*0.55), mat, bevel=0.008),
        box(f"{spec['id']}_respaldo", (s[0], 0.05, s[2]*0.4), (p[0], p[1]-s[1]/2, p[2]+s[2]*0.75), mat, bevel=0.006),
    ]
    for dx in (-s[0]*0.4, s[0]*0.4):
        objs.append(box(f"{spec['id']}_pata_{dx}", (0.06, s[1]*0.8, s[2]*0.5),
                        (p[0]+dx, p[1], p[2]+s[2]*0.25), mat, bevel=0.004))
    return objs

@register("auto_simple")
def f_auto(spec, mats_cat, report):
    mat, _ = mat_from_catalog("auto_simple", mats_cat, suffix=f"_{spec['id']}")
    glass = mat_pbr(f"{spec['id']}_vidrio", base=(0.2,0.25,0.3), rough=0.1, transmission=0.5, alpha=0.5)
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    body = box(f"{spec['id']}_carroceria", (s[0], s[1], s[2]*0.45), (c[0], c[1], c[2]-s[2]*0.1), mat, bevel=0.04)
    cabin = box(f"{spec['id']}_cabina", (s[0]*0.85, s[1]*0.5, s[2]*0.4),
                (c[0], c[1]-s[1]*0.05, c[2]+s[2]*0.2), glass, bevel=0.03)
    objs = [body, cabin]
    rubber = mat_pbr(f"{spec['id']}_rueda", base=(0.08,0.08,0.08), rough=0.9)
    for dx, dy in [(-s[0]*0.35, -s[1]*0.35),(s[0]*0.35, -s[1]*0.35),
                   (-s[0]*0.35, s[1]*0.35),(s[0]*0.35, s[1]*0.35)]:
        objs.append(cyl(f"{spec['id']}_rueda_{dx}_{dy}", s[2]*0.15, 0.12,
                        (c[0]+dx, c[1]+dy, c[2]-s[2]*0.35), rubber, verts=12,
                        rot=(math.radians(90), 0, 0)))
    return objs

@register("letrero_calle")
def f_letrero(spec, mats_cat, report):
    mat, _ = mat_from_catalog("letrero_calle", mats_cat, suffix=f"_{spec['id']}")
    metal = mat_pbr(f"{spec['id']}_poste", base=(0.3,0.3,0.32), rough=0.4, metal=0.7)
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    # letreros elevados (base alta): poste corto bajo la placa
    poste_h = max(0.3, min(s[2]*0.7, p[2] + s[2]*0.7)) if p[2] > 0.5 else s[2]*0.7
    poste_base = [p[0], p[1], 0.0] if p[2] > 0.5 else p
    placa_z = p[2] + s[2]*0.5
    return [
        cyl_base(f"{spec['id']}_poste", 0.03, max(0.3, placa_z - poste_base[2]), poste_base, metal),
        box(f"{spec['id']}_placa", (s[0], max(0.04, s[1]*0.3), max(0.15, s[2]*0.35)),
            (p[0], p[1], placa_z), mat, bevel=0.005),
    ]

@register("semaforo_calle")
def f_semaforo(spec, mats_cat, report):
    mat, _ = mat_from_catalog("semaforo_calle", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    objs = [cyl_base(f"{spec['id']}_poste", 0.05, s[2]*0.85, p, mat)]
    head = box(f"{spec['id']}_cabeza", (0.25, 0.2, 0.7), (p[0], p[1], p[2]+s[2]*0.85), mat, bevel=0.01)
    objs.append(head)
    for i, col in enumerate([(1,0.1,0.05),(1,0.8,0.1),(0.1,0.8,0.15)]):
        em = mat_pbr(f"{spec['id']}_luz_{i}", base=col, rough=0.3, emit=col, emit_strength=2)
        objs.append(box(f"{spec['id']}_luz_{i}", (0.12, 0.02, 0.12),
                        (p[0], p[1]-0.11, p[2]+s[2]*0.85 + 0.2 - i*0.2), em))
    return objs

@register("bolardo_calle")
def f_bolardo(spec, mats_cat, report):
    mat, _ = mat_from_catalog("bolardo_calle", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    # may be a row (long in Y) — place several posts
    if s[1] > s[0] * 2:
        n = max(2, int(s[1] / 0.6))
        objs = []
        for i in range(n):
            y = p[1] - s[1]/2 + (i+0.5)*(s[1]/n)
            objs.append(cyl_base(f"{spec['id']}_{i}", 0.08, s[2], (p[0], y, p[2]), mat))
        return objs
    return [cyl_base(spec["id"], max(s[0],s[1])/2, s[2], p, mat)]

@register("hidrante_calle")
def f_hidrante(spec, mats_cat, report):
    mat, _ = mat_from_catalog("hidrante_calle", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    r = max(s[0], s[1]) / 2
    return [
        cyl_base(f"{spec['id']}_cuerpo", r*0.7, s[2]*0.7, p, mat),
        cyl_base(f"{spec['id']}_tapa", r*0.85, s[2]*0.15, (p[0], p[1], p[2]+s[2]*0.7), mat),
    ]

@register("jardinera_calle")
def f_jardinera(spec, mats_cat, report):
    mat, _ = mat_from_catalog("jardinera_calle", mats_cat, suffix=f"_{spec['id']}")
    green = mat_pbr(f"{spec['id']}_planta", base=(0.2,0.4,0.15), rough=0.85)
    s = spec["tamano_m"]; c = center_from_ancla(spec); p = base_pos_from_ancla(spec)
    return [
        box(f"{spec['id']}_maceta", s, c, mat, bevel=0.01),
        box(f"{spec['id']}_planta", (s[0]*0.7, s[1]*0.7, s[2]*0.4),
            (c[0], c[1], p[2]+s[2]*0.9), green, bevel=0.02),
    ]

@register("bicicletero_calle")
def f_bicicletero(spec, mats_cat, report):
    mat, _ = mat_from_catalog("bicicletero_calle", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; p = base_pos_from_ancla(spec)
    objs = []
    n = max(2, int(s[0] / 0.4))
    for i in range(n):
        x = p[0] - s[0]/2 + (i+0.5)*(s[0]/n)
        objs.append(cyl_base(f"{spec['id']}_arco_{i}", 0.02, s[2], (x, p[1], p[2]), mat, verts=8))
        # inverted U top
        objs.append(cyl(f"{spec['id']}_top_{i}", 0.02, s[1]*0.8, (x, p[1], p[2]+s[2]), mat, verts=8,
                        rot=(math.radians(90), 0, 0)))
    return objs

@register("parada_autobus")
def f_parada(spec, mats_cat, report):
    mat, _ = mat_from_catalog("parada_autobus", mats_cat, suffix=f"_{spec['id']}")
    glass = mat_pbr(f"{spec['id']}_vidrio", base=(0.7,0.8,0.9), rough=0.1, transmission=0.6, alpha=0.4)
    s = spec["tamano_m"]; c = center_from_ancla(spec); p = base_pos_from_ancla(spec)
    return [
        box(f"{spec['id']}_techo", (s[0], s[1], 0.08), (c[0], c[1], p[2]+s[2]-0.04), mat, bevel=0.01),
        box(f"{spec['id']}_panel", (s[0]*0.9, 0.04, s[2]*0.7), (c[0], c[1]+s[1]/2, c[2]), glass),
        box(f"{spec['id']}_banco", (s[0]*0.8, s[1]*0.4, 0.06), (c[0], c[1], p[2]+0.45), mat, bevel=0.008),
    ]

@register("quiosco_calle")
def f_quiosco(spec, mats_cat, report):
    mat, _ = mat_from_catalog("quiosco_calle", mats_cat, suffix=f"_{spec['id']}")
    return [box(spec["id"], spec["tamano_m"], center_from_ancla(spec), mat, bevel=0.015)]

@register("toldo_calle")
def f_toldo(spec, mats_cat, report):
    mat, _ = mat_from_catalog("toldo_calle", mats_cat, suffix=f"_{spec['id']}")
    s = spec["tamano_m"]; c = center_from_ancla(spec)
    return [box(spec["id"], s, c, mat, bevel=0.01)]

# ---------------------------------------------------------------------------
def build_objects(escenario, mats_cat, report):
    LIGHT_HANDLES.clear()
    global SKY_BUILT
    SKY_BUILT = False
    built = []
    for spec in escenario.get("objetos") or []:
        if spec.get("_omitir"):
            continue
        formula = spec.get("formula")
        if not formula:
            report["falta"].append(f"{spec['id']}: sin formula")
            continue
        fn = REGISTRY.get(formula)
        if not fn:
            report["falta"].append(f"{spec['id']}: fórmula {formula!r} no está en biblioteca → FALTA")
            continue
        try:
            objs = fn(spec, mats_cat, report) or []
            built.append({"id": spec["id"], "formula": formula, "n_meshes": len(objs),
                          "ancla_z": spec.get("ancla_z"), "pos_m": spec.get("pos_m"),
                          "tamano_m": spec.get("tamano_m")})
        except Exception as e:
            report["falta"].append(f"{spec['id']}: error en fórmula {formula}: {e}")
    return built

def setup_world(mats_cat, oscuro=False):
    defaults = mats_cat.get("_defaults_exposicion") or {}
    color = tuple(defaults.get("world_color") or [0.08, 0.09, 0.12])
    strength = float(defaults.get("world_strength") or 0.55)
    if oscuro:
        strength = max(float((defaults.get("oscuridad_legible") or {}).get("world_strength_min") or 0.28),
                       strength * 0.55)
    w = bpy.data.worlds.new("WorldFill")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return strength

def apply_exposure(scene, mats_cat):
    defaults = mats_cat.get("_defaults_exposicion") or {}
    vs = scene.view_settings
    vs.view_transform = str(defaults.get("view_transform") or "Standard")
    vs.look = str(defaults.get("view_look") or "None")
    vs.exposure = float(defaults.get("view_exposure") or 0.85)
    vs.gamma = float(defaults.get("view_gamma") or 1.0)

def apply_light_state(estado, mats_cat, report):
    if not estado:
        estado = {}
    defaults = mats_cat.get("_defaults_exposicion") or {}
    osc = defaults.get("oscuridad_legible") or {}
    pl = float(estado.get("plafon", 1))
    mon = float(estado.get("monitores", 1))
    cur = float(estado.get("corriente_cables", 0))
    # keep monitors readable even when "dark"
    if mon > 0 and pl < 0.5:
        mon_eff = max(mon, float(osc.get("monitor_energy_min_factor") or 0.55))
    else:
        mon_eff = mon

    # world strength depends on plafon
    setup_world(mats_cat, oscuro=(pl < 0.5))

    for oid, h in LIGHT_HANDLES.items():
        t = h["tipo"]
        if t == "plafon" and h.get("light"):
            h["light"].data.energy = h["energy_base"] * pl
            set_emission_strength(h.get("mat"), float(h.get("emit_base", 1.8)) * pl)
        elif t == "monitor":
            for m in h.get("mats") or []:
                set_emission_strength(m, h["energy_base"] * mon_eff)
            if h.get("light"):
                h["light"].data.energy = h.get("light_energy_base", 28) * mon_eff
        elif t == "cables":
            strength = 5.0 * cur
            for m in h.get("mats") or []:
                set_emission_strength(m, strength, color=h.get("emit_col"))
            # also tint cable objects' materials if they share mat
            if h.get("light"):
                h["light"].data.energy = h.get("light_energy_base", 35) * cur
        elif t == "lampara" and h.get("light"):
            # desk lamp follows plafon mostly; dim residual when off
            h["light"].data.energy = h["energy_base"] * (0.85 if pl > 0.5 else 0.15)
        elif t == "farola" and h.get("light"):
            h["light"].data.energy = h["energy_base"]  # street lamps always on unless data says else

def setup_eevee(scene, res=(1280,720)):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = res[0]
    scene.render.resolution_y = res[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    ee = getattr(scene, "eevee", None)
    if ee:
        if hasattr(ee, "use_shadows"):
            ee.use_shadows = True
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = 64
        if hasattr(ee, "use_raytracing"):
            ee.use_raytracing = True
        if hasattr(ee, "use_volumetric_shadows"):
            ee.use_volumetric_shadows = False
        # Blender 4 bloom; Blender 5 may not have these — guard
        if hasattr(ee, "use_bloom"):
            ee.use_bloom = False
        if hasattr(ee, "bloom_intensity"):
            ee.bloom_intensity = 0.0

def make_camera(toma, report):
    cam_data = toma.get("camara") or {}
    loc = cam_data.get("loc")
    mira = cam_data.get("mira")
    if not loc or not mira:
        report["falta"].append(f"toma {toma.get('toma')}: camara sin loc/mira")
        return None
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = f"cam_toma_{toma.get('toma')}"
    look_at(cam, mira)
    lente = float(cam_data.get("lente_mm") or 24)
    cam.data.lens = lente
    cam.data.clip_start = 0.05
    cam.data.clip_end = 500
    return cam

def qc_camera(toma, esc, report):
    """Check camera roughly frames expected subject area; report mismatches."""
    cam = toma.get("camara") or {}
    loc = cam.get("loc"); mira = cam.get("mira")
    plano = (toma.get("plano") or "").lower()
    issues = []
    if not loc or not mira:
        return issues
    dist = (Vector(mira) - Vector(loc)).length
    # heuristic: "cerrado" / close should be nearer; "amplio"/"general" farther
    if "cerrado" in plano or "primer plano" in plano:
        if dist > 3.5:
            issues.append(f"toma {toma.get('toma')}: plano={toma.get('plano')!r} pero distancia cam→mira={dist:.2f}m (parece lejos para cerrado)")
    if "amplio" in plano or "general" in plano:
        if dist < 1.2:
            issues.append(f"toma {toma.get('toma')}: plano={toma.get('plano')!r} pero distancia cam→mira={dist:.2f}m (parece corto para amplio)")
    # subject height: mira z should be around torso/face for medio
    if "medio" in plano and mira:
        if mira[2] < 0.6 or mira[2] > 1.8:
            issues.append(f"toma {toma.get('toma')}: mira.z={mira[2]} fuera de rango típico pecho/rostro (0.6–1.8) para plano medio")
    # lens sanity
    lente = float(cam.get("lente_mm") or 24)
    if lente < 14 or lente > 85:
        issues.append(f"toma {toma.get('toma')}: lente_mm={lente} fuera de rango típico 14–85")
    for iss in issues:
        report.setdefault("qc_camara", []).append(iss)
    return issues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escenario", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--materiales", required=True)
    ap.add_argument("--estado-luces", default="")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--blend", default="")
    ap.add_argument("--prefix", default="fondo_toma")
    ap.add_argument("--res-x", type=int, default=1280)
    ap.add_argument("--res-y", type=int, default=720)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = {"falta": [], "dudas": [], "notas": [], "construidos": [], "renders": [], "qc_camara": []}

    esc = load(args.escenario)
    plan = load(args.plan)
    mats_cat = load(args.materiales)
    estado_doc = load(args.estado_luces) if args.estado_luces else {"por_toma": {}}
    if isinstance(plan, dict) and "tomas" in plan:
        tomas = plan["tomas"]
    elif isinstance(plan, list):
        tomas = plan
    else:
        tomas = plan.get("tomas") or []

    # QC: cámaras duplicadas en el plan (genérico)
    seen = {}
    for toma in tomas:
        cam = toma.get("camara") or {}
        key = (tuple(cam.get("loc") or []), tuple(cam.get("mira") or []), cam.get("lente_mm"))
        tid = toma.get("toma") or toma.get("id")
        if key in seen and key[0]:
            report["qc_camara"].append(
                f"tomas {seen[key]} y {tid}: misma cámara loc/mira/lente (plan idéntico; no es error del motor)"
            )
        else:
            seen[key] = tid

    clear_scene()
    setup_world(mats_cat, oscuro=False)
    built = build_objects(esc, mats_cat, report)
    report["construidos"] = built
    report["falta_adaptacion"] = esc.get("falta_adaptacion") or []
    report["dudas_adaptacion"] = esc.get("dudas_adaptacion") or []

    scene = bpy.context.scene
    setup_eevee(scene, (args.res_x, args.res_y))
    apply_exposure(scene, mats_cat)

    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.blend).resolve()))

    for toma in tomas:
        tid = toma.get("toma") or toma.get("id")
        if isinstance(tid, str) and tid.startswith("toma_"):
            key = str(int(tid.split("_")[-1]))
        else:
            key = str(int(tid)) if str(tid).isdigit() else str(tid)

        estado = (estado_doc.get("por_toma") or {}).get(key) or (estado_doc.get("por_toma") or {}).get(str(tid))
        apply_light_state(estado, mats_cat, report)
        qc_camera(toma, esc, report)

        cam = make_camera(toma, report)
        if not cam:
            continue
        scene.camera = cam
        out_png = out / f"{args.prefix}_{int(key):02d}.png"
        scene.render.filepath = str(out_png)
        bpy.ops.render.render(write_still=True)
        report["renders"].append({"toma": int(key), "path": str(out_png), "estado_luces": estado,
                                  "plano": toma.get("plano"), "camara": toma.get("camara")})
        print(f"RENDER_OK {out_png} plafon={(estado or {}).get('plafon')} mon={(estado or {}).get('monitores')}")

    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.blend).resolve()))

    rep_path = out / "informe_motor.json"
    rep_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"INFORME {rep_path} falta={len(report['falta'])} dudas={len(report['dudas'])} "
          f"renders={len(report['renders'])} qc={len(report['qc_camara'])}")

if __name__ == "__main__":
    main()
