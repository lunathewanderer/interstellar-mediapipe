"""Run inside TD Textport. Repair the four-input compositor without rebuilding."""
from pathlib import Path

network = op('/project1/galaxy')
if network is None:
    raise RuntimeError('The /project1/galaxy network was not found.')
folder = Path(network.par.Projectdir.eval())
required = ('webcam', 'trails', 'glow_horizontal', 'controls', 'OUT', 'composite_pixel')
missing = [name for name in required if network.op(name) is None]
if missing:
    raise RuntimeError('The existing network is incomplete: ' + ', '.join(missing))

composite = network.op('final_composite')
if composite is not None and not isinstance(composite, glslmultiTOP):
    suffix = 1
    while network.op(f'final_composite_previous_{suffix}'):
        suffix += 1
    composite.name = f'final_composite_previous_{suffix}'
    print('Original compositor preserved as ' + composite.path)
    composite = None
if composite is None:
    composite = network.create(glslmultiTOP, 'final_composite')

network.op('composite_pixel').text = (folder / 'shaders' / 'composite.frag').read_text(encoding='utf-8')
composite.setInputs([network.op(name) for name in ('webcam', 'trails', 'glow_horizontal', 'controls')])
composite.par.pixeldat = network.op('composite_pixel').path
composite.par.glslversion = 'glsl460'
composite.par.format = 'rgba16float'
composite.par.outputresolution = 'custom'
composite.par.resolutionw.expr = "int(op('controller').module.state(parent()).controls[0,8,0]) or 960"
composite.par.resolutionh.expr = "int(op('controller').module.state(parent()).controls[0,8,1]) or 540"
composite.par.compilebehavior = 'stalluntildone'
network.op('OUT').setInputs([composite])
composite.cook(force=True)

# Refresh the real TD compiler report after the repair.
diagnostic_script = folder / 'touchdesigner' / 'diagnose.py'
exec(compile(diagnostic_script.read_text(encoding='utf-8'), str(diagnostic_script), 'exec'))
failed = [name for name, log in report['shader_logs'].items()
          if 'Compiled Successfully' not in log or 'ERROR:' in log]
if failed:
    print('The repair was applied, but these shaders need attention: ' + ', '.join(failed))
else:
    print('All four shaders compiled successfully in TouchDesigner.')
    print('Save this project as ' + str(folder / 'GalaxyHands.toe'))
    print('Then start Run.bat to see the webcam galaxy. A black screen is expected until tracking starts.')
