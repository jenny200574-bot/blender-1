import json, hashlib, shutil, csv, re, zipfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path('/opt/myia-motor-v9/avance07_20261107'); E=R/'entrega'; P=R/'esc1_candidata'; B=R/'esc1_antes'
def load(p):return json.loads(p.read_text())
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def out(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
tests=[]
def ck(n,v):
 tests.append({'test':n,'passed':bool(v)})
 if not v:raise AssertionError(n)
g=load(E/'evidencias/prevalidacion_cpu07_entrega_resultado.json'); l=load(E/'evidencias/ledger.json'); d=load(P/'entrada_escena.json'); b=load(B/'entrada_escena.json')
ck('7 bloqueos reales; no preview completo, master o GPU',g['faltantes']==7 and not g['master'] and not g['full_cpu_preview_passed'] and not g['gpu_used'])
for n in ['respuesta_2b.json','catalogo_poses_escena.json','asignacion_para_motor.json','source_01.json','source_01_integral.json','programa_2b.json']:
 ck('original intacto '+n,h(P/n)==h(B/n))
ck('motion no sustituido ni aprobado',d['motion']==b['motion'])
pi=lambda x:next(e for e in x['entities'] if e['id']=='ch-piquito-030a')
ck('Piquito rig/perfil intacto',pi(d)==pi(b))
ck('solo 3 reglas con fuente',d['rules_source']=={'com_accel_max_m_s2':20,'joint_speed_max_deg_s':600,'slip_max_m_per_frame':.05})
a=load(E/'evidencias/assets_blender_refinado07.json'); v=load(E/'evidencias/vivo_assets_cpu_refinado07.json')
ck('4 activos reales con dimensiones y mallas cerradas',a['passed'] and len(a['checks'])==4 and all(c['passed'] and not c['nonmanifold_parts'] for c in a['checks']))
ck('54 estados ejecutados, 5 omitidos honestamente',v['assertions_verified']==54 and len(v['skipped_actor_assertions'])==5 and v['checks']['all_passed'] and not v['full_esc1_preview_passed'])
r6=Path('/opt/myia-motor-v9/avance06_20261107/MOTOR_UNICO_20261107'); r7=R/'MOTOR_UNICO_20261107'
files=list(r6.rglob('*.py')); changed=[str(p.relative_to(r6)) for p in files if not (r7/p.relative_to(r6)).exists() or h(p)!=h(r7/p.relative_to(r6))]
ck('todos los Python del motor intactos',len(files)>0 and not changed)
p0=load(R/'respaldos/politica_busqueda_formas_antes_MESH.json');p1=load(r7/'bibliotecas/politica_busqueda_formas_cpu.json')
def diffs(a,b,path=''):
 if type(a)!=type(b):return [path]
 if isinstance(a,dict):return sum([diffs(a.get(k),b.get(k),path+'/'+k) for k in a.keys()|b.keys()],[])
 return [] if a==b else [path]
policy_diff=diffs(p0,p1)
ck('umbral de formas sin cambio',p0.get('minimum_score')==p1.get('minimum_score'))
gold=load(R/'oro_av07_fixture_correcto/metricas_oro.json')
ck('oro 23/23 mismo fixture',gold['all_equal'] and gold['count']==23 and gold['package_sha256']=='432cb20629d5d17fb0190433ca916b9f5eb81f5dac366fdfee75555c3a968aa1')
ck('14 asientos previos, reservas cero y presupuesto',len(l['entries'])==14 and l['reserved_usd']==0 and l['step_gross_usd']<10 and l['step_gross_usd']+l['previous_plan_gross_usd']<50 and all(x['date_bogota']<x['settled_bogota'] for x in l['entries']))
c=load(E/'evidencias/cierre_gasto07.json');ck('guardas off y prueba negativa sin gasto',c['passed'] and c['negative_off_test_rejected_before_network'] and c['ledger_unchanged_by_negative_test'])
out(E/'evidencias/integridad_entrega07.json',{'passed':True,'tests':tests,'engine_python_files_compared':len(files),'policy_diff_paths':policy_diff,'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat()})
shutil.copy2(R/'oro_av07_fixture_correcto/metricas_oro.json',E/'evidencias/oro_23_23.json')
with (E/'7_BLOQUEOS_ESC1.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=['codigo','campo','modulo','mensaje']);w.writeheader();w.writerows({k:x[k] for k in w.fieldnames} for x in g['errores'])
(E/'modelos/LEER_PRIMERO.md').write_text('Borradores conservados, superados por modelos_refinados/. No son el resultado final ni video de esc1.\n')
(E/'INFORME_AVANCE_07.md').write_text("""# AVANCE_07 — cierre 7 noviembre 2026, Bogotá (UTC-5)
## Resultado y alcance
Esc1 baja de 15 a **7 bloqueos**. Sigue BLOQUEADO: no hay preview CPU completo aprobado, master ni video. No se reanudó, detuvo, creó ni eliminó ningún pod. RunPod mantiene como último antecedente HTTP403; no se repitió ni se buscó un rodeo esta fase. GPU US$0.

## Cambios comprobados
- Esquemas Vertex JSON tipados, correcciones y composición sin falsos alias: cuatro fichas ADN **locales** para los IDs exactos de libro, visor, ventana y tapete de este capítulo; medidas de 4b1/4a2 existentes. No se declararon equivalentes a los sellos globales antiguos: las revisiones del libro/visor difieren. La geometría nueva es diseño GENERADO, no medición certificada.
- Libro refinado después de rechazar visualmente páginas que parecían platos: páginas curvas cerradas y letras separadas. Cuatro activos construidos realmente con Blender CPU, medidas verificadas y sin partes no-manifold.
- Escenario vivo: 27 pistas/59 aserciones declaradas. Tres letras vuelan/desaparecen, siete bandas de arcoíris se tornan grises, cuatro efectos descienden y desaparecen, cofre cerrado con tres candados completos. 54 aserciones reales de activos PASAN; 5 de actores se omiten explícitamente porque la escena completa no puede construirse. No se sustituyeron personajes por EMPTY ni se certificó física.
- Tres reglas recuperadas de fuente vigente: aceleración COM20 m/s², velocidad articular600°/s y deslizamiento0.05m/cuadro. Ningún valor físico faltante se inventó; el margen global0.06m no se convirtió en margen de Piquito.
- Ejes del escenario m/Z/+Y documentados desde fuente y contraste de medidas, sin afirmar certificación metrológica de Blender (unit_system NONE). No valida automáticamente ejes anatómicos o 2B.
- Integración mínima: MESH añadido solo a allowlist de copia nueva del motor; backend y validador ya lo soportaban. Ningún Python del motor modificado. action_id exactos a6..a10 evitan escritores duplicados; detección de conflictos intacta. Oro23/23 con fixture y tolerancias originales.
- n8n leído y respaldado privadamente; no modificado en AV07. Sigue activo/publicado con versión06d22a09-e7fa-40ff-9335-d81b6222a995. Compatibilidad JSON de pago de AV06 sigue publicada; no afirmar nueva conexión automática AV07.

## Costes y cierre seguro
Argon/Vertex gemini-3-flash-preview global: **US$0.1925595 bruto** esta fase; acumulado registrado **US$0.6690880 bruto**. 14 solicitudes con asiento/reserva previos:13 respuestas con uso y1 HTTP400 sin cargo de tokens registrado. Cálculo con usageMetadata y tarifa aplicada, no factura conciliada. Neto esperado US$0 por créditos, no verificado en factura. Reservas abiertas0; cap faseUS$10, plan~US$50. Generador, pago y recetas automáticas quedan .off; prueba negativa confirma rechazo antes de red y ledger inalterado.

## Siete bloqueos (CSV y evidencia JSON adjuntos)
1. Respuesta2B original truncada MAX_TOKENS.
2. Lista explícita completa de contactos/anclas no recibida.
3. Siete parámetros físicos vigentes faltantes: allowed_collision_pairs, bone_length_error_m, colliders, penetration_tolerance_m, reject_surface_intersections, root_accel_max_m_s2, root_speed_max_m_s.
4. Piquito sin balance_margin_m vigente; rig estático19 huesos/40 partes previo no implica anclaje funcional.
5. Quince movimientos sin validación/aprobación técnica comprobable.
6. 2B permanece provisional.
7. Programa de movimiento completo no acreditado.

**No son siete simples números:** varios son contratos/listas y aprobaciones. Hombro IZQUIERDO de Eco y tiempos0..55 ya constan; no pedirlos otra vez. Falta enlazar punto ejecutable Star, marco/offset/rotación métricos y apoyos/modos/intervalos. Medir/parametrizar eso es trabajo técnico, no nueva decisión artística de Ricardo.

## Lo que sí necesita Ricardo
Aportar/localizar la respuesta2B íntegra o decidir cómo obtener una fuente autorizada nueva si la cola original no existe en las rutas buscadas, manteniendo la restricción de no inventar2B. Identificar/autorizar la fuente vigente del perfil físico de ave y las siete reglas/listas faltantes, y el responsable de aprobar movimientos tras prueba técnica. No sustituir aprobación comprobada por un 'approved=true' escrito por el modelo.
Solo tras resolver fuentes, ejecutar validación técnica de movimientos/anclas y preflight0, luego preview CPU gratuito. Revisar también colocación en conjunto: las pruebas entregadas son aisladas; hay indicios previos de ambigüedad centro/esquina en ventana/tapete del molde. No se corrigieron mediante posiciones supuestas ni se aprobó colocación/intersecciones del escenario completo.

## Respaldos / rutas para retomar
Servidor${VPS_HOST}: /opt/myia-motor-v9/avance07_20261107/
Candidata: esc1_candidata/; motor independiente: MOTOR_UNICO_20261107/.
Respaldos: esc1_antes/, esc1_antes_aplicar07/, esc1_antes_integracion07/, esc1_antes_refinar_libro07/ y respaldos/ (incluye politica_busqueda_formas_antes_MESH.json y generar_schema_antes_cierre07.py).
Snapshot n8n privado en box:/workspace/avance07/n8n/workflow_leido_privado.json (0600, excluido de entrega). Solo metadata pública adjunta.
No se alteraron T317,24_TRASPASO,v9_universal_calidad_20261106,/opt/video-studio, el otro VPS ni el pod prohibido. No borrados. No se empaquetan credenciales ni backups privados.

## Qué abrir
modelos_refinados/asset_0.png libro;1 tapete;2 visor;3 ventana. .blend correspondientes son prototipos/activos, **NO video de esc1**. esc1_candidata/ conserva datos y fuentes con bloqueos. evidencias/ contiene llamadas, validaciones, ledger y oro. modelos/ conserva borradores superados.
""",encoding='utf-8')
(E/'2B_FALTANTE_EXACTO.md').write_text("""# Fuente2B incompleta; no rellenada
Original respuesta_2b.json conservado byte a byte. Solo35 asignaciones completas. La siguiente (índice35) comienza con Eco/segmento_01_ch-eco-eff3_2/m_caminar_ciclo/t0=30 y se corta en t1 (error cadena sin terminar en posición37942).
Recuperación histórica:17poses,15movimientos,52asignaciones. Sus17 asignaciones adicionales no son cola original: Eco segmentos2(parcial),3,4,5+a16,a19,a23; Pintor segmentos0..5+a9,a12,a20,a24. No se aplicaron como fuente íntegra.
Falta cola2B autorizada: mapping movimiento/capas/huesos y cierre de asignaciones; iniciales/anclas/faltantes originales no recibidos. Arrays vacíos del recuperador son inicialización, no fuente de ausencia. Los tiempos ya están en01; no hacen falta tiempos inventados.
Fuentes consultadas: candidata respuesta_2b.json; recuperación histórica AV06/fuentes/respuesta_2b_ingresada.json; source_01_integral.json; rutas del capítulo /opt/myia-taller-n8n/trabajo/paso00_cadena/cn-los-guardianes-de-la-9fb323be/cap01_ep-89b93118ad/. No afirmar que no exista otra copia fuera de rutas investigadas.
Ver evidencias/2b_original_y_derivaciones.json para listado exacto.
""",encoding='utf-8')
(E/'CONTINUAR_AQUI.md').write_text('Leer INFORME_AVANCE_07.md y7_BLOQUEOS_ESC1.csv. No reabrir guardas .off sin ledger y propósito aprobado. No generar2B ni certificar perfiles con supuestos. Recuperar fuentes primero; validar movimientos/anclas; preflight cero antes de preview CPU completo; solo si pasa y acceso RunPod permitido, resume pul0wcedwdkwm7, render, copia video y stop, nunca terminate/delete. Ante403 detenerse. La candidata final está en servidor avance07/esc1_candidata; esta entrega no sustituye el motor completo.\n')
# Independent delivery copy; refuse overwriting prior package.
D=R/'AVANCE_07';assert not D.exists();shutil.copytree(E,D)
shutil.copytree(P,D/'esc1_candidata')
# Secret patterns are checked without revealing any matching bytes.
patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'AIza[0-9A-Za-z_-]{30,}',rb'"private_key"\s*:\s*"[^" ]{10,}']
for p in D.rglob('*'):
 if p.is_file():
  raw=p.read_bytes()
  if any(re.search(q,raw) for q in patterns):raise RuntimeError('Secret scan failed; packaging stopped')
files=sorted(p for p in D.rglob('*') if p.is_file())
(D/'SHA256SUMS.txt').write_text(''.join(h(p)+'  '+p.relative_to(D).as_posix()+'\n' for p in files))
z=R/'AVANCE_07_ENTREGA.zip';assert not z.exists()
with zipfile.ZipFile(z,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as f:
 for p in D.rglob('*'):
  if p.is_file():f.write(p,p.relative_to(R))
print(json.dumps({'tests':len(tests),'passed':True,'archive':str(z),'bytes':z.stat().st_size,'sha256':h(z),'files':len(files)+1}))
