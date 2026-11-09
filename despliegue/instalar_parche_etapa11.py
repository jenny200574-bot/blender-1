#!/usr/bin/env python3
"""Instala, en seco por defecto, el parche de etapa 11 sobre una COPIA del candidato (MOTOR_BVH08_CANDIDATO).

  python3 instalar_parche_etapa11.py --destino COPIA --origen REPO/motor --manifiesto manifiesto_etapa11.json
  ... --aplicar --respaldo DIR_NUEVO      escribe (solo si el seco sale 0) y guarda los archivos previos en DIR_NUEVO
  ... --revertir --respaldo DIR           devuelve los previos y mueve los archivos nuevos a DIR/retirados (no borra)
  python3 instalar_parche_etapa11.py --generar --origen REPO/motor --manifiesto salida.json   (solo en el repo)

Rechaza sin escribir nada si un hash previo no coincide, si un archivo nuevo ya existe, si el
paquete trae otro hash, o si el manifiesto toca física o código atado a los recibos del núcleo/paquete.
La bandera camara_lotes_por_cuadro.off se instala presente: el cálculo nuevo queda apagado.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ESQUEMA = 'parche_etapa11/1'
FISICA = 'motor/fisica_final.py'
FISICA_SHA = '3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2'
# Código que entra en compatibilidad_nucleo.json / compatibilidad_paquete.json: tocarlo invalida el núcleo o el paquete reutilizable.
PROTEGIDOS = ('motor/heredado/', 'motor/compatibilidad_artefacto.py', 'motor/malla_cabeza.py', 'motor/nucleo_bueno_cpu.py',
              'motor/apariencia_base_cpu.py', 'motor/eje_objetos.py', 'motor/objetos_adn.py', 'motor/superficies_adn.py',
              'motor/traductor_adn.py', FISICA)
PREVIOS = {
    'motor/camara_v2_blender.py': 'a3962fd2ba540cf5e3521ee346de5a6055ac6ed5812ef4b78d9e2091929fd320',
    'motor/buscador_posicion_camara.py': 'cec7cbe39e441a18791ffddf2957ec8ad63378b148a2aec4f0212aadb99c8e7e',
    'motor/constructor_final.py': '8eca43c3e4d375e96b7d9082842475df65d341968c0d9f655bdd20e906f54ef2',
}
NUEVOS = ('motor/progreso_camara.py', 'motor/camara_lotes_por_cuadro.off', 'motor/preflight_constructor.py', 'motor/preflight_blend.py',
          'motor/validar_salida_constructor.py', 'pruebas/test_buscador_por_cuadro.py', 'pruebas/test_preflight_constructor.py',
          'pruebas/test_progreso_y_salida_constructor.py', 'pruebas/blender_camara/escena_sintetica.py',
          'pruebas/blender_camara/correr_etapa11_sintetica.py', 'pruebas/blender_camara/medir.py', 'pruebas/blender_camara/comparar_salidas.py',
          'pruebas/blender_camara/probar_preflight_blend.py', 'pruebas/blender_camara/probar_constructor_sintetico.py')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def generar(origen):
    origen = Path(origen)
    archivos = [{'ruta': r, 'antes': a, 'despues': sha256(origen / r), 'bytes': (origen / r).stat().st_size} for r, a in PREVIOS.items()]
    archivos += [{'ruta': r, 'antes': None, 'despues': sha256(origen / r), 'bytes': (origen / r).stat().st_size} for r in NUEVOS]
    return {'esquema': ESQUEMA, 'sobre': 'avance13/14 con buscador cec7cbe3 y cámara a3962fd2 (3d1653a). No toca test_buscador_posicion_camara.py instalado.',
            'fisica_preservada': {'ruta': FISICA, 'sha256': FISICA_SHA}, 'protegidos': list(PROTEGIDOS), 'archivos': archivos}


def cargar(manifiesto):
    data = json.loads(Path(manifiesto).read_text(encoding='utf-8'))
    if data.get('esquema') != ESQUEMA:
        raise SystemExit('El manifiesto no es ' + ESQUEMA)
    rutas = [x.get('ruta') for x in data.get('archivos') or []]
    if not rutas or len(set(rutas)) != len(rutas):
        raise SystemExit('Manifiesto vacío o con rutas repetidas')
    for r in rutas:
        if not isinstance(r, str) or r.startswith('/') or '..' in Path(r).parts:
            raise SystemExit('Ruta no permitida: ' + str(r))
        if any(r == p or (p.endswith('/') and r.startswith(p)) for p in PROTEGIDOS):
            raise SystemExit('El manifiesto toca código protegido por recibo o la física: ' + r)
    return data


def revisar(destino, origen, data):
    destino, origen = Path(destino), Path(origen)
    errores = []
    if not (destino / FISICA).is_file() or sha256(destino / FISICA) != FISICA_SHA:
        errores.append(FISICA + ' ausente o con otro hash; no es el candidato esperado')
    for x in data['archivos']:
        src, dst = origen / x['ruta'], destino / x['ruta']
        if not src.is_file() or sha256(src) != x['despues']:
            errores.append('el paquete no trae ' + x['ruta'] + ' con el hash nuevo')
        if x['antes'] is None:
            if dst.exists():
                errores.append('ya existe ' + x['ruta'] + '; no se pisa')
        elif not dst.is_file():
            errores.append('falta el previo ' + x['ruta'])
        elif sha256(dst) != x['antes']:
            errores.append('hash previo distinto en %s: %s (esperado %s)' % (x['ruta'], sha256(dst)[:12], x['antes'][:12]))
    return errores


def aplicar(destino, origen, data, respaldo):
    destino, origen, respaldo = Path(destino), Path(origen), Path(respaldo)
    respaldo.mkdir(parents=True, exist_ok=False)
    registro = {'esquema': ESQUEMA, 'destino': str(destino.resolve()), 'archivos': data['archivos']}
    for x in data['archivos']:
        if x['antes'] is not None:
            copia = respaldo / 'previos' / x['ruta']
            copia.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destino / x['ruta'], copia)
            if sha256(copia) != x['antes']:
                return ['el respaldo de ' + x['ruta'] + ' no coincide; no se escribió nada']
    (respaldo / 'registro.json').write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding='utf-8')
    for x in data['archivos']:
        dst = destino / x['ruta']
        if x['antes'] is not None and sha256(dst) != x['antes']:
            return ['cambió ' + x['ruta'] + ' durante la instalación; revertir con --revertir']
        dst.parent.mkdir(parents=True, exist_ok=True)
        parcial = dst.with_name(dst.name + '.parcial_etapa11')
        parcial.write_bytes((origen / x['ruta']).read_bytes())
        os.replace(parcial, dst)
        if sha256(dst) != x['despues']:
            return ['la escritura de ' + x['ruta'] + ' no coincide; revertir con --revertir']
    if sha256(destino / FISICA) != FISICA_SHA:
        return [FISICA + ' cambió durante la instalación']
    return []


def revertir(destino, respaldo):
    destino, respaldo = Path(destino), Path(respaldo)
    reg = json.loads((respaldo / 'registro.json').read_text(encoding='utf-8'))
    errores = []
    for x in reg['archivos']:
        dst = destino / x['ruta']
        if dst.exists() and sha256(dst) not in (x['despues'], x['antes']):
            errores.append('hash ajeno en %s; no se revierte encima de otro cambio' % x['ruta'])
    if errores:
        return errores
    for x in reg['archivos']:
        dst = destino / x['ruta']
        if x['antes'] is None:
            if dst.exists():
                retirado = respaldo / 'retirados' / x['ruta']
                retirado.parent.mkdir(parents=True, exist_ok=True)
                os.replace(dst, retirado)
        else:
            parcial = dst.with_name(dst.name + '.parcial_etapa11')
            shutil.copy2(respaldo / 'previos' / x['ruta'], parcial)
            os.replace(parcial, dst)
            if sha256(dst) != x['antes']:
                errores.append('no quedó el previo en ' + x['ruta'])
    return errores


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--destino')
    p.add_argument('--origen')
    p.add_argument('--manifiesto', required=True)
    p.add_argument('--respaldo')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--aplicar', action='store_true')
    g.add_argument('--revertir', action='store_true')
    g.add_argument('--generar', action='store_true')
    a = p.parse_args(argv)
    if a.generar:
        Path(a.manifiesto).write_text(json.dumps(generar(a.origen), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('GENERADO ' + a.manifiesto)
        return 0
    if a.revertir:
        if not a.respaldo:
            p.error('--revertir exige --respaldo')
        err = revertir(a.destino, a.respaldo)
        for e in err:
            print('FALLO', e)
        print('REVERTIDO' if not err else 'NO_REVERTIDO')
        return 0 if not err else 3
    data = cargar(a.manifiesto)
    errores = revisar(a.destino, a.origen, data)
    if errores:
        for e in errores:
            print('RECHAZADO', e)
        return 2
    if not a.aplicar:
        print('SECO %d archivos listos; física, heredado y recibos sin tocar; bandera camara_lotes_por_cuadro.off incluida. Falta --aplicar --respaldo.' % len(data['archivos']))
        return 0
    if not a.respaldo:
        p.error('--aplicar exige --respaldo (carpeta nueva)')
    fallos = aplicar(a.destino, a.origen, data, a.respaldo)
    for e in fallos:
        print('FALLO', e)
    if fallos:
        return 3
    print('APLICADO %d archivos. Respaldo en %s' % (len(data['archivos']), a.respaldo))
    return 0


if __name__ == '__main__':
    sys.exit(main())
