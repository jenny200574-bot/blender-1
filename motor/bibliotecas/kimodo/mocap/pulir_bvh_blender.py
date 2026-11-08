"""Blender polish: suaviza cadera XZ y bloquea pies/manos en contacto con IK, exporta BVH.
Universal (umbrales relativos a altura). Apache-2.0 ideas de feet.py (NVIDIA).
Uso: blender -b -P pulir_bvh_blender.py -- in.bvh out.bvh [margin_m=0.06] [mode=all|smooth|ik]
"""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Euler
import numpy as np

# Suavizado numpy puro (misma energía que NVIDIA: min ||Ax||^2 + w||x-x0||^2 + proyección a margen)
A = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = Path(A[0]), Path(A[1])
MARGIN = float(A[2]) if len(A) > 2 else 0.06
MODE = A[3] if len(A) > 3 else "all"  # all|smooth|ik

def smooth_signal(x, margins, pos_weight=0.1, smooth_weight=100.0):
    x = np.asarray(x, float); margins = np.asarray(margins, float)
    N, D = x.shape
    if N < 3:
        return x.copy()
    A = np.zeros((N - 2, N))
    for i in range(N - 2):
        A[i, i] = 1.0; A[i, i + 1] = -2.0; A[i, i + 2] = 1.0
    M = smooth_weight * (A.T @ A) + pos_weight * np.eye(N)
    out = np.zeros_like(x)
    for d in range(D):
        out[:, d] = np.linalg.solve(M, pos_weight * x[:, d])
    diff = out - x
    nrm = np.linalg.norm(diff, axis=1)
    m = nrm > margins
    if np.any(m):
        out[m] = x[m] + diff[m] * (margins[m] / (nrm[m] + 1e-8))[:, None]
    return out

# Clean scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_anim.bvh(filepath=str(SRC), axis_forward="-Z", axis_up="Y", rotate_mode="NATIVE", update_scene_fps=False, update_scene_duration=True)
M = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
sc = bpy.context.scene
act = M.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
sc.frame_start, sc.frame_end = f0, f1

def bone_world(name):
    return M.matrix_world @ M.pose.bones[name].head

# Identify EE
feet = [n for n in ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase") if n in M.pose.bones]
hands = [n for n in ("LeftHand", "RightHand") if n in M.pose.bones]
ees = feet + hands
hips_n = "Hips" if "Hips" in M.pose.bones else "Root"

# Sample
T = f1 - f0 + 1
hips = np.zeros((T, 3))
ee = np.zeros((T, len(ees), 3))
for i, f in enumerate(range(f0, f1 + 1)):
    sc.frame_set(f); bpy.context.view_layer.update()
    hips[i] = bone_world(hips_n)
    for j, n in enumerate(ees):
        ee[i, j] = bone_world(n)

# Blender Z-up: height = Z. Horizontal = XY
char_h = max(float(np.percentile(hips[:, 2], 95)), 0.5)
# If units cm
unit = 0.01 if char_h > 3 else 1.0
char_h_m = char_h * unit
vel_thres = 0.25 / unit  # Blender units / s
height_thresh = max(0.05 / unit, 0.10 * char_h)

dt = 1.0 / max(sc.render.fps, 1)
# Prefer frame_time from BVH ~30fps
dt = (1.0 / 30.0)

vel = np.zeros_like(ee)
vel[1:] = (ee[1:] - ee[:-1]) / dt
speed = np.linalg.norm(vel, axis=-1)
# height above lowest point of that EE over clip
base = ee[:, :, 2].min(axis=0)
height = ee[:, :, 2] - base
contacts = (speed < vel_thres) & (height < height_thresh)

report = {"ees": ees, "contact_rate": contacts.mean(0).tolist(), "char_h": char_h, "unit": unit, "mode": MODE}

# Smooth hips horizontal (XY in Blender) with margin in blender units
if MODE in ("all", "smooth"):
    margins = np.full(T, MARGIN / unit)
    sm = smooth_signal(hips[:, :2], margins, pos_weight=0.02)
    # Write hip location keys — BVH hips may be pose bone; armature object often identity
    # In BVH import, locations are on pose bones as fcurves
    pb = M.pose.bones[hips_n]
    # Ensure we can set location
    pb.bone.use_local_location = True
    for i, f in enumerate(range(f0, f1 + 1)):
        sc.frame_set(f)
        # delta in world XY
        cur = bone_world(hips_n)
        dxy = Vector((sm[i, 0] - cur.x, sm[i, 1] - cur.y, 0))
        # apply via armature object location (affects all)
        M.location = M.location + dxy
        M.keyframe_insert("location", frame=f)
    report["smooth"] = True
else:
    report["smooth"] = False

# IK lock: create empties as targets, constrain shin/forearm
if MODE in ("all", "ik"):
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = M
    # Map EE -> IK bone (shin/forearm parent chain)
    ik_map = {
        "LeftFoot": "LeftShin", "LeftToeBase": "LeftShin",
        "RightFoot": "RightShin", "RightToeBase": "RightShin",
        "LeftHand": "LeftForeArm", "RightHand": "RightForeArm",
    }
    # Prefer Foot over Toe for IK target
    primary = []
    for n in ("LeftFoot", "RightFoot", "LeftHand", "RightHand"):
        if n in ees:
            primary.append(n)
    targets = {}
    for n in primary:
        e = bpy.data.objects.new(f"tgt_{n}", None)
        bpy.context.collection.objects.link(e)
        e.empty_display_size = 0.05 / unit if unit == 0.01 else 0.05
        targets[n] = e
    # Set target positions: freeze XY during contact segments, keep Z free-ish
    for j, n in enumerate(primary):
        j_ee = ees.index(n)
        eobj = targets[n]
        t = 0
        while t < T:
            if not contacts[t, j_ee]:
                # follow live
                eobj.location = Vector(ee[t, j_ee])
                eobj.keyframe_insert("location", frame=f0 + t)
                t += 1
                continue
            t0 = t
            while t < T and contacts[t, j_ee]:
                t += 1
            anchor_xy = ee[t0, j_ee, :2].copy()
            for i in range(t0, t):
                loc = Vector((anchor_xy[0], anchor_xy[1], ee[i, j_ee, 2]))
                eobj.location = loc
                eobj.keyframe_insert("location", frame=f0 + i)
    # Add IK constraints
    bpy.context.view_layer.objects.active = M
    bpy.ops.object.mode_set(mode="POSE")
    for n, eobj in targets.items():
        ib = ik_map.get(n)
        if not ib or ib not in M.pose.bones:
            continue
        pb = M.pose.bones[ib]
        c = pb.constraints.new("IK")
        c.target = eobj
        c.chain_count = 2
        c.influence = 1.0
    bpy.ops.object.mode_set(mode="OBJECT")
    # Bake visual transforms to pose
    bpy.context.view_layer.objects.active = M
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(
        frame_start=f0, frame_end=f1,
        only_selected=False, visual_keying=True, clear_constraints=True,
        use_current_action=True, bake_types={"POSE"},
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    # remove empties
    for eobj in targets.values():
        bpy.data.objects.remove(eobj, do_unlink=True)
    report["ik"] = True
else:
    report["ik"] = False

# Export BVH
DST.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_anim.bvh(
    filepath=str(DST),
    check_existing=False,
    global_scale=1.0,
    frame_start=f0,
    frame_end=f1,
    root_transform_only=False,
)
(Path(str(DST) + ".report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2))
print("PULIR_BVH_OK", DST, report.get("contact_rate"))
