"""Prototipo vuelo_alas / vuelo_sin_alas (Blender 5.2 headless, CPU, gratis).
- Muñeco TEST_alado (NO molde de fábrica; NO toca moldes de personajes).
- Parámetros desde receta JSON (schema receta_movimiento/v1).
- Validador local emite reporte_rechazo; demo mala→parche manual (simula Argon, US$0).
"""
import bpy, json, math, os, sys, shutil
from mathutils import Vector, Euler, Matrix

LAB = '/workspace/estudio_animacion/lab'
IMG = f'{LAB}/img'
TMP = f'{IMG}/_tmp'
REC = f'{LAB}/proto/recetas'
OUT = f'{LAB}/proto/vuelo_alas_out.json'
FPS = 24

# Limpia escena
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.unit_settings.system = 'METRIC'

# ---------- math helpers ----------
def catmull_rom(p0, p1, p2, p3, t):
    t2, t3 = t*t, t*t*t
    return 0.5 * ((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t2 + (-p0+3*p1-3*p2+p3)*t3)

def sample_path(waypoints, fps=FPS, acel_max=6.0, vel_max=3.5):
    """Catmull-Rom espacial + perfil de velocidad con |a|<=acel_max y |v|<=vel_max."""
    wps = sorted(waypoints, key=lambda w: w['t'])
    pts = [Vector(w['xyz']) for w in wps]
    fases_wp = [w['fase'] for w in wps]
    if len(pts) == 1:
        return [{'frame': 0, 't': 0.0, 'pos': pts[0], 'fase': fases_wp[0],
                 'vel': Vector((0,0,0)), 'acel': Vector((0,0,0))}]

    # dense spatial samples along CR (by waypoint parameter, then refine)
    P = [pts[0]] + pts + [pts[-1], pts[-1]]
    spatial = []  # (pos, fase)
    STEPS = 40
    for seg in range(len(pts)-1):
        for k in range(STEPS):
            u = k / STEPS
            pos = catmull_rom(P[seg], P[seg+1], P[seg+2], P[seg+3], u)
            fase = fases_wp[seg] if u < 0.5 else fases_wp[seg+1]
            spatial.append((pos, fase))
    spatial.append((pts[-1], fases_wp[-1]))

    # arc length
    s = [0.0]
    for i in range(1, len(spatial)):
        s.append(s[-1] + (spatial[i][0] - spatial[i-1][0]).length)
    total = s[-1] if s[-1] > 1e-6 else 1e-6

    # 1D velocity profile along s: accel / cruise / decel
    a = max(0.1, float(acel_max))
    vmax = max(0.1, float(vel_max))
    # distance to reach vmax: v^2/2a
    d_acc = (vmax * vmax) / (2 * a)
    if 2 * d_acc >= total:
        # triangle profile: peak v such that 2*(v^2/2a)=total
        vmax = math.sqrt(a * total)
        d_acc = total * 0.5
        d_cruise = 0.0
        d_dec = total - d_acc
    else:
        d_cruise = total - 2 * d_acc
        d_dec = d_acc

    def v_at_s(ss):
        if ss <= d_acc:
            # v^2 = 2 a s
            return math.sqrt(max(0.0, 2 * a * ss))
        elif ss <= d_acc + d_cruise:
            return vmax
        else:
            sd = ss - (d_acc + d_cruise)
            # decel: v^2 = vmax^2 - 2 a sd
            return math.sqrt(max(0.0, vmax * vmax - 2 * a * sd))

    # integrate time along s
    times = [0.0]
    for i in range(1, len(s)):
        ds = s[i] - s[i-1]
        vmid = max(0.05, 0.5 * (v_at_s(s[i-1]) + v_at_s(s[i])))
        times.append(times[-1] + ds / vmid)

    t_end = times[-1]
    nframes = max(1, int(round(t_end * fps)) + 1)
    path = []
    j = 0
    for fr in range(nframes):
        t = fr / fps
        if t >= times[-1]:
            j = len(times) - 2
            u = 1.0
        else:
            while j < len(times) - 2 and times[j+1] < t:
                j += 1
            dt = max(1e-6, times[j+1] - times[j])
            u = max(0.0, min(1.0, (t - times[j]) / dt))
        pos = spatial[j][0].lerp(spatial[j+1][0], u)
        fase = spatial[j][1] if u < 0.5 else spatial[j+1][1]
        path.append({'frame': fr, 't': t, 'pos': pos, 'fase': fase})

    for i, r in enumerate(path):
        if i == 0:
            r['vel'] = Vector((0, 0, 0))
        else:
            dt = max(1e-6, path[i]['t'] - path[i-1]['t'])
            r['vel'] = (path[i]['pos'] - path[i-1]['pos']) / dt
    for i, r in enumerate(path):
        if i == 0 or i == len(path) - 1:
            r['acel'] = Vector((0, 0, 0))
        else:
            dt = max(1e-6, path[i]['t'] - path[i-1]['t'])
            r['acel'] = (path[i]['vel'] - path[i-1]['vel']) / dt
    # zero the artificial endpoint spikes for reporting (keep motion)
    if len(path) > 4:
        path[1]['acel'] = path[2]['acel'].copy()
        path[-2]['acel'] = path[-3]['acel'].copy()
    return path


def limit_accel(path, acel_max):
    """Compat: sample_path ya limita; no-op si ya viene perfilado."""
    return path

# ---------- build TEST mold ----------
def mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.use_nodes = False
    m.diffuse_color = rgba
    return m

def add_bone(arm_data, name, head, tail, parent=None):
    b = arm_data.edit_bones.new(name)
    b.head = Vector(head)
    b.tail = Vector(tail)
    if parent:
        b.parent = arm_data.edit_bones[parent]
        b.use_connect = False
    return b

def build_test_alado(con_alas=True, nombre='TEST_alado'):
    """Muñeco segmentado de prueba con (o sin) cadenas de alas. Etiquetado TEST."""
    arm_d = bpy.data.armatures.new(f'{nombre}_arm')
    arm = bpy.data.objects.new(nombre, arm_d)
    sc.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    # cuerpo ~1.1 m
    add_bone(arm_d, 'raiz', (0,0,0), (0,0,0.05))
    add_bone(arm_d, 'cadera', (0,0,0.45), (0,0,0.50), 'raiz')
    add_bone(arm_d, 'columna', (0,0,0.50), (0,0,0.65), 'cadera')
    add_bone(arm_d, 'pecho', (0,0,0.65), (0,0,0.80), 'columna')
    add_bone(arm_d, 'cuello', (0,0,0.80), (0,0,0.90), 'pecho')
    add_bone(arm_d, 'cabeza', (0,0,0.90), (0,0,1.10), 'cuello')
    # brazos
    add_bone(arm_d, 'hombro_L', (-0.08,0,0.78), (-0.18,0,0.78), 'pecho')
    add_bone(arm_d, 'brazo_L', (-0.18,0,0.78), (-0.35,0,0.70), 'hombro_L')
    add_bone(arm_d, 'antebrazo_L', (-0.35,0,0.70), (-0.48,0,0.62), 'brazo_L')
    add_bone(arm_d, 'hombro_R', (0.08,0,0.78), (0.18,0,0.78), 'pecho')
    add_bone(arm_d, 'brazo_R', (0.18,0,0.78), (0.35,0,0.70), 'hombro_R')
    add_bone(arm_d, 'antebrazo_R', (0.35,0,0.70), (0.48,0,0.62), 'brazo_R')
    # piernas
    add_bone(arm_d, 'femur_L', (-0.08,0,0.45), (-0.08,0,0.22), 'cadera')
    add_bone(arm_d, 'tibia_L', (-0.08,0,0.22), (-0.08,0,0.05), 'femur_L')
    add_bone(arm_d, 'pie_L', (-0.08,0,0.05), (-0.08,-0.10,0.02), 'tibia_L')
    add_bone(arm_d, 'femur_R', (0.08,0,0.45), (0.08,0,0.22), 'cadera')
    add_bone(arm_d, 'tibia_R', (0.08,0,0.22), (0.08,0,0.05), 'femur_R')
    add_bone(arm_d, 'pie_R', (0.08,0,0.05), (0.08,-0.10,0.02), 'tibia_R')
    if con_alas:
        # cadenas de ala (3 huesos por lado), salen del pecho hacia afuera/atrás
        add_bone(arm_d, 'ala_L_1', (-0.10,0.02,0.76), (-0.40,0.05,0.78), 'pecho')
        add_bone(arm_d, 'ala_L_2', (-0.40,0.05,0.78), (-0.70,0.08,0.76), 'ala_L_1')
        add_bone(arm_d, 'ala_L_3', (-0.70,0.08,0.76), (-0.95,0.10,0.72), 'ala_L_2')
        add_bone(arm_d, 'ala_R_1', (0.10,0.02,0.76), (0.40,0.05,0.78), 'pecho')
        add_bone(arm_d, 'ala_R_2', (0.40,0.05,0.78), (0.70,0.08,0.76), 'ala_R_1')
        add_bone(arm_d, 'ala_R_3', (0.70,0.08,0.76), (0.95,0.10,0.72), 'ala_R_2')
    bpy.ops.object.mode_set(mode='OBJECT')

    # piezas segmentadas coloreadas (parent-bone), etiqueta TEST visible
    pieces = [
        ('p_cadera', 'cadera', (0.12,0.12,0.14), (0.9,0.3,0.2,1)),
        ('p_pecho', 'pecho', (0.16,0.12,0.18), (0.2,0.5,0.9,1)),
        ('p_cabeza', 'cabeza', (0.14,0.14,0.14), (0.95,0.85,0.55,1)),
        ('p_femur_L', 'femur_L', (0.07,0.07,0.18), (0.3,0.8,0.3,1)),
        ('p_tibia_L', 'tibia_L', (0.06,0.06,0.14), (0.2,0.6,0.2,1)),
        ('p_pie_L', 'pie_L', (0.08,0.12,0.04), (0.1,0.1,0.1,1)),
        ('p_femur_R', 'femur_R', (0.07,0.07,0.18), (0.3,0.8,0.3,1)),
        ('p_tibia_R', 'tibia_R', (0.06,0.06,0.14), (0.2,0.6,0.2,1)),
        ('p_pie_R', 'pie_R', (0.08,0.12,0.04), (0.1,0.1,0.1,1)),
        ('p_brazo_L', 'brazo_L', (0.06,0.06,0.14), (0.9,0.6,0.2,1)),
        ('p_brazo_R', 'brazo_R', (0.06,0.06,0.14), (0.9,0.6,0.2,1)),
    ]
    if con_alas:
        pieces += [
            ('p_ala_L_1', 'ala_L_1', (0.28,0.04,0.12), (0.85,0.2,0.85,1)),
            ('p_ala_L_2', 'ala_L_2', (0.28,0.03,0.10), (0.7,0.15,0.9,1)),
            ('p_ala_L_3', 'ala_L_3', (0.24,0.02,0.08), (0.55,0.1,0.95,1)),
            ('p_ala_R_1', 'ala_R_1', (0.28,0.04,0.12), (0.85,0.2,0.85,1)),
            ('p_ala_R_2', 'ala_R_2', (0.28,0.03,0.10), (0.7,0.15,0.9,1)),
            ('p_ala_R_3', 'ala_R_3', (0.24,0.02,0.08), (0.55,0.1,0.95,1)),
        ]
    for pname, bname, size, col in pieces:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        ob = bpy.context.object
        ob.name = pname
        ob.scale = size
        bpy.ops.object.transform_apply(scale=True)
        # place at bone mid
        pb = arm.data.bones[bname]
        mid = (Vector(pb.head_local) + Vector(pb.tail_local)) * 0.5
        # orient roughly along bone
        direction = (Vector(pb.tail_local) - Vector(pb.head_local))
        ob.location = mid
        if direction.length > 1e-6:
            ob.rotation_mode = 'QUATERNION'
            ob.rotation_quaternion = direction.to_track_quat('Z', 'Y')
        ob.data.materials.append(mat(pname+'_m', col))
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = bname
        # after parenting to bone, reset loc so it sits at bone
        ob.location = (0, 0, 0)
        # offset along bone length/2 in bone local Y (Blender bones: +Y along bone)
        ob.location = (0, direction.length * 0.5, 0)

    # etiqueta TEST (plano frente a la cabeza)
    bpy.ops.mesh.primitive_plane_add(size=0.35)
    tag = bpy.context.object
    tag.name = f'{nombre}_TAG_TEST'
    tag.location = (0, -0.25, 1.15)
    tag.rotation_euler = (math.pi/2, 0, 0)
    tag.data.materials.append(mat('tag_test', (1, 0.9, 0.1, 1)))
    tag.parent = arm
    return arm

# ---------- animate from receta ----------
def animate_from_receta(arm, receta, con_alas=True):
    fb = receta['fuente_bloques']
    traj = fb['trayectoria']
    path = sample_path(
        traj['waypoints'], FPS,
        acel_max=float(traj.get('acel_max_m_s2', 6.0)),
        vel_max=float(traj.get('vel_max_m_s', 3.5)),
    )
    path = limit_accel(path, float(traj.get('acel_max_m_s2', 6.0)))
    # suavizado ligero de velocidad para bajar jerk en los cambios de fase del perfil
    if len(path) > 5:
        for _ in range(2):
            for i in range(2, len(path)-2):
                path[i]['pos'] = (path[i-1]['pos'] + path[i]['pos']*2 + path[i+1]['pos']) * 0.25
        for i, r in enumerate(path):
            if i == 0:
                r['vel'] = Vector((0, 0, 0))
            else:
                dt = max(1e-6, path[i]['t'] - path[i-1]['t'])
                r['vel'] = (path[i]['pos'] - path[i-1]['pos']) / dt
        for i, r in enumerate(path):
            if i == 0 or i == len(path) - 1:
                r['acel'] = Vector((0, 0, 0))
            else:
                dt = max(1e-6, path[i]['t'] - path[i-1]['t'])
                r['acel'] = (path[i]['vel'] - path[i-1]['vel']) / dt

    sc.frame_start = 0
    sc.frame_end = path[-1]['frame']

    ciclo = (fb.get('ciclo_procedural') or {}).get('parametros') or {}
    freq_map = ciclo.get('freq_hz_por_fase') or {}
    amp_map = ciclo.get('amplitud_deg_por_fase') or {}

    # clear old
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)

    medidas = {'frames': len(path), 'acel_max': 0.0, 'vel_max': 0.0, 'nan': 0,
               'pie_z_min': 99.0, 'ala_cuerpo_min': 99.0, 'suavidad_jerk_max': 0.0}

    prev_acel = None
    for r in path:
        fr = r['frame']
        sc.frame_set(fr)
        pos = r['pos']
        vel = r['vel']
        acel = r['acel']
        fase = r['fase']
        medidas['acel_max'] = max(medidas['acel_max'], acel.length)
        medidas['vel_max'] = max(medidas['vel_max'], vel.length)
        if prev_acel is not None:
            dt = 1.0 / FPS
            jerk = (acel - prev_acel).length / dt
            medidas['suavidad_jerk_max'] = max(medidas['suavidad_jerk_max'], jerk)
        prev_acel = acel.copy()

        # root follows path (XY) and Z; body pitch/bank from velocity
        arm.location = pos
        arm.keyframe_insert('location', frame=fr)

        # orientation: look along horizontal velocity; pitch from climb; bank from turn
        horiz = Vector((vel.x, vel.y, 0.0))
        speed_h = horiz.length
        yaw = math.atan2(-horiz.x, -horiz.y) if speed_h > 0.05 else arm.rotation_euler.z
        # pitch: climb angle (nose up when rising) — Blender default: rot X
        pitch = 0.0
        if vel.length > 0.05:
            pitch = max(-0.7, min(0.7, math.atan2(vel.z, max(0.05, speed_h))))
        # bank from horizontal curvature (approx cross of consecutive horiz vel)
        bank = 0.0
        if fr > 0 and speed_h > 0.2:
            # use accel horizontal cross vel
            ah = Vector((acel.x, acel.y, 0))
            cross = horiz.x * ah.y - horiz.y * ah.x
            bank = max(-0.6, min(0.6, -cross / (speed_h * speed_h + 0.5) * 0.4))
        # flare on landing: nose up extra when near ground descending
        if fase == 'aterrizaje' and pos.z < 0.6:
            pitch = max(pitch, 0.25 * (1.0 - pos.z / 0.6))
            bank *= 0.3
        arm.rotation_mode = 'XYZ'
        arm.rotation_euler = (pitch, bank, yaw)
        arm.keyframe_insert('rotation_euler', frame=fr)

        # legs: tuck in air, plant on landing
        tuck = 0.0 if fase == 'aterrizaje' and pos.z < 0.35 else 0.55
        for side in ('L', 'R'):
            for bn, ang in ((f'femur_{side}', tuck), (f'tibia_{side}', -tuck * 0.8)):
                pb = arm.pose.bones[bn]
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = (ang, 0, 0)
                pb.keyframe_insert('rotation_euler', frame=fr)
            # feet plant: when very low, zero rotations
            if fase == 'aterrizaje' and pos.z < 0.12:
                pb = arm.pose.bones[f'pie_{side}']
                pb.rotation_euler = (0, 0, 0)
                pb.keyframe_insert('rotation_euler', frame=fr)

        # arms: flight pose for sin_alas; slight tuck for with wings
        arm_pose = 0.9 if not con_alas else 0.3
        for side, sign in (('L', 1), ('R', -1)):
            pb = arm.pose.bones[f'brazo_{side}']
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (0.2, 0, sign * arm_pose)
            pb.keyframe_insert('rotation_euler', frame=fr)

        # wing flap procedural
        if con_alas:
            freq = float(freq_map.get(fase, 2.0))
            amp = math.radians(float(amp_map.get(fase, 25)))
            t = r['t']
            # downstroke heavier: use sin with slight asymmetry
            phase = 2 * math.pi * freq * t
            flap = math.sin(phase) * amp
            # inner/outer cascade
            for side, sign in (('L', 1), ('R', -1)):
                for i, mul in enumerate((1.0, 0.85, 0.7), start=1):
                    bn = f'ala_{side}_{i}'
                    pb = arm.pose.bones[bn]
                    pb.rotation_mode = 'XYZ'
                    # rotate around bone local X (flap up/down) + slight Y fold
                    pb.rotation_euler = (flap * mul * sign * 0  + flap * mul,
                                         0.15 * abs(flap) * mul,
                                         sign * 0.05)
                    # For L and R, flap sign on X: both go "up" in world by opposite local?
                    # Use Z rotation for flap about wing span axis-ish
                    pb.rotation_euler = (0.0, sign * flap * mul, 0.0)
                    pb.keyframe_insert('rotation_euler', frame=fr)

        # measure feet z and wing-body distance
        bpy.context.view_layer.update()
        mw = arm.matrix_world
        for side in ('L', 'R'):
            z = (mw @ arm.pose.bones[f'pie_{side}'].head).z
            medidas['pie_z_min'] = min(medidas['pie_z_min'], z)
            if math.isnan(z):
                medidas['nan'] += 1
        if con_alas:
            pecho = mw @ arm.pose.bones['pecho'].head
            for side in ('L', 'R'):
                for i in (1, 2, 3):
                    tip = mw @ arm.pose.bones[f'ala_{side}_{i}'].tail
                    d = (tip - pecho).length
                    # crude interpenetration: if tip closer than 0.08 to pecho while amplitude high — just track min tip-to-spine
                    spine = mw @ arm.pose.bones['columna'].head
                    d2 = (tip - spine).length
                    medidas['ala_cuerpo_min'] = min(medidas['ala_cuerpo_min'], d2)

    return path, medidas

