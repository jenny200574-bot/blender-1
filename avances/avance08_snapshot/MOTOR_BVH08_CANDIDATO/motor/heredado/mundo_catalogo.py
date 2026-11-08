import bpy
def mundo_v7(F, sc):
    """Cielo v7: elevación real (Generated de mundo = dirección -1..1), noche oscura y estrellas visibles (antes salía cian plano)."""
    w = bpy.data.worlds.new(F["nombre"] + "_v7"); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear(); P = F["mundo"]
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground"); tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    rp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(sep.outputs["Z"], rp.inputs["Fac"])
    hz = [c * 0.45 for c in P["color_horizonte"][:3]]; ce = [c * 0.35 for c in P["color_cenit"][:3]]
    rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = (*hz, 1); rp.color_ramp.elements[1].position = 0.45; rp.color_ramp.elements[1].color = (*ce, 1)
    nt.links.new(rp.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = P.get("fuerza", 1.0)
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 60.0; nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    r2 = nt.nodes.new("ShaderNodeValToRGB"); r2.color_ramp.elements[0].position = 0.0; r2.color_ramp.elements[0].color = (1, 1, 1, 1)
    r2.color_ramp.elements[1].position = 0.045; r2.color_ramp.elements[1].color = (0, 0, 0, 1); nt.links.new(vor.outputs["Distance"], r2.inputs["Fac"])
    var = nt.nodes.new("ShaderNodeMath"); var.operation = "MULTIPLY"; nt.links.new(r2.outputs["Color"], var.inputs[0]); nt.links.new(vor.outputs["Color"], var.inputs[1])  # brillo variable
    mk = nt.nodes.new("ShaderNodeMath"); mk.operation = "GREATER_THAN"; mk.inputs[1].default_value = 0.04; nt.links.new(sep.outputs["Z"], mk.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; nt.links.new(var.outputs[0], mul.inputs[0]); nt.links.new(mk.outputs[0], mul.inputs[1])
    em = nt.nodes.new("ShaderNodeBackground"); em.inputs["Strength"].default_value = max(4.0, P.get("estrellas_brillo", 2.0) * 8); nt.links.new(mul.outputs[0], em.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(bg.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1]); nt.links.new(add.outputs[0], out.inputs[0]); return w
