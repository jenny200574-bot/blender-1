import json,hashlib,shutil,zipfile,re,csv,sys,subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path('/opt/myia-motor-v9/avance08_20261107');E=R/'entrega';P=R/'esc1_bvh08';M=R/'MOTOR_BVH08_CANDIDATO';M0=R/'MOTOR_UNICO_20261107';O=R/'preview_cpu_bvh08';B=R/'esc1_antes';read=lambda p:json.loads(p.read_text());h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
assert (E/'evidencias/preview_cpu_bvh08_resultado.json').exists();assert (R/'oro_bvh08_final/metricas_oro.json').exists()
x=read(E/'evidencias/preview_cpu_bvh08_resultado.json');g=read(R/'oro_bvh08_final/metricas_oro.json');l=read(E/'evidencias/ledger.json');d=read(P/'entrada_escena.json');old=read(B/'entrada_escena.json');checks=[]
def ck(name,condition):
 checks.append({'test':name,'passed':bool(condition)})
 if not condition:raise AssertionError(name)
ck('native data preflight0',read(E/'evidencias/preflight_bvh08.json')['faltantes']==0)
ck('oro23/23 original fixture',g['all_equal'] and g['count']==23 and g['package_sha256']=='432cb20629d5d17fb0190433ca916b9f5eb81f5dac366fdfee75555c3a968aa1')
for n in ['source_01.json','source_01_integral.json','set.blend','adn_manifest.json','inventario_set_medido.json']:ck('source preserved '+n,h(P/n)==h(B/n))
ck('truncated original archived',h(P/'archivo/respuesta_2b_truncada_pre08.json')==h(B/'respuesta_2b.json'))
rows=read(P/'asignacion_para_motor.json');before=read(B/'asignacion_para_motor.json');ck('52 exact source tuples',len(rows)==52 and all(all(a.get(k)==b.get(k) for k in ['personaje','accion_plan','t0','t1','capa']) for a,b in zip(rows,before)))
ck('complete new response explicitly reconstructed',read(P/'respuesta_2b.json')['reconstruction08'] and read(P/'programa_2b.json')['status']=='complete')
ck('15 native CPU pose trials, no model approval',read(P/'movimientos08_prevalidacion_cpu.json')['passed'] and read(P/'movimientos08_prevalidacion_cpu.json')['unique_used_movements']==15 and read(P/'movimientos08_prevalidacion_cpu.json')['model_approval_used'] is False)
ck('physics bounds and negative tests',read(P/'physics08_sanity_final.json')['passed'] and all(a['rejected'] for a in read(P/'physics08_sanity_final.json')['negative_tests']))
ck('3 fixed rules preserved',all(d['rules_source'][k]==v for k,v in {'com_accel_max_m_s2':20,'joint_speed_max_deg_s':600,'slip_max_m_per_frame':.05}.items()))
ck('full CPU made no paid calls',x['paid_calls']==0 and x['ledger_unchanged'])
ck('cap and ledger closed',l['step_gross_usd']<10 and l['previous_plan_gross_usd']+l['step_gross_usd']<50 and l['reserved_usd']==0 and all(a['date_bogota']<a['settled_bogota'] for a in l['entries']))
files=list((Path('/opt/myia-motor-v9/avance07_20261107/MOTOR_UNICO_20261107')).rglob('*.py'));base=Path('/opt/myia-motor-v9/avance07_20261107/MOTOR_UNICO_20261107');ck('original independent engine Python preserved',all(h(p)==h(M0/p.relative_to(base)) for p in files));changes=[str(p.relative_to(base)) for p in files if h(p)!=h(M/p.relative_to(base))];ck('only reviewed BVH validator changed',changes==['motor/fisica_final.py']);ck('BVH11 negative and boundary tests',read(E/'evidencias/bvh08_regresion11.json')['passed']);ck('exact static environment native unit',read(E/'evidencias/colision_estatica08_final.json')['all_passed']);ck('immutable completed core retained',x['core_unchanged']);ck('tested module matches final CPU and gold',x['module_unchanged'] and x['module_sha256']==h(M/'motor/fisica_final.py')==read(E/'evidencias/bvh08_regresion11.json')['module_sha256']==read(E/'evidencias/oro_bvh08_codigo_vinculado.json')['code']['motor/fisica_final.py'])
for rel in ['config/preset_cpu.json','config/politica_ejecucion.json']:ck('config preserved '+rel,h(M/rel)==h(base/rel))
ck('manual generator flag remains off',(E/'config/generador.off').exists());lh=h(E/'evidencias/ledger.json');neg=subprocess.run([sys.executable,str(E/'codigo/generar_schema.py'),'av08_off_negative_test'],capture_output=True);ck('closed generator rejects before ledger/network',neg.returncode!=0 and lh==h(E/'evidencias/ledger.json') and not (E/'evidencias/av08_off_negative_test').exists())
save(E/'evidencias/integridad08.json',{'passed':True,'checks':checks,'date_bogota':datetime.now(ZoneInfo('America/Bogota')).isoformat(),'engine_files_compared':len(files)})
shutil.copy2(R/'oro_bvh08_final/metricas_oro.json',E/'evidencias/oro23_23.json')
for name in ['worker_resultado.json','revision_final.json','etapas_worker.json','resultado.json','etapas.json','constructor.log','nucleo_resultado.json','worker_manifiesto.json']:
 src=O/name
 if not src.exists():src=R/'preview_cpu08/nucleo'/name
 if src.exists():shutil.copy2(src,E/'evidencias'/('cpu_bvh_'+name))
