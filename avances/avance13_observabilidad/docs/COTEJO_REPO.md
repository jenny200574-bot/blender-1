# Cotejo blender-1 vs artefacto VPS (2026-11-08)

HEAD documental: `4a8165fc90bd0ab893a4a473a808a29aead3c481` (main, paquete Inmi). No es draft Origin T317.

## Supervisor
| Pieza | Repo blender-1 | VPS avance13 |
|---|---|---|
| `supervisor_oro_constructor.py` | AUSENTE | 3439 B, SHA `129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85` |
| `secuencia_estado.json` | AUSENTE | RUNNING/CONSTRUCTOR, PIDs 19177/19474, returncode null |

No hay equivalente de repo. No se sustituyó motor/ por esta copia. Paquete operativo aislado.

## Cámara / física (NO tocadas; identidades distintas)
| Archivo | blender-1 `motor/` | blender-1 `motor_candidato_bvh08/` | VPS avance13 (manifiesto) |
|---|---|---|---|
| `camara_v2_blender.py` | `b27cb818…` 54478 B | `b27cb818…` 54478 B | `a3962fd2…` 62778 B |
| `fisica_final.py` | `682856ed…` | `3423c9a7…` (coincide guarda VPS) | guarda exige `3423c9a7…` |
| `sonda_inspeccion_camara.py` | AUSENTE | AUSENTE | `c5a1054e…` |

Conciliación previa: adjunto cámara `4d660b6a…` ≠ T317 `b27cb818…` ≠ VPS `a3962fd2…`. No se sobrescribe uno con otro.

Commit `1611c56` existe en rama `cursor/import-y-reuso-artefactos-434f` (cámara), no es este supervisor. No se mezclan.

## Relación con el incidente
El adjunto localiza el lanzador: `Popen` + `secuencia_estado.json` + PIDs 19177/19474. No atestigua el hash cargado por el PID histórico. Logs `supervisor.log` y `constructor_tipoerror.log` = 0 B (SHA vacío `e3b0c442…`). oro_tipoerror.log 35 B, 23 checks.
