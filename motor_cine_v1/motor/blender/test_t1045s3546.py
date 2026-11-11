"""Pruebas CPU (sin Blender, US$0) de los 3 arreglos t1045s3546."""
import json, sys, math, traceback
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import numeros_json as NJ

fails = []
def check(name, cond, detail=""):
    if cond:
        print(f"  OK  {name}")
    else:
        print(f"  FALLO  {name} {detail}")
        fails.append(name)

print("== 1. a_numero / normalizar_camara ==")
check("int", NJ.a_numero(24, "lente_mm") == 24.0)
check("float", NJ.a_numero(2.5, "distancia_m") == 2.5)
check("str punto", NJ.a_numero("24.0", "lente_mm") == 24.0)
check("str coma", NJ.a_numero("24,5", "lente_mm") == 24.5)
check("sufijo mm en lente", NJ.a_numero("35mm", "lente_mm") == 35.0)
check("sufijo mm en metros", abs(NJ.a_numero("2500mm", "distancia_m") - 2.5) < 1e-9)
check("sufijo cm en metros", abs(NJ.a_numero("180cm", "altura_m") - 1.8) < 1e-9)
check("vacio -> None", NJ.a_numero("", "distancia_m") is None)
check("None -> None", NJ.a_numero(None, "distancia_m") is None)

# placeholder must NOT become 0
r = NJ.a_numero("por medir en 02N", "distancia_m")
check("placeholder distancia -> None, no 0", r is None)

try:
    NJ.a_numero("por medir en 02N", "lente_mm", obligatorio=True)
    check("placeholder lente obligatorio lanza", False)
except NJ.ValorNoNumerico as ex:
    check("placeholder lente obligatorio lanza", "no es un número" in str(ex) or "aún no medido" in str(ex), str(ex))

try:
    NJ.a_numero("abc-xyz", "lente_mm", obligatorio=True)
    check("basura lanza", False)
except NJ.ValorNoNumerico as ex:
    check("basura lanza", "abc-xyz" in str(ex), str(ex))

# live camera JSON from last corrida
cam = json.loads((AQUI / "camara_v1_camara.json").read_text())
CV, avisos = NJ.normalizar_camara(cam)
check("sensor floats", all(isinstance(x, float) for x in CV["sensor_mm"]))
n_none = 0
for v in CV["vinetas"]:
    check(f"{v['vineta']} t_abs floats", all(isinstance(x, float) for x in v["t_abs"]))
    check(f"{v['vineta']} altura_m is None (placeholder)", v.get("altura_m") is None)
    for k in v["keyframes"]:
        check(f"{v['vineta']} lente float", isinstance(k["lente_mm"], float))
        check(f"{v['vineta']} distancia_m is None not str", k["distancia_m"] is None)
        n_none += 1
        check(f"{v['vineta']} t float", isinstance(k["t"], float))
check("avisos de distancia no medible", any("distancia_m" in a for a in avisos), avisos[:3])

# interpolación tipo calc_vineta no debe TypeError
a, b = CV["vinetas"][0]["keyframes"][0], CV["vinetas"][0]["keyframes"][-1]
h = 0.18
da = a["distancia_m"] if a["distancia_m"] is not None else NJ.distancia_desde_plano(a["plano"], a["lente_mm"], h, CV["sensor_mm"][1])
db = b["distancia_m"] if b["distancia_m"] is not None else NJ.distancia_desde_plano(b["plano"], b["lente_mm"], h, CV["sensor_mm"][1])
u2 = 0.5
dist = da + (db - da) * u2
lente = a["lente_mm"] + (b["lente_mm"] - a["lente_mm"]) * u2
check("calc interpola floats", isinstance(dist, float) and dist > 0 and isinstance(lente, float), (dist, lente))

# lente basura en un doc debe fallar al normalizar
bad = {"sensor_mm": [36.0, 20.25], "vinetas": [{"keyframes": [{"t": 0, "lente_mm": "por medir en 02N", "distancia_m": 2.0}]}]}
try:
    NJ.normalizar_camara(bad)
    check("lente placeholder en JSON lanza", False)
except NJ.ValorNoNumerico as ex:
    check("lente placeholder en JSON lanza", "lente_mm" in str(ex), str(ex))

# distancias razonables
d_ws = NJ.distancia_desde_plano("WS", 24.0, 1.16, 20.25)
d_cu = NJ.distancia_desde_plano("CU", 50.0, 1.16, 20.25)
check("WS más lejos que CU (mismo sujeto/lente distinta ok, check WS>0.5)", d_ws > 0.5, d_ws)
# CU 50mm of 1.16m should still be a plausible close-up distance
check("CU distancia positiva", d_cu > 0.2, d_cu)

print("== 2. clip_desde_reposo (contrato, sin Blender) ==")
# The function lives in motor_blender and needs bpy; we replicate the contract here.
class V:  # stand-in
    def __init__(self): pass
    def copy(self): return V()
class Q:
    def copy(self): return Q()

