"""Adaptive low-pass filtering and a camera-visible finger-snap state machine."""
import math
import numpy as np


class OneEuro:
    """Speed-adaptive filter (Casiez et al., 2012), normalized coordinate units."""
    def __init__(self, minimum=1.5, beta=8., derivative_cutoff=1.):
        self.minimum, self.beta, self.derivative_cutoff = minimum, beta, derivative_cutoff
        self.raw = self.value = None
        self.derivative = None

    @staticmethod
    def gain(dt, cutoff):
        return 1. / (1. + 1. / (2. * math.pi * cutoff * max(dt, .001)))

    def update(self, value, dt):
        value = np.asarray(value, dtype=float)
        if self.raw is None:
            self.raw, self.value = value.copy(), value.copy()
            self.derivative = np.zeros_like(value)
        else:
            derivative = (value - self.raw) / max(dt, .001)
            self.derivative += self.gain(dt, self.derivative_cutoff) * (derivative - self.derivative)
            cutoff = self.minimum + self.beta * np.abs(self.derivative)
            self.value += self.gain(dt, cutoff) * (value - self.value)
            self.raw = value.copy()
        return self.value.copy()


class SnapDetector:
    """Thumb/middle contact -> quick relative release. No microphone is used.

    A webcam cannot prove that an audible snap occurred. A fast middle-finger
    pinch release is deliberately accepted as the accessible visual equivalent.
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.reset()

    def reset(self):
        self.contact_since = self.release_since = None
        self.armed = False
        self.contact_tip = None
        self.previous_ratio = self.previous_time = None
        self.cooldown_until = -float('inf')

    def update(self, points, now, aspect):
        p = points[:, :2] * np.array([aspect, 1.])
        axis = p[9] - p[0]
        size = float(np.linalg.norm(axis))
        if size < .025:
            self.reset()
            return False
        axis /= size
        across = np.array([-axis[1], axis[0]])
        tip = np.array([np.dot(p[12]-p[9], across), np.dot(p[12]-p[9], axis)]) / size
        ratio = float(np.linalg.norm(p[4]-p[12]) / size)
        index_gap = float(np.linalg.norm(p[4]-p[8]) / size)
        gap = 0. if self.previous_time is None else now - self.previous_time
        speed = 0. if not 0 < gap <= .12 else (ratio-self.previous_ratio) / gap
        if gap > .12:
            self.contact_since = self.release_since = None
            self.armed = False
        self.previous_ratio, self.previous_time = ratio, now
        if now < self.cooldown_until or not self.cfg['enabled']:
            return False
        contact = ratio < self.cfg['contact_ratio'] and index_gap > .45
        if contact:
            if self.contact_since is None:
                self.contact_since = now
            if now - self.contact_since >= self.cfg['contact_dwell_seconds']:
                self.armed = True
                self.contact_tip = tip.copy()
            self.release_since = None
            return False
        if not self.armed:
            self.contact_since = None
            return False
        if self.release_since is None:
            self.release_since = now
        displacement = float(np.linalg.norm(tip-self.contact_tip))
        fired = (ratio > self.cfg['release_ratio'] and speed > self.cfg['minimum_release_speed']
                 and displacement > self.cfg['minimum_finger_travel']
                 and now-self.release_since <= self.cfg['release_window_seconds'])
        if fired or now-self.release_since > self.cfg['release_window_seconds']:
            self.armed = False
            self.contact_since = self.release_since = None
        if fired:
            self.cooldown_until = now + self.cfg['cooldown_seconds']
        return fired