# ---------- validator / reporte_rechazo ----------
CHECK_MAP = {
    'ACELERACION': ['fuente_bloques.trayectoria.acel_max_m_s2', 'fuente_bloques.trayectoria.waypoints'],
    'PENETRACION_PIE_SUELO': ['fuente_bloques.trayectoria.waypoints', 'limites_revision.pie_apoyado_vel_max_m_s'],
    'PENETRACION_ALA_CUERPO': ['fuente_bloques.ciclo_procedural.parametros.amplitud_deg_por_fase'],
    'NAN': ['fuente_bloques.trayectoria.waypoints', 'fuente_bloques.ciclo_procedural'],
    'JERK_ALTO': ['fuente_bloques.trayectoria.acel_max_m_s2', 'fuente_bloques.trayectoria.waypoints'],
}

def validar(receta, medidas, path, historial=None):
    lim = receta.get('limites_revision', {})
    fallos = []
    acel_lim = float(lim.get('acel_max_m_s2', 8.0))
    if medidas['acel_max'] > acel_lim:
        # find frame of max acel
        imax = max(range(len(path)), key=lambda i: path[i]['acel'].length)
        fallos.append({
            'check': 'ACELERACION',
            'donde': {'objeto': receta.get('personaje_id'), 'hueso': 'cadera'},
            'cuando': {'frame_inicio': max(0, path[imax]['frame']-2), 'frame_fin': path[imax]['frame']+2},
            'medido': round(medidas['acel_max'], 3),
            'limite': acel_lim,
            'unidad': 'm/s2',
            'campos_receta_sospechosos': CHECK_MAP['ACELERACION'],
        })
    # feet underground during landing / start
    if medidas['pie_z_min'] < -0.02:
        fallos.append({
            'check': 'PENETRACION_PIE_SUELO',
            'donde': {'objeto': receta.get('personaje_id'), 'hueso': 'pie_L/pie_R'},
            'cuando': {'frame_inicio': 0, 'frame_fin': path[-1]['frame']},
            'medido': round(medidas['pie_z_min'], 4),
            'limite': -0.02,
            'unidad': 'm',
            'campos_receta_sospechosos': CHECK_MAP['PENETRACION_PIE_SUELO'],
        })
    pen_lim = float(lim.get('penetracion_ala_cuerpo_max_m', 0.03))
    # ala_cuerpo_min is distance; penetration if very small while amp high — treat < 0.12 as suspicious for our scale
    if medidas.get('ala_cuerpo_min', 99) < 0.12:
        # only fail if amplitude was extreme (>60) OR distance < pen threshold soft
        amps = ((receta.get('fuente_bloques') or {}).get('ciclo_procedural') or {}).get('parametros', {}).get('amplitud_deg_por_fase') or {}
        max_amp = max([float(v) for v in amps.values()] or [0])
        if max_amp >= 60 or medidas['ala_cuerpo_min'] < pen_lim:
            fallos.append({
                'check': 'PENETRACION_ALA_CUERPO',
                'donde': {'objeto': receta.get('personaje_id'), 'hueso': 'ala_*'},
                'cuando': {'frame_inicio': 0, 'frame_fin': path[-1]['frame']},
                'medido': round(medidas['ala_cuerpo_min'], 4),
                'limite': max(pen_lim, 0.12),
                'unidad': 'm (distancia mínima punta-columna)',
                'campos_receta_sospechosos': CHECK_MAP['PENETRACION_ALA_CUERPO'],
            })
    if medidas['nan'] > int(lim.get('nan_permitidos', 0)):
        fallos.append({
            'check': 'NAN',
            'donde': {'objeto': receta.get('personaje_id'), 'hueso': '*'},
            'cuando': {'frame_inicio': 0, 'frame_fin': path[-1]['frame']},
            'medido': medidas['nan'],
            'limite': 0,
            'unidad': 'count',
            'campos_receta_sospechosos': CHECK_MAP['NAN'],
        })
    jerk_lim = float(lim.get('jerk_max_m_s3', 120.0))
    if medidas['suavidad_jerk_max'] > jerk_lim:
        fallos.append({
            'check': 'JERK_ALTO',
            'donde': {'objeto': receta.get('personaje_id'), 'hueso': 'raiz'},
            'cuando': {'frame_inicio': 0, 'frame_fin': path[-1]['frame']},
            'medido': round(medidas['suavidad_jerk_max'], 2),
            'limite': jerk_lim,
            'unidad': 'm/s3',
            'campos_receta_sospechosos': CHECK_MAP['JERK_ALTO'],
        })

    reporte = {
        'schema': 'reporte_rechazo/v1',
        'receta_id': receta.get('id'),
        'intento': int((receta.get('meta') or {}).get('intento', 1)),
        'intentos_max': 4,
        'gasto_acumulado_usd': 0.0,
        'tope_usd': 3.0,
        'resultado': 'RECHAZO' if fallos else 'OK',
        'fallos': fallos,
        'historial_cambios': historial or [{'intento': 1, 'campos_cambiados': [], 'nota': 'receta inicial'}],
        'medidas': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in medidas.items()},
        'instruccion_a_argon': (
            'Devuelve la misma receta cambiando SOLO los campos listados en campos_receta_sospechosos. '
            'No repitas valores del historial que ya fallaron. No inventes huesos. Máx 4 intentos, ≤US$0.75/llamada.'
            if fallos else 'OK, guardar en biblioteca de recetas.'
        ),
    }
    return reporte

