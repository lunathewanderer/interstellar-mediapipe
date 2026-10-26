"""Start Galaxy Hands. Uses this folder's environment automatically when available."""
import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description='Open the saved TouchDesigner application and start MediaPipe.',
        epilog='Tracker options also work: --video FILE, --synthetic, --quality low|medium|high, --camera N.')
    parser.add_argument('--tracker-only', action='store_true', help='Open the basic webcam/core preview without TouchDesigner')
    parser.add_argument('--check', action='store_true', help='Check installation without opening the webcam or other applications')
    parser.add_argument('--prepare-touchdesigner', action='store_true', help='Copy the one-time TouchDesigner setup command')
    parser.add_argument('--touchdesigner-exe', type=Path, help='Optional TouchDesigner.exe path if the .toe file association is missing')
    return parser.parse_known_args(argv)


def local_python(root=ROOT):
    return root / '.venv' / 'Scripts' / 'python.exe'


def installation_status(root=ROOT):
    packages = {}
    for module, distribution in (('numpy', 'numpy'), ('cv2', 'opencv-contrib-python'), ('mediapipe', 'mediapipe')):
        try:
            packages[module] = importlib.metadata.version(distribution) if importlib.util.find_spec(module) else None
        except (ImportError, importlib.metadata.PackageNotFoundError, ValueError):
            packages[module] = None
    return {'python': sys.version.split()[0], 'interpreter': sys.executable,
            'packages': packages, 'model_present': (root / 'models' / 'hand_landmarker.task').is_file(),
            'touchdesigner_project_present': (root / 'GalaxyHands.toe').is_file(),
            'project_folder': str(root)}


def open_visual_project(project_file, executable=None):
    if executable is not None:
        executable = executable.expanduser().resolve()
        if not executable.is_file():
            raise FileNotFoundError(f'TouchDesigner executable not found: {executable}')
        # Argument list, no shell interpolation; paths with spaces remain safe.
        subprocess.Popen([str(executable), str(project_file)], cwd=project_file.parent)
    else:
        if os.name != 'nt':
            raise RuntimeError('The TouchDesigner launcher requires Windows.')
        os.startfile(str(project_file))


def tracker_arguments(arguments, full_visuals):
    result = list(arguments)
    if not any(arg == '--stage' or arg.startswith('--stage=') for arg in result):
        result += ['--stage', '4' if full_visuals else '1']
    return result


def run_tracker(arguments):
    previous_argv = sys.argv
    try:
        sys.argv = [str(ROOT / 'app.py'), *arguments]
        # Same process as the launcher: app.py remains the sole camera owner.
        runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')
        return 0
    finally:
        sys.argv = previous_argv


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    options, tracker_options = parse_arguments(arguments)
    if options.prepare_touchdesigner:
        from tools.prepare_touchdesigner import main as prepare
        previous_argv = sys.argv
        try:
            sys.argv = [str(ROOT / 'tools' / 'prepare_touchdesigner.py')]
            prepare()
        finally:
            sys.argv = previous_argv
        return 0
    environment_python = local_python()
    if environment_python.is_file() and Path(sys.executable).resolve() != environment_python.resolve():
        return subprocess.call([str(environment_python), str(ROOT / 'main.py'), *arguments], cwd=ROOT)
    status = installation_status()
    if options.check:
        print(json.dumps(status, indent=2))
        return 0 if all(status['packages'].values()) and status['model_present'] else 1
    if not all(status['packages'].values()):
        print('Setup is incomplete. Double-click Install.bat, then run main.py again.', file=sys.stderr)
        return 1
    if '--synthetic' not in tracker_options and not status['model_present']:
        print('MediaPipe model is missing. Double-click Install.bat to download it.', file=sys.stderr)
        return 1
    full_visuals = False
    project_file = ROOT / 'GalaxyHands.toe'
    if not options.tracker_only and project_file.is_file():
        try:
            open_visual_project(project_file, options.touchdesigner_exe)
            full_visuals = True
            print('Opening the saved TouchDesigner project and starting MediaPipe.', flush=True)
        except (OSError, RuntimeError) as error:
            print(f'Could not open TouchDesigner: {error}', flush=True)
            print('Opening the basic tracker preview instead. Install TouchDesigner or use --touchdesigner-exe.', flush=True)
    elif not options.tracker_only:
        print('Opening the basic MediaPipe webcam/core preview.', flush=True)
        print('For the full galaxy, run CreateProject.bat once and save GalaxyHands.toe in this folder.', flush=True)
    return run_tracker(tracker_arguments(tracker_options, full_visuals))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nStopped.')
        sys.exit(130)
