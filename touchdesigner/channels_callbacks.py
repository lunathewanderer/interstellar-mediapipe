def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    scriptOp.clear()
    scriptOp.numSamples = 1
    runtime = scriptOp.parent().op('controller').module.state(scriptOp.parent())
    for name, value in runtime.channels.items():
        scriptOp.appendChan(name)[0] = float(value)