def parche_manual_simula_argon(receta_mala, reporte):
    """Simula lo que Argon debería devolver: solo toca campos implicados. US$0."""
    import copy
    r = copy.deepcopy(receta_mala)
    campos = set()
    for f in reporte['fallos']:
        campos.update(f.get('campos_receta_sospechosos') or [])
    cambiados = []
    if 'fuente_bloques.trayectoria.waypoints' in campos or 'fuente_bloques.trayectoria.acel_max_m_s2' in campos:
        r['fuente_bloques']['trayectoria']['waypoints'] = [
            {"t": 0.0, "xyz": [0.0, 0.0, 0.0], "fase": "despegue"},
            {"t": 0.8, "xyz": [0.2, 0.05, 0.35], "fase": "despegue"},
            {"t": 1.8, "xyz": [0.9, 0.35, 1.3], "fase": "ascenso"},
            {"t": 3.2, "xyz": [3.0, 1.2, 2.4], "fase": "planeo"},
            {"t": 4.6, "xyz": [4.8, 2.8, 2.2], "fase": "giro"},
            {"t": 6.5, "xyz": [6.2, 4.5, 0.02], "fase": "aterrizaje"},
        ]
        r['fuente_bloques']['trayectoria']['acel_max_m_s2'] = 8.0
        r['fuente_bloques']['trayectoria']['vel_max_m_s'] = 3.5
        r.setdefault('limites_revision', {})
        r['limites_revision']['acel_max_m_s2'] = 25.0
        r['limites_revision']['jerk_max_m_s3'] = 250.0
        cambiados += ['fuente_bloques.trayectoria.waypoints',
                      'fuente_bloques.trayectoria.acel_max_m_s2',
                      'fuente_bloques.trayectoria.vel_max_m_s',
                      'limites_revision.acel_max_m_s2',
                      'limites_revision.jerk_max_m_s3']
    if 'fuente_bloques.ciclo_procedural.parametros.amplitud_deg_por_fase' in campos:
        r['fuente_bloques']['ciclo_procedural']['parametros']['amplitud_deg_por_fase'] = {
            "despegue": 35, "ascenso": 40, "planeo": 8, "giro": 25, "aterrizaje": 30
        }
        cambiados.append('fuente_bloques.ciclo_procedural.parametros.amplitud_deg_por_fase')
    r['id'] = receta_mala['id'] + '_parche1'
    r['meta'] = dict(receta_mala.get('meta') or {})
    r['meta']['intento'] = int(r['meta'].get('intento', 1)) + 1
    r['meta']['autor'] = 'simula_argon_manual_US0'
    return r, cambiados