# Keep diagnostic artefacts, never claim an unapproved video as final.
video=x.get('master')
if x['full_cpu_preview_passed'] and video:
 src=Path(video)
 if not src.is_absolute():src=O/video
 if src.exists():shutil.copy2(src,E/src.name)
with (E/'BLOQUEOS_O_ERRORES_CPU.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['codigo','campo','modulo','mensaje']);w.writeheader();w.writerows({k:e.get(k,'') for k in w.fieldnames} for e in x['errores'])
ph=read(P/'argon08_physics_canonica.json')['physics'];phase=l['step_gross_usd'];total=l['previous_plan_gross_usd']+phase
attempts=len(l['entries']);charged=sum(q['state']=='SETTLED' for q in l['entries'])
report=f"""# AVANCE_08 — {datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m-%d %H:%M')} Bogotá (UTC-5)
## Resultado real
- Datos esc1: **0 faltantes**, desde7 enAV07. Fuente completa2B aplicada; física propuesta por Argon conforme a decisión22:38.
- Intento CPU con núcleo nativo completo reutilizado por hash y constructor/revisor nativos: **{x['estado']}**. Revisión física de todos los cuadros terminó: **{x.get('scene_physics_review_completed',False)}**. Errores nativos originales: **{x.get('native_raw_error_count','ver registros')}**, agrupados en **{len(x['errores'])}** diagnósticos. Preview completo aprobado: **{x['full_cpu_preview_passed']}**.
- Master: **{x.get('master')}**. Sin videoGPU. No confundir0faltantes con aprobación de física/cámara/animación ni con producción.
- Resultado verificable: evidencias/preview_cpu_bvh08_resultado.json, cpu_bvh_revision_final.json si existe, cpu_bvh_worker_resultado.json, constructor.log y BLOQUEOS_O_ERRORES_CPU.csv. Los errores agrupados conservan recuentos y ejemplo; el registro nativo conserva los errores completos.

## Fuente2B: capítulo completo, sin inventar la cola perdida
ZIP original intacto SHA2569e7f7f91c915aff858fb144da0399063ab2543f17dde94df85d95c88770b12bb. Copia y extracción separadas en box:/workspace/avance08/. Contiene164DOCX de varias temporadas; usamos exclusivamente T01_E01_Don_Caos_borro_el_abecedario, completo. Mantuvimos los55s de esc1 y las identidades/tiempos/capas01 existentes, no sustituidos por16min del episodio ni60s del primer minuto.
La respuesta2B completa es una **reconstrucción nueva**:52asignaciones con cita literal comprobada de capítulo/01; NO es la cola original recuperada. Original truncado intacto: esc1_candidata/archivo/respuesta_2b_truncada_pre08.json.
Se corrigió 'mirando su visor': no significa tocarlo. m_hablar_visor_sin_toque/p_visor_sin_toque copia brazos/manos de p_de_pie_base y el resto de p_visor_toque según selección explícita Argon; **cero ángulos nuevos inventados**. Catálogo global anterior intacto.
15movimientos reales pasan Blender CPU de poses/fases/huesos/apoyos; error óseo máximo5.561821284083557e-08m. Su admisión determinista se limita a ensayoCPU, no certifica dinámica, continuidad, colisiones ni producción. El modelo no emite aprobaciones.

## Física por escena: decisión22:38 aplicada
'Que Argon proponga los valores físicos por escena y el motor los valide'. No se importóT317 ni falta decidir usar sus valores.
Esquemas JSON Vertex conresponseMimeTypeapplication/json yresponseSchema/responseJsonSchema según iteración; contrato, inventario real y cotas de cordura deterministas antes de aplicar.
Propuesta admitida: error óseo{ph['bone_length_error_m']}m; velocidad raíz{ph['root_speed_max_m_s']}m/s; aceleración raíz{ph['root_accel_max_m_s2']}m/s²; penetración{ph['penetration_tolerance_m']}m; rechazar intersecciones:{ph['reject_surface_intersections']}.
**Invariables**: COM20m/s², articulaciones600°/s, resbale.05m/cuadro; oro y tolerancias históricas intactos.
Cotas de cordura nuevas, conservadoras y de ingeniería, no hechos de biología: óseo1e-7..1e-3m; velocidad.01..10; aceleración.1..100; penetración1e-6...01m; margen ave0...01m; offsets/apoyos dentro.04m. Pruebas negativas rechazan valores absurdos, cambiar600, collidersvacíos y margen ave1m.
{len(ph['colliders'])}mallas físicas principales con IDs reales;{len(ph['allowed_collision_pairs'])}uniones adyacentes explícitas y{len(ph['contact_pairs'])}contactos superficiales. Estos contactos **NO dispensan profundidad de penetración**; ropa/decoración secundaria no queda certificada por la lista principal.
Rechazados: armaduras/raícesEMPTY como colliders, IDs inexistentes, excepciones injustificadas Spark/cofre y gaps ave/soporte de5cm y5mm.
Piquito: rig19huesos conservado; margen propuesto.005m; hombroIZQUIERDO Eco medido (clavicula_L.tail==brazo_L.head, distancia0). Propuestas convertidas al marcoREST_BONE medido. Attachment rígido y4puntos de apoyo durante6intervalos01. contactsIK=[] es decisión explícita del diseño completo: humanoides usan solver propio y ave attachment; NO un vacío inferido del JSON truncado.

## Corrección técnica BVH, aislada y con respaldo
El primer ensayo encontró un bucle de precisión float32 de ray_cast en el escenario cerrado original. La prueba de paso numérico solamente fue rechazada porque vértices solos no detectaban penetración de cajas coaxiales.
Original preservado: {M0}/motor/fisica_final.py. Nueva copia aislada: {M}/motor/fisica_final.py. Es el **único Python del motor cambiado**; núcleo heredado y presets idénticos. Respaldos: {R}/respaldos/fisica_final_original_motor_bvh08.py y fisica_final_antes_avance_float32.py. El intento fallido no está activo.
Se guardan además límites AABB idénticos una vez por malla/cuadro en vez de recalcularlos por cada par; no cambia el predicado ni ninguna tolerancia. Respaldo adicional:fisica_final_bvh08_antes_cache_aabb.py.
Cambio: avanzar el rayo según precisión float32 de coordenadas, no aumentar la tolerancia física; rechazar si la precisión no basta (paso superior a penetración/16). Añadir centroides y medios de aristas de triángulos evaluados como muestras de superficie reales, para no aceptar penetración coaxial por falta de vértices interiores.
11pruebas deterministas pasan: separados, penetración y contención, contacto transversal estricto, contacto explícito sin eximir profundidad,1.6002655mm rechazados con tolerancia1mm, caso inferior a1mm, barras entrelazadas y fallo cerrado de precisión a2000m. No es prueba formal de todas las mallas arbitrarias.
Cuatro contactos constructivos de profundidad0 observados por BVH fueron propuestos por Argon y comprobados contra exactamente esos4pares; añadidos solo en candidata aislada. Unidad estática del escenario original: **pasa**. No equivale a revisión de escena completa.
Oro **23/23** reejecutado después de la corrección, fixture original SHA256432cb20629d5d17fb0190433ca916b9f5eb81f5dac366fdfee75555c3a968aa1 y tolerancias idénticas.

## Ejecución CPU y reutilización honesta
El primer SSH de seguimiento agotó1200s; se comprobó que el trabajo original seguía vivo y progresando. No se reinició ni se duplicó el bake. El primer intento con motor original se conserva aparte.
Para probar la corrección se reutilizó el mismo core.blend completo e inmutable por la entrada opcional documentada de constructor_final.py, no se fabricó una animación nueva ni se omitió la compuerta física. Reuso acredita mismos legacy,52asignaciones, reloj, entidades, geometría, cámara, luz y movimiento; solo cambian metadatos de contacto y el módulo revisor BVH. Hash antes/después idéntico. Nuevos preflight y revisión nativos obligatorios.
Si la revisión pasa, el videoCPU usa exclusivamente el preset técnico de diagnóstico YA existente config/preset_cpu.json:320x180,4muestras,semilla0, mismo aspecto16:9, sin cambiar la entrada fuente1280x720/64muestras ni su cámara/física. El preset0 también liga explícitamente la semilla requerida por render_cpu.py. Ajustes reales usados, si hubo render: {x.get('cpu_render_preset','no hubo render; compuerta bloqueada')}. No se inventan valores de escena ni se aflojan gates.
Costo de API del CPU:0. El ledger cambió durante el primer bake exclusivamente por la reparación manual autorizada av08_contactos05, no por el CPU; la segunda ejecución exige ledger sin cambios.

## Costes
**Fase: US${phase:.6f} bruto. Acumulado registrado: US${total:.6f} bruto.** {attempts}solicitudes de red con asiento previo;{charged}conusage,1HTTP400 sin cargo de tokens observado; además1arranque previo a red/ledger fallido por archivo aún no subido, sin gasto. Reservas0; topesUS$10fase/~US$50plan respetados.
Bruto calculado segúnusageMetadata y tarifa registrada, no factura conciliada. **Neto esperado US$0 por créditos**, sin conciliación de factura. CPUUS$0 de API; no se inició consumoGPU en esta fase. Estado/cargos preexistentes deRunPod no verificados.
La compuerta manual se reabrió una vez con respaldo/auditoría para la reparación exacta de4contactos dentro de esta fase autorizada, y se restauró enfinally. Pago live y recetas automáticas siguieronoff. Prueba negativa del generador cerrado: sin red ni cambio de ledger.
n8n no fue modificado por este ejecutor en esta fase. No se afirma una nueva publicación ni habilitación de pagos.

## Respaldos, rutas y qué requiere a Ricardo
Raíz servidor${VPS_HOST}:{R}/. Originales independientes MOTOR_UNICO_20261107/ yesc1_candidata/ preservados; candidata final esc1_bvh08/; motor corregido aislado MOTOR_BVH08_CANDIDATO/. Respaldos esc1_antes/,esc1_antes_2b08/,esc1_antes_fisica08/,respaldos/. AV07 intacto.
Nada nuevo falta de capítulo2B ni de decisión sobre quién propone física. Si el CPU rechaza, continuar desde sus errores técnicos reales sin aflojar3fijas ni oro; no volver a pedir el capítulo ni valores manuales inventados.
GPU solo si pasa el preview; único pod pul0wcedwdkwm7, resume/stop, nunca create/delete/terminate. AntecedenteRunPod403: no se repitió ni rodeó en esta fase. No se reanudó ni se modificó el pod; su estado actual no se verificó por el403previo. Un bloqueo de permisos requiere atención del dueño antes de una futura GPU, no un rodeo.
No borrados en disco; sin cambios aT317,24_TRASPASO,v9_universal_calidad_20261106,/opt/video-studio, otroVPS ni podprohibido. No credenciales ni respaldos privados de n8n en esta entrega.
"""
(E/'INFORME_AVANCE_08.md').write_text(report,encoding='utf-8')
(E/'CONTINUAR_AQUI.md').write_text('Leer INFORME_AVANCE_08.md y evidencias/preview_cpu_bvh08_resultado.json. Candidata final servidor:esc1_bvh08; motor aislado:MOTOR_BVH08_CANDIDATO. Core original reutilizado por hash; no rehacerlo sin motivo.  Datos de esc1 ya0faltantes; no confundir con aprobación de ejecución. Corregir fallos físicos/cámara/geometría reales del CPU sin aflojar3fijas ni oro. Respaldar siempre. No reabrir generador.off sin fase autorizada y ledger. Fuente completa/canonical2B está en candidata08; originaltruncado archivado. NoT317 importado. SiCPU no pasó: noGPU. SiCPU pasó: revisar bloqueo403anterior y reglas depodúnico pul0wcedwdkwm7/resume-stop/nunca terminate-delete.\n')
shutil.copy2(M/'motor/fisica_final.py',E/'codigo/fisica_final_BVH08.py');shutil.copy2(M0/'motor/fisica_final.py',E/'codigo/fisica_final_ORIGINAL_preservada.py');D=R/'AVANCE_08';assert not D.exists();shutil.copytree(E,D);shutil.copytree(P,D/'esc1_candidata')
patterns=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'AIza[0-9A-Za-z_-]{30,}',rb'"private_key"\s*:\s*"[^" ]{10,}']
for p in D.rglob('*'):
 if p.is_file() and any(re.search(q,p.read_bytes()) for q in patterns):raise RuntimeError('Secret scan failed; archive not created')
files=sorted(p for p in D.rglob('*') if p.is_file());(D/'SHA256SUMS.txt').write_text(''.join(h(p)+'  '+p.relative_to(D).as_posix()+'\n' for p in files))
z=R/'AVANCE_08_ENTREGA.zip';assert not z.exists()
with zipfile.ZipFile(z,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as f:
 for p in D.rglob('*'):
  if p.is_file():f.write(p,p.relative_to(R))
print(json.dumps({'archive':str(z),'sha256':h(z),'bytes':z.stat().st_size,'files':len(files)+1,'phase_gross':phase,'total_gross':total,'CPU_passed':x['full_cpu_preview_passed'],'master':x.get('master')}))
