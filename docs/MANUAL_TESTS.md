# Complete local acceptance checklist

Do these on the computer/camera used for your assignment. Record observations, actual FPS and configuration values. Boxes remain unchecked for your own acceptance run. Automated and real TouchDesigner generated-input results are recorded in TEST_REPORT.md; physical webcam snapping has not been tested during authoring.

## Installation and transport

- [ ] Confirm Python 3.12 x64 and `pip check` passes.
- [ ] Confirm the model checksum matches `models/source.json`.
- [ ] Run unit tests; all pass.
- [ ] Run `tools/smoke_test.py` with no webcam; it passes.
- [ ] In TD, run the builder and inspect all four GLSL TOPs for zero compile errors.
- [ ] Start `app.py --synthetic`; OUT shows the labelled grid and a moving galaxy.
- [ ] Stop synthetic input; OUT becomes black and status reports stopped.
- [ ] Start the real camera: only Python owns it; TD contains no Video Device In TOP.

## Stage 1: actual MediaPipe and one core

- [ ] Raise one hand in normal room lighting; terminal `hands=1` and a core follows.
- [ ] Press d; 21 points/skeleton follow the correct parts of the hand.
- [ ] Move physically to each display edge. Debug points and camera image agree.
- [ ] In mirror mode, moving right in the preview increases CHOP `center_x`; moving up increases `center_y`.
- [ ] Switch mirror false, restart and repeat; there is no second unintended flip.
- [ ] Test your actual left hand alone, then right. Model labels are correct or the documented explicit label override is calibrated.
- [ ] Palm mode anchors near the palm; index mode anchors at landmark 8.
- [ ] A steady hand produces a steady core without conspicuous trembling.

## Snap lighting and fresh frames

- [ ] Run UpdateProject.bat once, paste in Textport, save with Ctrl+S, then restart via Run.bat.
- [ ] C cycles Silver -> Solar Amber -> Violet -> Silver, with a smooth blend and expanding ring.
- [ ] D shows `snap=READY` after a 0.2-second thumb/middle contact; a quick middle-finger flick changes lighting once.
- [ ] Index pinches, wrist translation, slow middle-finger release and ordinary open hands do not change lighting.
- [ ] Both hands snapping together cause one change; wait one second between deliberate snaps.
- [ ] A hand leaving and returning does not cause a false snap.
- [ ] Record success/miss/false-trigger counts for at least 20 attempts in actual room lighting; tune config only from those observations.
- [ ] Rapid sweeps feel responsive without a growing capture delay; compare against latest_frame_capture=false if needed.
- [ ] High quality is 1280x720; press - if GPU load is too high. Record actual FPS rather than inferring it from the shader harness.

## Pinch and release

- [ ] Note open and pinched ratios at near/middle/far distances; thresholds separate them.
- [ ] Very brief tip contact shorter than dwell does not toggle the gate.
- [ ] Hold a pinch: core moves to thumb/index midpoint, tightens and brightens.
- [ ] Move the fingertips around the threshold slightly: the state remains stable.
- [ ] Release/open: galaxy expands smoothly. The application reports pinch release, not a five-finger pose class.
- [ ] Test tilted hands and document the useful angle range/foreshortening limitation.

## Stages 2 and 3: full appearance

- [ ] Stage 2 adds many stable seed-based stars and a concentrated core.
- [ ] Points vary in size and brightness, with more layers at higher quality.
- [ ] Motion remains coherent as the center moves; stars do not become random noise every frame.
- [ ] Stage 3 adds thin elliptical lines and subtle clusters.
- [ ] Curved motion and hand travel produce fading arcs rather than permanent paint.
- [ ] Bloom is luminous while the webcam remains visible.
- [ ] A still hand does not cause feedback brightness to grow indefinitely.
- [ ] Try the color, exposure, glow and trail controls and note your chosen appearance.

## Stage 4: two hands and tracking loss

- [ ] Show two separated hands; `hand_count=2` and the center lies between anchors.
- [ ] Increase the gap: radius increases within configured bounds.
- [ ] Tilt the line between hands: the disk orientation follows smoothly.
- [ ] Change detection order/cross positions slowly: no arbitrary 180-degree flip.
- [ ] Pinch either hand: the shared galaxy contracts; release to expand.
- [ ] Hide one hand for <0.20 s: pair control holds briefly without a center jump.
- [ ] Keep one hand hidden: center eases to the remaining hand, scale returns toward 1, angle stays coherent.
- [ ] Hide both: short hold, gentle damped drift, gradual fade; camera stays live.
- [ ] Reappear on the opposite side: galaxy eases toward the new anchor and fades in.
- [ ] Cross/occlude hands deeply: document any identity ambiguity instead of claiming guaranteed identity.

## Keys, input failure and performance

- [ ] Test q and Esc from tracker preview: process ends, camera is released, shared image clears.
- [ ] Test d toggles actual landmark/debug pixels in both preview and TD.
- [ ] Test r: particle pattern reseeds, feedback clears, smoothing restarts.
- [ ] Test +/= and -: quality changes and feedback resets; repeat at both endpoints.
- [ ] Test keys from TD and document viewer focus requirements.
- [ ] Play a real prerecorded hand video with actual MediaPipe; loop it without timestamp errors.
- [ ] Start two trackers: second exits with a clear duplicate-writer error.
- [ ] Temporarily rename the model: clear missing-model message, no camera silently left open.
- [ ] Run with the wrong camera index: clear open-input error and correct recovery.
- [ ] Stop the producer abruptly: frozen camera is hidden by the TD timeout.
- [ ] Measure 60 seconds each at low, medium and high; write fresh tracking FPS and TD display FPS separately.
- [ ] Run for five minutes; confirm stable memory, no accumulating latency and no recordings created.

## Suggested experiment record

| Scenario | Config/lighting/distance | Observed result | Tracking FPS | TD FPS | Pass/fix |
|---|---|---|---|---|---|
| One hand open | Fill after your test | Not measured | - | - | - |
| Pinch near/far | Fill after your test | Not measured | - | - | - |
| Two-hand scale/tilt | Fill after your test | Not measured | - | - | - |
| One/both hands lost | Fill after your test | Not measured | - | - | - |
| 720p high preset | Fill after your test | Not measured | - | - | - |

Capture demo footage only deliberately after you decide to record. This project does not record automatically.
