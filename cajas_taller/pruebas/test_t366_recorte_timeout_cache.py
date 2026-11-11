"""t366u — pruebas GRATIS (sin red, sin Argon/Vertex, sin ledger real) de los 4 arreglos del 4a4:
1) recorte genérico por escenario, 2) tiempo automático, 3) no pagar dos veces, 4) avisos en la bitácora.
Todo en una carpeta temporal; el «Argon» es falso. Uso: <venv>/python test_t366_recorte_timeout_cache.py"""
import os, sys, json, time, tempfile, types
from pathlib import Path
CAJAS = Path('/opt/myia-taller-n8n/cajas'); sys.path.insert(0, str(CAJAS))
TMP = Path(tempfile.mkdtemp(prefix='t366_')); R = {}
import paralelo_cadena as PC, recorte_pedido as RP, llamada_segura as LS
cfg_tmp = TMP / 'llamadas_config.json'; c0 = json.loads(PC.CONFIG.read_text(encoding='utf-8'))
c0['avisos_bitacora'] = dict(c0.get('avisos_bitacora') or {}, archivo=str(TMP / 'BITACORA_PRUEBA.md')); cfg_tmp.write_text(json.dumps(c0), encoding='utf-8')
PC.CONFIG = cfg_tmp   # nunca escribe en la bitácora real

# 1) TIEMPO AUTOMÁTICO
ta = PC.timeout_auto
R['1_timeout'] = {'cocina_recortada_118807c_32768': ta(118807, 32768), 'cocina_vieja_213340c_32768': ta(213340, 32768), 'chico_minimo': ta(1000, 1000),
                  'enorme_maximo': ta(900000, 65536), 'sin_tamano_usa_por_paso': PC.timeout_paso('prompts_escenarios__x'), 'por_paso_config': PC.timeout_fijo('prompts_escenarios__x')}
R['1_timeout']['PASA'] = (R['1_timeout']['chico_minimo'] == 360 and R['1_timeout']['enorme_maximo'] == 1200 and 500 < R['1_timeout']['cocina_recortada_118807c_32768'] < 700
                          and R['1_timeout']['sin_tamano_usa_por_paso'] == R['1_timeout']['por_paso_config'])

# 2) RECORTE GENÉRICO (canal inventado, nada de Guardianes)
rc = json.loads(cfg_tmp.read_text())['recorte_pedido']['pasos']['prompts_escenarios']
escenas = [{'numero': str(i), 'titulo': f'{i}. Escena de prueba {i}', 'escenario_id': 'esc-a' if i < 3 else 'esc-b' if i < 5 else 'esc-c'} for i in range(1, 7)]
g = 'CABECERA\n' + ''.join(f"{e['titulo']}\n" + ('texto ' * 200) + '\n' for e in escenas)
base = {'escenas': [e for e in escenas if e['escenario_id'] == 'esc-b'], 'catalogo_oficial': {'objetos': [{'id': 'obj-1'}, {'id': 'obj-9'}], 'personajes': [{'id': 'ch-1'}]},
        'dudas_resueltas': [{'duda_id': 'd1', 'texto': 'sobre esc-b', 'decision': 'x', 'justificacion': 'larga ' * 50}, {'duda_id': 'd2', 'texto': 'sobre esc-c', 'decision': 'y'}]}
obj = {'objeto_id': 'obj-1', 'forma': {'tipo': 'caja'}, 'apariciones': [{'escena': str(i), 'estado': f'e{i}'} for i in range(1, 7)], 'prompt_imagen': 'P' * 500, 'justificacion': 'J' * 300}
obj_sin = {'objeto_id': 'obj-2', 'forma': {'tipo': 'bola'}, 'apariciones': [{'estado': 'siempre'}]}
nv, inf = RP.recortar_4a4(rc, ['esc-b'], base, {'nombre': 'canal prueba', 'personajes': [{'x': 'y' * 500}], 'datos': {'language': 'es', 'budget_day': 3}},
                          [{'escenario_id': 'esc-b', 'medidas': {'ancho_m': 3}, 'camaras_sugeridas': [1, 2]}], [obj, obj_sin], [], {'imagenes_adjuntas': [], 'moldes': []}, {}, g, escenas)
ap = [a['escena'] for a in nv['inv4b1'][0]['apariciones']]
R['2_recorte'] = {'escenas': inf['escenas'], 'apariciones_obj1': ap, 'obj_sin_escena_se_queda': [a.get('estado') for a in nv['inv4b1'][1]['apariciones']],
                  'dudas_quedan': [d['duda_id'] for d in nv['base'].get('dudas_resueltas', [])], 'guion_antes': len(g), 'guion_despues': len(nv['guion']),
                  'escena3_completa': ('3. Escena de prueba 3\n' + 'texto ' * 200) in nv['guion'], 'escena6_solo_titulo': '6. Escena de prueba 6' in nv['guion'] and nv['guion'].count('texto') < 3 * 200 + 2 * 100,
                  'sin_prompt_imagen': 'prompt_imagen' not in nv['inv4b1'][0], 'config_sin_personajes': 'personajes' not in nv['cfg'], 'medidas_quedan': nv['i4'][0].get('medidas') == {'ancho_m': 3}}
