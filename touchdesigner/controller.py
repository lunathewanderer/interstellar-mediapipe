"""Loaded as the controller Text DAT module. Only NumPy + Python stdlib in TD."""
import json
import math
from pathlib import Path
import sys
import time
import numpy as np

_runtime = None


def state(base):
    global _runtime
    if _runtime is None:
        root = Path(base.par.Projectdir.eval())
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        _runtime = Runtime(root)
    return _runtime


class Runtime:
    def __init__(self, root):
        from galaxy.bridge import FrameBridge
        from galaxy.settings import load_config
        self.root = root
        self.cfg = load_config(root / 'config.json')
        self.bridge = FrameBridge()
        self.meta = {}
        self.image = np.zeros((360, 640, 4), dtype=np.uint8)
        self.controls = np.zeros((1, 16, 4), dtype=np.float32)
        self.started = self.previous = time.monotonic()
        self.last_frame = None
        self.reset_key = None
        self.status = 'Waiting for tracker. Start app.py in PowerShell.'
        self.channels = {}
        self.stopped = False

    def tick(self, base):
        now = time.monotonic()
        dt = min(max(now - self.previous, .001), .1)
        self.previous = now
        snapshot = self.bridge.read()
        if snapshot:
            metadata, pixels = snapshot
            fid = (metadata['session'], metadata['frame_id'])
            if fid != self.last_frame:
                self.last_frame, self.meta = fid, metadata
                if metadata.get('running'):
                    self.image = np.ascontiguousarray(np.frombuffer(pixels, dtype=np.uint8).reshape(
                        metadata['height'], metadata['width'], 4)[::-1])
                    self.stopped = False
                else:
                    self.image = np.zeros((metadata['height'], metadata['width'], 4), np.uint8)
        m = self.meta
        age = max(0., time.time() - m.get('timestamp', 0))
        alive = bool(m.get('running', False)) and age < 2. and not self.stopped
        stale_fade = math.exp(-max(0., age - .25) / .35) if alive else 0.
        if age > 1. or not alive:
            # Do not leave a frozen webcam image visible after a producer crash.
            self.image.fill(0)
        v = m.get('visual', self.cfg['visual'])
        p = m.get('preset', self.cfg['quality_presets'][v['quality']])
        stage = v['stage']
        reset_key = (m.get('session'), m.get('epoch', 0), m.get('quality'), alive)
        if reset_key != self.reset_key:
            feedback = base.op('history')
            if feedback:
                feedback.par.resetpulse.pulse()
            self.reset_key = reset_key
        c = self.controls
        c.fill(0)
        c[0, 0] = [m.get('center_x', .5), m.get('center_y', .5),
                    m.get('scale', 1.) if stage >= 4 else 1., m.get('angle', 0.) if stage >= 4 else 0.]
        c[0, 1] = [m.get('pinch', 0.), m.get('visibility', 0.) * stale_fade, now - self.started, dt]
        c[0, 2] = [m.get('velocity_x', 0.), m.get('velocity_y', 0.), m.get('epoch', 0), stage]
        c[0, 3] = [v['galaxy_radius'], v['flattening'], v['pinched_radius_multiplier'], v['orbit_count']]
        c[0, 4] = [p['particle_count'], p['layers'], v['star_size_pixels'], v['rotation_speed']]
        c[0, 5] = [*m.get('light_color', v['color']), v['exposure']]
        c[0, 6] = [v['glow'], v['glow_radius_pixels'], v['trail_seconds'], v['orbit_brightness']]
        c[0, 7] = [v['camera_brightness'], float(m.get('debug', False)), m.get('hand_count', 0), 0]
        c[0, 8] = [p['width'], p['height'], float(alive), m.get('momentum', .035)]
        c[0, 9] = [*m.get('light_accent', [.60, .78, 1.]), m.get('snap_pulse', 0.) * stale_fade]
        c[0, 10] = [m.get('snap_age', 100.), m.get('palette_index', 0),
                     v.get('nebula_brightness', .20), v.get('filament_brightness', .28)]
        # Control texture is sampled with texelFetch; unused slots remain zero.
        self.channels = {'center_x': c[0,0,0], 'center_y': c[0,0,1], 'scale': c[0,0,2],
            'angle': c[0,0,3], 'pinch': c[0,1,0], 'visibility': c[0,1,1],
            'velocity_x': c[0,2,0], 'velocity_y': c[0,2,1], 'hand_count': c[0,7,2],
            'alive': float(alive), 'frame_age': age, 'stage': float(stage),
            'palette': c[0,10,1], 'snap_pulse': c[0,9,3]}
        if not m:
            self.status = 'WAITING: run app.py or app.py --synthetic.'
        elif not alive:
            self.status = 'STOPPED / STALE: restart app.py. The shared image is hidden.'
        else:
            self.status = f"{'SYNTHETIC' if m.get('synthetic') else 'TRACKING'} | hands {m.get('hand_count',0)} | {m.get('palette', 'Silver')} | {m.get('quality')} | age {age:.2f}s"
        status = base.op('status')
        if status:
            status.text = self.status
        for name in ('webcam', 'controls', 'gesture_channels'):
            node = base.op(name)
            if node:
                node.cook(force=True)

    def command(self, key):
        directory = self.root / 'runtime'
        directory.mkdir(exist_ok=True)
        temporary = directory / 'command.tmp'
        temporary.write_text(json.dumps({'id': time.time_ns(), 'key': key}), encoding='utf-8')
        temporary.replace(directory / 'command.json')
        if key in ('q', '\x1b', 'escape', 'esc'):
            self.stopped = True

    def close(self):
        self.image.fill(0)
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None
