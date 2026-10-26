"""Download Google's numbered model revision. No webcam access."""
from pathlib import Path
import hashlib
import json
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'


def main():
    target = ROOT / 'models' / 'hand_landmarker.task'
    target.parent.mkdir(exist_ok=True)
    temporary = target.with_suffix('.download')
    try:
        print('Downloading official model revision 1 ...', flush=True)
        with urllib.request.urlopen(URL, timeout=60) as source, temporary.open('wb') as output:
            while chunk := source.read(1024 * 1024):
                output.write(chunk)
        if temporary.stat().st_size < 1_000_000 or not zipfile.is_zipfile(temporary):
            raise ValueError('Download is not a valid MediaPipe task ZIP bundle.')
        with zipfile.ZipFile(temporary) as bundle:
            if bundle.testzip() is not None:
                raise ValueError('Model ZIP failed its CRC check.')
            if not {'hand_detector.tflite', 'hand_landmarks_detector.tflite'}.issubset(set(bundle.namelist())):
                raise ValueError('Wrong model: expected hand detector and landmark detector.')
        checksum = hashlib.sha256(temporary.read_bytes()).hexdigest()
        known = ROOT / 'models' / 'source.json'
        if known.exists():
            expected = json.loads(known.read_text())['sha256']
            if checksum != expected:
                raise ValueError('Model SHA-256 differs from the project manifest. Keep the existing model; investigate the download.')
        temporary.replace(target)
        known.write_text(json.dumps({'url': URL, 'sha256': checksum, 'bytes': target.stat().st_size}, indent=2) + '\n')
        print(f'Saved {target}\nSHA-256: {checksum}')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: Model download failed: {error}\nCheck Internet access or retry from PowerShell.', file=sys.stderr)
        sys.exit(1)
