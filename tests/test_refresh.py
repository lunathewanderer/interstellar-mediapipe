"""Fault injection for document recovery; this does not emulate the TD compiler."""
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from touchdesigner.refresh_project import refresh
from galaxy.settings import ROOT


class Parameter:
    def __init__(self,value):
        self.value=value
    def eval(self):
        return self.value


class Node:
    def __init__(self,name):
        self.text='# previous embedded source\n'
        self.path='/project1/galaxy/'+name
        self.par=SimpleNamespace(pixeldat=Parameter('previous_pixel'),active=True,
            resetpulse=SimpleNamespace(pulse=lambda:None),winopen=SimpleNamespace(pulse=lambda:None))
        self.module=SimpleNamespace(_runtime=None,
            state=lambda base:SimpleNamespace(tick=lambda base:None))
    def cook(self,force=False):
        pass
    def errors(self,recurse=False):
        return ''


class RefreshRecoveryTests(unittest.TestCase):
    def test_missing_node_aborts_before_mutation(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base=SimpleNamespace(par=SimpleNamespace(Projectdir=Parameter(temporary)),op=lambda name:None)
            with self.assertRaisesRegex(RuntimeError,'Incomplete project'):
                refresh(temporary,lambda path:base)
            self.assertFalse((Path(temporary)/'runtime').exists())

    def test_shader_cook_failure_restores_embedded_sources_and_wires(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            folder=Path(temporary)
            for name in ('touchdesigner','shaders'):
                shutil.copytree(ROOT/name,folder/name,ignore=shutil.ignore_patterns('__pycache__'))
            names=('controller webcam_callbacks controls_callbacks channels_callbacks keyboard_callbacks '
                   'frame_tick galaxy_pixel trail_pixel glow_h_pixel composite_pixel galaxy_raw trails '
                   'glow_horizontal final_composite history OUT webcam controls gesture_channels keyboard display_window').split()
            nodes={name:Node(name) for name in names}
            nodes['final_composite']=type('glslmultiTOP',(Node,),{})('final_composite')
            base=SimpleNamespace(par=SimpleNamespace(Projectdir=Parameter(str(folder))),op=nodes.get)
            def fail(force=False):
                raise RuntimeError('injected compile failure')
            nodes['final_composite'].cook=fail
            with self.assertRaisesRegex(RuntimeError,'injected compile failure'):
                refresh(folder,lambda path:base)
            for name in names[:10]:
                self.assertEqual(nodes[name].text,'# previous embedded source\n')
            self.assertEqual(nodes['final_composite'].par.pixeldat,'previous_pixel')
            self.assertTrue(nodes['frame_tick'].par.active)
            self.assertTrue(list((folder/'runtime'/'td_source_backups').glob('*.json')))


if __name__=='__main__':
    unittest.main()
