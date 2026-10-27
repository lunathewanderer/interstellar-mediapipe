"""Refresh a managed, complete network in place; run INSIDE TouchDesigner."""
from pathlib import Path
import importlib
import json
import sys
import time


def refresh(folder, lookup, auto_start=False):
    root=Path(folder).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    base=lookup('/project1/galaxy')
    if base is None or Path(base.par.Projectdir.eval()).resolve()!=root:
        raise RuntimeError('Open your saved GalaxyHands.toe first, or run CreateProject.bat.')
    paths={
        'controller':'touchdesigner/controller.py',
        'webcam_callbacks':'touchdesigner/webcam_callbacks.py',
        'controls_callbacks':'touchdesigner/controls_callbacks.py',
        'channels_callbacks':'touchdesigner/channels_callbacks.py',
        'keyboard_callbacks':'touchdesigner/keyboard_callbacks.py',
        'frame_tick':'touchdesigner/frame_callbacks.py',
        'galaxy_pixel':'shaders/galaxy.frag', 'trail_pixel':'shaders/trail.frag',
        'glow_h_pixel':'shaders/glow_h.frag', 'composite_pixel':'shaders/composite.frag',
    }
    shader_nodes={'galaxy_raw':'galaxy_pixel','trails':'trail_pixel',
                  'glow_horizontal':'glow_h_pixel','final_composite':'composite_pixel'}
    required=set(paths)|set(shader_nodes)|{'history','OUT','webcam','controls','gesture_channels','keyboard','display_window'}
    missing=sorted(name for name in required if base.op(name) is None)
    if missing:
        raise RuntimeError('Incomplete project; use CreateProject.bat. Missing: '+', '.join(missing))
    if type(base.op('final_composite')).__name__!='glslmultiTOP':
        raise RuntimeError('Rebuild with CreateProject.bat; the four-input compositor requires GLSL Multi TOP.')
    sources={name:(root/relative).read_text(encoding='utf-8') for name,relative in paths.items()}
    for name,relative in paths.items():
        if relative.endswith('.py'):
            compile(sources[name],relative,'exec')
    changed=any(base.op(name).text!=source for name,source in sources.items())
    originals={name:base.op(name).text for name in paths}
    old_pixels={name:base.op(name).par.pixeldat.eval() for name in shader_nodes}
    # Make a source-only recovery snapshot before touching the embedded DATs.
    if changed:
        backup=root/'runtime'/'td_source_backups'
        backup.mkdir(parents=True,exist_ok=True)
        (backup/f'{time.time_ns()}.json').write_text(json.dumps(
            originals,indent=2),encoding='utf-8')
    tick=base.op('frame_tick')
    tick.par.active=False
    old_module=base.op('controller').module
    if getattr(old_module,'_runtime',None) is not None:
        old_module._runtime.close()
        old_module._runtime=None
    try:
        import galaxy.settings
        importlib.reload(galaxy.settings)
        for name,source in sources.items():
            if base.op(name).text!=source:
                base.op(name).text=source
        # Fix callback/pixel DAT references, including previously repaired nodes.
        for name in ('webcam','controls'):
            base.op(name).par.callbacks=base.op(name+'_callbacks').path
        base.op('gesture_channels').par.callbacks=base.op('channels_callbacks').path
        base.op('keyboard').par.callbacks=base.op('keyboard_callbacks').path
        for name,shader in shader_nodes.items():
            node=base.op(name)
            node.par.pixeldat=base.op(shader).path
            node.par.compilebehavior='stalluntildone'
        base.op('controller').module.state(base).tick(base)
        base.op('history').par.resetpulse.pulse()
        for name in shader_nodes:
            base.op(name).cook(force=True)
        errors=base.op('OUT').errors(recurse=True)
        if errors:
            raise RuntimeError('TouchDesigner reported: '+str(errors))
        base.op('display_window').par.winopen.pulse()
    except Exception:
        # Restore the in-memory document if a TD cook or assignment fails.
        runtime=getattr(base.op('controller').module,'_runtime',None)
        if runtime is not None:
            runtime.close()
        for name,source in originals.items():
            base.op(name).text=source
        base.op('controller').module._runtime=None
        for name,source in old_pixels.items():
            base.op(name).par.pixeldat=source
        print('Update stopped and embedded sources restored. Recovery copies: runtime/td_source_backups.')
        raise
    finally:
        tick.par.active=True
    print('Galaxy Hands updated: adaptive tracking, snap lighting and intricate galaxy.')
    if not auto_start:
        print('Press Ctrl+S to save GalaxyHands.toe. Then run Run.bat.')
    return changed


if 'project_dir' in globals():
    refresh(project_dir,op,globals().get('auto_start',False))
