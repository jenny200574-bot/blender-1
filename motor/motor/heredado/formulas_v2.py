"""Fórmulas de puntos v2 (Blender 5.2.3). Esquema 'formula_puntos.v2' = v1 de Star/Ako + puntos EMPARENTADOS al objeto,
bisagras c (0..1), desgaste procedural en materiales, luces y fórmulas de 'mundo' (cielo). Genérico: no sabe de ninguna escena."""
import bpy, math, json, importlib.util
from pathlib import Path
from mathutils import Vector
AQUI = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("motor_fondos", AQUI / "star_src/src/motor_fondos.py")
MF = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(MF)   # 44 fórmulas Star, sin editar
STAR = sorted(MF.REGISTRY)

def catalogo(path):
    root=Path(path).parent;idx = json.load(open(path))
    F = {}
    for k, v in idx["formulas"].items():
        if v.get("archivo"): F[k] = json.load(open(root / v["archivo"]))
    return idx, F

def mat(nombre, m):
    M = bpy.data.materials.new(nombre); M.use_nodes = True; nt = M.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    base = tuple(m.get("base", [.5, .5, .5]))[:3]
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Roughness"].default_value = m.get("rough", .5); b.inputs["Metallic"].default_value = m.get("metal", 0)
    if m.get("emit") and m.get("emit_strength", 0) > 0:
        b.inputs["Emission Color"].default_value = (*m["emit"][:3], 1); b.inputs["Emission Strength"].default_value = m["emit_strength"]
    if m.get("alpha", 1) < 1:
        b.inputs["Alpha"].default_value = m["alpha"]
        try: M.surface_render_method = "BLENDED"
        except Exception: pass
    de = m.get("desgaste")
    if de and de.get("fuerza", 1) > 0:   # manchas: ruido estirado en Z (escurrimiento vertical) u orgánico; oscurece el color base
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        sx = de.get("escala", 2.0); mp.inputs["Scale"].default_value = (sx, sx, sx * (0.12 if de.get("tipo") == "vertical" else 1))
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
        rp = nt.nodes.new("ShaderNodeValToRGB"); f = max(0.0, min(1.0, de.get("fuerza", .5)))
        rp.color_ramp.elements[0].position = 0.35; rp.color_ramp.elements[0].color = (*de.get("color", [x * .35 for x in base])[:3], 1)
        rp.color_ramp.elements[1].position = 0.35 + 0.3 * (1 - f) + 0.05; rp.color_ramp.elements[1].color = (*base, 1)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"]); nt.links.new(rp.outputs["Color"], b.inputs["Base Color"])
        rr = nt.nodes.new("ShaderNodeMapRange"); nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
        rr.inputs["To Min"].default_value = m.get("rough", .5) - .1; rr.inputs["To Max"].default_value = min(1, m.get("rough", .5) + .1); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    nt.links.new(b.outputs[0], out.inputs[0]); return M

def prim(tipo, dim, verts=None):
    dx, dy, dz = dim
    if tipo == "caja": bpy.ops.mesh.primitive_cube_add(size=1)
    elif tipo in ("cilindro", "prisma"): bpy.ops.mesh.primitive_cylinder_add(radius=.5, depth=1, vertices=verts or (8 if tipo == "prisma" else 24))
    elif tipo == "cono": bpy.ops.mesh.primitive_cone_add(radius1=.5, radius2=0, depth=1, vertices=verts or 24)
    elif tipo == "esfera":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.5, segments=24, ring_count=12); o = bpy.context.object; o.scale = (dx, dy, dz); bpy.ops.object.transform_apply(scale=True); return o
    elif tipo == "toro":
        bpy.ops.mesh.primitive_torus_add(major_radius=.5, minor_radius=.5 * max(dz / max(dx, 1e-3), .01), major_segments=48, minor_segments=12)
        o = bpy.context.object; o.scale = (dx, dy, dx); bpy.ops.object.transform_apply(scale=True); return o
    elif tipo == "plano": bpy.ops.mesh.primitive_plane_add(size=1)
    else: raise ValueError(f"tipo de pieza desconocido: {tipo}")
    o = bpy.context.object; o.scale = (dx, dy, max(dz, 1e-4)); bpy.ops.object.transform_apply(scale=True)
    if tipo in ("caja", "cilindro", "prisma", "cono"):
        for v in o.data.vertices: v.co.z += dz / 2      # origen en la base
    return o

