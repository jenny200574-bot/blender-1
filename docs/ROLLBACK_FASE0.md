# ROLLBACK — Fase 0 (11 de noviembre de 2026)

- **Hora del respaldo:** 10:21 a 10:27 America/Bogota (UTC-5). En el 213 el reloj estaba en UTC+1 (16:21–16:27 +0100).
- **Host:** vmi3640856 (`213.199.63.67`), carpeta `/opt/myia-respaldos/20261111_fase0/`
- **Reglas:** nunca borrar árboles vivos ni personajes. El rollback **renombra** lo actual a un lado y deja el respaldo en su lugar. No se toca T317, `24_TRASPASO`, `v9_universal_calidad_20261106`, el host `217.76.52.53` ni el pod/volumen `32soe7oh2f1gtf`.
- **Estos tarballs incluyen `secretos/` del motor y de las fábricas.** Sirven para restaurar en el mismo 213. **No se copian fuera del 213 ni se suben a GitHub.**

## 1. Inventario (sha256 verificado en el 213)

| Archivo | Bytes | Tamaño | SHA256 |
| --- | ---: | ---: | --- |
| motor_cine_v1_20261110.tar.gz | 1 987 733 093 | 1,9 G | `9b9ed16bab15ea4d27418ff217e2a6ec294cb240888cf35c77051b341750708d` |
| fabricas.tar.gz | 203 136 694 | 194 M | `9b4f45d4112abc9ad6d002754cf69f40f83560e012efe52649137e843d716a42` |
| cajas.tar.gz | 542 613 906 | 518 M | `57ecdd591efa02dad7bb01a70d660f0b79818e8aa06aa197b1288765e003612e` |
| biblioteca.tar.gz | 348 847 558 | 333 M | `e23156e7d6dc35470f9e25fa3c3fa6f331d57fb500ac32fc6545c9c3f2cfe380` |

Disco del 213 antes: 14 G libres (86 %). Después: 12 G libres (89 %). Inodes: 5 % usados.

**Biblioteca (completa, ningún personaje omitido):** 3 canales (`_comun`, `cn-gnesis-digital-el-de-ed178619`, `cn-los-guardianes-de-la-9fb323be`), 6 personajes (`gdc-don-caos`, `gdc-eco`, `gdc-pintor`, `gdc-piquito`, `gdc-spark`, `gdc-valentina`), 1308 archivos, 80 `.blend`. El listado del tar confirma los 6 directorios de personaje.

Miembros del tar (listado, sin extraer): motor 3106, fábricas 1251, cajas 3430, biblioteca 1954.

Comprobar integridad (en el 213):

```bash
cd /opt/myia-respaldos/20261111_fase0
sha256sum -c SHA256SUMS
```

(Ya se comprobó el 11-nov-2026 10:27 America/Bogota: los cuatro OK.)

## 2. Restaurar un árbol (nunca borrar)

Sustituye `NOMBRE` y rutas. `STAMP` es una fecha, p. ej. `20261111_1030`. Se extrae a un hermano, se aparta lo vivo con `mv` y se pone el respaldo en su lugar. Nada de `rm -rf` sobre la biblioteca, fábricas, cajas o motor.

```bash
set -euo pipefail
DEST=/opt/myia-respaldos/20261111_fase0
STAMP=$(date +%Y%m%d_%H%M%S)
cd /opt
sha256sum -c $DEST/SHA256SUMS
```

### 2.1 Motor cine_v1 (`/opt/myia-motor-unificado/v1_20261110`)

```bash
mkdir -p /opt/myia-motor-unificado/restore_$STAMP
tar -C /opt/myia-motor-unificado/restore_$STAMP -xzf $DEST/motor_cine_v1_20261110.tar.gz
# el tar contiene el directorio v1_20261110/
mv /opt/myia-motor-unificado/v1_20261110 /opt/myia-motor-unificado/v1_20261110.bak_$STAMP
mv /opt/myia-motor-unificado/restore_$STAMP/v1_20261110 /opt/myia-motor-unificado/v1_20261110
# no borrar v1_20261110.bak_$STAMP
```

### 2.2 Fábricas (`/opt/myia-fabricas`)

