"""No MediaPipe dependency: deterministic gesture logic can be tested with landmarks."""
import itertools
import math
from dataclasses import dataclass
import numpy as np
from galaxy.motion import OneEuro, SnapDetector
from galaxy.lighting import Lighting


def alpha(dt, tau):
    return 1.0 - math.exp(-max(0.0, dt) / max(tau, 1e-6))


def display_points(points, mirror):
    p = np.asarray(points, dtype=float).copy()
    if p.shape != (21, 3) or not np.isfinite(p).all():
        raise ValueError('Expected 21 finite x/y/z landmarks.')
    if mirror:
        p[:, 0] = 1.0 - p[:, 0]
    p[:, 1] = 1.0 - p[:, 1]  # OpenCV top-left -> TouchDesigner bottom-left
    return p


def pinch_ratio(points, aspect):
    # Pixel-correct XY distances. z is deliberately excluded: it is noisier.
    metric = np.array([aspect, 1.0])
    size = np.linalg.norm((points[0, :2] - points[9, :2]) * metric)
    return float(np.linalg.norm((points[4, :2] - points[8, :2]) * metric) / max(size, .015))


@dataclass
class PinchGate:
    enter: float
    exit: float
    dwell: float
    state: bool = False
    since: float | None = None

    def update(self, ratio, now):
        candidate = ratio < self.enter if not self.state else ratio <= self.exit
        if candidate == self.state:
            self.since = None
        elif self.since is None:
            self.since = now
        if candidate != self.state and self.since is not None and now - self.since >= self.dwell:
            self.state, self.since = candidate, None
        return self.state


class GestureEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.g = cfg['gestures']
        self.tracks = {}
        self.next_id = 0
        self.previous_time = None
        self.last_seen = None
        self.active_ids = []
        self.center = np.array([.5, .5])
        self.velocity = np.zeros(2)
        self.scale, self.angle, self.pinch, self.visibility = 1., 0., 0., 0.
        self.center_filter = OneEuro(self.g['adaptive_min_cutoff'], self.g['adaptive_beta'])
        self.center_filter.update(self.center, 1/30)
        self.lighting = Lighting(cfg['visual']['color'])
        self.last_snap = -float('inf')

    def cycle_palette(self, now):
        self.lighting.cycle(now)
        self.last_snap = now

    def _associate(self, hands, now):
        # Match geometry first; a weak handedness penalty breaks ties without
        # swapping tracks when the model briefly reverses its labels.
        self.tracks = {i: t for i, t in self.tracks.items()
                       if now - t['seen'] <= self.g['identity_hold_seconds']}
        ids = list(self.tracks)
        best, best_cost = {}, float('inf')
        for candidates in itertools.product([None] + ids, repeat=len(hands)):
            used = [i for i in candidates if i is not None]
            if len(used) != len(set(used)):
                continue
            cost = 0.
            for hand, tid in zip(hands, candidates):
                if tid is None:
                    cost += .4
                else:
                    track = self.tracks[tid]
                    predicted = track['raw_wrist'] + track['wrist_velocity'] * min(.12, now-track['seen'])
                    cost += float(np.linalg.norm(hand['points'][0, :2] - predicted))
                    cost += .035 * (hand['label'] != track['label'])
            if cost < best_cost:
                best_cost = cost
                best = dict(enumerate(candidates))
        return best

    def update(self, detections, now, aspect=16/9, mirror=True):
        if self.previous_time is not None and now <= self.previous_time:
            raise ValueError('Gesture timestamps must increase monotonically.')
        dt = 1/30 if self.previous_time is None else min(now - self.previous_time, .25)
        self.previous_time = now
        a = alpha(dt, self.g['smoothing_seconds'])
        hands = []
        for detection in detections[:2]:
            label = detection['label']
            if self.cfg['tracking']['swap_handedness']:
                label = {'Left': 'Right', 'Right': 'Left'}.get(label, label)
            hands.append({'points': display_points(detection['points'], mirror),
                          'label': label, 'score': float(detection.get('score', 0))})
        assignment = self._associate(hands, now)
        visible = []
        for n, hand in enumerate(hands):
            tid = assignment.get(n)
            if tid is None:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {'points': hand['points'].copy(), 'seen': now,
                    'filter': OneEuro(self.g['adaptive_min_cutoff'], self.g['adaptive_beta']),
                    'raw_wrist': hand['points'][0, :2].copy(), 'wrist_velocity': np.zeros(2),
                    'snap': SnapDetector(self.cfg['snap']),
                    'gate': PinchGate(self.g['pinch_enter'], self.g['pinch_exit'],
                                      self.g['pinch_dwell_seconds'])}
            track = self.tracks[tid]
            # Clear a partially completed dwell across a missed detection.
            if now - track['seen'] > self.g['lost_hold_seconds']:
                track['gate'].state, track['gate'].since = False, None
                track['snap'].reset()
                track['filter'] = OneEuro(self.g['adaptive_min_cutoff'], self.g['adaptive_beta'])
                track['wrist_velocity'].fill(0)
            interval = max(.001, now-track['seen'])
            if interval < .12:
                measured = np.clip((hand['points'][0, :2]-track['raw_wrist']) / interval, -3., 3.)
                track['wrist_velocity'] += alpha(dt, .06) * (measured-track['wrist_velocity'])
            track['raw_wrist'] = hand['points'][0, :2].copy()
            track['points'] = track['filter'].update(hand['points'], dt)
            # Raw relative finger motion retains fast releases that smoothing hides.
            snapped = track['snap'].update(hand['points'], now, aspect)
            if snapped and now-self.last_snap >= self.cfg['snap']['cooldown_seconds']:
                self.cycle_palette(now)
            ratio = pinch_ratio(track['points'], aspect)
            pinched = track['gate'].update(ratio, now)
            p = track['points']
            anchor = (p[4, :2] + p[8, :2]) * .5 if pinched else (
                p[8, :2] if self.g['center_mode'] == 'index' else p[[0, 5, 9, 13, 17], :2].mean(axis=0))
            track.update(seen=now, anchor=anchor, label=hand['label'])
            visible.append({'id': tid, 'label': hand['label'], 'score': hand['score'],
                'landmarks': p.tolist(), 'pinch_ratio': ratio, 'pinched': pinched,
                'snap_armed': track['snap'].armed, 'snapped': snapped})
        current_ids = [h['id'] for h in visible]
        kept_ids = current_ids.copy()
        if not hands or len(self.active_ids) == 2:
            for tid in self.active_ids:
                if tid not in kept_ids and tid in self.tracks and len(kept_ids) < 2:
                    if now - self.tracks[tid]['seen'] <= self.g['lost_hold_seconds']:
                        kept_ids.append(tid)
        self.active_ids = kept_ids
        held = [self.tracks[tid] for tid in kept_ids]
        old = self.center.copy()
        if hands:
            self.last_seen = now
        if held:
            target = np.mean([t['anchor'] for t in held], axis=0)
            target = .5 + (target - .5) * self.g['sensitivity']
            self.center = self.center_filter.update(np.clip(target, 0, 1), dt)
            self.pinch += a * (float(any(t['gate'].state for t in held)) - self.pinch)
            if len(held) == 2:
                delta = held[1]['anchor'] - held[0]['anchor']
                delta = delta * np.array([aspect, 1.])
                distance = float(np.linalg.norm(delta))
                scale = np.clip(distance / (self.g['two_hand_reference_distance'] * aspect),
                                self.g['min_scale'], self.g['max_scale'])
                # A line has no arrow: angles differing by pi are identical.
                angle = math.atan2(delta[1], delta[0])
                difference = (angle - self.angle + math.pi / 2) % math.pi - math.pi / 2
                self.angle += a * difference
                self.scale += a * (float(scale) - self.scale)
            else:
                self.scale += a * (1. - self.scale)
            velocity = np.clip((self.center - old) / max(dt, .001), -2., 2.)
            self.velocity += alpha(dt, self.g['velocity_smoothing_seconds']) * (velocity - self.velocity)
        else:
            self.velocity *= math.exp(-dt / .25)
            self.center = np.clip(self.center + self.velocity * dt * .35, 0, 1)
            self.pinch += a * (0. - self.pinch)
            # Restart the center filter from its drifted position after loss.
            self.center_filter.value = self.center.copy()
            self.center_filter.raw = self.center.copy()
            self.center_filter.derivative.fill(0)
        age = 100. if self.last_seen is None else now - self.last_seen
        target_visibility = math.exp(-max(0., age - self.g['lost_hold_seconds']) / self.g['lost_fade_seconds'])
        self.visibility += a * (target_visibility - self.visibility)
        return dict(self.lighting.update(now), **{'center_x': float(self.center[0]), 'center_y': float(self.center[1]),
            'velocity_x': float(self.velocity[0]), 'velocity_y': float(self.velocity[1]),
            'scale': self.scale, 'angle': self.angle, 'pinch': self.pinch,
            'visibility': self.visibility, 'hand_count': len(hands), 'hands': visible})
