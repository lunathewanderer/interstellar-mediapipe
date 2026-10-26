import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None):
    path = Path(path) if path else ROOT / 'config.json'
    cfg = json.loads(path.read_text(encoding='utf-8'))
    # Existing saved projects/configurations also receive the new controls.
    cfg.setdefault('snap', {})
    for key, value in dict(enabled=True, contact_ratio=.34, release_ratio=.70,
            contact_dwell_seconds=.055, release_window_seconds=.20,
            minimum_release_speed=3.0, minimum_finger_travel=.32,
            cooldown_seconds=.75).items():
        cfg['snap'].setdefault(key, value)
    cfg['gestures'].setdefault('adaptive_min_cutoff', 1.5)
    cfg['gestures'].setdefault('adaptive_beta', 8.0)
    cfg['tracking'].setdefault('latest_frame_capture', True)
    cfg['visual'].setdefault('nebula_brightness', .20)
    cfg['visual'].setdefault('filament_brightness', .28)
    g, v = cfg['gestures'], cfg['visual']
    if not 0 < g['pinch_enter'] < g['pinch_exit']:
        raise ValueError('pinch_enter must be positive and smaller than pinch_exit.')
    s = cfg['snap']
    if not 0 < s['contact_ratio'] < s['release_ratio']:
        raise ValueError('Snap contact_ratio must be smaller than release_ratio.')
    if any(s[k] <= 0 for k in ('contact_dwell_seconds', 'release_window_seconds',
            'minimum_release_speed', 'minimum_finger_travel', 'cooldown_seconds')):
        raise ValueError('Snap timing, speed and travel settings must be positive.')
    if g['adaptive_min_cutoff'] <= 0 or g['adaptive_beta'] < 0:
        raise ValueError('Adaptive cutoff must be positive and beta nonnegative.')
    if g['center_mode'] not in ('palm', 'index'):
        raise ValueError('center_mode must be palm or index.')
    for key in ('smoothing_seconds', 'velocity_smoothing_seconds', 'lost_fade_seconds',
                'identity_hold_seconds', 'two_hand_reference_distance'):
        if g[key] <= 0:
            raise ValueError(f'{key} must be positive.')
    if not 0 <= g['lost_hold_seconds'] < g['identity_hold_seconds']:
        raise ValueError('identity_hold_seconds must exceed lost_hold_seconds >= 0.')
    if g['pinch_dwell_seconds'] < 0 or not 0 < g['min_scale'] <= g['max_scale']:
        raise ValueError('Invalid dwell time or scale limits.')
    if v['quality'] not in cfg['quality_presets'] or v['stage'] not in (1, 2, 3, 4):
        raise ValueError('Use a defined quality preset and stage 1..4.')
    if not 0 < v['flattening'] <= 1 or v['galaxy_radius'] <= 0:
        raise ValueError('flattening must be (0,1], galaxy_radius must be positive.')
    if not 0 < v['pinched_radius_multiplier'] <= 1:
        raise ValueError('pinched_radius_multiplier must be (0,1].')
    if v['trail_seconds'] < 0 or not 0 <= v['orbit_count'] <= 12:
        raise ValueError('trail_seconds >= 0, orbit_count in 0..12 required.')
    if len(v['color']) != 3 or any(not 0 <= c <= 4 for c in v['color']):
        raise ValueError('color must have three RGB numbers in 0..4.')
    for preset in cfg['quality_presets'].values():
        if not 16 <= preset['width'] <= 1280 or not 16 <= preset['height'] <= 720:
            raise ValueError('Preset dimensions must fit the 1280x720 bridge.')
        if not 1 <= preset['layers'] <= 3 or not 10 <= preset['particle_count'] <= 100000:
            raise ValueError('Use 1..3 layers and 10..100000 particles.')
    return cfg
