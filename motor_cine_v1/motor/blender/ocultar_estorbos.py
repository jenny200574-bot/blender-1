"""ocultar_estorbos (Blender 5.2.3/4.2.3, código propio MYIA).
La cámara ejecuta el storyboard TAL CUAL (no se re-elige plano, lente, ángulo ni posición).
Por cada cuadro de la toma: rayos cámara -> puntos de muestra (cabeza/cara y cuerpo) de los sujetos protegidos.
Todo objeto NO protegido que tapa (o que encierra la cámara) recibe visible_camera=False SOLO en esos cuadros
(keyframes CONSTANT). visible_shadow y la luz no se tocan. Lo protegido (objetivo, en_cuadro, objetos_sb que existen,
debe_verse) nunca se oculta: si tapa al sujeto principal -> conflicto en el reporte.
Uso: blender -b escena.blend -P ocultar_estorbos.py -- --toma toma.json --out dir [--guardar nueva.blend]
     [--render "f1,f2"] [--orbita_demo]
[t1066u, 10-nov-2026] ARREGLO UNIVERSAL: NUNCA se oculta un objeto de historia (N0 de sb3d_niveles: todos los personajes, el piso,
el mueble que soporta o toca a alguien, los props y lo que nombra el guion). Si un N0 tapa al sujeto, NO se esconde: se reporta
'protegido_tapa_sujeto' y el paso sb3d cambia la cámara (otra candidata). toma['n0'] = mallas N0; toma['n2_protegido'] = muros
que tampoco se ocultan aquí (sb3d los recorta aparte, solo con la cámara fuera de ese muro). Personajes = TODO armature con mallas
(no se depende de un prefijo de nombre)."""
import bpy, json, sys, os, math, time, argparse
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camara_sin_paredes as CSP
from bpy_extras.object_utils import world_to_camera_view

CABEZA = ('cabeza', 'face', 'head', 'hair', 'helmet', 'casco', 'eye', 'nose', 'mouth', 'brow', 'iris', 'pupil', 'pelo', 'ojo', 'boca')
EPS_PUNTO = 0.03       # m: un choque a menos de 3 cm del punto cuenta como el propio punto (piso bajo la suela, etc.)
MIN_MUESTRAS = 2       # muestras tapadas mínimas para ocultar un objeto en un cuadro
MAX_CABEZA, MAX_CUERPO = 30, 40   # tope de muestras por personaje y cuadro (repartidas parejo entre sus mallas)
UNIR_HUECO = 3         # cuadros: si un objeto vuelve a tapar en <=3 cuadros, se mantiene oculto (evita parpadeo)

def entidad_de(nombre, ids_personajes):
    for i in ids_personajes:
        if nombre == i or nombre.startswith(i + '.') or nombre.startswith(i + '_'): return i
    return None

def es_cabeza(nombre):
    n = nombre.lower(); return any(k in n for k in CABEZA)

def renderizable(o):
    return o.type == 'MESH' and not o.hide_render and o.visible_camera_eval if hasattr(o, 'visible_camera_eval') else (o.type == 'MESH' and not o.hide_render)

