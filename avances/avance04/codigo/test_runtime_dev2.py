"""Only inject the real Blender binary path; assertions and tolerances unchanged."""
import importlib.util,unittest,shutil,sys
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance04_20261107');R=B/'MOTOR_UNICO_20261107';archive=B/'test_outputs_segundo_intento';archive.mkdir()
for rel in ['evidencia/montaje_colores_dev2','evidencia/fixture_negativa_oclusor','paquetes/fixture_negativa_oclusor']:
 p=R/rel
 if p.exists():shutil.move(str(p),str(archive/rel.replace('/','__')))
spec=importlib.util.spec_from_file_location('dev2_runtime',R/'pruebas/test_dev2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.BL='/opt/blender/actual/blender';result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));sys.exit(0 if result.wasSuccessful() else 1)
