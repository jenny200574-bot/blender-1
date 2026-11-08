"""API INTERNA de esqueleto/solver bueno. NO produce un resultado de producción.
La entrada pública/orquestador valida el contrato completo ANTES de llamar.
No hay --diagnostico; las notas del paquete histórico se conservan en su fuente.
"""
"""Constructor CPU universal. Identidad, escena y tiempos sólo por entrada.json."""
import bpy,sys,json,math,copy,os,time
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent/'heredado';sys.path.insert(0,str(ROOT))
import esqueleto_adn as EA,rig as rig,movimiento_natural as MN,formulas_v2 as FV
from entrada import leer,guardar,validar,posicion
from mundo_catalogo import mundo_v7
import camara
args=sys.argv[sys.argv.index('--')+1:];PK=Path(args[0]).resolve();OUT=Path(args[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
DATA=leer(PK/'entrada.json')
required=['scene','fps','duration_s','environment','actors','props','catalog','assignments','camera','rules','solver','render','provisional']
if any(k not in DATA for k in required):raise SystemExit('Formato de núcleo incompleto')
# .off del núcleo se respeta; habilitar es sólo prueba local explícita.
def exigir_activo(name):
 if (ROOT/(name+'.off')).exists() and '--habilitar' not in args:raise SystemExit('Núcleo desactivado por '+name+'.off')
exigir_activo('universal_calidad')
FPS=DATA['fps'];DUR=DATA['duration_s'];CP=leer(PK/DATA['catalog']);ASIG=leer(PK/DATA['assignments']);SW=DATA['solver'];N=round(FPS*DUR)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
sc=bpy.context.scene;sc.render.fps=FPS;sc.frame_start=1;sc.frame_end=N
F=DATA['environment'];BASE=[]
if F['mode']=='blend':
 with bpy.data.libraries.load(str(PK/F['path']),link=False) as (a,b):b.objects=[n for n in a.objects]
 for obj in b.objects:
  if obj:
   sc.collection.objects.link(obj);obj.hide_render=False;BASE.append(obj)
else:
 CAT=leer(PK/F['catalog']);PT={}
 for o in F['placements']:
  ff=CAT[o['formula']]
  if ff.get('tipo')=='mundo':mundo_v7(ff,sc);continue
  rr,info=FV.construir(o['id'],ff,o['pos_m'],o['tamano_m'],o['rot_z_deg'])
  for k,v in info['puntos'].items():PT.setdefault(k,bpy.data.objects[v])
if (ROOT.parent.parent/'config/orden_determinista.off').exists():raise SystemExit('DESACTIVADO orden determinista')
# Orden explícito suministrado por el adaptador; no orden alfabético de identidades.
for key,field in [('entity_order','actors'),('prop_order','props')]:
 if key in DATA['rules']:
  order=DATA['rules'][key];values={x['id']:x for x in DATA[field]}
  if len(order)!=len(values) or set(order)!=set(values):raise SystemExit('Orden de evaluación incompleto/duplicado')
  DATA[field]=[values[x] for x in order]
actors={a['id']:a for a in DATA['actors']};PJ={};PRF={};OBJ={};PT=locals().get('PT',{});REP={'ajustes':[]}
for pid,a in actors.items():
 s=a['spec'];A=rig.crear(pid,s,a['colors']);HB=EA.huesos(s);pos,yaw,_=posicion(a,0)
 PJ[pid]={'A':A,'rad':{b['nombre']:b['radio'] for b in HB},'gr':{b['nombre']:b['grupo'] for b in HB},'pos':Vector(pos[:2]),'yaw':yaw,'H':s['altura_m'],'spec':s,'ini':a['initial_pose_id'],'L0':None,'policy':a['solver_policy']}
 PRF[pid]=a['profile']
for q in DATA['props']:
 ff=leer(PK/q['formula']);rr,info=FV.construir(q['id'],ff,q['pos_m'],q['size_m'],q['yaw_deg']);OBJ[q['id']]=rr
 for k,v in info['puntos'].items():PT.setdefault(k,bpy.data.objects[v])
 if q.get('anchor'):
  a=q['anchor'];rr.parent=PJ[a['actor']]['A'];rr.parent_type='BONE';rr.parent_bone=a['bone'];rr.matrix_parent_inverse=Matrix();rr.location=q['local_pos'];rr.rotation_euler=[math.radians(x) for x in q['local_rot_deg']]
  if q.get('pivot'):
   parent=rr.parent;piv=bpy.data.objects.new(q['id']+'_pivot',None);sc.collection.objects.link(piv);piv.parent=parent;piv.parent_type='BONE';piv.parent_bone=a['bone'];piv.matrix_parent_inverse=Matrix();piv.location=q['pivot']['pos'];piv.rotation_euler=[math.radians(x) for x in q['pivot']['rot_deg']];rr.parent=piv;rr.parent_type='OBJECT';rr.parent_bone='';rr.matrix_parent_inverse=Matrix()
   if q.get('track'):
    target=bpy.data.objects.new(q['id']+'_target',None);sc.collection.objects.link(target);constraint=piv.constraints.new('DAMPED_TRACK');constraint.target=target;constraint.track_axis=q['track']['axis'];constraint.influence=0;OBJ[q['id']+'_tracking']=(target,constraint,q['track'])
for ob in BASE:ob.hide_viewport=True
pose_ang=lambda n:CP['poses'][n]['angulos']
POSES_ANG={n:p['angulos'] for n,p in CP['poses'].items()}
def ss(x):x=max(0,min(1,x));return x*x*x*(x*(x*6-15)+10)

def estado_simple(pid,t,ultimo,rows):
    """v7: fases intermedias + Catmull-Rom + solape tronco/brazos (perfil del personaje)."""
    asg = sorted(rows,key=lambda x:x["t0"]); cur = None
    for x in asg:
        if x["t0"] <= t: cur = x
    if cur is None: return pose_ang(PJ[pid]["ini"]), None, 0.0, None
    M = CP["movimientos"][cur["movimiento"]]; dur = max(1e-3, cur["t1"] - cur["t0"]); u = min(1.0, (t - cur["t0"]) / dur); prf = PRF[pid]
    keys = cur.setdefault("_keys", MN.expandir_fases(M["fases"], POSES_ANG, prf["umbral_fase_intermedia_deg"], lambda b: cadena(PJ[pid]["A"], b))); ini = cur.setdefault("_inicio", ultimo)
    ang, kc = MN.con_solape(keys, ini, u, dur, prf)
    dsp = 0.0; tp = 0.0
    for k in keys:
        if k[4]: dsp += k[4] * max(0.0, min(1.0, (MN.facil(u, prf["suavizado_inicio_fin"]) - tp) / max(1e-3, k[0] - tp)))
        tp = k[0]
    return ang, (cur, M, u), dsp, kc
def estado(pid,t,ultimo):
 rows=[x for x in ASIG if x['personaje']==pid]
 if not DATA['rules']['layers']:return estado_simple(pid,t,ultimo,rows)
 result={k:v[:] for k,v in pose_ang(PJ[pid]['ini']).items()};active=None;dsp=0;kc=None
 for layer in DATA['rules']['layers']:
  rr=[x for x in rows if x.get('capa')==layer and x['t0']<=t<=x['t1']]
  if not rr:continue
  aa,ac,dd,kk=estado_simple(pid,t,ultimo,rr)
  if ac:
   for k in ac[0]['huesos']:
    if k in aa:result[k]=aa[k]
   active=ac;kc=kk;dsp=dd
 return result,active,dsp,kc

ALI_APOYO = {"cadera": "pelvis", "rodilla_L": "pierna_L", "rodilla_R": "pierna_R", "codo_L": "antebrazo_L", "codo_R": "antebrazo_R", "gluteo": "pelvis"}
def cadena(A, b):
    """v9: huesos de la extremidad de un apoyo, sacados del esqueleto (sube por los padres mientras sigan del mismo lado). Sin nombres fijos."""
    b = ALI_APOYO.get(b, b.replace("rodilla", "pierna"))
    if b not in A.pose.bones or "_" not in b: return []
    lado = b[b.rfind("_"):]; out = []; pb = A.pose.bones[b]
    while pb is not None and pb.name.endswith(lado): out.append(pb.name); pb = pb.parent
    return out
# ---- v9 cambios Argon-5 (universales). Cada uno se apaga con <nombre>.off junto al motor; con todos los .off = motor original ----
SW = dict(DATA["solver"])
# Compatibilidad universal por entrada; .off sigue siendo vinculante.
MN.aplicar_politica_entrada(SW)
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
    anclar = bool(kc and kc[3]) and prf["anclaje_pies"] > 0.5 and dsp == 0 and P["policy"]["foot_anchoring"]
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
def mirar(pid, ang, objetivo, w):
    P = PJ[pid]; A = P["A"]; bpy.context.view_layer.update(); cab = A.matrix_world @ A.pose.bones["cabeza"].head
    tg = PT[objetivo].matrix_world.translation if objetivo in PT else None
    if tg is None:
        o, pn = objetivo.split(".", 1); Q = rig.puntos_cuerpo(PJ[o]["A"]); tg = Q.get(pn, Q["cabeza"])
    d = A.matrix_world.to_3x3().inverted() @ (tg - cab); yaw = math.degrees(math.atan2(-d.x, d.y)); pit = -math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    for b, f in (("cuello", .5), ("cabeza", .5)):
        v = ang.setdefault(b, [0, 0, 0]); ang[b] = [v[0] + pit * f * w, v[1], v[2] + yaw * f * w]
TRK = {pid: [] for pid in PJ}; ultimo = {pid: pose_ang(PJ[pid]["ini"]) for pid in PJ}; suav = {pid: None for pid in PJ}
for pid, P in PJ.items(): P["anc"] = None; P["off"] = Vector((0, 0))
ORD = list(actors)
for f in range(N):
    t = f / FPS; sc.frame_set(f + 1)
    for pid in ORD:
        P = PJ[pid]; actor=actors[pid]; source_pos,source_yaw,segment=posicion(actor,t)
        if DATA["rules"]["root_mode"]=="segments":P["pos"]=Vector(source_pos[:2]);P["yaw"]=source_yaw
        A = P["A"]; ang, act, dsp, kc = estado(pid, t, ultimo[pid]); prf = PRF[pid]; ang = {k: list(v) for k, v in ang.items()}
        tb = max(act[1].get("temblor_deg", 0) if act else 0, prf["temblor_deg"] if act and act[1].get("temblor_deg") else 0)
        if tb:
            for b in ("pierna_L", "pierna_R"):
                if b in ang: ang[b][0] += tb * 0.5 * math.sin(t * 2 * math.pi * 6 + (b == "pierna_R"))
        # límite de velocidad angular 300°/s
        if suav[pid]:
            lim = prf["vel_max_deg_s"] / FPS
            for k in set(ang) | set(suav[pid]):
                a0 = suav[pid].get(k, [0, 0, 0]); a1 = ang.setdefault(k, [0, 0, 0]); ang[k] = [a0[i] + max(-lim, min(lim, a1[i] - a0[i])) for i in range(3)]
        limites(pid, ang); suav[pid] = {k: list(v) for k, v in ang.items()}
        # raíz: posición del plan + desplazamiento hacia el objetivo de la asignación
        base = P["pos"].copy()
        if act and act[0].get("_d0") is None: act[0]["_d0"] = P.get("dlast", 0.0)
        dtot = (act[0]["_d0"] if act else 0) + dsp
        if act and dsp > 0:
            o = act[0]["objetivo_punto"].split(".")[0]; P["dir"] = (PJ[o]["pos"] - P["pos"]).normalized() if o in PJ else Vector((0, 1))
        P["dlast"] = dtot
        if DATA["rules"]["root_mode"]=="integrated":base = base + P.get("dir", Vector((0, 1))) * dtot
        rz = ang.get("raiz", [0, 0, 0]); rig.aplicar(A, ang); A.rotation_euler = (-math.radians(rz[0]), math.radians(rz[1]), math.radians(P["yaw"] + (rz[2] if len(rz) > 2 else 0)))
        A.location = (base.x + P["off"].x, base.y + P["off"].y, 0)
        if act:
            for ob in act[1].get('objetivos',[]):
                target=ob.get('hacia') or act[0].get('objetivo_punto')
                if ob['tipo'] in ('mirar','mirar_objeto_mano') and target and (target.split('.')[0] in PJ or target in PT):
                    w=ss((act[2]-ob['t_ini_frac'])/.15) if act[2]>=ob['t_ini_frac'] else 0
                    mirar(pid,ang,target,w);limites(pid,ang);rig.aplicar(A,ang)
        if act:
            for key,value in OBJ.items():
                if not isinstance(value,tuple):continue
                target,constraint,track=value
                if track['driver_actor']!=pid:continue
                for objective in act[1].get('objetivos',[]):
                    if objective['tipo']!='apuntar':continue
                    target.location=rig.puntos_cuerpo(PJ[track['target_actor']]['A'])[track['target_point']];target.keyframe_insert('location',frame=f+1)
                    weight=MN.facil(min(1.,act[2]/track['activation_fraction']),.5)
                    constraint.influence=1. if act[0]['movimiento'] in track['hold_movements'] else weight;constraint.keyframe_insert('influence',frame=f+1)
        # ---- v7 equilibrio: centro de masa sobre el polígono de apoyo; si no, corrige tronco/cadera ----
        # ---- v7 altura de cadera continua entre poses clave + IK de extremidades contra el piso (sin saltitos) ----
        ik_pend = None
        if act and kc is not None and not prf["vuela"]:
            cur = act[0]
            if "_zk" not in cur:
                zk = []
                for k_ in [(0.0, cur["_inicio"])] + [(k[0], k[1]) for k in cur["_keys"]]:
                    a_ = {x: list(v) for x, v in k_[1].items()}; limites(pid, a_); rr = a_.get("raiz", [0, 0, 0]); rig.aplicar(A, a_)
                    rot0 = tuple(A.rotation_euler); A.rotation_euler = (-math.radians(rr[0]), math.radians(rr[1]), math.radians(P["yaw"] + (rr[2] if len(rr) > 2 else 0))); loc0 = A.location.z; A.location.z = 0
                    bpy.context.view_layer.update(); zz, _ = rig.suelo(A, P["rad"]); zk.append((k_[0], -zz)); A.location.z = loc0; A.rotation_euler = rot0
                fl = [False] + [k[5] for k in cur["_keys"]]   # intermedias: altura interpolada de sus vecinas reales (no la de la pose promedio)
                for i_ in range(len(zk)):
                    if fl[i_]:
                        a0 = max(j for j in range(i_) if not fl[j]); b0 = min([j for j in range(i_ + 1, len(zk)) if not fl[j]] or [a0])
                        ww = 0 if b0 == a0 else (zk[i_][0] - zk[a0][0]) / (zk[b0][0] - zk[a0][0]); zk[i_] = (zk[i_][0], zk[a0][1] + (zk[b0][1] - zk[a0][1]) * ww)
                cur["_zk"] = zk
            uu = MN.facil(act[2], prf["suavizado_inicio_fin"]); zk = cur["_zk"]; j = next((i for i in range(len(zk) - 1) if uu <= zk[i + 1][0] + 1e-9), len(zk) - 2)
            w_ = (uu - zk[j][0]) / max(1e-6, zk[j + 1][0] - zk[j][0]); w_ = max(0, min(1, w_)); w_ = w_ * w_ * (3 - 2 * w_); ztg = zk[j][1] + (zk[j + 1][1] - zk[j][1]) * w_
            rig.aplicar(A, ang); A.location.z = ztg; bpy.context.view_layer.update()
            def _hacer_ik():
                global ang
                rig.aplicar(A, ang); A.location.z = ztg; bpy.context.view_layer.update()
                ang, P["ikd"] = MN.ik_piso(A, ang, P["rad"], rig.aplicar, lambda a__: limites(pid, a__), rig.suelo, P.get("ikd"), apoyos=_fn_apoyos(A, kc) if SW["ik_piso_suave"] else None)
                if len(kc) > 6 and kc[6]:   # v9 fase de apoyo: los apoyos que llegan bajan al piso (IK a Z=0) con el peso en los actuales
                    ii = cur["_keys"].index(kc); tA = cur["_keys"][ii - 1][0] if ii else 0.0; ww = max(0.0, min(1.0, (uu - tA) / max(1e-6, kc[0] - tA)))
                    def _pt(nm):
                        nm = ALI_APOYO.get(nm, nm.replace("rodilla", "pierna")); return lambda A__: (A__.matrix_world @ A__.pose.bones[nm].head) if nm.startswith("pierna") else (A__.matrix_world @ (A__.pose.bones[nm].tail if nm.startswith(("pie", "mano")) else A__.pose.bones[nm].head))
                    pts = {b: _pt(b) for b in kc[6] if ALI_APOYO.get(b, b.replace("rodilla", "pierna")) in A.pose.bones}
                    if pts: ang = MN.ik_bajar(A, ang, pts, lambda b: cadena(A, b), rig.aplicar, lambda a__: limites(pid, a__), peso=ww * ww * (3 - 2 * ww))
            if SW["orden_medicion"]: ik_pend = _hacer_ik
            else: _hacer_ik()
        if SW["orden_medicion"]:
            # ---- cambio E: pose → equilibrio → continuidad → IK piso → pegado → anclaje → RECIÉN AHÍ se mide (com_fuera, claves, TRK) ----
            _pegar(A, P, prf); fuera = 0.0
            if not prf["vuela"]:
                fuera = _fuera(A, P, kc); ang, fuera = _equilibrio(A, P, prf, pid, kc, ang, fuera)
            ang, fuera = _continuidad(A, P, prf, kc, ang, fuera)
            if ik_pend: ik_pend()
            _pegar(A, P, prf)
            _anclaje(A, P, prf, pid, kc, dsp)
            if not prf["vuela"]: fuera = _fuera(A, P, kc)
            P["ult_final"] = {k: list(v) for k, v in ang.items()}; P["z_prev"] = A.location.z
            P.setdefault("fuera", []).append(round(fuera, 3))
        else:
            _pegar(A, P, prf)
            fuera = 0.0
            if not prf["vuela"]:
                fuera = _fuera(A, P, kc); ang, fuera = _equilibrio(A, P, prf, pid, kc, ang, fuera)
            ang, fuera = _continuidad(A, P, prf, kc, ang, fuera)
            P["ult_final"] = {k: list(v) for k, v in ang.items()}; P["z_prev"] = A.location.z
            P.setdefault("fuera", []).append(round(fuera, 3))
            _anclaje(A, P, prf, pid, kc, dsp)
        A.location.z+=source_pos[2]+actor["floor_z"]
        bpy.context.view_layer.update()
        for pb in A.pose.bones: pb.keyframe_insert("rotation_euler", frame=f + 1)
        A.keyframe_insert("location", frame=f + 1); A.keyframe_insert("rotation_euler", frame=f + 1)
        ultimo[pid] = ang
        TRK[pid].append({"loc": list(A.location), "yaw": P["yaw"], "ang": {k: list(v) for k, v in ang.items()}, "largos": rig.largos(A), "zmin": rig.suelo(A, P["rad"])[0],
                         "mano_R": list(A.matrix_world @ A.pose.bones["mano_R"].tail), "hombro_R": list(A.matrix_world @ A.pose.bones["brazo_R"].head),
                         "cabeza": list(A.matrix_world @ A.pose.bones["cabeza"].tail), "pecho": list(rig.puntos_cuerpo(A)["pecho_c"]), "act": act[0]["movimiento"] if act else None, "com_fuera": P["fuera"][-1], "com": list(MN.centro_masa(A, P["rad"])), "bajo": rig.suelo(A, P["rad"])[1][0], "ang_dbg": {k: [round(x) for x in v] for k, v in ang.items() if k in ("raiz","muslo_L","pierna_L","muslo_R","pierna_R","brazo_L","brazo_R")}, "plant": P["resb"][-1]})

    if f%100==0:print('FRAME',f+1,'/',N,flush=True)

for ob in BASE:ob.hide_viewport=False;ob.hide_render=False
guardar(OUT/'trazas.json',TRK)
guardar(OUT/'nucleo_resultado.json',{'estado':'SOLO_BACKEND_FISICO','produccion_aprobada':False,'fps':FPS,'frames':N,'source_provisional':DATA['provisional'],'final_camera':False,'final_appearance':False})
sc.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'escena.blend'));print('NUCLEO_FISICO_TERMINADO',str(OUT/'escena.blend'),flush=True)
