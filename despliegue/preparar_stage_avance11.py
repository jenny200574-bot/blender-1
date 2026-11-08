#!/usr/bin/env python3
"""Arma un stage nuevo, mínimo, sin escribir en el origen.

No usa reflink, hardlink ni symlink. Copia bytes a un destino distinto.
No copia evidencia/, archivo/ ni respaldos/ de la raíz del motor: ningún
lector de oro, preflight o reconstrucción los abre como catálogo.
Sí copia cada ruta relativa citada por la entrada o por el código.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

FISICA = 'motor/fisica_final.py'
FISICA_SHA = '3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2'
PROHIBIDO_DESTINO = ('avance10_20261108', 'v9_motor_unico', 'v9_universal_calidad', 'T317')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def es_regular(path):
    path = Path(path)
    if path.is_symlink():
        return False
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode)


def exigir_separados(origen, destino):
    origen = Path(origen).resolve()
    destino = Path(destino).resolve()
    if origen == destino or origen in destino.parents or destino in origen.parents:
        raise SystemExit('Origen y destino se pisan: ' + str(origen) + ' / ' + str(destino))
    texto = str(destino)
    for marca in PROHIBIDO_DESTINO:
        if marca in texto:
            raise SystemExit('Destino prohibido (' + marca + '): ' + texto)
    return origen, destino


def cargar_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rutas_nucleo(data):
    """Rutas que nucleo_bueno_cpu.py abre desde entrada.json. No inventa otras."""
    if not isinstance(data, dict):
        return []
    out = []
    for clave in ('catalog', 'assignments'):
        if isinstance(data.get(clave), str):
            out.append(data[clave])
    env = data.get('environment') or {}
    if isinstance(env, dict):
        if env.get('mode') == 'blend' and isinstance(env.get('path'), str):
            out.append(env['path'])
        elif isinstance(env.get('catalog'), str):
            out.append(env['catalog'])
    for prop in data.get('props') or []:
        if isinstance(prop, dict) and isinstance(prop.get('formula'), str) and prop['formula'].endswith('.json'):
            out.append(prop['formula'])
    return out


def parece_ruta(value):
    return isinstance(value, str) and (value.endswith('.json') or value.endswith('.blend') or value.endswith('.bvh') or '/' in value)


def rutas_de_entrada(entrada):
    """Rutas que orquestador.fuentes, el puente de cámara y el núcleo abren."""
    data = cargar_json(entrada)
    relativas = []
    absolutas = []
    for asset in data.get('assets') or []:
        path = asset.get('path') if isinstance(asset, dict) else None
        if not isinstance(path, str) or not path:
            continue
        if path.startswith('/') or Path(path).is_absolute():
            absolutas.append(path)
        else:
            relativas.append(path)
    legacy = data.get('legacy')
    if isinstance(legacy, dict):
        relativas.extend(rutas_nucleo(legacy))
    env = data.get('environment') or {}
    if isinstance(env, dict):
        if env.get('mode') == 'blend' and isinstance(env.get('path'), str) and not str(env['path']).startswith('/'):
            relativas.append(env['path'])
        elif isinstance(env.get('catalog'), str) and not str(env['catalog']).startswith('/'):
            relativas.append(env['catalog'])
    motion = data.get('motion') or {}
    if parece_ruta(motion.get('assignments')):
        relativas.append(motion['assignments'])
    for job in motion.get('retarget_jobs') or []:
        if isinstance(job, dict) and parece_ruta(job.get('raw_bvh')):
            relativas.append(job['raw_bvh'])
    camera = data.get('camera') or {}
    # auditar() abre camera.source solo cuando es una ruta. "plan congelado" no lo es.
    if parece_ruta(camera.get('source')):
        relativas.append(camera['source'])
    for value in (camera.get('resolver_inputs') or {}).values():
        if parece_ruta(value):
            relativas.append(value)
    # formulas_v2 abre v['archivo'] solo si el catálogo de fórmulas lo trae.
    vistos = []
    for rel in relativas:
        if rel not in vistos:
            vistos.append(rel)
    return data, vistos, absolutas


def archivos_de_catalogo(base, relativos):
    extra = []
    for rel in relativos:
        path = base / rel
        if not path.is_file() or path.suffix != '.json':
            continue
        try:
            data = cargar_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for value in data.values():
            if isinstance(value, dict) and isinstance(value.get('archivo'), str):
                extra.append(value['archivo'])
    return extra


def bvh_citados(biblioteca):
    """buscar_bvh y reusar solo abren rec['path'] dentro de movimientos_aprobados."""
    catalogo = Path(biblioteca) / 'movimientos_aprobados' / 'catalogo.json'
    if not catalogo.is_file():
        return []
    try:
        data = cargar_json(catalogo)
    except (OSError, json.JSONDecodeError):
        return []
    out = ['bibliotecas/movimientos_aprobados/catalogo.json']
    for rec in data.get('entries') or []:
        if isinstance(rec, dict) and isinstance(rec.get('path'), str):
            out.append('bibliotecas/movimientos_aprobados/' + rec['path'])
    return out


def archivos_codigo(origen):
    """motor/*.py lo lee empaquetar() con rglob, y el import del núcleo."""
    origen = Path(origen)
    out = []
    unico = origen / 'motor_unico.py'
    if es_regular(unico):
        out.append('motor_unico.py')
    schema = origen / 'CONTRATO_ENTRADA.schema.json'
    if es_regular(schema):
        out.append('CONTRATO_ENTRADA.schema.json')
    motor = origen / 'motor'
    if motor.is_dir():
        for path in sorted(motor.rglob('*')):
            if not es_regular(path):
                continue
            if 'archivo' in path.relative_to(origen).parts or '__pycache__' in path.parts:
                continue
            if path.suffix in {'.py', '.off', '.json'}:
                out.append(path.relative_to(origen).as_posix())
    config = origen / 'config'
    if config.is_dir():
        for path in sorted(config.iterdir()):
            if es_regular(path) and path.suffix in {'.json', '.off'}:
                out.append(path.relative_to(origen).as_posix())
    bibliotecas = origen / 'bibliotecas'
    if bibliotecas.is_dir():
        for path in sorted(bibliotecas.rglob('*')):
            if not es_regular(path):
                continue
            rel = path.relative_to(origen)
            if 'archivo' in rel.parts:
                continue
            if path.suffix == '.json':
                out.append(rel.as_posix())
        out.extend(bvh_citados(bibliotecas))
    return list(dict.fromkeys(out))


def planear(origen, entrada, etapa):
    origen = Path(origen)
    data, relativas, absolutas = rutas_de_entrada(entrada)
    base = Path(entrada).resolve().parent
    paquete = []
    faltan = []
    claves = []
    for rel in relativas + archivos_de_catalogo(base, relativas):
        path = base / rel
        if path.is_symlink():
            faltan.append(rel + ' es symlink')
            continue
        if path.is_file():
            paquete.append(rel)
        else:
            # set.blend y cualquier asset citado tienen que existir. No se sustituyen.
            faltan.append(rel)
    entrada_path = Path(entrada).resolve()
    if entrada_path.name != 'entrada_escena.json':
        faltan.append('la entrada debe llamarse entrada_escena.json')
    elif 'entrada_escena.json' not in paquete:
        # motor_unico.py exige ese nombre. No está en assets, pero es la raíz del paquete.
        paquete.insert(0, 'entrada_escena.json')
    codigo = archivos_codigo(origen)
    if etapa == 'oro':
        # regresion() no llama empaquetar ni lee bibliotecas ni config, salvo el .off negativo.
        codigo = [p for p in codigo if p == 'motor_unico.py' or p.startswith('motor/')]
        if (origen / 'config' / 'orden_determinista.off').exists():
            codigo.append('config/orden_determinista.off')
    codigo, faltan_pre = exigir_preimagenes(origen, codigo)
    faltan.extend(faltan_pre)
    return {
        'etapa': etapa,
        'entrada': str(entrada),
        'paquete': paquete,
        'faltan': faltan,
        'claves_no_archivo': claves,
        'absolutas_no_abiertas_por_assets': absolutas,
        'codigo': codigo,
        'production_approved': False,
    }


def manifiesto_13():
    return Path(__file__).resolve().parent / 'manifiesto_13.json'


def exigir_preimagenes(origen, codigo):
    """El instalador exige cada archivo con hash `antes`. Los de `antes` null no se copian."""
    data = cargar_json(manifiesto_13())
    faltan = []
    prohibidos = set()
    origen = Path(origen)
    for item in data['archivos']:
        rel = item['ruta']
        if item.get('antes') is None:
            prohibidos.add(rel)
            continue
        src = origen / rel
        if not es_regular(src):
            faltan.append('preimagen ausente ' + rel)
            continue
        if sha256(src) != item['antes']:
            faltan.append('preimagen hash distinto ' + rel)
            continue
        if rel not in codigo:
            codigo.append(rel)
    codigo = [rel for rel in codigo if rel not in prohibidos]
    return codigo, faltan


def auditar_config(origen):
    """Lista rutas absolutas de config sin cambiar los archivos."""
    hallados = []
    config = Path(origen) / 'config'
    if not config.is_dir():
        return hallados
    for path in sorted(config.glob('*.json')):
        if not es_regular(path):
            continue
        texto = path.read_text(encoding='utf-8')
        for ruta in re.findall(r'"(/[^"]+)"', texto):
            hallados.append({'archivo': 'config/' + path.name, 'ruta': ruta, 'se_copia_sin_cambiar': True, 'abre_blend_de_preview': 'preview_cpu' in ruta or ruta.endswith('.blend')})
    return hallados


def copiar_archivo(src, dst):
    src = Path(src)
    dst = Path(dst)
    if src.is_symlink() or not es_regular(src):
        raise SystemExit('Se rechaza symlink o no-regular: ' + str(src))
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink() or not es_regular(dst) or sha256(dst) != sha256(src) or dst.stat().st_nlink != 1:
            raise SystemExit('El destino ya existe y no es la misma copia simple: ' + str(dst))
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    parcial = dst.with_name(dst.name + '.parcial_stage')
    parcial.write_bytes(src.read_bytes())
    os.replace(parcial, dst)
    if dst.is_symlink() or dst.stat().st_nlink != 1:
        raise SystemExit('El destino no quedó como archivo simple: ' + str(dst))
    if sha256(dst) != sha256(src):
        raise SystemExit('Copia distinta del origen: ' + str(dst))


def copiar_plan(origen, entrada, destino, etapa, referencia=None):
    origen, destino = exigir_separados(origen, destino)
    plan = planear(origen, entrada, etapa)
    if plan['faltan']:
        return plan, []
    copiados = []
    motor_dest = destino / 'MOTOR_BVH08_CANDIDATO'
    for rel in plan['codigo']:
        src = origen / rel
        dst = motor_dest / rel
        copiar_archivo(src, dst)
        copiados.append({'etapa': etapa, 'clase': 'codigo', 'ruta': rel, 'sha256': sha256(dst), 'bytes': dst.stat().st_size})
    nombre = 'oro' if etapa == 'oro' else 'escena'
    escena = destino / 'entradas' / nombre
    for rel in plan['paquete']:
        src = Path(entrada).resolve().parent / rel
        dst = escena / rel
        copiar_archivo(src, dst)
        copiados.append({'etapa': etapa, 'clase': 'fixture', 'ruta': 'entradas/' + nombre + '/' + rel, 'sha256': sha256(dst), 'bytes': dst.stat().st_size})
    if referencia is not None:
        ref = Path(referencia)
        if not es_regular(ref):
            raise SystemExit('La referencia oro no es un archivo regular')
        dst = destino / 'entradas' / 'revisor_comparable.json'
        if not dst.exists():
            copiar_archivo(ref, dst)
        copiados.append({'etapa': 'oro', 'clase': 'referencia_solo_lectura_copiada', 'ruta': 'entradas/revisor_comparable.json', 'sha256': sha256(dst), 'bytes': dst.stat().st_size, 'origen': str(ref)})
    return plan, copiados


def escribir_recibo(destino, planes, copiados, fisica_sha, config_rutas):
    total = sum(item['bytes'] for item in copiados)
    doc = {
        'production_approved': False,
        'append_only': True,
        'no_reutiliza_nucleo_viejo': True,
        'salida_solo_en_este_stage': True,
        'fisica_sha256': fisica_sha,
        'bytes': total,
        'entradas_raiz': ['entradas/oro/entrada_escena.json', 'entradas/escena/entrada_escena.json'],
        'preimagen_pruebas': 'pruebas/test_malla_cabeza.py',
        'config_rutas_absolutas_sin_cambiar': config_rutas,
        'archivos': copiados,
        'planes': [{k: v for k, v in plan.items() if k != 'codigo'} for plan in planes],
        'excluidos_porque_el_codigo_no_los_abre': [
            'MOTOR_BVH08_CANDIDATO/evidencia',
            'MOTOR_BVH08_CANDIDATO/archivo',
            'MOTOR_BVH08_CANDIDATO/respaldos',
        ],
    }
    destino = Path(destino)
    nombre = 'manifiesto_stage_completar.json' if (destino / 'manifiesto_stage.json').exists() else 'manifiesto_stage.json'
    path = destino / nombre
    if path.exists():
        raise SystemExit('No se reescribe ' + nombre)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prepara avance11 sin escribir el origen')
    parser.add_argument('--origen-motor', required=True)
    parser.add_argument('--destino', required=True)
    parser.add_argument('--entrada-oro')
    parser.add_argument('--entrada-escena')
    parser.add_argument('--referencia-oro')
    parser.add_argument('--copiar', action='store_true')
    args = parser.parse_args(argv)
    origen, destino = exigir_separados(args.origen_motor, args.destino)
    fisica = origen / FISICA
    if not es_regular(fisica) or sha256(fisica) != FISICA_SHA:
        print('RECHAZADO fisica_final.py no es el hash instalado en el VPS')
        return 2
    etapas = []
    if args.entrada_oro:
        etapas.append(('oro', args.entrada_oro))
    if args.entrada_escena:
        etapas.append(('preflight', args.entrada_escena))
        etapas.append(('reconstruccion', args.entrada_escena))
    if not etapas:
        print('RECHAZADO falta entrada de oro o de escena')
        return 2
    planes = []
    for etapa, entrada in etapas:
        plan = planear(origen, entrada, etapa)
        planes.append(plan)
        print(json.dumps({'etapa': etapa, 'fixtures': len(plan['paquete']), 'codigo': len(plan['codigo']), 'faltan': plan['faltan'], 'production_approved': False}, ensure_ascii=False))
        if plan['faltan']:
            print('FALTAN', etapa, ' '.join(plan['faltan']))
            return 2
    if not args.copiar:
        print('SECO no se copió nada')
        return 0
    copiados = []
    for etapa, entrada in etapas:
        # La reconstrucción lee las mismas entradas/escena que el preflight.
        if etapa == 'reconstruccion':
            continue
        plan, hechos = copiar_plan(origen, entrada, destino, etapa, args.referencia_oro if etapa == 'oro' else None)
        copiados.extend(hechos)
    if sha256(fisica) != FISICA_SHA:
        print('RECHAZADO el origen cambió durante la copia')
        return 3
    doc = escribir_recibo(destino, planes, copiados, FISICA_SHA, auditar_config(origen))
    print('COPIADO', doc['bytes'], 'bytes en', destino)
    return 0


if __name__ == '__main__':
    sys.exit(main())