def _copias(pz, S):
    rp = pz.get("repetir") or {}; pat = rp.get("patron")
    base = [pz["dim"][i] * S[i] + (pz.get("dim_m") or [0, 0, 0])[i] for i in range(3)]
    p0 = Vector([pz["pos"][i] * S[i] + (pz.get("pos_m") or [0, 0, 0])[i] for i in range(3)]); out = []
    if not pat or pat == "ninguno": return [(p0, 0, base)]
    if pat in ("rejilla_x", "rejilla_y"):
        ax = 0 if pat == "rejilla_x" else 1; k = 1
        while -S[ax] / 2 + k * rp["paso_m"] < S[ax] / 2:
            q = p0.copy(); q[ax] = -S[ax] / 2 + k * rp["paso_m"]; out.append((q, 0, base)); k += 1
    elif pat == "esquinas": out = [(p0 + Vector((sx * rp["f"] * S.x, sy * rp["f"] * S.y, 0)), 0, base) for sx in (-1, 1) for sy in (-1, 1)]
    elif pat == "radial":
        for k in range(rp["n"]):
            a = math.radians(rp.get("desfase_deg", 0) + 360 * k / rp["n"])
            out.append((p0 + Vector((math.cos(a) * rp["f"] * S.x, math.sin(a) * rp["f"] * S.y, 0)), math.degrees(a), base))
    elif pat == "fila_x":
        for k in range(rp["n"]):
            h = rp.get("alturas_f", [1] * rp["n"])[k % len(rp.get("alturas_f", [1]))]; d = list(base); q = p0.copy(); q.x = -S.x / 2 + (k + .5) * S.x / rp["n"]
            if rp.get("en_tope"): q.z = h * S.z - d[2]
            else: d[2] = base[2] * h
            out.append((q, 0, d))
    elif pat == "pila_z":
        for k in range(rp["n"]):
            q = p0.copy(); q.z += ((k - (rp["n"] - 1) / 2) if rp.get("centrado") else k) * rp["paso_f"] * S.z; out.append((q, 0, base))
    elif pat == "dispersion":   # manchas/fragmentos: posiciones pseudoaleatorias deterministas dentro del objeto
        import random; R = random.Random(rp.get("semilla", 7))
        for k in range(rp["n"]):
            q = p0 + Vector([(R.random() - .5) * rp.get("f_xyz", [1, 1, 0])[i] * S[i] for i in range(3)]); s = 0.6 + R.random() * 0.8
            out.append((q, R.random() * 360, [base[0] * s, base[1] * s, base[2]]))
    else: raise ValueError(f"patrón desconocido: {pat}")
    return out

