import bpy,sys,shutil,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from entrada import leer,guardar
import camara
args=sys.argv[sys.argv.index('--')+1:];pk=Path(args[0]);out=Path(args[1]);data=leer(pk/'entrada.json');bpy.ops.wm.open_mainfile(filepath=str(out/'escena.blend'));sc=bpy.context.scene
cam,report=camara.crear(sc,data['camera'],leer(out/'trazas.json'),{a['id']:a for a in data['actors']},data['fps']);guardar(out/'camara_actualizada.json',report);shutil.copy2(out/'escena.blend',out/('antes_seguimiento_'+str(time.time_ns())+'.blend'));bpy.ops.wm.save_as_mainfile(filepath=str(out/'escena.blend'))
