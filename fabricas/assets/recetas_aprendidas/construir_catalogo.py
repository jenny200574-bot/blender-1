# -*- coding: utf-8 -*-
"""Construye la capa recetas_aprendidas a partir de las 20 recetas APTAS (vía B).
Copia versionada: NO toca la biblioteca Star original ni producción. US$0, sin IA."""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
ESC = AQUI.parents[1] / 'escenario'
VIA = ESC / 'via_b'
DATOS = ESC / 'datos'
OUT_REC = AQUI / 'recetas'
OUT_CAT = AQUI / 'catalogo.json'
ALIAS = json.loads((AQUI / 'alias_objeto_n8n.json').read_text(encoding='utf-8'))
BOG = ZoneInfo('America/Bogota')

# Archivos de respuesta a usar (CON_ANCLA_TUBO donde exista)
RESPUESTAS = {
    'G1_juguetes_textiles': VIA / 'respuestas/G1_juguetes_textiles_CON_ANCLA_TUBO.json',
    'G2_pared_ventana_luz': VIA / 'respuestas/G2_pared_ventana_luz.json',
    'G3_utiles_dibujo': VIA / 'respuestas/G3_utiles_dibujo_CON_ANCLA_TUBO.json',
    'G4_objetos_magicos': VIA / 'respuestas/G4_objetos_magicos.json',
}
COSTO_REAL_GRUPO = {  # ledger_argon.csv / envio.log 9-nov-2026
    'G1_juguetes_textiles': 0.3208,
    'G2_pared_ventana_luz': 0.4131,
    'G3_utiles_dibujo': 0.1985,
    'G4_objetos_magicos': 0.3077,
}
CATEGORIA = {
    'peluche_oso': 'juguetes', 'pelota_colores': 'juguetes', 'bloques_geometricos': 'juguetes',
    'cesta_tela': 'contenedores', 'avion_madera': 'juguetes',
    'cortinas_ventana': 'textiles', 'barra_cortinero': 'fijaciones', 'guirnalda_banderines': 'decoracion',
    'repisa_pared': 'muebles', 'perchero_pared': 'muebles', 'interruptor_luz': 'instalaciones',
    'lamparita_noche': 'iluminacion', 'lapiz': 'utiles', 'bote_crayones': 'utiles',
    'pincel_magico': 'utiles', 'papel_numeros': 'utiles', 'candados': 'objetos_magicos',
    'vocales': 'objetos_magicos', 'numeros': 'objetos_magicos', 'visor': 'objetos_magicos',
}
NOMBRE_EN = {
    'peluche_oso': 'teddy bear plush', 'pelota_colores': 'color ball', 'bloques_geometricos': 'building blocks',
    'cesta_tela': 'fabric basket', 'avion_madera': 'wooden toy plane', 'cortinas_ventana': 'curtains',
    'barra_cortinero': 'curtain rod', 'guirnalda_banderines': 'bunting garland', 'repisa_pared': 'wall shelf',
    'perchero_pared': 'wall coat rack', 'interruptor_luz': 'light switch', 'lamparita_noche': 'night lamp',
    'lapiz': 'pencil', 'bote_crayones': 'crayon cup', 'pincel_magico': 'paintbrush', 'papel_numeros': 'number paper',
    'candados': 'padlocks', 'vocales': 'vowel blocks', 'numeros': 'number blocks', 'visor': 'visor',
}

def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def generico_de(nombre: str, oid: str) -> str:
    """Nombre genérico sin amarrar al canal: quita prefijos de escena y adjetivos de lugar."""
    g = ALIAS.get(oid)
    if g:
        return g
    s = re.sub(r'^(amb-esc-[a-z0-9]+-|obj-)', '', oid)
    s = re.sub(r'-(izquierda|derecha|frente|atras)$', '', s)
    return s.replace('-', '_')