def construir(oid, F, pos=(0, 0, 0), tam=None, rot_z=0.0, c=None, coleccion=None):
    """Construye una fórmula v1/v2. Devuelve (raiz, info). Los puntos nombrados son empties HIJOS (siguen al objeto)."""
    col = coleccion or bpy.context.scene.collection
    S = Vector(tam or F["tamano_m_por_defecto"]); raiz = bpy.data.objects.new(oid, None); col.objects.link(raiz)
    raiz.location = Vector(pos); raiz.rotation_euler.z = math.radians(rot_z); raiz["formula"] = F["nombre"]
    mats = {k: mat(f"{oid}_{k}", v) for k, v in F["materiales"].items()}
    piv = {}; info = {"piezas": 0, "puntos": {}, "bisagras": {}, "luces": 0}
    for bz in F.get("bisagras", []):   # pivotes de bisagra: c en [0,1] → ángulo
        p = bpy.data.objects.new(f"{oid}~{bz['id']}", None); col.objects.link(p); p.parent = raiz
        p.location = Vector([bz.get("pivote", [0, 0, 0])[i] * S[i] for i in range(3)]); piv[bz["id"]] = p
        cv = (c or {}).get(bz["id"], bz.get("c", 0.0)); ax = "xyz".index(bz.get("eje", "z"))
        r = list(p.rotation_euler); r[ax] = math.radians(bz.get("ang_min", 0) + (bz.get("ang_max", 90) - bz.get("ang_min", 0)) * cv); p.rotation_euler = r
        info["bisagras"][bz["id"]] = cv
    padre_de = {pid: bz["id"] for bz in F.get("bisagras", []) for pid in bz.get("piezas", [])}
    for pz in F["piezas"]:
        for i, (q, rz, d) in enumerate(_copias(pz, S)):
            o = prim(pz["tipo"], d, pz.get("verts") or None); o.name = f"{oid}_{pz['id']}_{i}"
            for c_ in o.users_collection: c_.objects.unlink(o)
            col.objects.link(o)
            r = [math.radians(x) for x in pz.get("rot_deg", [0, 0, 0])]; o.rotation_euler = (r[0], r[1], r[2] + math.radians(rz))
            o.data.materials.append(mats[pz["material"]])
            pv = piv.get(padre_de.get(pz["id"]))
            if pv: o.parent = pv; o.location = q - pv.location
            else: o.parent = raiz; o.location = q
            if pz.get("sombra") is False: o.visible_shadow = False
            info["piezas"] += 1
    for k, L in enumerate(F.get("luces", [])):
        ld = bpy.data.lights.new(f"{oid}_luz{k}", L["tipo"].upper()); ld.energy = L["energy"]; ld.color = L["color"][:3]
        if L["tipo"].upper() == "AREA": ld.size = L.get("size") or 1.0
        lo = bpy.data.objects.new(f"{oid}_luz{k}", ld); col.objects.link(lo); lo.parent = raiz
        lo.location = Vector([L["pos"][i] * S[i] for i in range(3)])
        if L.get("rot_deg"): lo.rotation_euler = [math.radians(x) for x in L["rot_deg"]]
        info["luces"] += 1
    for n, p in F.get("puntos_nombrados", {}).items():
        e = bpy.data.objects.new(f"{oid}:{n}", None); col.objects.link(e); e.empty_display_size = 0.05
        pp = p if isinstance(p, list) else p["pos"]; en = None if isinstance(p, list) else (p.get("en") or None)
        par = piv.get(en, raiz); e.parent = par; loc = Vector([pp[i] * S[i] for i in range(3)])
        e.location = loc - (par.location if par is not raiz else Vector()); info["puntos"][n] = e.name
    return raiz, info

def mundo(F, sc):
    """Fórmula tipo 'mundo' (cielo): degradado cenit→horizonte + estrellas (densidad, brillo, sesgo)."""
    w = bpy.data.worlds.new(F["nombre"]); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    P = F["mundo"]; out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    rp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(sep.outputs["Z"], rp.inputs["Fac"])
    rp.color_ramp.elements[0].position = 0.5; rp.color_ramp.elements[0].color = (*P["color_horizonte"][:3], 1)
    rp.color_ramp.elements[1].position = 0.75; rp.color_ramp.elements[1].color = (*P["color_cenit"][:3], 1)
    nt.links.new(rp.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = P.get("fuerza", 1.0)
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = P.get("estrellas_escala", 350)
    r2 = nt.nodes.new("ShaderNodeValToRGB"); d = P.get("estrellas_densidad", .03)
    r2.color_ramp.elements[0].position = 0; r2.color_ramp.elements[0].color = (1, 1, 1, 1); r2.color_ramp.elements[1].position = d; r2.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(vor.outputs["Distance"], r2.inputs["Fac"])
    mask = nt.nodes.new("ShaderNodeMath"); mask.operation = "GREATER_THAN"; mask.inputs[1].default_value = 0.52; nt.links.new(sep.outputs["Z"], mask.inputs[0])
    mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1; nt.links.new(r2.outputs["Color"], mul.inputs[1]); nt.links.new(mask.outputs[0], mul.inputs[2])
    em = nt.nodes.new("ShaderNodeBackground"); em.inputs["Strength"].default_value = P.get("estrellas_brillo", 2.0); nt.links.new(mul.outputs[0], em.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(bg.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1]); nt.links.new(add.outputs[0], out.inputs[0])
    return w

def construir_star(oid, nombre, pos, tam, rep):
    sp = {"id": oid, "formula": nombre, "pos_m": list(pos), "tamano_m": list(tam), "ancla_z": "base"}
    mats = json.load(open(AQUI / "catalogo_formulas/materiales_por_formula.json"))
    return MF.REGISTRY[nombre](sp, mats, rep) or []
