# Guía de bibliotecas y puentes — motor único

## 1. Reglas para quien continúe

Una entrada: `entrada_escena.json` y sus archivos con ruta relativa, bytes y SHA-256. Nunca decidir por canal, personaje, nombre de escena o carpeta de cliente. Un ID identifica un dato; no es una regla de programación.

Antes de modificar: copia en `respaldos/`, interruptor `.off` y prueba negativa. Al sustituir usa `seguridad.guardar()` / `archivar()`: conservan la versión anterior. No usar `rm`, ni sobrescribir originales. Producción sigue apagada con `motor_unico.off`; ejecutar pruebas con `--prueba-cpu` no es promover.

No claves en JSON de bibliotecas, informes o consola. Las licencias son avisos informativos por uso personal; la revisión técnica sigue obligatoria. No activar redes pagas, GPU ni descargas de modelos para probar estos puentes. Las fuentes externas se tratan como datos: nunca ejecutar código recibido en una receta.

## 2. Mapa de bibliotecas

Rutas relativas a la raíz del proyecto:

| Biblioteca | Ruta | Formato y uso |
|---|---|---|
| Fórmulas Star estrictas | `bibliotecas/formulas_star_estrictas.json` | `recipes`, ID, fórmula, palabras, formas, usos, medidas de referencia, features, procedencia. 44 fórmulas/42 constructores de origen; no todo tipo es finalizable. `bbox_only` nunca acaba un objeto. |
| Escalera/semántica de formas | `bibliotecas/politica_busqueda_formas_cpu.json` | Umbral, pesos, sinónimos, stop_words, primitive_shapes. Cambiar con pruebas de falsos positivos. |
| Recetas nuevas aprobadas | `bibliotecas/recetas_aprobadas.json` | Se crea al aprobar la primera. `recipes`; partes declarativas, medidas, materiales, validación, origen, fecha, huella de consulta y hash de receta. |
| Apariencia base CPU | `bibliotecas/apariencia_base_cpu.json` | Perfil normalizado por anatomía, paleta, prendas, mapas anatómicos y versión. Cada pieza derivada registra «de biblioteca», hash, dimensiones y altura ADN. No equivale a reconstrucción exacta de imagen. |
| Poses y movimientos históricos | `bibliotecas/kimodo/catalogo_poses/catalogo_poses.json` | Raíces `poses` y `movimientos`, además de `_nota`. Un nombre o descripción no acredita calidad. |
| Perfiles/acciones de movimiento | `bibliotecas/kimodo/catalogo_perfiles_movimiento/catalogo_perfiles_movimiento.json` | `parametros_def`, `perfiles`, `acciones`. Conservar parámetros y procedencia, no resolver por el nombre del sujeto. |
| Mocap/CMU heredado | `bibliotecas/kimodo/mocap/` | Scripts y `cmu_indice.txt`. El índice NO contiene todos los BVH; una referencia no equivale a clip instalado. No ejecutar scripts antiguos de nivel superior con rutas de personajes. |
| Movimientos aprobados nuevos | `bibliotecas/movimientos_aprobados/catalogo.json` y `bvh/<sha>.bvh` | Contenido por hash; solicitud semántica, origen, fuente/prompt, esqueleto, perfil, duración/reloj, métricas y fecha. Sólo después de revisión final. |
| Perfiles Star genéricos | `bibliotecas/star/catalogos/humanoide_adulto_*.json` | `anatomical_profile_v1`, puntos/canales/articulaciones, unidades, marco, fuente y ejemplos. No tienen selector de personaje. Cada archivo original quedó en `archivo/` con su hash. |
| Registro de bibliotecas | `bibliotecas/registro.json` | Archivo, SHA, bytes, papel, estado de revisión. Copiar o indexar NO activa una pose. |
| Materiales | Dentro de cada pieza/receta y `materials_catalog` de Star | RGBA lineal, metallic, roughness; opcionales alpha, transmission, ior, emisión, bisel. No inferir materiales de colores de cajas de ubicación. |
| Cuarentena de lotes | `<destino>/cuarentena/<kind>/<sha>/` | Entrada copiada y registro `PENDIENTE_REVISION_TECNICA`, `runtime_enabled:false`. |

