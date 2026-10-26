"""The only camera owner. Run from PowerShell; TouchDesigner only reads the bridge."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

from galaxy.settings import ROOT, load_config


def arguments():
    parser = argparse.ArgumentParser(description='Local MediaPipe -> TouchDesigner galaxy controller')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--video', type=Path, help='Prerecorded local video instead of webcam')
    source.add_argument('--synthetic', action='store_true', help='Fake hands + grid; no model or camera')
    parser.add_argument('--camera', type=int, help='Override config camera index')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--no-preview', action='store_true', help='No OpenCV window; console keys still work')
    parser.add_argument('--frames', type=int, default=0, help='Stop after N frames; 0 = unlimited')
    parser.add_argument('--loop', action='store_true', help='Loop video with monotonically increasing task timestamps')
    parser.add_argument('--stage', type=int, choices=(1, 2, 3, 4))
    parser.add_argument('--quality', choices=('low', 'medium', 'high'))
    return parser.parse_args()


def synthetic_hands(t):
    """Deliberately fake landmarks, labelled as such in the image and metadata."""
    import numpy as np
    hands = []
    two = (int(t / 5) % 2) == 1
    for i in range(2 if two else 1):
        x = .5 + .23 * math.sin(t * .65) if not two else .28 + .44 * i
        y = .53 + .12 * math.cos(t * .75 + i)
        p = np.tile([x, y, 0.], (21, 1))
        for finger in range(5):
            for joint in range(4):
                p[1 + finger * 4 + joint] = [x + (finger - 2) * .025, y - .025 * (joint + 1), 0]
        p[0] = [x, y + .08, 0]
        p[9] = [x, y - .03, 0]
        # Alternates pinch/open every two seconds; wrists stay continuous.
        p[4] = p[8] + np.array([.012 if int(t / 2) % 2 == 0 else .10, 0, 0])
        hands.append({'points': p, 'label': 'Left' if i == 0 else 'Right', 'score': 1.})
    return hands


def read_command(path, previous):
    try:
        command = json.loads(path.read_text(encoding='utf-8'))
        if command['id'] != previous:
            return command.get('key', ''), command['id']
    except (OSError, ValueError, KeyError):
        pass
    return '', previous


def main():
    args = arguments()
    cfg = load_config(args.config)
    if args.stage:
        cfg['visual']['stage'] = args.stage
    if args.quality:
        cfg['visual']['quality'] = args.quality
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise RuntimeError('Missing packages. Run .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt') from error
    from galaxy.bridge import FrameBridge
    from galaxy.gestures import GestureEngine
    model = ROOT / cfg['model']
    if not args.synthetic and not model.is_file():
        raise RuntimeError(f'Model missing: {model}. Run .\\.venv\\Scripts\\python.exe tools/download_model.py')
    ROOT.joinpath('runtime').mkdir(exist_ok=True)
    command_file = ROOT / 'runtime' / 'command.json'
    # Ignore an old quit command from the preceding session.
    _, command_id = read_command(command_file, None)
    engine, cap, landmarker = GestureEngine(cfg), None, None
    bridge = FrameBridge(writer=True)
    qualities = list(cfg['quality_presets'])
    quality = cfg['visual']['quality']
    epoch, debug, frame_id, previous_ms = 0, False, 0, -1
    started, next_frame, last_report = time.monotonic(), time.monotonic(), time.monotonic()
    session = f'{time.time_ns()}'
    width, height = 640, 360
    try:
        if not args.synthetic:
            cache = ROOT / 'runtime' / 'matplotlib'
            cache.mkdir(exist_ok=True)
            os.environ.setdefault('MPLCONFIGDIR', str(cache))
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            options = vision.HandLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.VIDEO, num_hands=2,
                min_hand_detection_confidence=cfg['tracking']['detection_confidence'],
                min_hand_presence_confidence=cfg['tracking']['presence_confidence'],
                min_tracking_confidence=cfg['tracking']['tracking_confidence'])
            landmarker = vision.HandLandmarker.create_from_options(options)
            if args.video:
                cap = cv2.VideoCapture(str(args.video.resolve()))
            else:
                index = args.camera if args.camera is not None else cfg['camera']['index']
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg['camera']['width'])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg['camera']['height'])
                cap.set(cv2.CAP_PROP_FPS, cfg['camera']['fps'])
            if not cap.isOpened():
                raise RuntimeError('Cannot open input. Check video path/camera index, Windows camera privacy, and close Teams/Camera/Zoom.')
            if not args.video and cfg['tracking']['latest_frame_capture']:
                from galaxy.capture import LatestFrameCapture
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap = LatestFrameCapture(cap)
        fps = cfg['camera']['fps']
        if args.video:
            fps = cap.get(cv2.CAP_PROP_FPS)
        fps = fps if math.isfinite(fps) and 1 <= fps <= 120 else 30
        print('Galaxy Hands started. q/Esc quit | c lighting | d debug | r reset | +/- quality', flush=True)
        print('Input:', 'SYNTHETIC (no tracking)' if args.synthetic else str(args.video or 'webcam'), flush=True)
        while not args.frames or frame_id < args.frames:
            now = time.monotonic()
            key, command_id = read_command(command_file, command_id)
            if not args.no_preview:
                pressed = cv2.waitKey(1) & 0xff
                if pressed != 255:
                    key = chr(pressed)
            else:
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getwch()
            if key.lower() in ('q', 'escape', 'esc', '\x1b'):
                break
            if key.lower() == 'd':
                debug = not debug
            if key.lower() == 'r':
                epoch += 1
                engine = GestureEngine(cfg)
            if key.lower() == 'c':
                engine.cycle_palette(now)
            if key in ('+', '=', '-'):
                i = qualities.index(quality) + (-1 if key == '-' else 1)
                quality = qualities[max(0, min(len(qualities) - 1, i))]
                print('Quality:', quality, flush=True)
            preset = cfg['quality_presets'][quality]
            width, height = preset['width'], preset['height']
            elapsed = now - started
            if args.synthetic:
                frame = np.zeros((height, width, 3), np.uint8)
                frame[:, :, :] = (24, 19, 15)
                for x in range(0, width, max(1, width // 16)):
                    cv2.line(frame, (x, 0), (x, height - 1), (45, 39, 34), 1)
                for y in range(0, height, max(1, height // 9)):
                    cv2.line(frame, (0, y), (width - 1, y), (45, 39, 34), 1)
                detections = synthetic_hands(elapsed)
            else:
                ok, frame = cap.read()
                if not ok and args.video and args.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = cap.read()
                if not ok:
                    if args.video and frame_id:
                        print('End of video.', flush=True)
                        break
                    raise RuntimeError('Input opened but returned no frame. Check camera permissions, USB connection or video codec.')
                # Preserve geometry by letterboxing rather than stretching 4:3 cameras.
                h, w = frame.shape[:2]
                ratio = min(width / w, height / h)
                resized = cv2.resize(frame, (max(1, round(w * ratio)), max(1, round(h * ratio))))
                frame = np.zeros((height, width, 3), np.uint8)
                rh, rw = resized.shape[:2]
                y, x = (height - rh) // 2, (width - rw) // 2
                frame[y:y + rh, x:x + rw] = resized
                iw = min(width, cfg['tracking']['inference_width'])
                inference = cv2.resize(frame, (iw, max(1, round(height * iw / width))))
                rgb = np.ascontiguousarray(cv2.cvtColor(inference, cv2.COLOR_BGR2RGB))
                timestamp_ms = max(previous_ms + 1, round(elapsed * 1000))
                previous_ms = timestamp_ms
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
                detections = []
                for points, categories in zip(result.hand_landmarks, result.handedness):
                    detections.append({'points': [[p.x, p.y, p.z] for p in points],
                        'label': categories[0].category_name, 'score': categories[0].score})
            controls = engine.update(detections, now, width / height, cfg['camera']['mirror'])
            if cfg['camera']['mirror']:
                frame = cv2.flip(frame, 1)
            if args.synthetic:
                cv2.putText(frame, 'SYNTHETIC INPUT - NOT A CAMERA TEST', (18, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (180, 200, 220), 1, cv2.LINE_AA)
            if debug:
                for hand in controls['hands']:
                    points = [(round(p[0] * (width - 1)), round((1 - p[1]) * (height - 1)))
                              for p in hand['landmarks']]
                    for finger in ([0,1,2,3,4], [0,5,6,7,8], [0,9,10,11,12], [0,13,14,15,16], [0,17,18,19,20], [5,9,13,17]):
                        for a, b in zip(finger, finger[1:]):
                            cv2.line(frame, points[a], points[b], (170, 150, 70), 1, cv2.LINE_AA)
                    for point in points:
                        cv2.circle(frame, point, 2, (230, 220, 160), -1, cv2.LINE_AA)
                    label = f"{hand['label']} #{hand['id']} pinch={hand['pinched']} snap={'READY' if hand['snap_armed'] else 'waiting'}"
                    cv2.putText(frame, label, points[0], cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
                cv2.putText(frame, f"hands={controls['hand_count']} {quality} | {controls['palette']} | C: lighting",
                            (12, height - 14), cv2.FONT_HERSHEY_SIMPLEX, .45, (220, 230, 240), 1)
            frame_id += 1
            metadata = dict(controls, width=width, height=height, frame_id=frame_id, session=session,
                timestamp=time.time(), running=True, synthetic=args.synthetic, debug=debug,
                epoch=epoch, quality=quality, preset=preset, visual=cfg['visual'],
                momentum=cfg['gestures']['momentum'])
            rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            bridge.write(metadata, rgba.tobytes())
            if not args.no_preview:
                preview = frame.copy()
                # First milestone only; the complete visual renderer is TouchDesigner.
                if cfg['visual']['stage'] == 1:
                    px, py = round(controls['center_x'] * width), round((1 - controls['center_y']) * height)
                    overlay = preview.copy()
                    cv2.circle(overlay, (px, py), 12, (255, 245, 235), -1, cv2.LINE_AA)
                    preview = cv2.addWeighted(preview, 1., cv2.subtract(overlay, preview), controls['visibility'], 0)
                cv2.imshow('Galaxy Hands - tracker preview (final galaxy is in TouchDesigner)', preview)
                if cv2.getWindowProperty('Galaxy Hands - tracker preview (final galaxy is in TouchDesigner)', cv2.WND_PROP_VISIBLE) < 1:
                    break
            if now - last_report > 2:
                print(f"frame={frame_id} hands={controls['hand_count']} pinch={controls['pinch']:.2f} {controls['palette']} quality={quality}", flush=True)
                last_report = now
            next_frame += 1 / fps
            delay = next_frame - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            elif delay < -.25:
                next_frame = time.monotonic()  # No catch-up burst when inference is slow.
    finally:
        # Remove the last image from the shared segment even while TD is still open.
        try:
            bridge.write({'width': width, 'height': height, 'running': False, 'timestamp': time.time(),
                          'session': session, 'frame_id': frame_id + 1}, bytes(width * height * 4))
        finally:
            bridge.close()
            if cap is not None:
                cap.release()
            if landmarker is not None:
                landmarker.close()
            cv2.destroyAllWindows()
    print('Stopped; camera released and shared image cleared.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped by Ctrl+C.')
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
