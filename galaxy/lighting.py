"""Time-based lighting transitions shared by gestures and the C key."""
import math
import numpy as np


PALETTES = (
    ('Silver', (0.85, 0.91, 1.0), (0.60, 0.78, 1.0)),
    ('Solar Amber', (1.0, 0.40, 0.075), (1.0, 0.78, 0.25)),
    ('Violet', (0.55, 0.16, 1.0), (1.0, 0.42, 0.86)),
)


class Lighting:
    def __init__(self, initial_color):
        self.index = self.count = 0
        self.color = np.array(initial_color, dtype=float)
        self.accent = np.array(PALETTES[0][2], dtype=float)
        self.previous = self.last_event = None

    def cycle(self, now):
        self.index = (self.index + 1) % len(PALETTES)
        self.count += 1
        self.last_event = now

    def update(self, now):
        dt = 0. if self.previous is None else max(0., now - self.previous)
        self.previous = now
        target = PALETTES[self.index]
        a = 1. - math.exp(-dt / .18)
        # Retain a user's custom silver color until the first change.
        if self.count:
            self.color += a * (np.array(target[1]) - self.color)
        self.accent += a * (np.array(target[2]) - self.accent)
        age = 100. if self.last_event is None else max(0., now - self.last_event)
        return {'light_color': self.color.tolist(), 'light_accent': self.accent.tolist(),
                'palette': target[0], 'palette_index': self.index,
                'snap_pulse': math.exp(-age / .28), 'snap_age': age,
                'lighting_changes': self.count}
