def onKey(dat, key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time):
    if not state or ctrl or alt:
        return
    value = character.lower() if character else key.lower()
    if value in ('escape', 'esc'):
        value = '\x1b'
    if value in ('q', '\x1b', 'd', 'r', 'c', '+', '=', '-'):
        base = dat.parent()
        base.op('controller').module.state(base).command(value)
        if value in ('q', '\x1b'):
            ui.performMode = False  # Leave the unsaved project available in the editor.

def onShortcut(dat, shortcutName, time):
    return