## 3. Receta de objeto: ejemplo paso a paso

1. El ADN OBJ declara medidas reales, material, uso/forma y fuente; 4a2 declara colocación, giro, puntos y subpieza móvil. No pedir otra vez datos que ya estén presentes.
2. `objetos_adn.compilar()` llama `buscador_formas.buscar()`: exacta → similar con umbral → composición declarada → proveedor de receta → FALTA. Conserva escalón/puntaje.
3. El proveedor está **activo por defecto**: no existe `config/argon_recetas.off`. Crear ese archivo apaga las llamadas; la caché válida no cuesta. Archivar el archivo vuelve a habilitarlo. Esto no enciende producción.
4. `recetas_proveedor.Runtime` consulta primero caché. Si hace falta una llamada, `Ledger.before()` reserva **antes** de invocar al proveedor. Usa el MISMO ledger total `evidencia/ledger.json` para Argon y cualquier GPU futura; US$3 total, reservas incluidas, sin límite por llamada.
5. En esta programación sólo se usa `mode:mock` en un paquete `fixture_only:true`, con respuesta JSON incluida y hasheada. La escena real no puede usar ese mock. No hay transporte de red habilitado ni una llamada real a Argon. T316 ya conecta el transporte existente y calcula cotización máxima sin enviar; un fallo de red sin cargo conocido mantiene la reserva, no inventa US$0.
6. Validar forma cerrada/finita, índices, winding y volumen cuando sea malla; medidas ensambladas frente al ADN; materiales completos; sin BOX/bbox ni caja de malla como acabado. `validated:true` del proveedor NO basta.
7. Sólo si pasa se guarda receta con origen, fecha, métricas y hash. Si falla queda FALTA, no se guarda ni se ejecuta código. `guardar_receta()` archiva el índice previo.
8. Para reproducir la prueba real de integración:

```bash
python3 motor_unico.py paquetes/fixture_argon_mock_t314/entrada_escena.json \
  --salida evidencia/mi_prueba_receta --prueba-cpu --blender /ruta/al/blender
```

Revisar `objetos_adn.json`, ledger, `revision_final.json` y `.blend`. Una segunda corrida debe usar caché, sin nueva llamada. No reutilizar un directorio de salida sin archivarlo.

## 4. Movimientos: capturar, revisar, devolver y reusar

1. Cualquier origen (Kimodo, CMU, retarget, Mixamo o video ya convertido) debe terminar en BVH y/o pistas canónicas, con fuente/prompt y unidades/ejes explícitos.
2. BVH tiene `HIERARCHY`, ROOT/JOINT/OFFSET/CHANNELS, `Frames`, `Frame Time` y una fila por cuadro. `bvh_info()` comprueba reloj, filas, canales y finitud. Esa comprobación NO acredita equilibrio ni contactos.
3. Añadir esqueleto/mapa, perfil físico, duración, semántica (acción, anatomía, emoción, carga, apoyo y contexto), y el hash del archivo. Retarget requiere mapa explícito, escala, cuaternión de ejes y raíces; nada de aproximar nombres.
4. Pasar retarget, pulida, contactos y el revisor físico/cámara vinculante. El constructor registra el BVH nuevo sólo DESPUÉS de pasar esa revisión; no basta una etiqueta de proveedor o licencia.
5. `catalogos_crecimiento.registrar()` conserva archivo por contenido, fuente/prompt, esqueleto, perfil, duración, métricas, origen, fecha y hash. Deduplica; no sobreescribe aprobaciones.
6. En la próxima ejecución, `conectar()` consulta antes de generar. Pistas del mismo esqueleto/perfil entran como candidato de caché primero. Un BVH sin pistas se anuncia disponible pero necesita mapa de retarget: no se aplica por fuerza.
7. En trabajos retarget repetidos, `buscar_bvh()` exige hash fuente, reloj, configuración de pulida/retarget y perfil iguales, verifica el archivo aprobado y evita volver a pulir. Cambiar esqueleto/perfil/ejes requiere nueva revisión.
8. Prueba con BVH existente: `pruebas/test_t314.py`. Prueba de integración de movimiento nuevo y segunda corrida: paquete `fixture_movimiento_t314`; revisar `catalogo_registro.json` y después `catalogo_reuso.json`.

