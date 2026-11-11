# -*- coding: utf-8 -*-
"""CPU, US$0. Cámara v2 solo manda si calza con el SB/v1 o es más nueva que v1."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camara_vigente as CV


def _dump(p: Path, vinetas, extra=None):
    d = {"vinetas": vinetas}
    if extra:
        d.update(extra)
    p.write_text(json.dumps(d), encoding='utf-8')


def _v(i, t0, t1, obj=None):
    v = {"vineta": i, "t_abs": [t0, t1]}
    if obj:
        v["objetivo"] = obj
    return v


class TestCamaraVigente(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.d = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_sin_v2(self):
        ok, m = CV.v2_es_vigente(self.d / "no_existe.json")
        self.assertFalse(ok)
        self.assertEqual(m, "sin_v2")

    def test_calza_con_sb_y_v1(self):
        vins = [_v("v1", 0, 3, "ch-a"), _v("v2", 3, 8, "ch-b")]
        sb = [_v("v1", 0, 3), _v("v2", 3, 8)]  # SB a menudo sin objetivo
        _dump(self.d / "v2.json", vins)
        _dump(self.d / "v1.json", vins)
        _dump(self.d / "sb.json", [{"id": "v1", "t": [0, 3]}, {"id": "v2", "t": [3, 8]}])
        ok, m = CV.v2_es_vigente(self.d / "v2.json", self.d / "v1.json", self.d / "sb.json")
        self.assertTrue(ok, m)
        self.assertEqual(m, "calza_con_sb")

    def test_ids_distintos_no_calza(self):
        _dump(self.d / "v2.json", [_v("v1", 0, 3, "ch-a"), _v("v2", 3, 8, "ch-b")])
        _dump(self.d / "v1.json", [_v("v1", 0, 3, "ch-a"), _v("v2", 3, 8, "ch-b"), _v("v3", 8, 12, "ch-a")])
        _dump(self.d / "sb.json", [{"id": "v1", "t": [0, 3]}, {"id": "v2", "t": [3, 8]}, {"id": "v3", "t": [8, 12]}])
        # v2 más viejo que v1
        os.utime(self.d / "v2.json", (1, 1))
        os.utime(self.d / "v1.json", (100, 100))
        ok, m = CV.v2_es_vigente(self.d / "v2.json", self.d / "v1.json", self.d / "sb.json")
        self.assertFalse(ok)
        self.assertIn("ids_distintos", m)

    def test_t_y_objetivo_viejos_no_calzan(self):
        # patrón: v2 vieja con otra partición y otro sujeto
        _dump(self.d / "v2.json", [_v("v5", 18, 21, "ch-tarde")])
        _dump(self.d / "v1.json", [_v("v5", 15, 23, "ch-temprano")])
        _dump(self.d / "sb.json", [{"id": "v5", "t": [15, 23], "director_imagen": {"en_cuadro": [{"id": "ch-temprano"}]}}])
        os.utime(self.d / "v2.json", (1, 1))
        os.utime(self.d / "v1.json", (100, 100))
        ok, m = CV.v2_es_vigente(self.d / "v2.json", self.d / "v1.json", self.d / "sb.json")
        self.assertFalse(ok)
        self.assertTrue("t_distinto" in m or "ids_distintos" in m)

    def test_v2_mas_nueva_manda_aunque_no_calce(self):
        _dump(self.d / "v2.json", [_v("v1", 0, 10, "ch-a")])
        _dump(self.d / "v1.json", [_v("v1", 0, 3, "ch-b"), _v("v2", 3, 8, "ch-a")])
        _dump(self.d / "sb.json", [{"id": "v1", "t": [0, 3]}, {"id": "v2", "t": [3, 8]}])
        now = time.time()
        os.utime(self.d / "v1.json", (now - 100, now - 100))
        os.utime(self.d / "v2.json", (now, now))
        ok, m = CV.v2_es_vigente(self.d / "v2.json", self.d / "v1.json", self.d / "sb.json")
        self.assertTrue(ok)
        self.assertEqual(m, "v2_mas_nueva_que_v1")

    def test_objetivo_distinto_con_mismos_tiempos(self):
        _dump(self.d / "v2.json", [_v("v1", 0, 5, "ch-a")])
        _dump(self.d / "v1.json", [_v("v1", 0, 5, "ch-b")])
        _dump(self.d / "sb.json", [{"id": "v1", "t": [0, 5]}])
        os.utime(self.d / "v2.json", (1, 1))
        os.utime(self.d / "v1.json", (100, 100))
        ok, m = CV.v2_es_vigente(self.d / "v2.json", self.d / "v1.json", self.d / "sb.json")
        self.assertFalse(ok)
        self.assertIn("objetivo_distinto", m)

    def test_solo_v2_se_usa(self):
        _dump(self.d / "v2.json", [_v("v1", 0, 5, "ch-a")])
        ok, m = CV.v2_es_vigente(self.d / "v2.json", None, None)
        self.assertTrue(ok)
        self.assertEqual(m, "solo_esta_v2")


if __name__ == "__main__":
    unittest.main()
