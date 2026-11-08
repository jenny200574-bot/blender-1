from pathlib import Path
r=Path("/opt/myia-motor-v9/avance08_20261107")
p=r/"entrega/codigo/fisica_final_offset_publico_prueba08.py"
s=(r/"respaldos/fisica_final_antes_avance_float32.py").read_text()
old="                count+=1;origin=hit[0]+ray*1e-7"
new="""                count+=1
                # Numeric ray-origin progress only; physical tolerances unchanged.
                advance=max(1e-7,max(1.0,*(abs(v) for v in hit[0]))*(2**-20))
                if advance>rules['penetration_tolerance_m']/16:
                    raise ValueError('PRECISION_FLOAT32_INSUFICIENTE para tolerancia suministrada')
                origin=hit[0]+ray*advance"""
assert s.count(old)==1
p.write_text(s.replace(old,new))
print("Scale-aware candidate only; fail closed at inadequate float32 precision")
