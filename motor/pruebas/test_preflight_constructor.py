"""Preflight de la entrada del constructor sobre un paquete sintético normalizado por el orquestador real.

No abre Blender ni usa material de cliente: parte de paquetes/fixture_4g_v5 y le aplica cambios
controlados. Cada cambio se vuelve a sellar como lo haría el productor, salvo el que prueba
que una edición a mano después del sello se detecta.
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'motor'))
import preflight_constructor as PF  # noqa: E402
from compatibilidad_artefacto import sellar_paquete  # noqa: E402


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _arbol(pk):
    return {str(p.relative_to(pk)): _sha(p) for p in sorted(Path(pk).rglob('*')) if p.is_file()}


class PreflightConstructor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from orquestador import ejecutar
        cls.tmp = Path(tempfile.mkdtemp(prefix='preflight_'))
        r = ejecutar(str(ROOT / 'paquetes' / 'fixture_4g_v5' / 'entrada_escena.json'), str(cls.tmp / 'validacion'), prueba_cpu=True, solo_validar=True)
        assert r['estado'] == 'VALIDADO', r['errores'][:3]
        cls.base = cls.tmp / 'validacion' / 'paquete_normalizado'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def copia(self, cambio=None, archivos=None, resellar=True):
        pk = Path(tempfile.mkdtemp(prefix='pk_', dir=self.tmp)) / 'paquete_normalizado'
        shutil.copytree(self.base, pk)
        d = json.loads((pk / 'entrada_escena.json').read_text(encoding='utf-8'))
        for rel, fn in (archivos or {}).items():
            data = json.loads((pk / rel).read_text(encoding='utf-8'))
            fn(data)
            (pk / rel).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            for a in d['assets']:
                if a['path'] == rel:
                    a['sha256'] = _sha(pk / rel)
                    a['bytes'] = (pk / rel).stat().st_size
        if cambio:
            cambio(d)
        (pk / 'entrada_escena.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        if resellar:
            (pk / 'compatibilidad_paquete.json').unlink()
            self.assertTrue(sellar_paquete(ROOT, pk))
        return pk

    def codigos(self, r, severidad):
        return {f['codigo'] for f in r['filas'] if f['severidad'] == severidad}

    def test_paquete_normalizado_por_el_orquestador_es_apto(self):
        r = PF.revisar(self.base)
        self.assertEqual(r['estado'], 'APTO_PARA_CONSTRUIR', r['filas'])
        self.assertFalse(r['production_approved'])

    def test_no_escribe_en_el_paquete(self):
        antes = _arbol(self.base)
        PF.revisar(self.base)
        self.assertEqual(antes, _arbol(self.base))

    def test_edicion_a_mano_despues_del_sello_bloquea(self):
        pk = self.copia(lambda d: d['contacts'].pop(), resellar=False)
        r = PF.revisar(pk)
        self.assertIn('RECIBO_PAQUETE', self.codigos(r, 'BLOQUEO'))

    def test_altura_y_distancia_del_sb_vacias_son_derivadas_no_bloqueo(self):
        def sb(data):
            for v in data['vinetas']:
                v['altura_m'] = None
                v['altura_fuente'] = 'por medir en 02N'
                for k in v['keyframes']:
                    k['distancia_m'] = 'por medir en 02N'
        pk = self.copia(archivos={'camara_4g/sb_source.json': sb})
        r = PF.revisar(pk)
        self.assertEqual(r['estado'], 'APTO_PARA_CONSTRUIR', [f for f in r['filas'] if f['severidad'] == 'BLOQUEO'])
        self.assertIn('CAMARA_ALTURA_DISTANCIA', self.codigos(r, 'DERIVADO'))

    def test_contactos_vacios_sin_programa_que_lo_declare_bloquea(self):
        pk = self.copia(lambda d: d.__setitem__('contacts', []))
        r = PF.revisar(pk)
        self.assertIn('CONTACTOS_VACIOS_SIN_PROCEDENCIA', self.codigos(r, 'BLOQUEO'))
        self.assertIn('CONTACTOS_DISTINTOS', self.codigos(r, 'AVISO'))

    def test_contactos_vacios_declarados_por_el_programa_es_aviso(self):
        def cambio(d):
            d['contacts'] = []
            d['motion']['program'] = 'programa_sintetico.json'
        pk = self.copia(cambio)
        prog = pk / 'programa_sintetico.json'
        prog.write_text(json.dumps({'status': 'complete', 'contacts': []}), encoding='utf-8')
        d = json.loads((pk / 'entrada_escena.json').read_text(encoding='utf-8'))
        d['assets'].append({'path': 'programa_sintetico.json', 'sha256': _sha(prog), 'bytes': prog.stat().st_size})
        (pk / 'entrada_escena.json').write_text(json.dumps(d), encoding='utf-8')
        (pk / 'compatibilidad_paquete.json').unlink()
        sellar_paquete(ROOT, pk)
        r = PF.revisar(pk)
        self.assertNotIn('CONTACTOS_VACIOS_SIN_PROCEDENCIA', self.codigos(r, 'BLOQUEO'))
        self.assertIn('SIN_CONTACTOS_IK', self.codigos(r, 'AVISO'))

    def test_config_de_camara_de_otra_version_bloquea(self):
        pk = self.copia(archivos={'camara_4g/config.json': lambda c: c.pop('busqueda_acimut_deg')})
        r = PF.revisar(pk)
        fila = next(f for f in r['filas'] if f['codigo'] == 'CONFIG_CAMARA_INCOMPATIBLE')
        self.assertEqual(fila['dato_esperado'], ['busqueda_acimut_deg'])

    def test_plano_sin_fila_y_altura_explicita_bloquean(self):
        def sb(data):
            data['vinetas'][0]['keyframes'][0]['plano'] = 'PLANO_INEXISTENTE'
        def cmds(data):
            data['shot_A']['encuadre'].append(['AERIAL', {}])
        pk = self.copia(archivos={'camara_4g/sb_source.json': sb, 'camara_4g/commands.json': cmds})
        r = PF.revisar(pk)
        self.assertTrue({'PLANO_SIN_FILA', 'ALTURA_EXPLICITA'} <= self.codigos(r, 'BLOQUEO'))

    def test_limites_bloqueados_sin_conectar_es_aviso(self):
        pk = self.copia(lambda d: d['_rules_bridge'].__setitem__('locked_limits_connected', False))
        r = PF.revisar(pk)
        self.assertIn('LIMITES_BLOQUEADOS_SIN_CONECTAR', self.codigos(r, 'AVISO'))
        self.assertEqual(r['estado'], 'APTO_PARA_CONSTRUIR')

    def test_aprobacion_en_la_entrada_bloquea(self):
        pk = self.copia(lambda d: d.__setitem__('production_approved', True))
        self.assertIn('APROBACION_EN_ENTRADA', self.codigos(PF.revisar(pk), 'BLOQUEO'))

    def test_asset_alterado_y_regla_ausente_bloquean(self):
        pk = self.copia(lambda d: d['rules'].pop('slip_max_m_per_frame'))
        (pk / 'adn_entidades.json').write_text('{}', encoding='utf-8')
        r = PF.revisar(pk)
        self.assertTrue({'HASH_DISTINTO', 'REGLA_AUSENTE'} <= self.codigos(r, 'BLOQUEO'))

    def test_claves_de_config_salen_del_codigo_instalado(self):
        claves = PF.claves_config_camara(ROOT)
        for k in ('busqueda_acimut_deg', 'busqueda_factor_distancia', 'reparaciones_max', 'roles_hueso', 'transiciones'):
            self.assertIn(k, claves)

    def test_cli_codigo_de_salida(self):
        self.assertEqual(PF.main([str(self.base)]), 0)
        pk = self.copia(lambda d: d.__setitem__('production_approved', True))
        self.assertEqual(PF.main([str(pk)]), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
