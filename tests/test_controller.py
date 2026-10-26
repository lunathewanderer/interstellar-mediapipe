"""Test TD-side packing and stale image handling without claiming a TD runtime test."""
import time
import unittest
from unittest.mock import patch
import numpy as np
from galaxy.bridge import FrameBridge
from galaxy.settings import ROOT, load_config
from touchdesigner.controller import Runtime


class EmptyNetwork:
    def op(self,name):
        return None


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.writer=FrameBridge(writer=True)
        self.runtime=Runtime(ROOT)
        cfg=load_config()
        self.meta={'width':2,'height':2,'session':'test','frame_id':1,'running':True,
            'timestamp':100.,'visual':cfg['visual'],'preset':cfg['quality_presets']['medium'],
            'center_x':.25,'center_y':.75,'visibility':1.,'scale':1.4,'angle':.2,
            'pinch':.6,'hand_count':2,'quality':'medium','epoch':0}
        self.pixels=np.array([[[255,0,0,255],[255,0,0,255]],
                              [[0,255,0,255],[0,255,0,255]]],np.uint8)

    def tearDown(self):
        self.runtime.close()
        self.writer.close()

    def tick(self,now):
        with patch('touchdesigner.controller.time.time',return_value=now):
            self.runtime.tick(EmptyNetwork())

    def test_rgba_upload_flips_rows_once(self):
        self.writer.write(self.meta,self.pixels.tobytes())
        self.tick(100.)
        np.testing.assert_array_equal(self.runtime.image[0,0],[0,255,0,255])
        np.testing.assert_array_equal(self.runtime.image[1,0],[255,0,0,255])

    def test_controls_remain_unquantized_float32(self):
        self.writer.write(self.meta,self.pixels.tobytes())
        self.tick(100.)
        self.assertEqual(self.runtime.controls.dtype,np.float32)
        self.assertEqual(self.runtime.controls.shape,(1,16,4))
        self.assertAlmostEqual(self.runtime.controls[0,0,2],1.4,places=5)
        self.assertAlmostEqual(self.runtime.controls[0,1,0],.6,places=5)
        self.assertEqual(self.runtime.controls[0,8,0],960)

    def test_stale_fades_and_hides_frozen_image(self):
        self.writer.write(self.meta,self.pixels.tobytes())
        self.tick(100.)
        self.assertEqual(self.runtime.controls[0,1,1],1.)
        self.tick(100.7)
        self.assertLess(self.runtime.controls[0,1,1],.5)
        self.tick(101.1)
        self.assertEqual(self.runtime.image.max(),0)
        self.tick(102.1)
        self.assertEqual(self.runtime.controls[0,8,2],0)

    def test_stopped_producer_clears_image_immediately(self):
        self.writer.write(self.meta,self.pixels.tobytes())
        self.tick(100.)
        self.meta.update(frame_id=2,running=False)
        self.writer.write(self.meta,bytes(16))
        self.tick(100.01)
        self.assertEqual(self.runtime.image.max(),0)
        self.assertEqual(self.runtime.channels['alive'],0)

    def test_palette_and_snap_reach_float_control_texture(self):
        self.meta.update(light_color=[1.,.4,.075],light_accent=[1.,.78,.25],
                         palette_index=1,snap_pulse=.8,snap_age=.08)
        self.writer.write(self.meta,self.pixels.tobytes())
        self.tick(100.)
        np.testing.assert_allclose(self.runtime.controls[0,5,:3],[1.,.4,.075],atol=1e-6)
        np.testing.assert_allclose(self.runtime.controls[0,9],[1.,.78,.25,.8],atol=1e-6)
        self.assertAlmostEqual(self.runtime.controls[0,10,0],.08,places=5)
        self.assertEqual(self.runtime.channels['palette'],1.)

    def test_stages_before_four_ignore_two_hand_scale_and_angle(self):
        self.meta['visual']['stage']=2
        self.writer.write(self.meta,self.pixels.tobytes())
        self.tick(100.)
        self.assertEqual(self.runtime.controls[0,0,2],1.)
        self.assertEqual(self.runtime.controls[0,0,3],0.)


if __name__=='__main__':
    unittest.main()
