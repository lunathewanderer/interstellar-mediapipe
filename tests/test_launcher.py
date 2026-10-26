from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main as launcher
from tools.prepare_touchdesigner import bootstrap


class LauncherTests(unittest.TestCase):
    def test_default_stage_matches_available_renderer(self):
        self.assertEqual(launcher.tracker_arguments([], False), ['--stage', '1'])
        self.assertEqual(launcher.tracker_arguments([], True), ['--stage', '4'])

    def test_tracker_options_are_forwarded_without_duplicate_stage(self):
        args = ['--video', 'clip with spaces.mp4', '--stage=2', '--quality', 'low']
        self.assertEqual(launcher.tracker_arguments(args, True), args)

    def test_bootstrap_quotes_windows_path_with_apostrophe(self):
        root = Path("D:/student's folder/Mediapipe")
        command = bootstrap(root)
        # Parse and execute only the assignment; the TD builder is not executed here.
        assignment = command.split('; ', 1)[0]
        namespace = {}
        exec(assignment, namespace)
        self.assertEqual(namespace['project_dir'], str(root))

    def test_explicit_executable_uses_argument_list_without_shell(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            executable = Path(temporary) / 'TouchDesigner.exe'
            executable.touch()
            project = Path(temporary) / 'project with spaces.toe'
            with patch.object(launcher.subprocess, 'Popen') as process:
                launcher.open_visual_project(project, executable)
                process.assert_called_once_with([str(executable.resolve()), str(project)], cwd=project.parent)

    def test_missing_executable_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            launcher.open_visual_project(Path('GalaxyHands.toe'), Path('missing_td_executable.exe'))

    def test_default_start_without_toe_uses_basic_preview(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            with patch.object(launcher, 'ROOT', Path(directory)), \
                 patch.object(launcher, 'local_python', return_value=Path(directory)/'absent.exe'), \
                 patch.object(launcher, 'installation_status', return_value={
                     'packages': {'numpy': '1', 'cv2': '1', 'mediapipe': '1'}, 'model_present': True}), \
                 patch.object(launcher, 'run_tracker', return_value=0) as tracker:
                self.assertEqual(launcher.main([]), 0)
                tracker.assert_called_once_with(['--stage', '1'])

    def test_saved_toe_is_opened_before_full_tracker(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            (root/'GalaxyHands.toe').touch()
            events = []
            with patch.object(launcher, 'ROOT', root), \
                 patch.object(launcher, 'local_python', return_value=root/'absent.exe'), \
                 patch.object(launcher, 'installation_status', return_value={
                     'packages': {'numpy': '1', 'cv2': '1', 'mediapipe': '1'}, 'model_present': True}), \
                 patch.object(launcher, 'open_visual_project', side_effect=lambda *args: events.append('visual')), \
                 patch.object(launcher, 'run_tracker', side_effect=lambda args: events.append(args) or 0):
                self.assertEqual(launcher.main(['--quality', 'high']), 0)
                self.assertEqual(events, ['visual', ['--quality', 'high', '--stage', '4']])

    def test_missing_model_stops_before_opening_camera(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            with patch.object(launcher, 'local_python', return_value=Path(directory)/'absent.exe'), \
                 patch.object(launcher, 'installation_status', return_value={
                     'packages': {'numpy': '1', 'cv2': '1', 'mediapipe': '1'}, 'model_present': False}), \
                 patch.object(launcher, 'run_tracker') as tracker:
                self.assertEqual(launcher.main([]), 1)
                tracker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
