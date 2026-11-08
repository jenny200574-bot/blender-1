"""Funciones físicas heredadas; el contexto lo suministra la entrada universal."""
ALI_APOYO = {"cadera": "pelvis", "rodilla_L": "pierna_L", "rodilla_R": "pierna_R", "codo_L": "antebrazo_L", "codo_R": "antebrazo_R", "gluteo": "pelvis"}
def cadena(A, b):
    """v9: huesos de la extremidad de un apoyo, sacados del esqueleto (sube por los padres mientras sigan del mismo lado). Sin nombres fijos."""
    b = ALI_APOYO.get(b, b.replace("rodilla", "pierna"))
    if b not in A.pose.bones or "_" not in b: return []
    lado = b[b.rfind("_"):]; out = []; pb = A.pose.bones[b]
    while pb is not None and pb.name.endswith(lado): out.append(pb.name); pb = pb.parent
    return out
# ---- v9 cambios Argon-5 (universales). Cada uno se apaga con <nombre>.off junto al motor; con todos los .off = motor original ----
SW = {n: MN.activo(n) for n in ("slerp_raiz", "contacto_apoyos", "ik_piso_suave", "piso_suave", "equilibrio_memoria", "anclaje_mismo_cuadro", "orden_medicion")}
print("INTERRUPTORES", json.dumps(SW))
def _hueso_apoyo(b): return ALI_APOYO.get(b, b.replace("rodilla", "pierna"))
def _pto_apoyo(A, nm):
    pb = A.pose.bones[nm]; M_ = A.matrix_world; return (M_ @ pb.head) if nm.startswith("pierna") else (M_ @ (pb.tail if nm.startswith(("pie", "mano")) else pb.head))
def _nombres_apoyo(A, kc): return sorted({_hueso_apoyo(b) for b in (kc[2] if kc else [])} & set(A.pose.bones.keys()))
def _fn_apoyos(A, kc): return {nm: (lambda A__, nm=nm: _pto_apoyo(A__, nm)) for nm in _nombres_apoyo(A, kc)}
def _contactos(A, P, kc):
    return MN.puntos_contacto(A, P["rad"], apoyos={nm: _pto_apoyo(A, nm) for nm in _nombres_apoyo(A, kc)} if SW["contacto_apoyos"] else None)
def _fuera(A, P, kc): return MN.distancia_fuera(MN.centro_masa(A, P["rad"]), _contactos(A, P, kc))
def _pegar(A, P, prf):
    bpy.context.view_layer.update(); z, q = rig.suelo(A, P["rad"])
    if not SW["piso_suave"]: A.location.z -= z; bpy.context.view_layer.update(); return
    # cambio D1: pegado al piso suave (softmin de toda la superficie, sin cambiar de golpe de hueso) + límite de Δz por cuadro
    M = A.matrix_world; zs = []
    for pb in A.pose.bones:
        r = P["rad"][pb.name] if pb.name.split("_")[0] not in ("pie",) else 0.0; zs += [(M @ pb.head).z - r, (M @ pb.tail).z - r]
    tau = 0.004; sm = z - tau * math.log(sum(math.exp(-(v - z) / tau) for v in zs))
    zt = A.location.z - sm; zp = P.get("z_prev")
    if zp is not None: lim = prf["vel_vertical_max_m_s"] / FPS * 0.8; zt = max(zp - lim, min(zp + lim, zt))
    zh = A.location.z - z; zt = max(zh - 0.01, min(zh + 0.025, zt))   # nunca hundir >1 cm ni flotar >2.5 cm (el revisor marca a 3 cm)
    A.location.z = zt; bpy.context.view_layer.update()
def _dofs_eq(kc):
    return (("columna", 0), ("columna", 1), ("pecho", 0), ("raiz", 0), ("raiz", 1)) + tuple((f"{g}_{s}", k) for s in "LR" for g, k in (("brazo", 0), ("brazo", 1), ("muslo", 1)) if f"{g}_{s}" in [x.replace("rodilla", "muslo") for x in (kc[2] if kc else [])] or g == "muslo")
