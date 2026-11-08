# Migración pendiente — NO aplicada, NO ejecutable por accidente

## Nodos afectados
- SELLO PJ · 3 preparar ADN Fase 2 · Maestro 02 (sello_pago), id d64ab9c2-79e7-4eaf-93e3-a9bcb7bd0a35.
- SELLO OBJ · 3 preparar ADN · Maestro 03/04 (sello_pago), id 98167dd6-7b07-49d6-a3c6-6e562d75126f.
- SB vía `paso00_cadena storyboard correr`; escenario vivo no es el nodo de cotización de prompts de escenarios.
- 02T vía `motor_v9 traducir` debe consumir una salida validada, no confundir generación parcial con aprobación integral.

## Cambio propuesto, en orden
1. Guardar backups API/archivos y mantener .off. Revisión del puente SSH/sudo restringido antes de habilitar un comando nuevo; nunca invocar shell arbitrario ni incrustar credenciales en n8n.
2. Añadir adaptador dentro del árbol motor nuevo, con selector de contrato por clase (PJ/OBJ/vivo/SB), proyecto y global existentes, responseSchema plano compatible, lectura root-only de SA y reserva de ledger ANTES de red. No conectar aún.
3. El adaptador deberá devolver datos canónicos + recibo JSON y preservar el contrato legado de cinco bloques hasta migrar `parse_ako`. Sólo agrupar escalares: nunca arreglar números tras recibirlos.
4. PJ: ADN/forma/puntos y perfil humano J_Bip 21 o bird rig completo según identidad, no perfiles intercambiables. Deben existir las fuentes y validación que permitan certificación real; no asignar booleanos de aprobación sin pruebas.
5. OBJ: IDs globalmente únicos, materiales/receta completa y dimensiones validadas. Vivo: únicamente propiedades soportadas, curvas y estados. SB: conservar todas las tomas y tiempos fuente, completar parámetros numéricos faltantes.
6. Cada productor debe rechazar y conservar evidencia del fallo; FALTA no equivale a PASS. Incorporar contador de reintentos y presupuesto, primero prueba gratuita sin red y luego intento contabilizado.
7. Aplicar al workflow sólo después de prueba integrada de ambos formatos y recuperación; guardar frecuentemente con respaldo y promoción reversible. No editar un nodo de cotización como si fuera generador.

No hay parche listo para activar: este documento identifica trabajo pendiente real, no dice que los productores ya estén conectados.