def clip_desde_reposo_contrato(bones, fps=24):
    cuadros = max(1, int(round(fps)))
    poses = [{n: (V(), Q()) for n in bones} for _ in range(cuadros)]
    return {"poses": poses, "P": cuadros, "D": 0.0}, {"fuente": "reposo_del_molde", "cuadros": cuadros}

# Piquito real bone names (from gdc-piquito.blend on 213)
piquito = ['raiz', 'cadera', 'pecho', 'cuello', 'cabeza', 'copete',
           'hombro_L', 'ala_humero_L', 'ala_antebrazo_L', 'ala_mano_L',
           'hombro_R', 'ala_humero_R', 'ala_antebrazo_R', 'ala_mano_R',
           'cola', 'muslo_L', 'tibiotarso_L', 'tarso_L', 'dedos_L',
           'muslo_R', 'tibiotarso_R', 'tarso_R', 'dedos_R']
C, info = clip_desde_reposo_contrato(piquito, 24)
check("P y D del reposo", C["P"] == 24 and C["D"] == 0.0)
check("poses cubren todos los huesos del ave", set(C["poses"][0]) == set(piquito))
check("no exige pie_L/femur", "pie_L" not in C["poses"][0] and "femur_L" not in C["poses"][0])
# human skeleton also works (universal)
humano = ['cadera', 'femur_L', 'femur_R', 'pie_L', 'pie_R', 'cabeza']
C2, _ = clip_desde_reposo_contrato(humano, 30)
check("también sirve a un esqueleto humano", set(C2["poses"][0]) == set(humano) and C2["P"] == 30)

# gate: if clips missing, fill instead of clearing (logic replica)
clips = {}
if "quieto" not in clips or "caminar" not in clips:
    C0, _ = clip_desde_reposo_contrato(piquito, 24)
    for n in ("quieto", "caminar"):
        if n not in clips:
            clips[n] = C0
check("ya no queda clips vacío / no hay STOP", "quieto" in clips and "caminar" in clips)

print("== 3. verificación de salidas (false OK) ==")
# replica of correr_escena gate
def faltan_salidas(root: Path):
    requeridos = ['escena_motor.blend', 'final_camara_sb.mp4', 'revision_vista_amplia.mp4',
                  'revision_planta.mp4', 'REVISION_GRANDE_1920x1080.mp4']
    def _okfile(p, minimo=1024):
        return p.is_file() and p.stat().st_size >= minimo
    return [n for n in requeridos if not _okfile(root / n)]

# last failed corrida unpack on box? may not be here. Simulate.
import tempfile, os
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    # empty dir, pod "ok"
    f = faltan_salidas(d)
    check("sin archivos -> 5 faltantes", len(f) == 5, f)
    (d / "escena_motor.blend").write_bytes(b"x" * 2000)
    (d / "final_camara_sb.mp4").write_bytes(b"x" * 2000)
    f = faltan_salidas(d)
    check("faltan 3 mp4 de revisión", len(f) == 3, f)
    for n in ['revision_vista_amplia.mp4', 'revision_planta.mp4', 'REVISION_GRANDE_1920x1080.mp4']:
        (d / n).write_bytes(b"x" * 2000)
    check("completos -> sin faltantes", faltan_salidas(d) == [])
    # empty file does not count
    (d / "revision_planta.mp4").write_bytes(b"")
    check("mp4 vacío cuenta como falta", "revision_planta.mp4" in faltan_salidas(d))

# pod_motor.sh must exit $RC and reset planta timer
sh = (AQUI / "pod_motor.sh").read_text()
check("pod_motor exit $RC", sh.rstrip().endswith("exit $RC") or "\nexit $RC\n" in sh)
check("pod_motor FALLO_SIN_BLEND", "FALLO_SIN_BLEND" in sh)
check("pod_motor FALLO_SIN_SALIDAS", "FALLO_SIN_SALIDAS" in sh)
# two T1 resets: after final, after amplia (plus the original before final)
check("timer planta se reinicia (T1 after amplia)", sh.count("T1=$(date +%s)") >= 3, sh.count("T1=$(date +%s)"))

# correr_escena estado
ce = (AQUI / "correr_escena.py").read_text()
check("correr marca FALLO_SIN_SALIDAS", "FALLO_SIN_SALIDAS" in ce)
check("correr ya no pone OK solo por R.ok", "est['estado'] = 'OK' if R.get('ok')" not in ce)

# motor_blender hooks
mb = (AQUI / "motor_blender.py").read_text()
check("motor excepthook os._exit", "os._exit(1)" in mb and "sys.excepthook" in mb)
check("motor atexit si no guardó blend", "_MOTOR_OK" in mb and "atexit.register" in mb)
check("no queda el STOP que vaciaba clips", "STOP: plantilla sin clip retargeteable" not in mb)
check("clip_desde_reposo presente", "def clip_desde_reposo" in mb)
check("foot-lock guardado pie_L/pie_R", "pies_ok" in mb)

rm = (AQUI / "render_motor.py").read_text()
check("render excepthook", "sys.excepthook" in rm and "os._exit(1)" in rm)

print()
if fails:
    print(f"FALLOS: {len(fails)}")
    for x in fails:
        print(" -", x)
    sys.exit(1)
print("TODAS LAS PRUEBAS CPU OK")
