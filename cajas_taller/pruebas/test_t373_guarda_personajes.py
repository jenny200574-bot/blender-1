"""t366s1473 — pruebas GRATIS (sin red, sin app, sin ledger) de la guarda de personajes de 4a5/4b2/4c2 (personajes.py):
- falsos positivos que ahora PASAN: niño/persona como modificador de lugar, objeto o medida (inglés, español, otros);
- personajes REALES que siguen BLOQUEADOS: nombres/ids/formas del catálogo y descripciones genéricas de persona.
Canal y personajes INVENTADOS (nada de un canal real). Uso: <venv>/python test_t373_guarda_personajes.py  (o pytest)"""
import os, sys, json, tempfile
from pathlib import Path
CAJAS = Path(os.environ.get('CAJAS_PRUEBA', '/opt/myia-taller-n8n/cajas')); sys.path.insert(0, str(CAJAS))
import personajes as P

MP = {'ch-luna-77': {'nombre': 'Luna Prueba', 'formas': {'fm-zz9': {'nombre': 'abrigo'}}}, 'ch-tito': {'nombre': 'Tito', 'formas': {}}}
N = P.nombres_catalogo(MP)

PASAN = ['Wide shot from front-center child eye level (x=5.0, y=0.6, z=1.0) with a 28mm lens looking toward the garden.',
         "Wide-angle 35mm front shot of a warm preschool child's bedroom (4.5m x 4.0m x 2.8m) with no people or characters.",
         'On the left is a cozy honey-wood child bed (#C88A55) with a soft quilted bedspread.',
         'Futuristic cyan-blue translucent child visor goggles (#8FD3FF) positioned above the shelf.',
         'A kid-height wooden shelf holds toys and a lamp.', "The kids' playroom has a round rug.", 'Child-sized chairs around a low table.',
         'Camera at toddler eye-level looking at the crib.', 'A girl\'s bedroom with pink curtains.', 'Human-scale doorway, 2.1 m tall.',
         'Una cama de niño junto a la ventana.', 'La cámara a la altura de los ojos de un niño mira la mesa.', 'Silla para niños de madera.',
         'Quarto de menino com estante.', 'Le lit d\'enfant près de la fenêtre.', 'Empty kitchen, no people, no characters.',
         "In the right foreground stands a children's rectangular wooden garden table in warm cream (obj-mesa at x=6.2).",
         'obj-escudo-tito glows blue on the table.', 'Space for the character to stand later on the left.']
BLOQUEAN = [('A boy standing near the table.', 'figura'), ('A girl sitting on the bed.', 'figura'), ('A child near the bed.', 'figura'),
            ('A child sits on the child bed.', 'figura'), ('A woman cooking in the kitchen.', 'figura'), ('Two people talking by the door.', 'figura'),
            ('Un niño corre por el jardín.', 'figura'), ('Una niña sentada en la silla.', 'figura'), ('Kids playing on the swings.', 'figura'),
            ('Luna Prueba holds the lantern.', 'personaje'), ('The lantern of Tito glows.', 'personaje'), ('ch-luna-77 waits by the door.', 'personaje'),
            ('fm-zz9 hangs on the wall.', 'personaje'), ("A child's hand rests on the table.", 'figura'), ('A child in a red coat near the bed.', 'figura'),
            ('Children sitting at the garden table.', 'figura'), ('A man wearing a spacesuit.', 'prenda')]
R = {}
R['pasan'] = {s: P.revisar_frase(s, N) for s in PASAN}
R['bloquean'] = {s: P.revisar_frase(s, N) for s, _ in BLOQUEAN}
ok_pasan = all(not v for v in R['pasan'].values())
ok_bloq = all(k in R['bloquean'][s] for s, k in BLOQUEAN)

# pedido completo: con falso positivo → pasa ENTERO (ninguna frase quitada); con persona real → partir/bloquear como antes
hab = ("Wide-angle 35mm front shot of a warm preschool child's bedroom with no people or characters. On the left is a cozy honey-wood child bed "
       "with a sky-blue quilted bedspread. A round rug in the center.")