nv2, inf2 = RP.recortar_4a4(rc, ['esc-b'], base, {}, [], [], [], {}, {}, 'GUION SIN TITULOS ' * 50, escenas)
R['2_recorte']['sin_titulos_manda_guion_entero'] = nv2['guion'] == 'GUION SIN TITULOS ' * 50 and bool(inf2['avisos'])
R['2_recorte']['PASA'] = (inf['escenas'] == ['3', '4'] and ap == ['3', '4'] and R['2_recorte']['obj_sin_escena_se_queda'] == ['siempre'] and R['2_recorte']['dudas_quedan'] == ['d1']
                          and R['2_recorte']['escena3_completa'] and R['2_recorte']['escena6_solo_titulo'] and R['2_recorte']['sin_prompt_imagen'] and R['2_recorte']['config_sin_personajes']
                          and R['2_recorte']['medidas_quedan'] and R['2_recorte']['sin_titulos_manda_guion_entero'] and len(nv['guion']) < len(g))

# 3) NO PAGAR DOS VECES (Argon FALSO; ledger falso en memoria)
os.environ['TALLER_DATOS'] = str(TMP)
import paso00_cadena as C
C.TRABAJO = TMP; C.registrar_taller = lambda *a, **k: None
class ArFalso:
    MAX_OUT = 8192
    def __init__(s, modo='ok'): s.modo, s.llamadas, s.filas = modo, [], []
    def total(s): return 0.0
    def _leer(s): return s.filas
    def cotizacion(s, *a, **k): return {}
    def marcar(s, id_, estado, *a, **k):
        for f in s.filas:
            if f['id'] == id_: f['estado'] = estado
    def llamar(s, id_, pr, salida, est, nota, **k):
        s.filas.append({'id': id_, 'estado': 'enviado'}); s.llamadas.append(id_)
        Path(salida).write_text(json.dumps({'ok': True, 'n': len(s.llamadas)}), encoding='utf-8')
        if s.modo == 'timeout_tras_escribir' and len(s.llamadas) == 1: raise LS.LlamadaVencida('se cortó a los 600 s (prueba)')
        return {'usd': 0.1, 'tokens_entrada': 10, 'tokens_salida': 20, 'fin': 'STOP', 'texto': Path(salida).read_text()}
def correr(ar, pr='PEDIDO DE PRUEBA', repetir=False):
    D = TMP / 'cap'
    for z in ('pedidos', 'respuestas', 'resultados'): (D / z).mkdir(parents=True, exist_ok=True)
    a = types.SimpleNamespace(ok=10.0, aprobado='prueba-t366', corrida=None, repetir=repetir, max_intentos=2)
    X = {'AR': ar, 'P': None, 'D': D, 'FP': None, 'F': None, 'e': {'id': 'ep-prueba'}, 'modelo': 'falso', 'nivel': 'HIGH', 'transporte': object()}
    x = {'paso': 'prueba_t366', 'ids': ['esc-x'], '_pr': pr, '_fijo': {'paso': 'fijo_prueba', 'partes': {}}, 'peor_caso_usd': 0.2, '_esquema': None, '_max_out': 1000}
    return C.llamar_uno(a, X, x, 0.75, dormir=lambda s: None)
ar = ArFalso(); r1 = correr(ar); r2 = correr(ar); r3 = correr(ar, pr='OTRO PEDIDO'); r4 = correr(ar, repetir=True)
ar2 = ArFalso('timeout_tras_escribir'); r5 = correr(ar2, pr='PEDIDO QUE SE CORTA')
R['3_no_pagar_dos_veces'] = {'primera': [r1['estado'], r1['usd_real'], len(ar.llamadas)], 'igual_otra_vez': [r2['estado'], r2['usd_real'], bool(r2.get('desde_cache'))],
                             'pedido_distinto_si_paga': r3['usd_real'], 'con_repetir_si_paga': r4['usd_real'], 'llamadas_totales': len(ar.llamadas),
                             'reintento_tras_timeout': [r5['estado'], len(ar2.llamadas), r5.get('reintento_evitado'), r5['usd_posible_cobro']]}
R['3_no_pagar_dos_veces']['PASA'] = (r1['estado'] == 'ok' and r2['estado'] == 'ok' and r2['usd_real'] == 0 and r2.get('desde_cache') and len(ar.llamadas) == 3
                                     and r3['usd_real'] == 0.1 and r4['usd_real'] == 0.1 and r5['estado'] == 'ok' and len(ar2.llamadas) == 1 and r5.get('reintento_evitado'))

# 4) AVISOS EN LA BITÁCORA (archivo de PRUEBA)
f = PC.aviso_bitacora('caja de prueba: tardó 300 s = 83 % del tope de 360 s')
R['4_bitacora'] = {'archivo': f, 'texto': Path(f).read_text(encoding='utf-8') if f else None}
R['4_bitacora']['PASA'] = bool(f) and '83 %' in R['4_bitacora']['texto'] and str(TMP) in f

R['TODAS_PASAN'] = all(v.get('PASA') for v in R.values() if isinstance(v, dict))
R['carpeta_prueba'] = str(TMP); R['usd'] = 0; R['hora'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