class Escena:
    def __init__(self, toma):
        self.sc = bpy.context.scene; self.toma = toma
        self.cam = bpy.data.objects[toma["camara"]]
        self.ids_pj = sorted({o.name for o in bpy.data.objects if o.type == 'ARMATURE' and not o.name.startswith(('TMP_', 'SRC_'))
                              and any(c.type == 'MESH' for c in o.children_recursive)}, key=len, reverse=True)
        # protegidos: objetivo + en_cuadro + debe_verse + objetos_sb que EXISTEN en la escena (no se inventan)
        prot = set([toma["objetivo"]] + toma.get("en_cuadro", []) + toma.get("debe_verse", []))
        self.no_encontrados = []
        self.prot_objs = set()
        for nom in toma.get("objetos_sb", []) + toma.get("debe_verse", []):
            hits = [o.name for o in bpy.data.objects if o.name == nom or o.name.startswith(nom + '.') or o.name.startswith(nom + '_')]
            if nom in self.ids_pj: continue
            if hits: self.prot_objs.update(hits)
            else: self.no_encontrados.append(nom)
        self.prot_pj = {p for p in prot if p in self.ids_pj}
        self.no_encontrados += [p for p in prot if p.startswith('ch-') and p not in self.ids_pj]
        # N0 (historia) y N2 protegidos: nunca reciben visible_camera=False desde este módulo
        self.n0 = set(toma.get("n0") or []) | set(toma.get("n2_protegido") or [])
        if toma.get("n0") is not None:
            self.prot_n0_pj = set(self.ids_pj)          # todos los personajes son historia (también los que no están en_cuadro)
        else:
            self.prot_n0_pj = set()
        self.meshes = [o for o in bpy.data.objects if o.type == 'MESH']
        self.ent = {o.name: entidad_de(o.name, self.ids_pj) for o in self.meshes}
        self.ocultos = {}   # nombre -> set(frames) (decisión de este módulo)
        self.conflictos_ancla = []

    def protegido(self, o):
        return (o.name in self.prot_objs or o.name in self.n0 or (self.ent.get(o.name) in self.prot_pj)
                or (self.ent.get(o.name) in self.prot_n0_pj))

    def visible_en_cuadro(self, o):
        # hide_render animado (presencia) y visible_camera previo (despejes anteriores) ya evaluados al frame actual
        return o.type == 'MESH' and not o.hide_render and o.visible_camera

    def muestras(self, pj, dg):
        """puntos de la malla del personaje (evaluada) que caen DENTRO del cuadro de la cámara."""
        pts = []
        for o in self.meshes:
            if self.ent[o.name] != pj or not self.visible_en_cuadro(o): continue
            cab = es_cabeza(o.name)
            oe = o.evaluated_get(dg); me = oe.to_mesh(); mw = oe.matrix_world
            n = len(me.vertices); paso = max(1, n // (60 if cab else 12))
            for v in list(me.vertices)[::paso]:
                p = mw @ v.co; ndc = world_to_camera_view(self.sc, self.cam, p)
                if 0 <= ndc.x <= 1 and 0 <= ndc.y <= 1 and ndc.z > self.cam.data.clip_start:
                    pts.append((p, cab, o.name))
            oe.to_mesh_clear()
        cabs = [x for x in pts if x[1]]; cuer = [x for x in pts if not x[1]]
        def ralear(l, m): return l if len(l) <= m else [l[int(i * len(l) / m)] for i in range(m)]
        return ralear(cabs, MAX_CABEZA) + ralear(cuer, MAX_CUERPO)

    def rayo(self, dg, C, P, pj, ignorar):
        """devuelve ('libre'|'propio'|'tapado', [objetos que tapan antes del punto])."""
        d = P - C; L = d.length; d.normalize(); O = C.copy(); recorrido = 0.0; tapan = []
        for _ in range(40):
            hit, loc, nor, idx, ob, mx = self.sc.ray_cast(dg, O, d, distance=L - recorrido)
            if not hit: return ('tapado' if tapan else 'libre'), tapan
            dist = (loc - C).length
            if dist >= L - EPS_PUNTO: return ('tapado' if tapan else 'libre'), tapan
            ob = bpy.data.objects.get(ob.name, ob)
            if self.ent.get(ob.name) == pj:
                return ('tapado' if tapan else 'propio'), tapan      # cara de atrás: el propio cuerpo la tapa
            if ob.name not in ignorar and self.visible_en_cuadro(ob):
                tapan.append(ob.name)
            O = loc + d * 1e-4; recorrido = (O - C).length
        return ('tapado' if tapan else 'libre'), tapan

    def analizar(self, frames, ocultar_simulado=None):
        """ocultar_simulado: dict nombre->set(frames) que se tratan como invisibles (para verificar el 'después')."""
        res = {}
        for f in frames:
            self.sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
            C = self.cam.matrix_world.translation.copy()
            ign = {n for n, fs in (ocultar_simulado or {}).items() if f in fs}
            r = {"sujetos": {}, "tapan": {}, "conflictos": [], "dentro": []}
            # 1) cámara dentro de geometría
            cand = [o for o in self.meshes if self.visible_en_cuadro(o) and o.name not in ign]
            for o, mot, dd in CSP.revisar_cuadro(self.cam, cand, dg):
                if self.protegido(o): r["conflictos"].append({"tipo": "camara_dentro_de_protegido", "objeto": o.name, "motivo": mot})
                else: r["dentro"].append({"objeto": o.name, "motivo": mot, "dist_m": dd})
            ign_d = ign | {x["objeto"] for x in r["dentro"]}
            # 2) oclusión de los sujetos protegidos
            for pj in sorted(self.prot_pj):
                pts = self.muestras(pj, dg)
                cnt = {"en_cuadro": len(pts), "visibles": 0, "tapadas": 0, "propias": 0, "cabeza_en_cuadro": 0, "cabeza_tapadas": 0}
                for P, cab, _ in pts:
                    est, tapan = self.rayo(dg, C, P, pj, ign_d)
                    cnt["cabeza_en_cuadro"] += cab
                    if est == 'propio': cnt["propias"] += 1; continue
                    if est == 'libre': cnt["visibles"] += 1; continue
                    cnt["tapadas"] += 1; cnt["cabeza_tapadas"] += cab
                    for t in set(tapan):
                        k = r["tapan"].setdefault(t, {"muestras": 0, "cabeza": 0, "a": set()})
                        k["muestras"] += 1; k["cabeza"] += cab; k["a"].add(pj)
                r["sujetos"][pj] = cnt
            for t, k in r["tapan"].items():
                k["a"] = sorted(k["a"])
                if self.protegido(bpy.data.objects[t]) and k["muestras"] >= MIN_MUESTRAS:
                    r["conflictos"].append({"tipo": "protegido_tapa_sujeto", "objeto": t, "entidad": self.ent.get(t) or t, "tapa_a": k["a"], "muestras": k["muestras"]})
            res[f] = r
        return res

    def decidir(self, analisis):
        """frames por unidad a ocultar. Unidad = personaje completo (ch-*) o el objeto del set/prop que tapa."""
        porunidad = {}
        motivo = {}
        for f, r in analisis.items():
            for t, k in r["tapan"].items():
                o = bpy.data.objects[t]
                if self.protegido(o) or k["muestras"] < MIN_MUESTRAS: continue
                u = self.ent.get(t) or t
                porunidad.setdefault(u, set()).add(f); motivo.setdefault(u, set()).add("tapa:" + ",".join(k["a"]))
            for x in r["dentro"]:
                if self.protegido(bpy.data.objects[x["objeto"]]): continue
                u = self.ent.get(x["objeto"]) or x["objeto"]
                porunidad.setdefault(u, set()).add(f); motivo.setdefault(u, set()).add(x["motivo"])
        # anclados: un personaje que va pegado a otro (p. ej. uno sentado en el hombro de otro) se oculta con su portador
        for pj in self.ids_pj:
            a = bpy.data.objects[pj]; par = a.parent; port = None
            while par is not None:
                if par.name in porunidad and par.name in self.ids_pj: port = par.name; break
                par = par.parent
            if port is None: continue
            if pj in self.prot_pj or pj in self.prot_n0_pj:
                self.conflictos_ancla.append({"tipo": "protegido_anclado_a_oculto", "objeto": pj, "portador": port}); continue
            porunidad.setdefault(pj, set()).update(porunidad[port]); motivo.setdefault(pj, set()).add("anclado_a:" + port)
        # unir huecos cortos (anti-parpadeo)
        for u, fs in porunidad.items():
            s = sorted(fs); add = set()
            for a, b in zip(s, s[1:]):
                if 1 < b - a <= UNIR_HUECO + 1: add.update(range(a + 1, b))
            fs |= add
        return porunidad, {u: sorted(m) for u, m in motivo.items()}

    def objetos_de_unidad(self, u):
        if u in self.ids_pj: return [o for o in self.meshes if self.ent[o.name] == u]
        return [bpy.data.objects[u]]

    def aplicar(self, porunidad):
        """keyframes CONSTANT de visible_camera; visible_shadow intacto."""
        f0, f1 = self.toma["frame_ini"], self.toma["frame_fin"]
        aplicado = {}
        for u, fs in porunidad.items():
            for o in self.objetos_de_unidad(u):
                if self.protegido(o): continue          # guarda universal: lo de historia nunca se oculta
                # valor previo en el borde (respeta despejes anteriores fuera de la toma)
                self.sc.frame_set(f0 - 1); prev_antes = o.visible_camera
                self.sc.frame_set(f1 + 1); prev_despues = o.visible_camera
                for f in range(f0, f1 + 1):
                    v = f not in fs
                    o.visible_camera = v; o.keyframe_insert('visible_camera', frame=f)
                o.visible_camera = prev_despues; o.keyframe_insert('visible_camera', frame=f1 + 1)
                o.visible_camera = prev_antes; o.keyframe_insert('visible_camera', frame=f0 - 1)
                for fc in fcurves(o):
                    if fc.data_path == 'visible_camera':
                        for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
                aplicado[o.name] = sorted(fs)
                self.ocultos[o.name] = set(fs)
        return aplicado

def fcurves(id_):
    ad = id_.animation_data
    if not ad or not ad.action: return []
    a = ad.action
    if hasattr(a, 'fcurves') and not hasattr(a, 'layers'): return list(a.fcurves)
    out = []
    for L in a.layers:
        for s in L.strips:
            cb = s.channelbag(ad.action_slot) if ad.action_slot else None
            if cb: out += list(cb.fcurves)
    return out

def rangos(fs):
    s = sorted(fs); out = []
    for f in s:
        if out and f == out[-1][1] + 1: out[-1][1] = f
        else: out.append([f, f])
    return out

def resumen(an, E):
    tot = {"cuadros": len(an), "muestras_tapadas": 0, "cabeza_tapadas": 0, "cuadros_con_tapado": 0,
           "cuadros_cabeza_principal_tapada": 0, "cuadros_camara_dentro": 0, "conflictos": 0, "principal_en_cuadro_min_muestras": None}
    obj = E.toma["objetivo"]
    for f, r in an.items():
        t = sum(c["tapadas"] for c in r["sujetos"].values()); tot["muestras_tapadas"] += t
        tot["cabeza_tapadas"] += sum(c["cabeza_tapadas"] for c in r["sujetos"].values())
        tot["cuadros_con_tapado"] += t > 0; tot["cuadros_camara_dentro"] += bool(r["dentro"]); tot["conflictos"] += len(r["conflictos"])
        c = r["sujetos"].get(obj)
        if c:
            tot["cuadros_cabeza_principal_tapada"] += c["cabeza_tapadas"] > 0
            if c["cabeza_en_cuadro"] == 0: tot.setdefault("cuadros_cabeza_principal_fuera_de_cuadro", []).append(f)
            m = c["cabeza_en_cuadro"]
            tot["principal_en_cuadro_min_muestras"] = m if tot["principal_en_cuadro_min_muestras"] is None else min(m, tot["principal_en_cuadro_min_muestras"])
    return tot

def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser(); ap.add_argument('--toma'); ap.add_argument('--out'); ap.add_argument('--guardar', default=None)
    ap.add_argument('--render', default=''); ap.add_argument('--res', default='640x360'); ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--tag', default=None); ap.add_argument('--exposicion', type=float, default=None)
    a = ap.parse_args(argv)
    toma = json.load(open(a.toma)); os.makedirs(a.out, exist_ok=True)
    tag = a.tag or toma["vineta"]
    E = Escena(toma)
    frames = list(range(toma["frame_ini"], toma["frame_fin"] + 1, toma.get("paso_frames", 1)))
    t0 = time.time(); an0 = E.analizar(frames); t_an = time.time() - t0
    porunidad, motivos = E.decidir(an0)
    # verificación: misma medición tratando lo decidido como invisible
    sim = {}
    for u, fs in porunidad.items():
        for o in E.objetos_de_unidad(u): sim[o.name] = fs
    an1 = E.analizar(frames, ocultar_simulado=sim)
    R0, R1 = resumen(an0, E), resumen(an1, E)
    rep = {"contrato": "reporte_ocultar_v1", "toma_id": toma["toma_id"], "vineta": toma["vineta"], "blender": bpy.app.version_string,
           "camara": toma["camara"], "camara_movida": False, "frames": [toma["frame_ini"], toma["frame_fin"]],
           "protegidos": {"personajes": sorted(E.prot_pj), "objetos": sorted(E.prot_objs)}, "no_encontrados_en_escena": E.no_encontrados,
           "ocultados": [{"unidad": u, "tipo": "personaje" if u in E.ids_pj else "objeto", "cuadros": rangos(fs), "n_cuadros": len(fs),
                          "motivo": motivos.get(u), "propiedad": "visible_camera", "visible_shadow": "sin_cambio"} for u, fs in sorted(porunidad.items())],
           "conflictos": sorted({json.dumps({k: v for k, v in c.items() if k != "muestras"}, sort_keys=True) for r in an1.values() for c in r["conflictos"]}),
           "antes": R0, "despues": R1, "segundos_analisis": round(t_an, 1)}
    rep["conflictos"] = [json.loads(c) for c in rep["conflictos"]] + E.conflictos_ancla
    if rep["conflictos"]:
        cf = {}
        for f, r in an1.items():
            for c in r["conflictos"]: cf.setdefault(c["objeto"], []).append(f)
        rep["conflictos_cuadros"] = {k: rangos(v) for k, v in cf.items()}
    for R in (R0, R1):
        if "cuadros_cabeza_principal_fuera_de_cuadro" in R: R["cuadros_cabeza_principal_fuera_de_cuadro"] = rangos(R["cuadros_cabeza_principal_fuera_de_cuadro"])
    if R1.get("cuadros_cabeza_principal_fuera_de_cuadro"):
        rep["aviso_encuadre"] = "la cabeza del sujeto principal no está en cuadro en esos cuadros: NO es un estorbo, es encuadre del storyboard -> reporte al storyboard (el motor no mueve la cámara)"
    rep["estado"] = "conflicto_reportar_storyboard" if (rep["conflictos"] or R1.get("cuadros_cabeza_principal_fuera_de_cuadro")) else ("ok" if R1["muestras_tapadas"] == 0 and R1["cuadros_camara_dentro"] == 0 else "residual")
    # muestras por cuadro (compacto) para gráficas
    rep["por_cuadro"] = {f: {"tapadas_antes": sum(c["tapadas"] for c in an0[f]["sujetos"].values()),
                             "tapadas_despues": sum(c["tapadas"] for c in an1[f]["sujetos"].values()),
                             "dentro": [x["objeto"] for x in an0[f]["dentro"]],
                             "ocultos": sorted(u for u, fs in porunidad.items() if f in fs)} for f in frames}
    # render ANTES (sin aplicar) y DESPUÉS (aplicado)
    rfr = [int(x) for x in a.render.split(',') if x]
    sc = E.sc
    if rfr:
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = a.samples
        try: sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        except Exception: pass
        rx, ry = map(int, a.res.split('x')); sc.render.resolution_x, sc.render.resolution_y = rx, ry; sc.render.resolution_percentage = 100
        sc.camera = E.cam
        if a.exposicion is not None: sc.view_settings.exposure = a.exposicion   # solo legibilidad de las imágenes del lab
        for f in rfr:
            sc.frame_set(f); sc.render.filepath = f"{a.out}/{tag}_f{f:04d}_antes.png"; bpy.ops.render.render(write_still=True)
    rep["aplicado"] = {k: rangos(v) for k, v in E.aplicar(porunidad).items()}
    if rfr:
        for f in rfr:
            sc.frame_set(f); sc.render.filepath = f"{a.out}/{tag}_f{f:04d}_despues.png"; bpy.ops.render.render(write_still=True)
    # comprobar en la escena real: visible_camera evaluado por cuadro coincide con la decisión
    errores = 0
    for f in frames[::7]:
        sc.frame_set(f)
        for n, fs in E.ocultos.items():
            errores += bpy.data.objects[n].visible_camera != (f not in fs)
    rep["chequeo_keyframes_errores"] = errores
    json.dump(rep, open(f"{a.out}/reporte_{tag}.json", "w"), indent=1, ensure_ascii=False, default=list)
    if a.guardar:
        bpy.ops.wm.save_as_mainfile(filepath=a.guardar, copy=True)
    print("RESULT", json.dumps({k: rep[k] for k in ("estado", "ocultados", "conflictos", "antes", "despues", "no_encontrados_en_escena", "chequeo_keyframes_errores", "segundos_analisis")}, ensure_ascii=False, default=list))

if __name__ == "__main__":
    main()
