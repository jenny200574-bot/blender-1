#!/usr/bin/env python3
"""Genera tar.gz + zip del paquete experimental PR7 (cámara directa SB) con manifiesto SHA-256.

  python3 despliegue/empaquetar_avance14_directa_sb.py [--salida DIR]

No incluye credenciales, .env, evidencia de cliente ni .blend de producción.
Salida por defecto: /opt/cursor/artifacts/
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOMBRE = 'avance14_camara_directa_sb_exp'
VERSION_GIT = subprocess.run(
    ['git', 'rev-parse', '--short', 'HEAD'],
    cwd=ROOT,
    capture_output=True,
    text=True,
    check=False,
).stdout.strip() or 'sin_git'

INCLUIR = [
    ('avances/avance14_camara_directa_exp', 'avances/avance14_camara_directa_exp'),
    ('motor/motor', 'motor/motor'),
    ('motor/bibliotecas', 'motor/bibliotecas'),
    ('motor/paquetes/fixture_4g_v5', 'motor/paquetes/fixture_4g_v5'),
    ('motor/pruebas/test_camara_directa_sb.py', 'motor/pruebas/test_camara_directa_sb.py'),
    ('motor/pruebas/test_analisis_directa_t598.py', 'motor/pruebas/test_analisis_directa_t598.py'),
    ('motor/pruebas/test_cabeza_visible_legacy.py', 'motor/pruebas/test_cabeza_visible_legacy.py'),
    ('motor/pruebas/test_visibilidad_cabeza_fcurves.py', 'motor/pruebas/test_visibilidad_cabeza_fcurves.py'),
    ('motor/pruebas/test_presencia_aparicion_toma.py', 'motor/pruebas/test_presencia_aparicion_toma.py'),
    ('motor/pruebas/test_cargar_modulo_motor.py', 'motor/pruebas/test_cargar_modulo_motor.py'),
    ('motor/pruebas/test_malla_cabeza.py', 'motor/pruebas/test_malla_cabeza.py'),
    ('motor/pruebas/test_camara_memoria.py', 'motor/pruebas/test_camara_memoria.py'),
    ('motor/pruebas/test_validar_cuadro_encuadre.py', 'motor/pruebas/test_validar_cuadro_encuadre.py'),
    ('motor/pruebas/test_fisica_interior.py', 'motor/pruebas/test_fisica_interior.py'),
    ('motor/pruebas/test_progreso_fisica.py', 'motor/pruebas/test_progreso_fisica.py'),
    ('motor/pruebas/test_continuidad_tomas.py', 'motor/pruebas/test_continuidad_tomas.py'),
    ('motor/pruebas/test_superficie_caminable.py', 'motor/pruebas/test_superficie_caminable.py'),
    ('motor/pruebas/test_camara_despeje_render.py', 'motor/pruebas/test_camara_despeje_render.py'),
    ('motor/pruebas/test_camara_oclusion_sb.py', 'motor/pruebas/test_camara_oclusion_sb.py'),
    ('motor/paquetes/guardianes_t316/entrada_escena.json', 'motor/paquetes/guardianes_t316/entrada_escena.json'),
    ('motor/pruebas/blender_camara', 'motor/pruebas/blender_camara'),
    ('motor/CONTRATO_ENTRADA.schema.json', 'motor/CONTRATO_ENTRADA.schema.json'),
    ('motor/CONTRATO_TIEMPOS_DIALOGO.schema.json', 'motor/CONTRATO_TIEMPOS_DIALOGO.schema.json'),
    ('motor/DEPENDENCIAS.json', 'motor/DEPENDENCIAS.json'),
    ('motor/motor_unico.py', 'motor/motor_unico.py'),
    ('motor/motor_unico.off', 'motor/motor_unico.off'),
    ('despliegue/README_AVANCE14_DESPLIEGUE.md', 'README_DESPLIEGUE.md'),
    ('despliegue/INFORME_R14.md', 'INFORME_R14.md'),
    ('despliegue/INSTALAR_AISLADO_AVANCE14.sh', 'INSTALAR_AISLADO.sh'),
    ('despliegue/COMANDOS_AVANCE14.env.example', 'COMANDOS.env.example'),
]

OMITIR_DIR = {'__pycache__', '.git', 'evidencia', 'archivo'}
OMITIR_EXT = {'.pyc', '.blend', '.env'}
OMITIR_NOMBRE = {'.env', 'ledger.lock'}


def _copiar(orig: Path, dest: Path) -> None:
    if orig.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(orig, dest)
        return
    for p in orig.rglob('*'):
        if any(x in p.parts for x in OMITIR_DIR):
            continue
        if p.suffix in OMITIR_EXT or p.name in OMITIR_NOMBRE:
            continue
        rel = p.relative_to(orig)
        d = dest / rel
        if p.is_dir():
            d.mkdir(parents=True, exist_ok=True)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, d)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _manifest(staging: Path) -> dict:
    archivos = []
    for p in sorted(staging.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(staging).as_posix()
        archivos.append({'ruta': rel, 'bytes': p.stat().st_size, 'sha256': _sha256(p)})
    off = staging / 'motor/motor/camara_busqueda_reparacion.off'
    return {
        'esquema': 'paquete_avance14_directa_sb/1',
        'nombre': NOMBRE,
        'generado_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': VERSION_GIT,
        'base_pr6': 'cursor/camara-etapa11-construccion-43f7 @ 97a7a89 (+ commit directa SB 4f439fc)',
        'pr_github': 7,
        'modo_busqueda': 'OFF si existe motor/motor/camara_busqueda_reparacion.off (incluido en este paquete)',
        'runtime_blender': '4.2.3 LTS CPU (ajustar BLENDER en COMANDOS.env)',
        'python_preflight': '3.12+ con jsonschema (stdlib + jsonschema en VPS avance13)',
        'no_toca': ['/opt/myia-motor-v9/ instalado', 'main', 'rama producción sin .off'],
        'archivos': archivos,
        'sha256_paquete': None,
        'camara_busqueda_reparacion_off': off.is_file(),
        'sha256_camara_busqueda_reparacion_off': _sha256(off) if off.is_file() else None,
        'sha256_camara_v2_blender.py': _sha256(staging / 'motor/motor/camara_v2_blender.py'),
    }


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, default=Path('/opt/cursor/artifacts'))
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    staging = args.salida / f'.stage_{NOMBRE}'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    pkg_root = staging / NOMBRE
    pkg_root.mkdir()
    for src_rel, dst_rel in INCLUIR:
        src = ROOT / src_rel
        if not src.exists():
            raise SystemExit(f'falta en repo: {src_rel}')
        _copiar(src, pkg_root / dst_rel)
    man = _manifest(pkg_root)
    man_path = pkg_root / 'manifiesto_paquete.json'
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
  # re-hash with manifest inside
    man = _manifest(pkg_root)
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')

    base = args.salida / f'{NOMBRE}_{VERSION_GIT}'
    tgz = Path(str(base) + '.tar.gz')
    zipp = Path(str(base) + '.zip')

    def _add(arc, root: Path, arcname: str):
        arc.write(root, arcname)

    with tarfile.open(tgz, 'w:gz') as tar:
        tar.add(pkg_root, arcname=NOMBRE)
    with zipfile.ZipFile(zipp, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(pkg_root.rglob('*')):
            if p.is_file():
                zf.write(p, NOMBRE + '/' + p.relative_to(pkg_root).as_posix())

    hashes_pkg = {}
    for artefacto in (tgz, zipp):
        dig = _sha256(artefacto)
        hashes_pkg[artefacto.name] = dig
        (args.salida / f'{artefacto.name}.sha256').write_text(f'{dig}  {artefacto.name}\n', encoding='utf-8')

    resumen = {
        'paquetes': hashes_pkg,
        'manifiesto_en_tar': f'{NOMBRE}/manifiesto_paquete.json',
        'archivos_internos': len(man['archivos']),
        'directa_sb_off': man['camara_busqueda_reparacion_off'],
    }
    (args.salida / f'{NOMBRE}_RESUMEN.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding='utf-8')
    shutil.rmtree(staging)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