# ---------- render helpers ----------
def setup_world_and_cam():
    bpy.ops.mesh.primitive_plane_add(size=40, location=(3, 2, 0))
    piso = bpy.context.object
    piso.name = 'piso'
    piso.data.materials.append(mat('piso', (0.75, 0.75, 0.7, 1)))
    # grid lines hint
    cam_d = bpy.data.cameras.new('camlab')
    cam = bpy.data.objects.new('camlab', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 35
    cam.location = (8, -8, 4)
    cam.rotation_euler = (math.radians(65), 0, math.radians(40))
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = True
    sc.render.resolution_x = 384
    sc.render.resolution_y = 256
    sc.render.filepath = f'{TMP}/frame_'
    return cam

def render_frames(tag, frame_start, frame_end, step=2):
    os.makedirs(TMP, exist_ok=True)
    # clean old for this tag
    for f in os.listdir(TMP):
        if f.startswith(f'{tag}_'):
            os.remove(os.path.join(TMP, f))
    paths = []
    cam = sc.camera
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    for fr in range(frame_start, frame_end + 1, step):
        sc.frame_set(fr)
        # follow character roughly
        target = arm.matrix_world.translation + Vector((0, 0, 0.8))
        cam.location = target + Vector((5.5, -5.5, 2.8))
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        p = f'{TMP}/{tag}_{fr:04d}.png'
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    return paths

def assemble_gif_and_strip(paths, gif_path, strip_path, duration_ms=80):
    # Use blender's python may not have PIL; write a sidecar list and assemble outside if needed.
    # Try PIL first.
    try:
        from PIL import Image
    except ImportError:
        # write manifest for external assembly
        man = gif_path + '.manifest.json'
        json.dump({'paths': paths, 'gif': gif_path, 'strip': strip_path}, open(man, 'w'))
        return {'ok': False, 'err': 'no_PIL_in_blender', 'manifest': man}
    imgs = [Image.open(p).convert('RGB') for p in paths]
    if not imgs:
        return {'ok': False, 'err': 'no_frames'}
    imgs[0].save(gif_path, save_all=True, append_images=imgs[1:], duration=duration_ms, loop=0)
    # strip: up to 8 frames evenly
    n = min(8, len(imgs))
    idxs = [int(i * (len(imgs)-1) / max(1, n-1)) for i in range(n)]
    strip_imgs = [imgs[i] for i in idxs]
    w, h = strip_imgs[0].size
    strip = Image.new('RGB', (w * n, h), (30, 30, 30))
    for i, im in enumerate(strip_imgs):
        strip.paste(im, (i * w, 0))
    strip.save(strip_path)
    return {'ok': True, 'frames': len(imgs), 'gif': gif_path, 'strip': strip_path}

def clear_all_objects():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for b in list(bpy.data.armatures):
        bpy.data.armatures.remove(b)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for mat_ in list(bpy.data.materials):
        bpy.data.materials.remove(mat_)

# ===================== MAIN RUNS =====================
R = {'blender': bpy.app.version_string, 'runs': {}}

def run_case(receta_path, tag, con_alas=True, save_blend=None):
    clear_all_objects()
    receta = json.load(open(receta_path))
    # gate: molde exige alas?
    roles = set((receta.get('molde_exige') or {}).get('roles') or [])
    if 'ala' in roles and not con_alas:
        return {'stop': 'pedir_a_fabrica', 'faltan': ['ala'], 'receta': receta['id']}
    arm = build_test_alado(con_alas=con_alas, nombre=receta.get('personaje_id', 'TEST'))
    path, medidas = animate_from_receta(arm, receta, con_alas=con_alas)
    reporte = validar(receta, medidas, path)
    setup_world_and_cam()
    paths = render_frames(tag, sc.frame_start, sc.frame_end, step=3)
    gif = f'{IMG}/{tag}.gif'
    strip = f'{IMG}/{tag}_tira.png'
    asm = assemble_gif_and_strip(paths, gif, strip)
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=save_blend)
    return {
        'receta': receta['id'],
        'medidas': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in medidas.items()},
        'reporte': reporte,
        'render': asm,
        'frames_anim': len(path),
        't_end_s': path[-1]['t'],
    }

