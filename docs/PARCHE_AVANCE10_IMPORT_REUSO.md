# Parche avance10 — import único y recibo de reuso

Base git de esta rama: `5e65c123288901682a8305ed18ddb9dfb77b9721` (head del PR #3).
Padre: `9d450d4d1032e7fae8e0a78da2206c44d7cea188` (head del PR #2).
Ancestro común con main: `8839b1c25dd5a00339355fdf8840feeb57741524`.
Main observado, no usado como base: `4a8165fc90bd0ab893a4a473a808a29aead3c481`.
PR #1 (`b22819f`, física) no entra.

No se desplegó nada. No se unieron los PR #1, #2 ni #3.

## Cotejo del manifiesto (139 archivos, solo lectura)

Detalle: `docs/cotejo_vps_avance10.csv`.

- 97 iguales entre el VPS, el PR #3, `motor/` de main y `motor_candidato_bvh08`.
- 15 iguales solo al PR #3 (el parche ya estaba en el candidato; no faltaba).
- 21 de `entrega/codigo` iguales a `avances/avance08/codigo`.
- `motor/fisica_final.py` del VPS es `3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2` (candidato de main). En esta rama sigue el hash viejo `682856ed505cd6f63d66c81dd11e64ef8db582a94528ae228f5decd1667ec7fd`. No copiar ese archivo.
- Ausentes en git: `motor/heredado/malla_cabeza.py` (copia operativa, mismo hash que `motor/malla_cabeza.py` del PR #3: `db015e6a696399e07e50f7a7d6ab9a91be0ce7e974abaae2806acdfb5902af2d`), `entrega/codigo/preview_cpu_av09.py`, `entrega/codigo/preview_cpu_av10.py`.
- Divergen y no hay contenido en el manifiesto: `cerrar_entrega_bvh08.py` (VPS `b8f81d45ee8a`, repo `ad0bf27a99e7`) y `generar_schema.py` (VPS `9067cd678ac7`, repo `2d253f0627f9`). No forman parte de este parche.

## Qué no hacer en el VPS

- No copiar el árbol entero ni `motor/fisica_final.py` de esta rama.
- No hacer otra copia completa de avance. Disco al 97 %, 3,5 GB libres.
- No borrar la copia `heredado/malla_cabeza.py`. El código nuevo no la usa.
- No relanzar `preview_cpu_av10.py` hasta rehacer preflight y núcleo. Ese wrapper vuelve a pasar el blend viejo; el constructor ahora se detiene con `REUSO_INCOMPATIBLE`.
- No tocar T317, n8n, video-studio, GPU ni APIs.

## Aplicar solo estos archivos

Desde el candidato, las rutas del parche son `motor/...` y `pruebas/...` (`git diff 5e65c12` con `-p1`).

Hashes esperados después del parche (SHA256 del archivo en esta rama):

| Ruta en el candidato | SHA256 |
|---|---|
| motor/camara_v2_blender.py | `45e706ff53e02e261fbeb3936ef33c033657029f0dc67d6262022aad739e955e` |
| motor/constructor_final.py | `8eca43c3e4d375e96b7d9082842475df65d341968c0d9f655bdd20e906f54ef2` |
| motor/heredado/rig.py | `0e77225c7ff2e4b1ecac15938dc4a060490cb07a8adace55b2f0601153a5703b` |
| motor/heredado/cargar_modulo_motor.py | `6a82c8f62cc098bfcb088067dad66ee6bbbb831a8e9dd6ad77180b5116c024d5` |
| motor/malla_cabeza.py | `ef276da95cf7de25b96452ed97832b5b94bd2c2faa2815b6c5a60fee0bcce609` |
| motor/nucleo_bueno_cpu.py | `5da09ca74229c7a2db3e19c4a86311edbbeb320544e7bea6b22024fff5a1285b` |
| motor/objetos_adn.py | `c6140296d06f16fd60bd5a9ae160d866a2a7a6816f5ffae037848df8baa470f9` |
| motor/orquestador.py | `f7e81ed829922039ea66a714d33eaff8463e8ba0e4242e06b464638c7a96ec6b` |
| motor/traductor_adn.py | `fcc156672ee5fe99d2c2cad5ec961377b7af7f36677fef23799b23f48d919c4d` |
| motor/compatibilidad_artefacto.py | `591e47e87a4b153eda4d8d00ac6547736fdc2f30fba9fc870ce398b511c5ef05` |
| pruebas/test_malla_cabeza.py | `722aacaaca9c359ab384721c8317e257db9f2e7f4a137ddfee578b2c4a638d99` |
| pruebas/test_cargar_modulo_motor.py | `7ff8cdb1d2f7af17c2cd2b0306b5833b0f03969f0c68a5af7dde042af3aa6e7a` |
| pruebas/test_compatibilidad_artefacto.py | `ad5ad200c010d7c6a5f9c599ac14ab8d1f1d186f33faf14ccbac53ba6584ea69` |

Comprobar el hash de cada archivo después de copiarlo. Si no coincide, no seguir.

## Siguiente corrida, carpeta nueva y chica

1. Preflight desde la entrada fuente de la escena, no desde `paquete_normalizado` viejo. El orquestador nuevo escribe `compatibilidad_paquete.json` solo si la compilación dejó las marcas `_eje_objetos` y `_cabeza_compilada` y no hubo errores.
2. Núcleo nuevo, sin tercer argumento de blend. `nucleo_bueno_cpu.py` escribe `compatibilidad_nucleo.json` junto al `.blend`.
3. Constructor: si falta el recibo, el código no coincide o el legacy no es el mismo, sale `REUSO_INCOMPATIBLE` antes de abrir el blend.
4. Oro 23/23 en salida nueva, tolerancias intactas. Esta VM no corrió Blender. El desplazamiento de la cápsula no cambió; sí cambió el import y la cámara ahora puede medir el hueso de cabeza si no hay malla visible. No se afirma 23/23 ni preview de escena 1.
