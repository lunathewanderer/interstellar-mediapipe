# Validation report - 24 October 2026

## Current update: tracking, intricate galaxy and snap lighting

**57 automated checks passed** in the Windows Python 3.12.14 project environment. These include existing gesture, bridge, controller and launcher checks, plus:

- Thumb/middle contact and rapid relative release, cooldown, one-frame contact rejection and slow-release rejection.
- No snap from an ordinary index pinch, whole-hand translation, rotation or scale.
- Cancellation on tracking gaps; simultaneous two-hand snaps produce one palette event.
- Smooth palette cycling, raw RGB/pulse packing into TD controls and prediction through a clear synthetic hand crossing.
- Freshest-frame webcam-reader behavior and release, without accessing a physical camera.
- Update preflight and fault injection: a simulated shader cook failure restores embedded source text and shader references. This checks recovery logic, not TD compilation.

In a deterministic 30 FPS landmark sequence moving at 0.6 UV/s, the previous double exponential filter had mean position error **0.08274 UV**; the adaptive filters had **0.03152 UV** (about **62% lower**). Alternating stationary synthetic jitter with standard deviation 0.030 UV produced output standard deviation **0.00111 UV**. These are control-algorithm measurements, not real camera accuracy or end-to-end latency measurements.

## Real model and transport checks

`tools/smoke_test.py` passed: 225 distinct cross-process generated frames, writer-mutex exclusion, reset/debug/quality commands, Silver/Amber/Violet palette changes, one/two-hand transition and zeroed shutdown. The real MediaPipe Hand Landmarker also processed a generated 12-frame no-hands video successfully.

`tools/test_model_samples.py` passed with Google's public fixtures: `thumb_up.jpg` produced one hand with 21 landmarks; `right_hands.jpg` produced two hands with 21 landmarks each. These checks confirm real positive model inference, not physical snap recognition.

Environment: MediaPipe 0.10.32, NumPy 1.26.4, opencv-contrib-python 4.11.0.86. Requirements remain pinned; this update adds no runtime packages. The inference image width is now 768 and output defaults to the high preset, 1280x720. A single background reader discards old webcam frames while MediaPipe VIDEO inference keeps each submitted image paired with its landmarks.

## Actual standalone GPU rendering

All four shaders compiled in OpenGL 4.6 on **AMD Radeon 860M Graphics**, using ModernGL 5.12.0. Thirty generated 1280x720 frames completed in **0.148 s** in one measured harness run. This isolated GPU batch excludes webcam capture, MediaPipe, frame transfer, TD cooking and display, and must not be reported as application FPS.

Checks passed for finite pixels, a bright core, bottom-left coordinate placement, contraction on pinch, different seed patterns after reset, zero radiance when hands are invisible, and distinct finite amber/violet palettes. Generated previews contain only a plain dark backdrop; no user camera footage was captured.

## Actual TouchDesigner update and display check: passed

The existing local `GalaxyHands.toe` was backed up, refreshed inside **TouchDesigner 2025.33230**, saved successfully and reloaded. Its Start callback reopened the display and refreshed sources automatically. The refreshed real TD diagnostic report showed **all four updated shaders compiled successfully**, with no reported operator or script errors. The network uses `OP.setInputs` and a four-input **GLSL Multi TOP** compositor.

A real generated-input producer drove the refreshed TD display at **1280x720**. The display showed the labelled synthetic grid and moving galaxy. Pressing **C in the TD window** switched to Solar Amber and then Violet; both were observed in the real display and producer metadata. Q stopped the producer cleanly and the display became black. The project was then closed. This verifies the updated shader/control/keyboard/display path without accessing the webcam. Sustained application FPS was not benchmarked.

The prepared local `.toe` is ready for Run.bat. `UpdateProject.bat` remains available for older copies. The refresh checks required nodes, retains source recovery copies, and restores embedded text on failure. The original pre-update `.toe` and changed source files remain under `runtime/update_backups`.

## Remaining physical checks

Use [MANUAL_TESTS.md](MANUAL_TESTS.md). Actual snap hit/miss/false-trigger rates, camera exposure/motion blur, responsiveness and sustained application FPS need local validation. No real camera footage was recorded or uploaded in these tests. The visual detector recognizes thumb/middle contact plus a quick release; it cannot prove an audible snap occurred and can miss a gesture between camera frames. C provides the identical lighting change.

The supplied TikTok reference could not be played, so no exact visual match or original source-code reproduction is claimed.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/check_project.py
.\.venv\Scripts\python.exe tools/smoke_test.py
.\.venv\Scripts\python.exe tools/test_model_samples.py
.\.venv\Scripts\python.exe tools/validate_shaders.py --quality high
```

The optional shader harness uses `requirements-dev.txt`; those packages are unnecessary for normal use. The ZIP excludes environments, runtime diagnostics, video inputs, installers and machine-specific `.toe` files, and is checked for valid CRCs.

## Publication check - 26 October 2026

The curated publication copy passed all 57 unit tests and `tools/check_project.py` again. This check did not open a webcam or re-run the earlier GPU/TouchDesigner experiments. Local environments, model binaries, saved `.toe` documents, reports, installers, recordings, backups and unused generated preview images are excluded from the publication.
