"""Optional official sample-image check; downloads inputs, inference stays local.

The upstream MediaPipe hand_landmarker_test.py identifies thumb_up.jpg and
right_hands.jpg as one-hand and two-hand fixtures. No user camera is opened.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    directory=ROOT/'test-output'
    directory.mkdir(exist_ok=True)
    cache=ROOT/'runtime'/'matplotlib'
    cache.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(cache))
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    records=[]
    options=vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(ROOT/'models'/'hand_landmarker.task')),
        running_mode=vision.RunningMode.IMAGE,num_hands=2)
    with vision.HandLandmarker.create_from_options(options) as model:
        for filename,expected in (('thumb_up.jpg',1),('right_hands.jpg',2)):
            path=directory/filename
            url='https://storage.googleapis.com/mediapipe-assets/'+filename
            if not path.exists():
                with urllib.request.urlopen(url,timeout=30) as response:
                    path.write_bytes(response.read())
            image=mp.Image.create_from_file(str(path))
            result=model.detect(image)
            count=len(result.hand_landmarks)
            assert count==expected, (filename,count,expected)
            assert all(len(hand)==21 for hand in result.hand_landmarks)
            record={'source':url,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'expected':expected,'detected':count,
                    'labels':[h[0].category_name for h in result.handedness]}
            records.append(record)
            print(f"PASS: {filename}: {count} hand(s), 21 landmarks each, labels={record['labels']}")
    (directory/'model_samples_result.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Public fixture test only; physical camera/hand validation remains manual.')


if __name__=='__main__':
    main()