r_hab = P.revisar_pedido('esc-x', hab, MP)
jar = 'Wide shot from front-center child eye level with a 28mm lens looking toward the center of the backyard garden. Green lawn and a wooden fence.'
r_jar = P.revisar_pedido('esc-y', jar, MP)
mez = 'A sunny kitchen with a wooden table and a fruit bowl in the center. A boy standing near the sink. Yellow tiles on the wall.'
r_mez = P.revisar_pedido('esc-z', mez, MP)
tema = 'A girl sitting at the kitchen table. Warm morning light.'
r_tema = P.revisar_pedido('esc-w', tema, MP)
nom = 'Tito stands in the middle of the kitchen. Warm light.'
r_nom = P.revisar_pedido('esc-v', nom, MP)
nom2 = 'A cozy kitchen with yellow tiles and a round table. The lantern of Luna Prueba glows on the shelf.'
r_nom2 = P.revisar_pedido('esc-u', nom2, MP)
R['pedidos'] = {'habitacion_pasa_entera': r_hab, 'jardin_pasa_entero': r_jar, 'mezclado': r_mez, 'tema_persona': r_tema, 'tema_nombre': r_nom, 'mezclado_nombre': r_nom2}
ok_ped = (r_hab is None and r_jar is None and r_mez and r_mez['accion'] == 'partir' and 'boy' not in r_mez['texto'].lower() and 'fruit bowl' in r_mez['texto']
          and r_tema and r_tema['accion'] == 'bloquear' and r_nom and r_nom['accion'] == 'bloquear' and 'catálogo' in r_nom['motivo']
          and r_nom2 and r_nom2['accion'] == 'partir' and 'Luna' not in r_nom2['texto'])

# configurable: sin la sección guarda_personajes vuelve al comportamiento viejo (más estricto); otra palabra se añade sin tocar código
TMP = Path(tempfile.mkdtemp(prefix='t373_')); viejo = P.LLAMADAS_CONFIG
(TMP / 'sin.json').write_text('{}', encoding='utf-8'); P.LLAMADAS_CONFIG = TMP / 'sin.json'
sin_seccion = {'child_bed': P.revisar_frase('A honey-wood child bed.', P.nombres_catalogo(MP)), 'nombre_catalogo_sigue': P.revisar_frase('Tito waits.', P.nombres_catalogo(MP))}
c = json.loads(viejo.read_text(encoding='utf-8')); g = c['guarda_personajes']; g['sustantivos_contexto'] = g['sustantivos_contexto'] + ['hammock']; g['usar_catalogo'] = False
(TMP / 'mas.json').write_text(json.dumps(c), encoding='utf-8'); P.LLAMADAS_CONFIG = TMP / 'mas.json'
ampliado = {'child_hammock': P.revisar_frase('A striped child hammock.', P.nombres_catalogo(MP)), 'sin_catalogo_tito': P.revisar_frase('Tito waits.', P.nombres_catalogo(MP))}
P.LLAMADAS_CONFIG = viejo
R['config'] = {'sin_seccion': sin_seccion, 'ampliado': ampliado}
ok_cfg = ('figura' in sin_seccion['child_bed'] and 'personaje' in sin_seccion['nombre_catalogo_sigue'] and not ampliado['child_hammock'] and not ampliado['sin_catalogo_tito'])

R['PASA'] = {'falsos_positivos_pasan': ok_pasan, 'personajes_reales_bloqueados': ok_bloq, 'pedidos_completos': bool(ok_ped), 'configurable': ok_cfg}
R['TODO_PASA'] = all(R['PASA'].values())

def test_guarda_personajes():
    assert R['TODO_PASA'], json.dumps(R['PASA'])

if __name__ == '__main__':
    out = Path(os.environ.get('SALIDA_T373', str(TMP / 'resultado_t373.json'))); out.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'PASA': R['PASA'], 'TODO_PASA': R['TODO_PASA'], 'fallos_pasan': [s for s, v in R['pasan'].items() if v],
                      'fallos_bloquean': [s for s, k in BLOQUEAN if k not in R['bloquean'][s]], 'resultado': str(out)}, ensure_ascii=False, indent=1))
    sys.exit(0 if R['TODO_PASA'] else 1)