```bash
mkdir -p /tmp/restore_fab_$STAMP
tar -C /tmp/restore_fab_$STAMP -xzf $DEST/fabricas.tar.gz
mv /opt/myia-fabricas /opt/myia-fabricas.bak_$STAMP
mv /tmp/restore_fab_$STAMP/myia-fabricas /opt/myia-fabricas
# no borrar /opt/myia-fabricas.bak_$STAMP
```

### 2.3 Cajas del taller (`/opt/myia-taller-n8n/cajas`)

```bash
mkdir -p /opt/myia-taller-n8n/restore_$STAMP
tar -C /opt/myia-taller-n8n/restore_$STAMP -xzf $DEST/cajas.tar.gz
mv /opt/myia-taller-n8n/cajas /opt/myia-taller-n8n/cajas.bak_$STAMP
mv /opt/myia-taller-n8n/restore_$STAMP/cajas /opt/myia-taller-n8n/cajas
# no borrar cajas.bak_$STAMP
```

### 2.4 Biblioteca 3D (`/opt/myia-biblioteca`) — incluye todos los personajes

```bash
mkdir -p /tmp/restore_bib_$STAMP
tar -C /tmp/restore_bib_$STAMP -xzf $DEST/biblioteca.tar.gz
mv /opt/myia-biblioteca /opt/myia-biblioteca.bak_$STAMP
mv /tmp/restore_bib_$STAMP/myia-biblioteca /opt/myia-biblioteca
# no borrar /opt/myia-biblioteca.bak_$STAMP ni ningún personaje
```

Tras mover, comprobar que los 6 personajes siguen ahí:

```bash
ls /opt/myia-biblioteca/cn-los-guardianes-de-la-9fb323be/personajes/
```

## 3. Restaurar n8n (flujo de producción, sin crear copias)

Exportes (solo lectura en la fase 0; no se editó ningún flujo):

- Crudo (con ids de credenciales n8n, **sin** la clave SSH en sí): `/opt/myia-respaldos/20261111_fase0/n8n/produccion_debwaH9svFMoTnOf.json` y `referencia_fabricas_d2Bwmk2j4ijX28eK.json`
- Sanitizado (para GitHub / el box): mismos nombres con sufijo `_sanitizado`. El sanitizado **no** sirve para reimportar credenciales.

Para reponer `debwaH9svFMoTnOf` hay que usar el JSON **crudo** y la API de n8n (PUT del workflow, sin crear un flujo nuevo). La clave de API no va en este archivo; está en el almacén de claves del 213 / del operador.

```bash
# Ejemplo (NO ejecutar salvo rollback real; sustituir la clave por la del operador):
# curl -sS -X PUT "http://127.0.0.1:5678/api/v1/workflows/debwaH9svFMoTnOf" \
#   -H "X-N8N-API-KEY: $N8N_API_KEY" -H "Content-Type: application/json" \
#   --data-binary @/opt/myia-respaldos/20261111_fase0/n8n/produccion_debwaH9svFMoTnOf.json
```

La fase 0 no cambió el webhook ni el flujo. Este paso solo aplica si una fase posterior lo modifica.

COPIA FABRICAS `d2Bwmk2j4ijX28eK` se exportó solo como referencia; no era el flujo de trabajo y no se debe clonar para trabajar.

## 4. Qué no se restablece con estos tars

- T317, `24_TRASPASO`, `v9_universal_calidad_20261106` (prohibido tocarlos; no formaban parte de este respaldo).
- Host `217.76.52.53` y pod/volumen Star `32soe7oh2f1gtf`.
- El contenedor Docker de n8n en sí (solo el JSON de los dos flujos).
- Staging `/opt/myia-staging-arreglos-20261026/` (no era tarball obligatorio de la fase 0; el código útil se copia al repo, no se tocó en el 213).

## 5. Copias en el box (sin secretos de `secretos/`)

- Este archivo: `/workspace/recorrido_n8n_20261111/fase0/ROLLBACK.md`
- SHA256SUMS, inventory, log: `/workspace/recorrido_n8n_20261111/fase0/`
- n8n sanitizado: `/workspace/recorrido_n8n_20261111/fase0/n8n_debwaH9svFMoTnOf_sanitizado.json` y `n8n_d2Bwmk2j4ijX28eK_sanitizado.json`