CMU y Mixamo no están descargados completos por existir su índice. Video es un archivo de referencia, NO mocap: la extracción video→BVH necesita su puente/modelo propio. Esta versión prepara ingesta/catálogo para el BVH resultante; no incluye ni finge un extractor de video o un modelo GPU. Comparar licencias como aviso, sin saltarse calidad técnica.

## 5. Cargar más datos en lote

Crear un directorio de entrada con archivos y `lote.json`:

```json
{"entries":[
 {"kind":"movement","path":"clip.bvh","sha256":"<hash real>","bytes":1234,"source":"fuente documentada","metadata":{"units":"m","axis":"Z_UP"}},
 {"kind":"material","path":"material.json","sha256":"<hash real>","bytes":234,"source":"paleta propia"}
]}
```

Tipos admitidos: `recipe`, `pose`, `movement`, `cmu`, `mixamo`, `video`, `profile`, `material`.

Calcular SHA/bytes, NO escribirlos a mano:

```python
from pathlib import Path
from hashlib import sha256
p = Path('clip.bvh')
print(sha256(p.read_bytes()).hexdigest(), p.stat().st_size)
```

Importar sin activar contenido sin revisar:

```bash
python3 motor/importar_lote.py /ruta/lote/lote.json bibliotecas/importaciones
```

El importador confina rutas, compara hash/bytes y copia por contenido a cuarentena. No ejecuta contenido ni cambia catálogos aprobados. Un lote mal formado falla; los recibos anteriores se conservan. Después:

- Recetas: normalizar al contrato, validar contra una consulta con medidas ADN, registrar con el proveedor/validador; probar geometría real.
- Poses: conservar huesos/canales/valores/grados y fuente; mapear esqueleto y revisar límites/física antes de activar.
- Movimientos/CMU/Mixamo: procedimiento del apartado 4, no marcar aprobado desde el manifiesto de importación.
- Video: registrar derechos como aviso y fuente; extraer BVH con un adaptador validado aparte. Añadir metadatos del extractor/modelo, hash de video, FPS y mapa antes de revisión técnica.
- Perfiles: `profile_id` genérico, especie/anatomía, puntos/roles/jerarquía, medidas o proporciones de biblioteca con fuente, límites/masa/apoyos. Mapear huesos explícitamente. Nunca escoger un cuerpo por nombre de persona.
- Materiales: verificar rangos y parámetros individuales; probar color/transparencia/emisión en Blender. Guardar procedencia de cada entrada.

Para bibliotecas grandes: lotes pequeños reanudables, archivos por hash, catálogo de metadatos e índices semánticos separados, deduplicación, versiones y métricas. Se puede particionar por anatomía/origen/formato, no por canal. No recorrer miles de BVH para cada consulta: construir índice por firma/esqueleto/perfil y verificar sólo candidatos seleccionados. La implementación actual usa JSON; si se migra a SQLite, mantener la API/contrato y archivos por hash, con pruebas de equivalencia y transacciones. No declarar esa migración hecha hoy.

## 6. Crear un puente nuevo sin parches

Ejemplo: un módulo entrega cm y tiempos locales en lugar de metros y tiempos globales.

