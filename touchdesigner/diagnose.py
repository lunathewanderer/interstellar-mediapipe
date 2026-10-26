"""Run inside TD Textport to save shader/operator diagnostics without camera pixels."""
import json
from pathlib import Path
import time

network = op('/project1/galaxy')
if network is None:
    raise RuntimeError('The /project1/galaxy network was not found.')
folder = Path(network.par.Projectdir.eval())
report = {'timestamp': time.time(), 'operators': {}, 'shader_logs': {}}
for node in network.children:
    entry = {'type': type(node).__name__}
    try:
        entry['errors'] = node.errors()
        entry['script_errors'] = node.scriptErrors()
    except Exception as error:
        entry['diagnostic_error'] = str(error)
    report['operators'][node.name] = entry

# Info DAT contains the actual TD/Vulkan shader compiler messages.
# The temporary helper is removed after collecting the text.
helper = network.create(infoDAT, 'galaxy_diagnostics')
try:
    for name in ('galaxy_raw', 'trails', 'glow_horizontal', 'final_composite'):
        node = network.op(name)
        if node is None:
            report['shader_logs'][name] = 'Operator missing'
            continue
        try:
            helper.par.op = node.path
            helper.cook(force=True)
            report['shader_logs'][name] = helper.text
        except Exception as error:
            report['shader_logs'][name] = str(error)
finally:
    helper.destroy()

report_path = folder / 'runtime' / 'td_diagnostics.json'
report_path.parent.mkdir(exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Diagnostic report saved to: ' + str(report_path))
for name, text in report['shader_logs'].items():
    print('\n--- ' + name + ' ---\n' + text)
