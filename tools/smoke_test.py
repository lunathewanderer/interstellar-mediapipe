"""Integration checks using only generated images, never the user's webcam."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'runtime'/'matplotlib'))
from galaxy.bridge import FrameBridge, CameraBusyError


def main():
    import cv2
    import numpy as np
    directory=ROOT/'test-output'
    directory.mkdir(exist_ok=True)
    with FrameBridge(writer=True):
        try:
            other=FrameBridge(writer=True)
        except CameraBusyError:
            print('PASS: second tracker rejected by named mutex')
        else:
            other.close()
            raise AssertionError('Two writers were allowed')
    with FrameBridge() as reader:
        process=subprocess.Popen([sys.executable,str(ROOT/'app.py'),'--synthetic','--no-preview','--quality','medium','--frames','225'],
                                 cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        deadline=time.monotonic()+20
        seen=set()
        sent=set()
        qualities=set()
        epochs=set()
        debug_seen=False
        two_hands_seen=False
        palettes=set()
        while process.poll() is None and time.monotonic()<deadline:
            snapshot=reader.read()
            if snapshot:
                metadata,pixels=snapshot
                if metadata.get('running'):
                    seen.add(metadata['frame_id'])
                    qualities.add(metadata['quality'])
                    epochs.add(metadata['epoch'])
                    debug_seen |= metadata['debug']
                    two_hands_seen |= metadata['hand_count']==2
                    palettes.add(metadata['palette'])
                    assert len(pixels)==metadata['width']*metadata['height']*4
                    for threshold,key in ((10,'r'),(25,'d'),(40,'-'),(55,'c'),(90,'c')):
                        if metadata['frame_id']>=threshold and threshold not in sent:
                            command=ROOT/'runtime'/'command.json'
                            temporary=command.with_suffix('.tmp')
                            temporary.write_text(json.dumps({'id':time.time_ns(),'key':key}))
                            temporary.replace(command)
                            sent.add(threshold)
            time.sleep(.008)
        if process.poll() is None:
            process.kill()
            raise AssertionError('Synthetic producer timed out')
        output=process.communicate()[0]
        print(output)
        assert process.returncode==0, output
        assert len(seen)>=10, 'No live frames received'
        assert qualities=={'medium','low'}, qualities
        assert epochs=={0,1}, epochs
        assert debug_seen, 'Debug command not received'
        assert two_hands_seen, 'Synthetic two-hand transition not received'
        assert palettes=={'Silver','Solar Amber','Violet'}, palettes
        final=reader.read()
        assert final and final[0]['running'] is False and not any(final[1]), 'Image not cleared on exit'
        print(f'PASS: {len(seen)} distinct cross-process frames; reset/debug/quality commands; zeroed shutdown')
    # A real MediaPipe invocation on generated video checks package/model plumbing.
    path=directory/'generated_no_hands.avi'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),15.,(640,360))
    assert writer.isOpened(), 'OpenCV MJPG encoder unavailable'
    for _ in range(20):
        writer.write(np.zeros((360,640,3),np.uint8))
    writer.release()
    result=subprocess.run([sys.executable,str(ROOT/'app.py'),'--video',str(path),'--no-preview','--frames','12'],
                          cwd=ROOT,capture_output=True,text=True,timeout=45)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
    assert result.returncode==0, 'Real model/video smoke test failed'
    print('PASS: actual MediaPipe Hand Landmarker on generated 12-frame video (no hands expected)')


if __name__=='__main__':
    main()
