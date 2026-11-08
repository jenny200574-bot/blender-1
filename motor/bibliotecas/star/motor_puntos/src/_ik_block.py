
# ---------- STAR_IK_CONTACTOS_v1: mano → punto nombrado (c∈[0,1] hold) ----------
_HAND_MAP = {
    'mano_R': ('J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand'),
    'mano_L': ('J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand'),
    'mano_derecha': ('J_Bip_R_UpperArm', 'J_Bip_R_LowerArm', 'J_Bip_R_Hand'),
    'mano_izquierda': ('J_Bip_L_UpperArm', 'J_Bip_L_LowerArm', 'J_Bip_L_Hand'),
}
if _PARAM_REPORT and isinstance(_PARAM_REPORT.get('puntos'), dict):
    for _k, _v in _PARAM_REPORT['puntos'].items():
        if _k not in PT:
            try: PT[_k] = Vector(_v)
            except Exception: pass

def _star_ik_ccd(A, names, target_w, iters=14):
    up, lo, hand = names
    bup, blo = A.pose.bones.get(up), A.pose.bones.get(lo)
    if bup is None or blo is None: return False
    for pb in (bup, blo):
        pb.rotation_mode = 'QUATERNION'
    for _ in range(iters):
        bpy.context.view_layer.update()
        tip = A.matrix_world @ blo.tail
        hb = A.pose.bones.get(hand)
        if hb is not None:
            tip = A.matrix_world @ hb.head
        for b in (blo, bup):
            bpy.context.view_layer.update()
            origin = A.matrix_world @ b.head
            # current tip after previous bone
            tip2 = A.matrix_world @ (A.pose.bones.get(hand).head if A.pose.bones.get(hand) is not None else blo.tail)
            to_tip = (tip2 - origin)
            to_tgt = (target_w - origin)
            if to_tip.length < 1e-6 or to_tgt.length < 1e-6: continue
            q = to_tip.normalized().rotation_difference(to_tgt.normalized())
            q = Quaternion((1,0,0,0)).slerp(q, 0.7)
            Mw = A.matrix_world @ b.matrix
            Rnew = q.to_matrix().to_4x4() @ Mw
            b.matrix = A.matrix_world.inverted() @ Rnew
    bpy.context.view_layer.update()
    return True

def _star_resolve_punto(nombre):
    if nombre in PT: return PT[nombre].copy()
    oid = nombre.split('.', 1)[0]
    for cand in (f'param_{oid}', nombre, f'param_{nombre.replace(".","_")}'):
        o = bpy.data.objects.get(cand)
        if o is not None:
            return o.matrix_world.translation.copy()
    return None

_IK_MED = {'ok': [], 'faltas': [], 'dists': []}
CHK_IK = _IK_MED
for _ct in (E.get('contactos') or []):
    try:
        _actor = _ct.get('actor'); _parte = _ct.get('parte_cuerpo') or ''
        _pto = _ct.get('objeto_punto'); _t0 = float(_ct.get('t0') or 0); _t1 = float(_ct.get('t1') or (_t0+0.5))
        _dmax = float(_ct.get('dist_max_m') or 0.03)
        if _actor not in PERS:
            faltas.append(f"IK contacto: actor {_actor} FALTA"); continue
        A = PERS[_actor].get('A')
        if A is None:
            faltas.append(f"IK contacto: {_actor} sin armature FALTA"); continue
        names = _HAND_MAP.get(_parte)
        if not names:
            faltas.append(f"IK contacto: parte {_parte} desconocida FALTA"); continue
        tgt = _star_resolve_punto(_pto)
        if tgt is None:
            faltas.append(f"IK contacto: punto {_pto} FALTA"); continue
        f0 = max(1, int(round(fr(_t0)))); f1 = min(NF, int(round(fr(_t1))))
        _ds = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            bpy.context.view_layer.update()
            _star_ik_ccd(A, names, tgt)
            bpy.context.view_layer.update()
            hb = A.pose.bones.get(names[2]); blo = A.pose.bones[names[1]]
            tip = A.matrix_world @ (hb.head if hb is not None else blo.tail)
            d = (tip - tgt).length
            _ds.append(d)
            for bn in names[:2]:
                pb = A.pose.bones.get(bn)
                if pb is None: continue
                pb.keyframe_insert('rotation_quaternion', frame=f)
                pb.keyframe_insert('location', frame=f)
        dmin = min(_ds) if _ds else 999.0
        dmed = (sum(_ds)/len(_ds)) if _ds else 999.0
        _IK_MED['dists'].append({'punto': _pto, 'parte': _parte, 't0': _t0, 't1': _t1,
                                 'd_min_m': round(dmin, 4), 'd_med_m': round(dmed, 4),
                                 'ok_3cm': bool(dmin <= _dmax)})
        if dmin <= _dmax:
            _IK_MED['ok'].append(f"{_parte}->{_pto} dmin={dmin:.3f}")
            avisos.append(f"IK OK {_parte}->{_pto} t={_t0}-{_t1} dmin={dmin:.3f}m")
        else:
            msg = f"IK parcial {_parte}->{_pto} dmin={dmin:.3f}m (objetivo <={_dmax}m)"
            avisos.append(msg)
            if dmin > 0.08:
                faltas.append(msg)
    except Exception as _ex:
        faltas.append(f"IK contacto FALTA: {_ex}")
        avisos.append(f"IK contacto FALTA: {_ex}")
avisos.append(f"STAR_IK_CONTACTOS_v1 n={len(E.get('contactos') or [])} ok={len(_IK_MED['ok'])}")

for _ev in (E.get('eventos_escenario') or []):
    if (_ev.get('tipo') or '') != 'temblor':
        continue
    _ar = _ev.get('actor_reaccion')
    if not _ar or _ar not in PERS:
        continue
    try:
        _amp = float(_ev.get('amplitud_m') or 0.03)
        _freq = float(_ev.get('frecuencia_hz') or 5)
        _t0 = float(_ev.get('t0') or 0); _t1 = float(_ev.get('t1') or (_t0+1))
        _root = PERS[_ar]['A'] or PERS[_ar]['root']
        _n = max(2, int(round((_t1-_t0)*FPS)))
        sc.frame_set(int(round(fr(_t0)))); _base = list(_root.location)
        for _i in range(_n+1):
            _u = _i/max(1,_n); _t = _t0 + (_t1-_t0)*_u; _f = int(round(fr(_t)))
            _dx = _amp * math.sin(2*math.pi*_freq*_u)
            _dy = _amp * math.cos(2*math.pi*_freq*_u)
            sc.frame_set(_f)
            _root.location = (_base[0]+_dx, _base[1]+_dy, _base[2])
            _root.keyframe_insert('location', frame=_f)
        avisos.append(f"temblor actor {_ar} amp={_amp} t={_t0}-{_t1}")
    except Exception as _ex:
        avisos.append(f"temblor actor FALTA: {_ex}")

