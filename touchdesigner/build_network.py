"""Build the visual network inside TouchDesigner Textport.

CreateProject.bat copies the bootstrap command for the current project folder.
See README.md for installation and saving GalaxyHands.toe.
"""
from pathlib import Path

root = Path(project_dir).resolve()
if not (root / 'config.json').is_file():
    raise RuntimeError('project_dir must point to the GalaxyHands folder containing config.json.')
host = op('/project1')
previous = host.op('galaxy')
if previous:
    controller = previous.op('controller')
    directory = getattr(previous.par, 'Projectdir', None)
    managed = (controller is not None and directory is not None and
               'from galaxy.bridge import FrameBridge' in controller.text and
               Path(directory.eval()).resolve() == root)
    if not managed:
        raise RuntimeError('/project1/galaxy already exists and was preserved. Rename it before building.')
    suffix = 1
    while host.op(f'galaxy_previous_{suffix}'):
        suffix += 1
    tick = previous.op('frame_tick')
    if tick:
        tick.par.active = False
    previous.name = f'galaxy_previous_{suffix}'
    print(f'Previous Galaxy Hands network preserved as {previous.path}.')
base = host.create(baseCOMP, 'galaxy')
page = base.appendCustomPage('Galaxy')
page.appendStr('Projectdir', label='Project directory')[0].val = str(root)


def setpar(node, name, value):
    par = getattr(node.par, name, None)
    if par is None:
        raise RuntimeError(f'{node.path}: required parameter {name} is missing. Check the TouchDesigner version in README.md.')
    par.val = value


def text(name, relative):
    node = base.create(textDAT, name)
    node.text = (root / relative).read_text(encoding='utf-8')
    return node


try:
    text('controller', 'touchdesigner/controller.py')
    for name in ('webcam', 'controls'):
        callback = text(name + '_callbacks', f'touchdesigner/{name}_callbacks.py')
        node = base.create(scriptTOP, name)
        setpar(node, 'callbacks', callback.path)
    setpar(base.op('controls'), 'format', 'rgba32float')
    callback = text('channels_callbacks', 'touchdesigner/channels_callbacks.py')
    channels = base.create(scriptCHOP, 'gesture_channels')
    setpar(channels, 'callbacks', callback.path)
    base.create(textDAT, 'status').text = 'Waiting for tracker.'
    shaders = {}
    for name in ('galaxy', 'trail', 'glow_h', 'composite'):
        shaders[name] = text(name + '_pixel', f'shaders/{name}.frag')
    raw = base.create(glslTOP, 'galaxy_raw')
    history = base.create(feedbackTOP, 'history')
    trails = base.create(glslTOP, 'trails')
    glow = base.create(glslTOP, 'glow_horizontal')
    # The ordinary GLSL TOP supports only three inputs. The composite needs four.
    final = base.create(glslmultiTOP, 'final_composite')
    output = base.create(nullTOP, 'OUT')
    # Input order is part of the shader interface; do not reorder these wires.
    # OP.setInputs accepts the full ordered list. OP.setInput does not exist.
    raw.setInputs([base.op('controls'), base.op('webcam')])
    history.setInputs([raw])
    trails.setInputs([raw, history, base.op('controls')])
    glow.setInputs([trails, base.op('controls')])
    final.setInputs([base.op('webcam'), trails, glow, base.op('controls')])
    output.setInputs([final])
    window = base.create(windowCOMP, 'display_window')
    setpar(window, 'winop', output.path)
    setpar(history, 'top', trails.path)
    setpar(history, 'reset', False)
    for node, shader in ((raw, 'galaxy'), (trails, 'trail'), (glow, 'glow_h'), (final, 'composite')):
        setpar(node, 'pixeldat', shaders[shader].path)
        setpar(node, 'glslversion', 'glsl460')
        setpar(node, 'format', 'rgba16float')
        setpar(node, 'outputresolution', 'custom')
        node.par.resolutionw.expr = "int(op('controller').module.state(parent()).controls[0,8,0]) or 960"
        node.par.resolutionh.expr = "int(op('controller').module.state(parent()).controls[0,8,1]) or 540"
    # Execute DAT IS the callbacks DAT: put the full contents in that operator.
    execute = base.create(executeDAT, 'frame_tick')
    setpar(execute, 'active', False)
    execute.text = (root / 'touchdesigner/frame_callbacks.py').read_text(encoding='utf-8')
    for name in ('create', 'frameend', 'playstatechange', 'devicechange'):
        setpar(execute, name, False)
    setpar(execute, 'start', True)
    setpar(execute, 'framestart', True)
    setpar(execute, 'exit', True)
    callback = text('keyboard_callbacks', 'touchdesigner/keyboard_callbacks.py')
    keyboard = base.create(keyboardinDAT, 'keyboard')
    setpar(keyboard, 'callbacks', callback.path)
    output.viewer = True
    nodes = list(base.children)
    for i, node in enumerate(nodes):
        node.nodeX = (i % 6) * 210
        node.nodeY = -(i // 6) * 150
    base.op('controller').module.state(base).tick(base)
    history.par.resetpulse.pulse()
    setpar(execute, 'active', True)
    window.par.winopen.pulse()
    print('Galaxy network created. Right-click OUT -> View. Save As GalaxyHands.toe in project_dir.')
    print('Run diagnostics in Textport: op("/project1/galaxy/OUT").errors(recurse=True)')
except Exception:
    print('Build stopped. The partial galaxy component was kept for diagnosis; see the traceback below.')
    raise
