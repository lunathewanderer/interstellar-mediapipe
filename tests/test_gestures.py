import copy
import math
import unittest
import numpy as np
from galaxy.gestures import GestureEngine, PinchGate, alpha, display_points, pinch_ratio
from galaxy.settings import load_config


def hand(x=.3, y=.55, label='Left', ratio=.8, size=.12):
    p = np.tile([x, y, 0.], (21, 1))
    p[0] = [x, y + size / 2, 0]
    p[9] = [x, y - size / 2, 0]
    p[4] = [x, y - size, 0]
    p[8] = [x + ratio * size / (16/9), y - size, 0]
    return {'points': p, 'label': label, 'score': .99}


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def settle(self, engine, detections, start=0., frames=90):
        for i in range(frames):
            result = engine.update(detections, start + (i + 1) / 30)
        return result

    def test_mirror_and_y_mapping_exactly_once(self):
        p = hand()['points']
        q = display_points(p, True)
        np.testing.assert_allclose(q[:, 0], 1-p[:, 0])
        np.testing.assert_allclose(q[:, 1], 1-p[:, 1])
        np.testing.assert_allclose(display_points(p, False)[:, 0], p[:, 0])

    def test_pinching_is_invariant_to_hand_size(self):
        for size in (.06, .12, .22):
            self.assertAlmostEqual(pinch_ratio(hand(ratio=.24, size=size)['points'],16/9), .24)

    def test_pinch_uses_pixel_aspect_ratio(self):
        p = hand(ratio=.4)['points']
        self.assertAlmostEqual(pinch_ratio(p, 16/9), .4)
        self.assertNotAlmostEqual(pinch_ratio(p, 1.), .4)

    def test_zero_size_hand_is_finite(self):
        self.assertTrue(math.isfinite(pinch_ratio(np.zeros((21,3)), 16/9)))

    def test_invalid_landmarks_rejected(self):
        for p in (np.zeros((20,3)), np.full((21,3),float('nan'))):
            with self.assertRaises(ValueError):
                display_points(p, True)

    def test_pinch_hysteresis_and_dwell(self):
        gate = PinchGate(.3, .46, .075)
        self.assertFalse(gate.update(.2, 0))
        self.assertFalse(gate.update(.2, .05))
        self.assertTrue(gate.update(.2, .08))
        self.assertTrue(gate.update(.38, .1))
        self.assertTrue(gate.update(.5, .2))
        self.assertFalse(gate.update(.5, .28))

    def test_short_pinch_noise_does_not_toggle(self):
        gate = PinchGate(.3, .46, .075)
        for i in range(100):
            gate.update(.2 if i % 2 == 0 else .5, i / 30)
        self.assertFalse(gate.state)

    def test_exponential_smoothing_is_time_based(self):
        for fps in (20,30,60):
            value=0.
            for _ in range(fps):
                value += alpha(1/fps,.085)*(1-value)
            self.assertAlmostEqual(value, 1-math.exp(-1/.085), places=10)

    def test_engine_reduces_coordinate_jitter(self):
        engine = GestureEngine(self.cfg)
        values=[]
        for i in range(150):
            result = engine.update([hand(x=.5+.03*(-1)**i)], (i+1)/30)
            if i>50:
                values.append(result['center_x'])
        self.assertLess(np.std(values), .012)

    def test_pinched_anchor_is_finger_midpoint(self):
        engine = GestureEngine(self.cfg)
        h = hand(ratio=.1)
        result = self.settle(engine,[h])
        expected = display_points(h['points'],True)[[4,8],:2].mean(axis=0)
        self.assertGreater(result['pinch'], .99)
        np.testing.assert_allclose([result['center_x'],result['center_y']], expected,atol=.001)

    def test_index_anchor_mode(self):
        self.cfg['gestures']['center_mode']='index'
        h=hand()
        result=self.settle(GestureEngine(self.cfg),[h])
        expected=display_points(h['points'],True)[8,:2]
        np.testing.assert_allclose([result['center_x'],result['center_y']], expected,atol=.001)

    def test_result_order_does_not_change_identity(self):
        engine=GestureEngine(self.cfg)
        a,b=hand(.25),hand(.75,label='Right')
        first=self.settle(engine,[a,b])
        last=engine.update([b,a],3.1)
        self.assertEqual(first['hands'][0]['id'],last['hands'][1]['id'])
        self.assertEqual(first['hands'][1]['id'],last['hands'][0]['id'])

    def test_label_flicker_does_not_swap_identity(self):
        engine=GestureEngine(self.cfg)
        first=engine.update([hand(.2),hand(.8,label='Right')],1.)
        last=engine.update([hand(.2,label='Right'),hand(.8,label='Left')],1.04)
        self.assertEqual([h['id'] for h in first['hands']],[h['id'] for h in last['hands']])

    def test_handedness_labels_not_swapped_by_display_mirror(self):
        result=GestureEngine(self.cfg).update([hand(label='Left')],1.)
        self.assertEqual(result['hands'][0]['label'],'Left')
        self.cfg['tracking']['swap_handedness']=True
        result=GestureEngine(self.cfg).update([hand(label='Left')],1.)
        self.assertEqual(result['hands'][0]['label'],'Right')

    def test_two_hand_scale_increases_with_distance(self):
        near=self.settle(GestureEngine(self.cfg),[hand(.4),hand(.6,label='Right')])
        far=self.settle(GestureEngine(self.cfg),[hand(.15),hand(.85,label='Right')])
        self.assertGreater(far['scale'],near['scale'])

    def test_line_orientation_does_not_flip_with_detection_order(self):
        engine=GestureEngine(self.cfg)
        a,b=hand(.25,.3),hand(.75,.7,label='Right')
        first=self.settle(engine,[a,b])
        for i in range(30):
            last=engine.update([b,a],3.1+i/30)
        self.assertLess(abs(last['angle']-first['angle']),.01)

    def test_one_hand_disappears_without_center_jump(self):
        engine=GestureEngine(self.cfg)
        a,b=hand(.25),hand(.75,label='Right')
        before=self.settle(engine,[a,b])
        after=engine.update([a],3.04)
        self.assertEqual(after['hand_count'],1)
        self.assertLess(abs(after['center_x']-before['center_x']),.01)
        after=self.settle(engine,[a],start=3.1)
        self.assertAlmostEqual(after['scale'],1.,places=3)
        self.assertEqual(len(after['hands']),1)

    def test_both_disappear_hold_then_fade(self):
        engine=GestureEngine(self.cfg)
        before=self.settle(engine,[hand()])
        held=engine.update([],3.05)
        self.assertGreater(held['visibility'],.95)
        self.assertLess(abs(held['center_x']-before['center_x']),.01)
        after=self.settle(engine,[],3.1,180)
        self.assertLess(after['visibility'],.002)
        self.assertLess(abs(after['velocity_x']),.001)
        self.assertEqual(after['hand_count'],0)

    def test_reacquisition_starts_smoothly_and_clears_old_pinch(self):
        engine=GestureEngine(self.cfg)
        self.settle(engine,[hand(.2,ratio=.1)])
        self.settle(engine,[],3.1,90)
        before=engine.center.copy()
        after=engine.update([hand(.8)],6.2)
        self.assertLess(abs(after['center_x']-before[0]),.58)
        self.assertFalse(after['hands'][0]['pinched'])

    def test_no_hands_at_start_is_invisible(self):
        result=GestureEngine(self.cfg).update([],1.)
        self.assertLess(result['visibility'],1e-8)

    def test_nonmonotonic_timestamp_rejected(self):
        engine=GestureEngine(self.cfg)
        engine.update([],1.)
        with self.assertRaises(ValueError):
            engine.update([],1.)


if __name__=='__main__':
    unittest.main()
