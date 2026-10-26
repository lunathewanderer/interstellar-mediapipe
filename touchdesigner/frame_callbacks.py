def onStart():
    from pathlib import Path
    base = me.parent()
    root = Path(base.par.Projectdir.eval())
    script = root / 'touchdesigner' / 'refresh_project.py'
    if script.is_file():
        exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),
             {'project_dir':str(root),'op':op,'auto_start':True})
    else:
        base.op('display_window').par.winopen.pulse()

def onFrameStart(frame):
    base = me.parent()
    base.op('controller').module.state(base).tick(base)

def onExit():
    base = me.parent()
    base.op('controller').module.state(base).close()
