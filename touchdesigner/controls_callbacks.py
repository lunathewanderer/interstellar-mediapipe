def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    runtime = scriptOp.parent().op('controller').module.state(scriptOp.parent())
    scriptOp.copyNumpyArray(runtime.controls)
