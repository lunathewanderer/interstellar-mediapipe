# Diagnose one layer at a time

Start in the project directory and use `.\.venv\Scripts\python.exe`, not a bare `python` command that might launch Python 3.14. First get the camera preview working, then landmarks, then the TD camera TOP, then the galaxy.

## Install or package problems

| Symptom | Fix |
|---|---|
| `pymanager` not recognized | Reopen PowerShell after installing the official manager. Check Windows App Execution Aliases and `%LocalAppData%\Microsoft\WindowsApps` in your user PATH. Use the official installer link in README. |
| `py -0p` says no installed Pythons but Python 3.14 exists | That launcher may not see your install. The README's explicit `pymanager` command avoids the old launcher conflict. |
| No matching MediaPipe/NumPy wheel | Confirm **64-bit Python 3.12** using the command below. Do not use 32-bit, ARM64 Python, 3.14, or a free-threaded runtime for this pinned project. |
| `No module named mediapipe`, `cv2`, `numpy` | Use the project's interpreter; install `requirements.txt` there. |
| `DLL load failed`, missing `VCRUNTIME140` | Install Microsoft's official x64 Visual C++ runtime, restart PowerShell and retry. See command below. |
| NumPy ABI or OpenCV import error | Recreate an isolated environment. Install only `opencv-contrib-python`; `opencv-python` and `opencv-python-headless` share the same `cv2` namespace and must not coexist. |
| `mediapipe has no attribute solutions` | This project uses **Tasks Hand Landmarker**, not old `mp.solutions`. Run the supplied `app.py`; do not substitute an old tutorial. |
| `ensurepip` failed / `No module named pip` | For an official runtime try `pymanager exec -V:3.12 -m ensurepip --upgrade`; recreate the environment if needed. A packaged host runtime can omit pip; prefer the official Python installation for everyday use. |
| Internet/proxy/TLS error | Packages and model setup require Internet. Check your network/proxy and retry. Runtime does not need Internet. Never disable certificate validation to make a download work. |
| `Activate.ps1 cannot be loaded` | No activation is required. Use the full `.venv\Scripts\python.exe` path shown throughout the guide. |

Diagnostics:

```powershell
.\.venv\Scripts\python.exe -c "import sys,struct; print(sys.executable); print(sys.version); print(struct.calcsize('P')*8)"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip list
```

If repairing a broken environment, keep a backup instead of deleting it:

```powershell
Rename-Item -LiteralPath '.venv' -NewName '.venv-backup'
pymanager exec -V:3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pip==25.3
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Close Python processes first, and choose a different backup name if it already exists.

For a missing Microsoft runtime, the official [Microsoft runtime download guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) links the x64 redistributable:

```powershell
$vcInstaller = Join-Path $env:USERPROFILE 'Downloads\vc_redist.x64.exe'
Invoke-WebRequest -Uri 'https://aka.ms/vc14/vc_redist.x64.exe' -OutFile $vcInstaller
Start-Process -FilePath $vcInstaller -Wait
```

## Camera / video

`Cannot open input`: close other camera programs, open `ms-settings:privacy-webcam`, enable desktop-app access, and try another camera index:

```powershell
.\.venv\Scripts\python.exe app.py --camera 1 --stage 1
```

DirectShow is attempted first, then Media Foundation if opening fails. A camera can open yet return no image; check USB connection, Windows permissions and device availability. The script reports this separately. You can temporarily request 640x480 at 30 FPS in `config.json` if the device rejects 720p; the output is letterboxed, preserving the displayed geometry. Hardware may ignore requested settings.

Test without camera access:

```powershell
.\.venv\Scripts\python.exe app.py --synthetic
.\.venv\Scripts\python.exe app.py --video 'C:\path\to\real-hands.mp4' --stage 1
```

The first checks transport and rendering with fake hands. The second runs actual MediaPipe. A blank generated video should produce `hands=0`; it cannot test hand recognition. If a video codec fails, try a conventional H.264 MP4 or MJPG AVI that OpenCV can decode. Quote paths containing spaces.

## Model file

`Model missing`: run:

```powershell
.\.venv\Scripts\python.exe tools/download_model.py
Get-FileHash -LiteralPath '.\models\hand_landmarker.task' -Algorithm SHA256
```

Expected SHA-256: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`. The downloader uses Google's numbered revision, checks model archive names/CRC, checks the manifest hash and writes the final file only after validation. An HTML login/proxy/error page will be rejected. Do not use a Gesture Recognizer model with Hand Landmarker.

## No landmarks, wrong coordinates or flickering pinch

Press `d` in the tracker preview. If `hands=0`, show the whole palm in good light at a moderate distance. Keep thumb/index visible and avoid hands directly overlapping. Begin with confidence thresholds around 0.5..0.55.