def main():
    rv = json.loads((DATOS / 'recetas_validas.json').read_text(encoding='utf-8'))
    rev = json.loads((VIA / 'respuestas/REVISION.json').read_text(encoding='utf-8'))
    por_obj_rev = {}
    for g, info in rev.items():
        for oid, r in info.get('por_objeto', {}).items():
            por_obj_rev[oid] = {**r, 'grupo': g}

    # mapa objeto -> grupo + sha respuesta
    oid_grupo = {}
    sha_grupo = {}
    for g, path in RESPUESTAS.items():
        sha_grupo[g] = sha_file(path)
        data = json.loads(path.read_text(encoding='utf-8'))
        for r in data.get('recetas', []):
            oid_grupo[r['objeto_id']] = g

    OUT_REC.mkdir(parents=True, exist_ok=True)
    fichas = []
    indice = {}
    fecha = datetime.now(BOG).strftime('%Y-%m-%d')
    for oid, rec in rv.items():
        gid = generico_de(rec.get('nombre', ''), oid)
        g = oid_grupo.get(oid) or por_obj_rev.get(oid, {}).get('grupo')
        n_en_grupo = sum(1 for x, gg in oid_grupo.items() if gg == g) or 1
        costo_g = COSTO_REAL_GRUPO.get(g, 0.0)
        caja = rec['caja_m']
        citas = []
        for d in rec.get('datos') or []:
            if d.get('origen') == 'fuente' and d.get('cita'):
                citas.append({'fuente_id': d.get('fuente_id'), 'clave': d.get('clave'), 'cita': d['cita']})
        revisor = por_obj_rev.get(oid, {})
        ficha = {
            'id': gid,
            'nombre_generico': re.sub(r'\s+', ' ', (rec.get('nombre') or gid).split(',')[0]).strip()[:80],
            'nombre_en': NOMBRE_EN.get(gid, gid.replace('_', ' ')),
            'categoria': CATEGORIA.get(gid, 'aprendidas'),
            'medidas_tipicas': {
                'ancho_m': caja['ancho'], 'fondo_m': caja['fondo'], 'alto_m': caja['alto'],
            },
            'medidas_fuente': f'receta Argon vía B {g} (caja de n8n 4a1/4a2 del objeto origen)',
            'orientacion': 'origen en el centro de la base; x = ancho, y = fondo, z = alto; frente hacia -y',
            'parametros': {
                'ancho_m': 'cualquiera', 'fondo_m': 'cualquiera', 'alto_m': 'cualquiera',
                'colores': 'parámetro del canal (ADN/4a1); la receta trae color_guia por defecto',
                'otros': ['apoyo', 'conjunto'],
            },
            'bbox_generado_m': [caja['ancho'], caja['fondo'], caja['alto']],
            'diferencia_vs_tipico_m': [0.0, 0.0, 0.0],
            'ajusta_a_medidas': True,
            'colgado': 'cuelga / pared' if rec.get('apoyo') in ('pared', 'techo') else None,
            'base_m': 0.0 if rec.get('apoyo') == 'piso' else None,
            'apoyo': rec.get('apoyo'),
            'conjunto': bool(rec.get('conjunto')),
            'piezas': len(rec.get('partes') or []),
            'tipos_de_pieza': sorted({p['tipo'] for p in rec.get('partes') or []}),
            'partes': rec['partes'],  # absolutas a medidas_tipicas; escalar.py las reescala
            'caja_m': dict(caja),
            'anclajes_m': {
                'base': [0.0, 0.0, 0.0],
                'encima': [0.0, 0.0, caja['alto']],
                'frente': [0.0, -caja['fondo'] / 2, caja['alto'] / 2],
            },
            'estados': {},
            'color_guia': 'solo para ver la forma; no es color de molde',
            'color_molde': None,
            'color_molde_regla': 'lo pone la ficha del objeto en el canal (ADN/4a1); la biblioteca no fija colores de molde',
            'origen': {
                'tipo': 'argon',
                'paso': 'receta_objetos_faltantes_v1',
                'grupo': g,
                'objeto_id_origen': oid,
                'fecha': '2026-11-09',
                'sha256_respuesta': sha_grupo.get(g),
                'costo_usd_grupo': costo_g,
                'costo_usd_repartido': round(costo_g / n_en_grupo, 6),
                'citas': citas[:12],
                'licencia': 'receta generada para MYIA; geometría reusable como forma genérica',
            },
            'revisor': {
                'apta': bool(revisor.get('apta', True)),
                'errores': revisor.get('errores') or [],
                'avisos': revisor.get('avisos') or [],
                'vacios': revisor.get('vacios') or rec.get('vacios') or [],
                'info': revisor.get('info') or {},
                'fecha': '2026-11-09',
            },
            'alias_n8n': [oid],
            'equivale_a_biblioteca_objetos': None,
            'capa': 'recetas_aprendidas',
        }
        assert ficha['revisor']['apta'], (oid, ficha['revisor'])
        (OUT_REC / f'{gid}.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=1), encoding='utf-8')
        fichas.append({k: v for k, v in ficha.items() if k != 'partes'})  # catálogo liviano sin partes
        # el catálogo liviano apunta al archivo con partes
        fichas[-1]['archivo_partes'] = f'recetas/{gid}.json'
        fichas[-1]['n_partes'] = len(rec['partes'])
        indice[gid] = oid
        indice[oid] = gid

    catalogo = {
        'version': 1,
        'nombre': 'recetas aprendidas (capa sobre Star; genérica, sin canal)',
        'generado_por': 'construir_catalogo.py',
        'fecha': fecha,
        'capa': 'recetas_aprendidas',
        'base_star': {
            'ruta_original_no_tocada': '/workspace/pr17/comb/herramientas/escenario_detallado/biblioteca_formas/',
            'sha256_biblioteca_formas_json': '1b98e28f0abe0618af81fe7b981ede9e9cde3bc0d2144bb8a31a05547dc6351c',
            'sha256_formas_biblioteca_py': 'ec0ea54b0fee76877427fa2293a6655ec8b87a1cb718db9a97df7a71e3ebb1ab',
        },
        'n_fichas': len(fichas),
        'costo_total_usd_origen': round(sum(COSTO_REAL_GRUPO.values()), 4),
        'alias_n8n': ALIAS,
        'indice': indice,
        'fichas': sorted(fichas, key=lambda f: f['id']),
    }
    OUT_CAT.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1), encoding='utf-8')
    # índice rápido id -> partes path
    (AQUI / 'indice.json').write_text(json.dumps({
        'por_id': {f['id']: f['archivo_partes'] for f in fichas},
        'por_objeto_n8n': ALIAS,
        'n': len(fichas),
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'n_fichas': len(fichas), 'ids': [f['id'] for f in sorted(fichas, key=lambda x: x['id'])],
                      'costo_usd': catalogo['costo_total_usd_origen'], 'catalogo': str(OUT_CAT)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
