# Contrato del motor único — dev6 CPU, t314

Una entrada: `entrada_escena.json` y su paquete con hashes. Identidades, rutas de recursos, medidas, materiales, acciones, puntos, reglas, cámaras y luces provienen de esa entrada y sus bibliotecas declaradas. No hay ramas por canal ni nombres de personajes en el código.

## Alcance actual
- 16 etapas conectadas al mismo constructor y compuertas. Un fixture completo llega a render/montaje; una escena con datos B incompletos devuelve BLOQUEADO y cero master parcial.
- Caras/rasgos/ropa: construcción medida si existe; de lo contrario BASE_CPU autorizado por t314, ajustado al texto/altura/proporciones del ADN. Plantillas genéricas humanoide/ave, materiales, pelo, gafas, prendas por segmentos, huesos reales. Cada cota/transformación de plantilla queda «de biblioteca» con fuente/hash de biblioteca/generador. Las cotas no aportadas NO se presentan como medidas ADN. Son AVISO de fidelidad.
- Acabado BASE_CPU es aproximado: no promete reproducir exactamente una hoja pintada ni animación facial detallada. Imagen→3D GPU es extensión futura, no ejecutada/implementada.
- Anatomía/contactos/anclas requieren datos estructurales explícitos. La autorización de cotas de apariencia no autoriza inventar límites articulares, apoyos o anclas de acciones.
- ADN OBJ → receta exacta, receta similar con puntaje/umbral, composición medida, proveedor, FALTA. bbox/caja no se acepta como acabado final. Puntos con marco WORLD/LOCAL; pieza_movil explícita cuando corresponde, pivote y jerarquía reales. Cables por polilínea nombrada o FALTA.
- Perfil luminoso independiente por emisor, sin dependencias fijas. Puente heredado de tres canales sólo por IDs declarados. World, exposición, reloj global y apagones CONSTANT por datos. Eventos geométricos antes de crear luces; eventos de emisor/World después, validando todos los escritores juntos.
- SB manda sobre la cámara; no sustituir PAN/CRANE sin amplitudes por una toma quieta aceptada. Los faltantes del resolutor bloquean el constructor.
- Licencia de movimientos: AVISO por uso personal. Integridad, perfil, semántica y calidad técnica siguen obligatorios.

## Proveedor de recetas y gasto
La capacidad Argon receta está activa por defecto como interfaz local: caché primero, interruptor opcional `config/argon_recetas.off`, reserva en ledger ANTES del callback, tope TOTAL de US$3, validación de geometría/medidas/materiales y alta sólo con procedencia, fecha y hash. El mock sólo se permite en fixture explícito y con respuesta hasheada. T316 implementa transporte real con el cliente SB existente, streaming1800s y caché. Sólo cotización seca: dry_run:true y argon_envio.off impiden enviar. No se acredita una llamada real ni se hace gasto en esta programación CPU. No hay GPU. El ledger actual registra US$0 y reserva US$0. Una excepción sin comprobante no libera ficticiamente una reserva real.

## Bibliotecas que crecen
Un movimiento técnicamente aprobado se registra tras la revisión final con prompt/fuente, esqueleto/perfil, duración, métricas, hash y origen. Se busca/reusa antes de generar o repetir pulida. Archivos por hash, deduplicación y control de parámetros de trabajo. Los datos de Star antes nominados se conservan archivados y como ejemplos; el perfil activo es genérico y necesita bone_map explícito. Conservar datos articulares no implica remapear automáticamente ejes de cualquier rig.

## Voz, labios y diálogo — cambio t295
Voz y lip-sync los hace Omni DESPUÉS del motor. Audio opcional: no bloquea. El motor exporta `tiempos_dialogo.json`: hablante, texto, inicio/fin en segundos y cuadros, toma(s) e intervalos cuando cruza un corte. Sale del guion/01/SB. Si falta texto/tiempo/hablante/toma, se indica el productor; no se estima desde audio ni velocidad de lectura.

## Seguridad y entrega
Respaldo previo, interruptores .off y archivo de todo reemplazo. Nunca borrar originales ni registrar secretos. Producción permanece OFF; pruebas CPU explícitas. Sin tocar n8n, producción, servidor/pod prohibidos. La carpeta nueva del 213 no se considera instalada ni probada mientras sólo existan timeouts. Promoción fuera de estas fases.

## Estado real
A=0 dentro de BASE_CPU; B=23 filas/16 causas; 12 AVISOS de cotas. Guardianes NO COMPLETO: 1320 cuadros/12 tomas/6 entidades solicitados, cero cuadros finales aprobados. Hoja real sólo diagnóstica: 12 renders CPU, cinco sujetos colocados, ave y objetos no resueltos no inventados. No constituye aceptación ni video parcial.

Ver [guía](motor/GUIA_BIBLIOTECAS_Y_PUENTES.md), [mejoras activas](MEJORAS_ACTIVAS_T314.md) y [faltantes B](FALTANTES_GRUPO_B.md).