If the raw dots follow the hand but the core is offset: return to default `sensitivity=1`, check center mode and mirroring, and verify that no extra Flip TOP was added. Palm mode intentionally uses an average of wrist and MCPs, not the index fingertip. Pinch intentionally changes the anchor to the tip midpoint. Both image and points are mirrored once; y is converted to bottom-left UV once.

Raise only your left hand and read the model label, then test the right. For an already-mirrored recording, the `tracking.swap_handedness` override can correct labels. A rendered mirror itself does not require swapping anatomical labels.

Read pinch ratios with a frontal hand. Adjust `pinch_enter` below the normal open ratio and above the normal closed ratio; keep `pinch_exit` larger. Increase dwell or smoothing modestly if it flickers. Extremely edge-on hands are a limitation of the 2D hand-size normalization.

## No data in TouchDesigner / OSC / port errors

**This project does not use OSC, UDP, TCP or any network port.** There are no OSC channels, IP addresses or ports to configure. A `port already in use` error belongs to another program or an earlier OSC-based tutorial; close that program if needed, then run this project's `app.py`. No firewall rule is necessary.

`Another Galaxy Hands tracker is running`: stop its terminal/preview first. The named mutex prevents two writers. The mutex disappears when the process exits, including after a crash; there is no lock file to delete.

If TD `status` says WAITING:

1. Start `app.py --synthetic --no-preview`. Its terminal must report frames.
2. Ensure TD and Python run in the **same Windows login session** with the same normal-user privilege level.
3. Confirm the Base COMP's `Projectdir` points to this exact folder and its `controller` DAT contains the supplied code.
4. Confirm `frame_tick`: Active On, Frame Start On, timeline playing. The update is driven from this DAT.
5. Inspect `webcam` and `gesture_channels`. If webcam is live and `alive=1`, the bridge works. `hand_count=0` is a tracking condition, not a transport failure.
6. If the controller reports a Python exception, inspect Textport; do not silently ignore it.

STOPPED / STALE means producer timestamps stopped, rather than a network failure. Restart the tracker. A fresh process writes a new session ID, resetting the feedback automatically. An abrupt producer crash hides its frozen image after one second; normal quit clears it immediately.

## TD visual/compiler errors

| Symptom | Check |
|---|---|
| Builder reports missing parameter | Use the targeted 2025.33230 build; follow the manual recipe and compare internal parameter names. No `.toe` compatibility is claimed as tested. |
| Checkerboard/red error marker | Point an Info DAT at that GLSL TOP; check compiler output. Keep GLSL 4.60 and the exact input order. |
| Shader cannot find input sampler / wrong texture | Use all wires in the recipe. `controls` is input 0 only on `galaxy_raw`; each shader has its own documented layout. |
| Galaxy stuck at origin/black or controls clipped to 1 | `controls` must be **rgba32float**, not the default 8-bit normalized image. It must remain 16x1. |
| Only a core appears | Stage 1 is selected. Stop/restart with `--stage 4`. |
| Camera flipped vertically | Use the supplied webcam callback and controller row reversal; remove extra Flip TOPs. |
| Thick streaks/feedback gets too strong | Lower `trail_seconds`, pulse `history.resetpulse`, and check trails use the supplied max/decay shader. |
| q does not close TD | Intended: q stops the experience and releases the camera while preserving the unsaved TD document. Close TD normally. |
| Keys do nothing | Click the tracker preview, or focus TD with Keyboard In active. A text editor receives keystrokes as text. Ctrl+C is a terminal fallback. |
| Edited config not reflected | Restart `app.py`; `r` resets state but does not reload configuration. |

## Poor frame rate / lag

The high preset targets 720p; measured performance depends on both inference and rendering. The standalone shader timing excludes webcam capture, MediaPipe, TD's Vulkan shader translation, uploads and UI.

1. Press `-` to reach medium (960x540, two layers) or low (640x360, one layer). This resets feedback to match the new resolution.
2. Restart with `--no-preview` to avoid a second image viewer. Use console keys or TD's Keyboard In DAT.
3. Set inference width to 480 or 320 to reduce CPU work. Confirm small hands remain detectable.
4. Close unused TD node viewers; keep only OUT open. Keep timeline Real-Time enabled.
5. Reduce layer count and orbit count, or select a lower render resolution. Particle count is a density target and does not significantly change the fixed 3x3-cell shader workload.
6. Reduce webcam request FPS to 24 or 20 for a weak CPU. More smoothing may feel pleasant but cannot fix a low processing rate.
7. Update GPU drivers through the hardware vendor's official support site and confirm Derivative's system requirements.

Use TD's Performance Monitor or Info CHOP cook time to identify the expensive stage. A 30 FPS target allows roughly 33 ms per frame. A CPU tracker publishing 15 FPS can still be displayed at 60 FPS, but this is not 60 fresh tracking results per second.
