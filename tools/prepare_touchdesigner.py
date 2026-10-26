"""Prepare a portable one-line TD bootstrap; --print-only never changes clipboard."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def bootstrap(root, update=False):
    # repr safely quotes Windows paths, including spaces, Unicode and apostrophes.
    script = 'refresh_project.py' if update else 'build_network.py'
    return (f'project_dir = {str(root)!r}; '
            f"builder = project_dir + '/touchdesigner/{script}'; "
            "exec(compile(open(builder, encoding='utf-8').read(), builder, 'exec'))")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--print-only', action='store_true')
    parser.add_argument('--update', action='store_true', help='Refresh an existing saved TD project')
    args = parser.parse_args()
    command = bootstrap(ROOT, args.update)
    if args.print_only:
        print(command)
        return
    # Explicitly invoked by CreateProject.bat; no clipboard change during normal startup.
    subprocess.run(['clip.exe'], input=command.encode('utf-16'), check=True)
    print('The project update command has been copied.' if args.update else 'The project setup command has been copied to the clipboard.')
    print('Open TouchDesigner -> Dialogs -> Textport -> Ctrl+V -> Enter.')
    print('Press Ctrl+S to save the updated project in:' if args.update else 'Then save the project as GalaxyHands.toe in:')
    print(ROOT)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