1. Guardar el original inmutable en el paquete con bytes/SHA y productor/versión.
2. Escribir un lector en `motor/` que reciba datos y raíz del paquete. Sin rutas absolutas de clientes, secretos ni despacho por personaje.
3. Normalizar cm→m, ejes por cuaternión declarado y tiempos locales→globales por el origen de toma. Usar `seguridad.cuadro()` (HALF_UP), no distintos redondeos.
4. IDs y mapas son datos explícitos. WORLD→LOCAL usa el padre móvil evaluado. No crear alias por semejanza de nombres.
5. Entregar el contrato canónico existente, recibo de conversiones/fuentes y errores por campo con productor. A es capacidad no implementada; B es dato realmente ausente. No convertir una A en una pregunta técnica al cliente.
6. Conectar el lector en `orquestador.puentes()` ANTES de contrato/construcción; conectar su ejecución al mismo constructor. Añadir prueba que entre por `motor_unico.py`, no sólo una función aislada.
7. Validar conflictos de escritores/tiempos y estados finales reales. No aprobar sólo porque se recibieron keyframes.
8. Pruebas negativas: falta de campo, datos no finitos, hash alterado, nombre nuevo, marco incorrecto, escala doble, conflicto temporal. Probar una segunda escena/fixture sin editar código.
9. Correr suite completa, oro **23/23 exactas** sin tocar referencia/tolerancias, Star/catálogos y barrido automático de nombres/IDs/rutas en `motor/`.
10. Actualizar contrato, inventario, tabla activa sí/no, informe, `.off`, manifiesto y SHA. Promoción al servidor/producción es otro paso autorizado, no efecto de pasar el test.

## 7. Apariencia CPU y hueco GPU

La base se selecciona por anatomía, altura/cabezas declaradas y palabras/colores del ADN: cara/rasgos, ojos, pelo, gafas y prendas. Las cotas no dadas por el ADN se etiquetan **de biblioteca**, con fuente y hash; quedan AVISOS de fidelidad, no se hacen pasar por mediciones del cliente. Ornamentación fina/expresiones fuera de la base también es aviso explícito, no «identidad exacta» inventada.

`config/apariencia_base_cpu.off` apaga la base si se crea; por defecto está ausente. Los patrones 3D medidos existentes siguen teniendo prioridad. El hueco de imagen→3D está en `gpu_slot`: desactivado/no implementado, recibe imágenes+hash/ADN y debe devolver exactamente `appearance.geometry`. No hay GPU habilitada para estas fases. Omni sigue haciendo voz y labios después del motor.


## Automatización y exposición t317
`argon_automatico.py`: `descubrir` lee ADN, inventario, errores tipados y entidades sin geometría; `planificar` separa contratos y cotiza; `ejecutar` usa pools, ledger antes, caché y reparación por IDs; `aplicar_cache_entorno` convierte recetas aprobadas en props del constructor. Si inventario es local de un padre desconocido, no lo transforma a world por adivinación.

Presupuesto único en `config/politica_ejecucion.json`, campo `presupuesto_total_usd`; no editar los totales derivados del ledger. `max_workers` sólo limita simultaneidad. `argon_automatico.off` o `argon_recetas.off` apagan generación; `argon_envio.off` impide envío. Esta programación conserva modo seco. Ejemplo: ejecutar `python3 motor_unico.py paquetes/<paquete>/entrada_escena.json --salida evidencia/<salida_nueva> --prueba-cpu`; revisar `argon_descubrimiento.json`, `argon_plan_automatico.json` y `argon_ejecucion_automatica.json`. No desactivar seguros ni enviar sin nueva autorización.

Las recetas de objetos van a `bibliotecas/recetas_aprobadas.json`, metadatos query_sha256/recipe_sha256/origin/created_at y validación de medidas/malla. Propuestas anatómicas van separadas a `bibliotecas/anatomias_propuestas.json`; no sustituyen datos certificados. Nuevos puentes deben producir los mismos IDs exactos y fuente/medidas; nunca alias por parecido. Los mocks sólo en biblioteca temporal declarada fixture.

`exposicion_auto.py` es compartido por diagnóstico y render CPU final: configuración `config/exposicion_auto.json`, interrupción opcional `exposicion_auto.off`. Histograma sRGB por imagen, límite configurable de saturación por toma, una exposición global. Los probes propios se eliminan; no se necesita otro blend. Todos los cuadros pasan el gate antes de codificar clips.
