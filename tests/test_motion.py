import math
import threading
import unittest
import numpy as np
from galaxy.motion import OneEuro, SnapDetector
from galaxy.gestures import GestureEngine, alpha
from galaxy.lighting import Lighting
from galaxy.capture import LatestFrameCapture
from galaxy.settings import load_config
from test_gestures import hand


def snap_pose(released=False, scale=1., shift=(.5, .5), rotation=0., index_pinch=False):
    # Model-image coordinates, with all geometry measured in equal pixel units.
    p=np.zeros((21,3))
    p[0,:2]=[0,.10]
    p[9,:2]=[0,0]
    p[4,:2]=[.015,-.10]
    p[8,:2]=[.10,-.10] if not index_pinch else p[4,:2]
    p[12,:2]=[0,.055] if released else [0,-.10]
    angle=np.array([[math.cos(rotation),-math.sin(rotation)],
                    [math.sin(rotation),math.cos(rotation)]])
    p[:,:2]=p[:,:2]@angle.T*scale
    p[:,0]/=16/9
    p[:,:2]+=shift
    return p


class SnapTests(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()
        self.detector=SnapDetector(self.cfg['snap'])

    def arm(self, **kwargs):
        for t in (0., .033, .067, .100):
            self.assertFalse(self.detector.update(snap_pose(**kwargs),t,16/9))
        self.assertTrue(self.detector.armed)

    def test_contact_then_fast_release_fires_once_with_cooldown(self):
        self.arm()
        self.assertTrue(self.detector.update(snap_pose(True),.133,16/9))
        for i in range(1,18):
            self.assertFalse(self.detector.update(snap_pose(i%4==0),.133+i/30,16/9))

    def test_no_contact_and_one_frame_contact_do_not_fire(self):
        for i in range(20):
            self.assertFalse(self.detector.update(snap_pose(i!=10),i/30,16/9))

    def test_slow_release_does_not_fire(self):
        self.arm()
        for i in range(1,21):
            p=snap_pose()
            p[12]=(1-i/20)*p[12]+(i/20)*snap_pose(True)[12]
            self.assertFalse(self.detector.update(p,.1+i/30,16/9))

    def test_translation_rotation_and_scale_do_not_fire(self):
        self.arm()
        for i in range(1,20):
            p=snap_pose(scale=1.+i*.015,shift=(.5+i*.009,.5),rotation=i*.05)
            self.assertFalse(self.detector.update(p,.1+i/30,16/9))

    def test_valid_snap_is_invariant_to_size_and_rotation(self):
        for scale in (.55,1.,1.7):
            for angle in (-1.,0.,1.5):
                self.detector=SnapDetector(self.cfg['snap'])
                self.arm(scale=scale,rotation=angle)
                self.assertTrue(self.detector.update(snap_pose(True,scale,rotation=angle),.133,16/9))

    def test_index_pinch_is_not_a_snap(self):
        for i in range(20):
            self.assertFalse(self.detector.update(snap_pose(i%5==0,index_pinch=True),i/30,16/9))

    def test_tracking_gap_cancels_armed_gesture(self):
        self.arm()
        self.assertFalse(self.detector.update(snap_pose(True),.35,16/9))

    def test_two_simultaneous_snaps_change_palette_only_once(self):
        engine=GestureEngine(self.cfg)
        for i in range(5):
            result=engine.update([{'points':snap_pose(i==4,shift=(x,.5)),
                                   'label':label} for x,label in ((.3,'Left'),(.7,'Right'))],i/30)
        self.assertEqual(result['lighting_changes'],1)
        self.assertEqual(result['palette'],'Solar Amber')


class MotionTests(unittest.TestCase):
    def test_adaptive_filter_reduces_fast_motion_lag_against_previous_double_ema(self):
        cfg=load_config()
        engine=GestureEngine(cfg)
        old_landmark=old_center=.8
        adaptive_errors, previous_errors=[],[]
        for i in range(90):
            x=.2 if i<30 else .2+min(i-30,30)*.6/30
            target=1-x
            a=alpha(1/30,.085)
            old_landmark+=a*(target-old_landmark)
            old_center+=a*(old_landmark-old_center)
            result=engine.update([hand(x=x)],(i+1)/30)
            if 40<i<60:
                adaptive_errors.append(abs(result['center_x']-target))
                previous_errors.append(abs(old_center-target))
        self.assertLess(np.mean(adaptive_errors),np.mean(previous_errors)*.7)

    def test_predictive_identity_survives_clear_hand_crossing(self):
        engine=GestureEngine(load_config())
        first=engine.update([hand(.2,label='Left'),hand(.8,label='Right')],0.)
        for i in range(1,16):
            a,b=hand(.2+i*.025,label='Left'),hand(.8-i*.025,label='Right')
            result=engine.update([b,a] if i%2 else [a,b],i/30)
            left=next(h for h in result['hands'] if h['label']=='Left')
            self.assertEqual(first['hands'][0]['id'],left['id'])

    def test_lighting_is_smooth_and_cycles_back_to_silver(self):
        light=Lighting([.85,.91,1.])
        light.update(0.)
        light.cycle(.1)
        first=light.update(.101)
        last=light.update(2.)
        self.assertLess(np.linalg.norm(np.array(first['light_color'])-[.85,.91,1.]),.5)
        self.assertGreater(last['light_color'][0],last['light_color'][2]*5)
        light.cycle(3.)
        self.assertEqual(light.update(3.1)['palette'],'Violet')
        light.cycle(4.)
        self.assertEqual(light.update(4.1)['palette'],'Silver')
        self.assertLess(last['snap_pulse'],.01)

    def test_filter_handles_irregular_frame_intervals(self):
        f=OneEuro()
        for dt in (.01,.033,.08,.02,.2):
            self.assertTrue(np.isfinite(f.update([1.,2.],dt)).all())

    def test_latest_capture_returns_newest_frame_and_releases(self):
        class Capture:
            def __init__(self):
                self.finished=threading.Event()
                self.released=False
                self.i=0
            def read(self):
                self.i+=1
                if self.i>5:
                    return False,None
                return True,np.full((2,2,3),self.i,np.uint8)
            def release(self):
                self.released=True
                self.finished.set()
        capture=Capture()
        stream=LatestFrameCapture(capture)
        self.assertTrue(capture.finished.wait(1.))
        ok,frame=stream.read()
        self.assertTrue(ok)
        self.assertEqual(int(frame[0,0,0]),5)
        self.assertFalse(stream.read()[0])
        stream.release()
        self.assertTrue(capture.released)


if __name__=='__main__':
    unittest.main()
