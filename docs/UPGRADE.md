# Galaxy and snap lighting update

**The prepared copy in `D:\UIT.Study\NMLT\Mediapipe` has already been upgraded and saved in TouchDesigner. Just double-click Run.bat. No package installation or manual refresh is needed on this computer.**

For an older saved copy, the TouchDesigner document contains its own shader sources, so refresh it once:

1. Stop the tracker by clicking its webcam preview and pressing **Q**.
2. Double-click **UpdateProject.bat** in the project folder. It copies the update command.
3. Open **GalaxyHands.toe** from that same folder in TouchDesigner.
4. Choose **Dialogs -> Textport**, paste with **Ctrl+V**, and press **Enter**.
5. Wait for `Galaxy Hands updated`, then press **Ctrl+S** to save the document.
6. Double-click **Run.bat**. The full galaxy appears in the TouchDesigner display; the separate camera window is the tracking preview.

After this one-time refresh, this saved project reads updated shader/callback files whenever it opens. If you have no saved project yet, use **CreateProject.bat** instead.

The updater validates the required nodes and Python sources first. It keeps a source-only recovery copy in `runtime/td_source_backups`, and restores the embedded source text if the update fails. The original saved `.toe` is backed up during installation; the updater only changes it on disk when you save.

## Try the improved effect

- Move one palm slowly: the galaxy follows with depth between its layers.
- Sweep your hand across the camera: curved star trails follow the movement.
- Touch **thumb + index finger**: the galaxy contracts; release to expand it.
- Raise two hands and spread them apart: enlarge the galaxy. Tilt the line between them to rotate it.
- Press **C** to try the lighting immediately: **Silver -> Solar Amber -> Violet -> Silver**. The transition blends smoothly and emits a short expanding ring.
- Press **D** to see tracking landmarks and snap readiness. Press **-** if 720p is slow; **+** increases quality again. Quality keys affect the running session.

## Make the snap gesture

1. Keep one hand fully in view, about 40-70 cm from the camera, with the palm angled toward it.
2. Touch your **thumb and middle fingertip** together. Keep the index finger away from that contact.
3. Hold the contact for about **0.2 seconds**. In debug mode the hand label should show `snap=READY`.
4. Snap/flick your middle finger quickly away from the thumb, toward your palm, while keeping your wrist fairly steady.
5. The galaxy changes lighting. Wait roughly **one second** before the next snap.

The camera recognizes visible contact and quick finger release, rather than sound. A deliberate middle-finger pinch-and-flick works as an accessible equivalent. A very fast real snap can happen between webcam frames and be missed; **C** always provides the same lighting change. No microphone is used.

If no snap registers, press D and check that the fingertip landmarks follow your fingers. Improve room lighting, avoid overlapping hands, move slightly closer, and hold the contact longer. If your palm is edge-on, face it more toward the camera. The thresholds are adjustable under `snap` in `config.json`; restart after editing.

## What changed

- 720p high quality by default; finer stars, split spiral filaments, subtle nebula, seven orbital arcs, rare diffraction sparkles, shorter trails, and controlled bloom.
- Adaptive landmark/anchor filters reduce still-hand jitter and respond faster to motion. Predicted wrist positions help maintain hand identity across frames.
- A single webcam reader continually takes fresh frames; inference skips old frames if it cannot keep up. Image/control pairing remains synchronous through MediaPipe Tasks.
- A timed snap detector uses relative finger motion, contact dwell and cooldown to avoid treating a moving wrist or an ordinary index pinch as a snap.

The video reference could not be played during development, so an exact match is not claimed. All 57 automated checks pass. The updated shaders also compiled in the actual TouchDesigner installation, the saved project reloaded, and a generated-input display test verified both colored palettes. Your physical snap still needs a webcam check.