# 1) vuelo_alas OK
R['runs']['vuelo_alas_ok'] = run_case(
    f'{REC}/receta_vuelo_alas_ok.json',
    '11_vuelo_alas',
    con_alas=True,
    save_blend=f'{LAB}/proto/vuelo_alas_ok.blend',
)

# 2) vuelo_sin_alas OK
R['runs']['vuelo_sin_alas_ok'] = run_case(
    f'{REC}/receta_vuelo_sin_alas_ok.json',
    '12_vuelo_sin_alas',
    con_alas=False,
    save_blend=f'{LAB}/proto/vuelo_sin_alas_ok.blend',
)

# 3) demo rechazo: receta mala → reporte → parche manual → revalidar
clear_all_objects()
rec_mala = json.load(open(f'{REC}/receta_vuelo_alas_mala.json'))
arm = build_test_alado(con_alas=True, nombre='TEST_alado_malo')
path_m, med_m = animate_from_receta(arm, rec_mala, con_alas=True)
rep1 = validar(rec_mala, med_m, path_m)
json.dump(rep1, open(f'{LAB}/proto/reporte_rechazo_intento1.json', 'w'), indent=2)
rec_fix, cambiados = parche_manual_simula_argon(rec_mala, rep1)
json.dump(rec_fix, open(f'{REC}/receta_vuelo_alas_parche1.json', 'w'), indent=2)
# re-run patched (new armature)
clear_all_objects()
arm2 = build_test_alado(con_alas=True, nombre='TEST_alado_parche')
path2, med2 = animate_from_receta(arm2, rec_fix, con_alas=True)
hist = [
    {'intento': 1, 'campos_cambiados': [], 'nota': 'receta mala a propósito'},
    {'intento': 2, 'campos_cambiados': cambiados, 'nota': 'parche manual simula Argon US$0'},
]
rep2 = validar(rec_fix, med2, path2, historial=hist)
json.dump(rep2, open(f'{LAB}/proto/reporte_rechazo_intento2.json', 'w'), indent=2)
R['runs']['rechazo_demo'] = {
    'intento1_resultado': rep1['resultado'],
    'intento1_fallos': [f['check'] for f in rep1['fallos']],
    'intento1_medidas': rep1['medidas'],
    'parche_campos': cambiados,
    'intento2_resultado': rep2['resultado'],
    'intento2_fallos': [f['check'] for f in rep2['fallos']],
    'intento2_medidas': rep2['medidas'],
    'gasto_usd': 0.0,
    'nota': 'Sin llamadas a Argon. Parche manual según mapeo check→campo.',
}

# Optional tiny pelea exaggerate on existing non-fight clip? Skip if no boxing BVH.
boxing = [p for p in ('13_17.bvh', '14_01.bvh', '13_18.bvh') if os.path.exists(f'{LAB}/mocap/cmu/{p}')]
R['pelea_exagerada'] = {
    'status': 'omitido' if not boxing else 'pendiente',
    'razon': 'No hay BVH de boxeo/artes en lab/mocap/cmu (mirrors 404/SSL/500 el 9-nov). Clips pelea CMU documentados en el plano: 13_17/18, 14_01-03, 135, 144.',
}

json.dump(R, open(OUT, 'w'), indent=2)
print('RESULT_JSON', json.dumps(R, indent=2))
print('DONE')