def _equilibrio(A, P, prf, pid, kc, ang, fuera):
    if not SW["equilibrio_memoria"]:   # original (rejilla ±corr/3·1..3 sin memoria)
        if fuera > prf["margen_equilibrio_m"]:
            mejor = (fuera, None); paso = prf["correccion_equilibrio_max_deg"] / 3
            for dh, dk in _dofs_eq(kc):
                for sg in (1, -1):
                    for n_ in (1, 2, 3):
                        a2 = {k: list(v) for k, v in ang.items()}; v = a2.setdefault(dh, [0, 0, 0]); v[dk] += sg * paso * n_; limites(pid, a2); rig.aplicar(A, a2)
                        _pegar(A, P, prf)
                        d2 = _fuera(A, P, kc)
                        if d2 < mejor[0] - 1e-4: mejor = (d2, a2)
            if mejor[1] is not None: ang = mejor[1]; fuera = mejor[0]; REP["ajustes"].append(f"f{f+1} {pid} equilibrio corregido")
            rig.aplicar(A, ang); _pegar(A, P, prf)
        return ang, fuera
    # cambio D2: equilibrio con memoria (parte de la corrección del cuadro anterior, pasos finos, castigo por cambiar, tope por cuadro)
    prev = P.get("deq", {}); marg = prf["margen_equilibrio_m"]
    if fuera <= marg and not prev: return ang, fuera
    cmax = prf["correccion_equilibrio_max_deg"]; dmax = cmax / 3; dofs = _dofs_eq(kc); d0 = {x: prev.get(x, 0) * 0.9 for x in dofs}
    def ev(d):
        a2 = {k: list(v) for k, v in ang.items()}
        for (h, k), v in d.items():
            if v: a2.setdefault(h, [0, 0, 0])[k] += v
        limites(pid, a2); rig.aplicar(A, a2); _pegar(A, P, prf); fo = _fuera(A, P, kc)
        return max(0.0, fo - marg * 0.5) + 4e-4 * sum((d[x] - prev.get(x, 0)) ** 2 for x in dofs) + 5e-5 * sum(v * v for v in d.values()), fo, a2
    best = (d0,) + ev(d0)
    for st in (2, 1, 0.5):
        for _ in range(2):
            mej = False
            for x in dofs:
                for sg in (1, -1):
                    d = dict(best[0]); nv = d[x] + sg * st
                    if abs(nv) > cmax or abs(nv - prev.get(x, 0)) > dmax: continue
                    d[x] = nv; r_ = ev(d)
                    if r_[0] < best[1] - 1e-7: best = (d,) + r_; mej = True
            if not mej: break
    d, _c, fo, a2 = best; P["deq"] = {x: v for x, v in d.items() if abs(v) > 1e-3}
    if P["deq"]: REP["ajustes"].append(f"f{f+1} {pid} equilibrio (memoria)")
    rig.aplicar(A, a2); _pegar(A, P, prf)
    return a2, fo
def _continuidad(A, P, prf, kc, ang, fuera):
    if P.get("ult_final"):
        lim2 = prf["vel_max_deg_s"] / FPS; cambio = False
        for k in set(ang) | set(P["ult_final"]):
            a0 = P["ult_final"].get(k, [0, 0, 0]); a1 = ang.setdefault(k, [0, 0, 0]); nv = [a0[i] + max(-lim2, min(lim2, a1[i] - a0[i])) for i in range(3)]
            if nv != a1: ang[k] = nv; cambio = True
        if cambio:
            rr = ang.get("raiz", [0, 0, 0]); rig.aplicar(A, ang); A.rotation_euler = (-math.radians(rr[0]), math.radians(rr[1]), math.radians(P["yaw"] + (rr[2] if len(rr) > 2 else 0)))
            if SW["piso_suave"]: _pegar(A, P, prf)
            else:
                bpy.context.view_layer.update(); z, q = rig.suelo(A, P["rad"]); zt = A.location.z - z
                vz = prf["vel_vertical_max_m_s"] / FPS; zp = P.get("z_prev", zt)
                A.location.z = zt if zt > zp + vz * 0 and zt - zp > vz and z < 0 else zt   # nunca hundir; la subida rápida queda medida por el revisor
                bpy.context.view_layer.update()
            if not prf["vuela"]: fuera = _fuera(A, P, kc)
    return ang, fuera
def _anclaje(A, P, prf, pid, kc, dsp):
    apo = _nombres_apoyo(A, kc) if SW["anclaje_mismo_cuadro"] else [x for x in [_hueso_apoyo(x) for x in (kc[2] if kc else [])] if x in A.pose.bones]
    anclar = bool(kc and kc[3]) and prf["anclaje_pies"] > 0.5 and dsp == 0 and not prf["vuela"]
    pto = lambda nm: _pto_apoyo(A, nm)
    if SW["anclaje_mismo_cuadro"] and apo:
        # cambio D3: histéresis — se mantiene el apoyo principal anterior mientras siga válido (no argmin cada cuadro)
        zmin = min(pto(n).z for n in apo); pv = P["anc"][0] if P["anc"] else None
        plant = pv if (pv in apo and pto(pv).z <= zmin + 0.03) else min(apo, key=lambda nm: pto(nm).z)
    else: plant = min(apo, key=lambda nm: pto(nm).z) if apo else None
    if anclar and plant and P["anc"] and P["anc"][0] == plant:
        now = pto(plant); dd = Vector((P["anc"][1].x - now.x, P["anc"][1].y - now.y))
        if not SW["anclaje_mismo_cuadro"]:
            if dd.length > 0.06: dd = dd.normalized() * 0.06
            if (P["off"] + dd).length < 0.6: P["off"] += dd; A.location.x += dd.x; A.location.y += dd.y; bpy.context.view_layer.update()
        else:   # cambio D3: corrección completa en el mismo cuadro; solo un tope de excursión total (del perfil)
            nw = P["off"] + dd; lim = prf["anclaje_excursion_max_m"]
            if nw.length > lim: nw = nw.normalized() * lim
            dd = nw - P["off"]; P["off"] += dd; A.location.x += dd.x; A.location.y += dd.y; bpy.context.view_layer.update()
    if plant: P["anc"] = (plant, pto(plant).copy())   # apoyo nuevo: se congela donde aterrizó (Δ=0)
    P.setdefault("resb", []).append(None if not (anclar and plant) else (plant, list(pto(plant))))
def limites(pid, ang):
    gr = PJ[pid]["gr"]
    for k, v in ang.items():
        if k in gr:
            for i, (lo, hi) in enumerate(EA.LIMITES[gr[k]]): v[i] = max(lo, min(hi, v[i]))
