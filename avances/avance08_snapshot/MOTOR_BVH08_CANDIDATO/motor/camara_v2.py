#!/usr/bin/env python3
"""MOTOR · cámara v2 (fase 4g, Ricardo t273u). GRATIS (CPU, sin Argon ni GPU). Universal: sin canal/escena/personaje en el código.
Sobre una escena YA ARMADA (paquete/motor_previa/escena.blend) con cámara SB:
  manifiesto espacial + resolutor de cámara + revisión geométrica por toma → PAQUETE/motor_camara_v2/{escena.blend, camara_v2.json}.
  Las tomas que no pasan quedan 'bloqueada' con su motivo; los datos que faltan van a 'faltantes' (campo, módulo, acción).
  Además revisa el máximo por toma (toma_max_s, 10 s por defecto) en el SB recibido: avisa, no parte ni recorta.
Interruptores: contrato_camara_v2.off (aquí: no corre), motor/{manifiesto_espacial,resolver_camara,validacion_camara}.off, max_10s_toma.off.
Uso: camara_v2.py --paquete-dir PK [--run-dir PK/motor_previa] [--salida PK/motor_camara_v2] [--sb-camara RUTA] [--sb-escena RUTA]
Después: render_por_tomas.py --paquete-dir PK --run-dir PK/motor_camara_v2 (sin cambios en render_por_tomas)."""
import argparse, json, subprocess, sys, datetime
from pathlib import Path
A = Path(__file__).resolve().parent
def out(d, c=0): print(json.dumps(d, ensure_ascii=False)); sys.exit(c)
def leer(p, d=None):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception: return d
p = argparse.ArgumentParser()
for k in ['--paquete-dir', '--run-dir', '--salida', '--sb-camara', '--sb-escena', '--blender']: p.add_argument(k)
a = p.parse_args()
if (A / 'contrato_camara_v2.off').exists(): out({'ok': False, 'error': 'DESACTIVADO por contrato_camara_v2.off (camino anterior: cámara de motor/camara.py)'})
RT = leer(A / 'rutas.json', {}) or {}; CFG = leer(A / 'motor/camara_v2_config.json')
if not CFG: out({'ok': False, 'error': 'falta motor/camara_v2_config.json'}, 1)
pk = Path(a.paquete_dir); run = Path(a.run_dir) if a.run_dir else pk / 'motor_previa'; sal = Path(a.salida) if a.salida else pk / 'motor_camara_v2'
E = leer(pk / 'entrada.json'); res = leer(pk / 'preparar_resultado.json', {}) or {}
if not E or not (run / 'escena.blend').is_file(): out({'ok': False, 'error': 'falta entrada.json o escena.blend armada', 'run_dir': str(run)}, 1)
taller = Path((leer(Path(RT.get('preparar', '')) / 'config.json', {}) or {}).get('taller', '/nonexistent'))
esc = str(res.get('escena') or pk.parent.name.replace('esc_', ''))
D = taller / 'trabajo/paso00_cadena' / str(res.get('canal')) / str(res.get('capitulo')) / 'cubos/SB'
sbc = Path(a.sb_camara) if a.sb_camara else D / 'blender' / f'esc_{esc}_camara.json'
sbe = Path(a.sb_escena) if a.sb_escena else D / f'esc_{esc}.json'
aj = taller / 'cajas/storyboard/config/ajustes_sb.json'
SBC = leer(sbc)
if not SBC or not SBC.get('vinetas'):
    out({'ok': False, 'error': 'no hay cámara SB para esta escena', 'faltante': {'campo': 'camera/shots', 'modulo': 'SB · traducir', 'ruta': str(sbc), 'accion': 'correr SB'}}, 1)
# máximo por toma (también para SB antiguos): avisa, no parte
largas = []
if not (A / 'max_10s_toma.off').exists():
    mx = float(RT.get('toma_max_s', CFG.get('toma_max_s', 10)))
    for v in SBC['vinetas']:
        d = float(v['t_abs'][1]) - float(v['t_abs'][0])
        if d > mx + 1e-9: largas.append({'vineta': v['vineta'], 'dur_s': round(d, 3), 'max_s': mx, 'accion': 'SB: subdividir la viñeta sin partir diálogos (no se recorta aquí)'})
BL = a.blender or RT.get('blender') or 'blender'; sal.mkdir(parents=True, exist_ok=True); t = datetime.datetime.now()
# TODOS los comandos del SB, leídos con la gramática DSL real del SB (sb_comun.analizar/comandos), para que ninguno quede en silencio
cmds = {}; err_dsl = None; SBE = leer(sbe, {}) or {}
try:
    sys.path.insert(0, str(taller / 'cajas/storyboard')); import sb_comun as SC
    for v in SBE.get('vinetas', []):
        di = v.get('director_imagen') or {}; dc = v.get('director_camara') or {}
        enc = [[c, ar] for (_, _, c, ar) in SC.comandos(SC.analizar(di.get('dsl_encuadre') or ''))] if di.get('dsl_encuadre') else []
        mov = [[t0_, t1_, c, ar] for (t0_, t1_, c, ar) in SC.comandos(SC.analizar(dc.get('dsl_movimiento') or ''))] if dc.get('dsl_movimiento') else []
        cmds[v['id']] = {'encuadre': enc, 'movimiento': mov}
except Exception as ex: err_dsl = f'no se pudo leer el DSL con sb_comun: {ex}'
(sal / 'comandos_sb.json').write_text(json.dumps(cmds, ensure_ascii=False, indent=1, default=str))
prep_cfg = Path(RT.get('preparar', '')) / 'config.json'; tp05 = taller / 'cajas/paso01_datos/tipos_plano.json'
r = subprocess.run([BL, '-b', str(run / 'escena.blend'), '-P', str(A / 'motor/camara_v2_blender.py'), '--', str(pk / 'entrada.json'), str(sbc),
                    str(sbe) if sbe.is_file() else '-', str(A / 'motor/camara_v2_config.json'), str(aj), str(sal), str(sal / 'comandos_sb.json'), str(prep_cfg) if prep_cfg.is_file() else '-', str(tp05) if tp05.is_file() else '-'], capture_output=True, text=True, timeout=int(RT.get('tope_segundos_paso', 10800)))
(sal / 'camara_v2.log').write_text(r.stdout[-20000:] + '\n--- stderr ---\n' + r.stderr[-8000:])
if 'CAMARA_V2_OK' not in r.stdout: out({'ok': False, 'error': 'camara_v2_blender falló', 'log': str(sal / 'camara_v2.log'), 'cola': (r.stdout + r.stderr)[-1200:]}, 1)
R = leer(sal / 'camara_v2.json'); R['tomas_largas'] = largas; R['fuentes'] = {'sb_camara': str(sbc), 'sb_escena': str(sbe) if sbe.is_file() else None, 'ajustes_sb': str(aj), 'escena_armada': str(run / 'escena.blend')}
R['error_dsl'] = err_dsl; R['segundos'] = round((datetime.datetime.now() - t).total_seconds(), 1); (sal / 'camara_v2.json').write_text(json.dumps(R, ensure_ascii=False, indent=1))
out({'ok': True, 'salida': str(sal), 'resumen': R['resumen'], 'faltantes': len(R['faltantes']), 'avisos': len(R['avisos']), 'tomas_largas': largas, 'segundos': R['segundos'],
     'estados': {t['toma']: (t['estado'], t['motivos']) for t in R['tomas']}})
