# Artefactos operativos avance13 — transferencia de sólo lectura

Fecha: 2026-11-08T16:28:48.137375-05:00 (Bogotá).

## Fuente localizada
VPS 213, base `/opt/myia-motor-v9/avance13_20261108_tipoerror/operaciones/`.
`supervisor_oro_constructor.py` (3439 bytes), SHA256 `129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85`.

Su relación documental con la corrida está sustentada por referencias literales:
- Línea 2: ruta de `secuencia_estado.json` en esa misma carpeta.
- Línea 3: campo `supervisor_pid=os.getpid()`; el estado recuperado contiene 19177.
- Líneas 15–16: lanzamiento del hijo y persistencia de command/PID/log.
- Líneas 27–29: comando de constructor y rutas de salida coincidentes con el estado, PID constructor 19474.
Estas referencias identifican el supervisor pertinente y su lanzador interno; NO son una atestación del hash del script que efectivamente cargó el PID histórico. No hay proceso vivo para recuperarlo ni se ejecutó esta fuente.

## Lanzador mínimo
El lanzamiento de los hijos está dentro del mismo archivo (subprocess.Popen). No se encontró un lanzador separado en el listado directo de `operaciones/`. El estado conserva el argv del hijo, NO el comando exterior que arrancó el supervisor. No se fabricó un .sh ni un comando histórico. El archivo fue leído/copiadο como dato; no importado ni ejecutado.

## Qué contiene
- Fuente del supervisor, estado original de la corrida y logs de ésta (dos vacíos, uno con el resultado de regresión).
- Inventario existente de hashes de la copia de fuentes, manifiesto de parche y pre/post hashes.
- `MANIFIESTO_TRANSFERENCIA.json`: ruta original, bytes, SHA original/entregado y líneas omitidas por cada archivo.
- `LOCALIZACION_SANEADA.json`: inventario acotado y estado recuperado; no contiene entorno del proceso SSH.

Los nueve archivos transferidos pasaron el filtro de secretos sin omisiones y sus hashes coinciden con los originales leídos. No se incluyeron contraseña, variables de autenticación, archivos privados de acceso ni credenciales. Se verificó ausencia de la contraseña usada, bloques de clave privada, JWT y asignaciones obvias de credenciales; esto es un filtro estático, no garantía universal de detección de cualquier secreto desconocido.

## Relación con repo/Cursor
NO cotejada. No se abrió/clonó/leyó el repositorio documental `jenny200574-bot/blender-1`, ni se consultó su HEAD. El manifiesto del VPS declara base avance12 con 1611c56 y enumera hashes de parche; esa declaración no certifica equivalencia del supervisor con el repo actual. Cursor debe cotejar los bytes adjuntos con su material antes de intervenir; no asumir identidad por el nombre avance13.

Destino de continuidad indicado por el padre: Cursor `bc-5cccd371-c6ed-560c-a1c0-320c4b035ad3`. Este paquete NO se ha enviado a Cursor desde esta tarea: queda preparado para que el padre lo adjunte.

## Límites de la autorización
Únicamente preservar/registrar errores y cierre y prueba simulada conforme alcance aprobado. No corregir cámara, no inferencias ni reintentos/autorrelanzamientos, no despliegue o ejecución real. No modificar los guardas/presupuestos existentes por esta transferencia. El estado RUNNING histórico se conserva como evidencia, no como prueba de proceso vivo.

Servidor, originales y estado antiguo intactos. No nuevas pruebas, GPU, APIs, n8n, 217 ni gastos de ejecución.
