"""Verify local project structure, source syntax, DAT assets and Markdown links."""
import ast
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def main():
    files=[ROOT/'main.py',ROOT/'app.py',*(ROOT/'galaxy').glob('*.py'),*(ROOT/'touchdesigner').glob('*.py'),
           *(ROOT/'tools').glob('*.py'),*(ROOT/'tests').glob('*.py')]
    for path in files:
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    for path in (ROOT/'config.json',ROOT/'models'/'source.json'):
        json.loads(path.read_text(encoding='utf-8'))
    for path in [ROOT/'README.md',*(ROOT/'docs').glob('*.md')]:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):
                assert (path.parent/link.split('#')[0]).is_file(), (path,link)
    builder=(ROOT/'touchdesigner'/'build_network.py').read_text()
    for name in ('webcam_callbacks.py','controls_callbacks.py','channels_callbacks.py',
                 'frame_callbacks.py','keyboard_callbacks.py','controller.py'):
        assert (ROOT/'touchdesigner'/name).is_file()
    for name in ('galaxy','trail','glow_h','composite'):
        text=(ROOT/'shaders'/f'{name}.frag').read_text()
        assert 'TDOutputSwizzle' in text and 'layout(location = 0)' in text
        assert '#version' not in text
    print(f'PASS: {len(files)} Python files parse; JSON, local documentation links and TD shader/callback assets valid')


if __name__=='__main__':
    main()
