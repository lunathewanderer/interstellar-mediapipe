# Understanding the MediaPipe project

Read this alongside `galaxy/gestures.py` and `app.py`. The landmarks come from MediaPipe; event decisions and visual control values are implemented by this project.

## 1. Input and actual inference

One external Python process opens the camera or video using OpenCV. A single webcam reader thread drains capture into a latest-frame slot: inference consumes the newest frame, skipping older frames instead of processing a growing queue. Video files retain sequential decoding. Frames are letterboxed, preserving aspect ratio. A smaller inference image (default width 768) is converted from BGR to RGB and passed to **MediaPipe Tasks Hand Landmarker**, with `num_hands=2` and `RunningMode.VIDEO`.

VIDEO mode is intentionally used for both webcam frames and video files: it returns a result synchronously for each submitted image, simplifying image/control pairing. It supports tracking between frames. LIVE_STREAM is another supported mode but may drop submitted frames while busy; an asynchronous application would need explicit image/result matching. Here, monotonically increasing timestamps come from `time.monotonic()`, including across a video loop. Processing is local on the CPU. [Official Python task guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python).

For each hand MediaPipe provides 21 image landmarks `(x,y,z)` and a handedness category with confidence. `x` and `y` are normalized image coordinates. This application uses XY for controls; relative landmark z is not reliable camera distance. Layer depth in the shader is an artistic visual effect, not a 3D hand reconstruction. [Official model and output description](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/index).

## 2. Coordinates, mirroring and hand identity

Inference uses the unmirrored, letterboxed image. We then transform positions exactly once:

```text
display_x = 1 - model_x       if mirror=true, otherwise model_x
display_y = 1 - model_y       because TouchDesigner UV starts at the bottom
```

The displayed camera is flipped horizontally exactly once when `mirror=true`. Its rows are reversed on upload to the TD Script TOP. The resulting frame and landmarks share the same origin. Debug dots convert display UV back to OpenCV's top-left origin for drawing.

Keep the model's Left/Right labels; displaying a mirror does not automatically relabel a person's anatomy. `swap_handedness` is an explicit calibration override for already-mirrored source videos or a camera pipeline with different handedness conventions. Test by raising only your left hand, then right, and read the debug label. A unit test confirms our transformation preserves the label; it does not certify the model's physical classification on your camera.

Do not use detection list index as permanent hand identity. The association step evaluates possible assignments of up to two current hands to recent tracks. It predicts each wrist from its last raw location and a filtered velocity, capped at a 0.12-second prediction horizon. Its cost is displacement from that prediction plus a small penalty for handedness disagreement. Recent tracks are retained for 0.6 seconds. Geometry dominates a brief label reversal. Crossed hands with heavy occlusion can still be ambiguous; the matcher does not guarantee identity through a complete occlusion.

## 3. Adaptive, time-based smoothing

Landmarks and the selected anchor use a speed-adaptive [One Euro filter](https://gery.casiez.net/1euro/) (Casiez, Roussel and Vogel, CHI 2012). The project implements it directly without another package. For each coordinate:

```text
raw_velocity = (measurement - previous_measurement) / dt
filtered_velocity = low_pass(raw_velocity, derivative_cutoff=1 Hz)
cutoff = minimum_cutoff + beta * abs(filtered_velocity)
alpha = 1 / (1 + 1 / (2*pi*cutoff*dt))
filtered = previous_filtered + alpha * (measurement - previous_filtered)
```

At rest the low cutoff suppresses jitter; during motion the cutoff increases to reduce lag. Defaults are `adaptive_min_cutoff=1.5 Hz` and `adaptive_beta=8`, with normalized coordinates as the units. Lower the minimum for steadier slow motion, or increase beta for a quicker fast-motion response. These parameters do not make camera frames arrive faster or improve the model's raw detection accuracy.

Pinch amount, visibility, scale and angle retain `alpha=1-exp(-dt/tau)`, with `smoothing_seconds=0.085`. Velocity has its separate 0.13-second time constant. Timestamps, rather than frame counts, determine both filters. Filters reset safely on longer detection gaps.

## 4. Pinch as a measured event

Thumb tip = landmark **4**, index tip = **8**, wrist = **0**, middle finger MCP = **9**. For an image with aspect `a = width/height`, define:

```text
distance(i,j) = sqrt(((xi-xj)*a)^2 + (yi-yj)^2)
ratio = distance(4,8) / max(distance(0,9), 0.015)
```

Aspect correction matters: normalized x and y are fractions of different pixel dimensions. Dividing by hand size makes the ratio more consistent as the hand moves nearer or farther from the camera. The denominator floor avoids division by zero on degenerate landmarks. Strong foreshortening still changes the 2D hand size; tune with a mostly frontal hand first.

The gate enters pinch when ratio stays below **0.30** for **0.075 s**. It exits when the ratio stays above **0.46** for the same dwell time. Values between thresholds keep the existing state. This combination of hysteresis and dwell rejects small threshold oscillations and momentary bad landmarks. `PinchGate` is the event logic; the continuous output `pinch` is separately smoothed for animation.

When pinched, the center target is the midpoint of thumb/index tips. Otherwise it is either the average of wrist plus four MCP landmarks `[0,5,9,13,17]` (palm mode) or index tip (index mode). The radius changes continuously from `galaxy_radius * scale` to that value multiplied by `pinched_radius_multiplier` (default 0.12). Core intensity increases with the contraction.

**Opening** in this implementation means releasing a pinch; it is not an independent classifier for all five fingers being extended. This covers the requested open-to-expand interaction without falsely calling a fist an open palm. A future extension can add finger joint-angle features if a distinct open-palm gesture is needed.

## 5. Two-hand control

With two active anchors:

```text
center_target = (anchor_A + anchor_B) / 2
metric_delta = (aspect * delta_x, delta_y)
scale_target = clamp(length(metric_delta) / (aspect * reference_distance), min_scale, max_scale)
orientation_target = atan2(metric_delta.y, metric_delta.x)
```

`reference_distance = 0.45` is measured in image-width units. The line has no arrow: an angle and the same angle plus pi represent the same line. We smooth the shortest difference modulo pi, preventing a 180-degree flip if result order changes. Bounds default to 0.45..2.2. Either hand pinching contracts the single shared galaxy. Separate galaxies per hand are outside this project's current design.

When one hand briefly drops out, the previous pair is held for at most 0.20 s, while `hand_count` immediately reports the fresh detection count. After the hold the remaining hand becomes the center target and scale eases back to 1; the existing orientation is retained. In stages 1..3 TD ignores two-hand scale/orientation so each milestone isolates fewer features.

## 6. Motion and tracking loss

The algorithm estimates UV velocity from the smoothed center, clamps it to +/-2 units/s and smooths it. During total loss it damps velocity exponentially with a 0.25 s time constant, applies a small drift and clamps the center to the frame. Hand visibility is held for 0.20 s then decays exponentially with a 0.65 s constant. Identity state expires independently after 0.6 s. A reappearing hand blends into the current center rather than setting the center in one assignment.

TD also monitors producer age: data older than 0.25 s starts a separate fade, an image older than one second is hidden, and a tracker older than two seconds is marked dead. Normal quit writes a zero image immediately. This handles the different failure cases of hands disappearing and the entire producer process stopping.

## 7. GPU-friendly particles and trails

The GLSL TOP performs an **analytic, deterministic particle field**. A particle has a stable cell ID and a hash-derived subcell position, brightness and phase. The shader maps a pixel backward through ellipse scaling, orientation and differential rotation into the particle domain, then checks only the 3x3 nearby cells for each of at most three depth layers. Stable seeds preserve structure as the hands move. A four-arm density, split spiral filaments, three-octave value-noise nebula, concentrated core and rare star diffraction crosses add detail. Independent sparse stars drift slowly in the background. Thin antialiased orbital arcs change brightness along their circumference.

`particle_count` is an **expected density target**, not an exact allocation of N live particles: hashed rejection, disk masking and overlap change the visible number. Changing it rebuilds the cell lattice. This is documented so you can describe the implementation accurately. Count does not create an N-by-pixel loop. Work is approximately `pixels * (layers * 9 + orbit_count + bloom taps)`, so resolution and layer count are the primary performance controls.

This is not an N-body gravity simulator or a free-flying physics system. It deliberately trades physical interactions for a coherent artistic galaxy. Motion is analytic, seeded and curved; hand velocity offsets layers to create gentle lag. A TD Feedback TOP retains last-frame radiance, slightly advects it along the control velocity and exponentially decays it using `exp(-dt/trail_seconds)`. A component-wise max prevents stationary stars from accumulating unlimited brightness. The moving curved stars leave short arcs. Reset changes the seed epoch and pulses feedback reset.

Separable 13-tap horizontal/vertical Gaussian bloom softens luminous areas. The final shader applies exposure, compresses highlights and adds the effect to the dimmed camera image. All four shaders and feedback textures run on the GPU. Only frame upload and the small control array pass through Python on the TD side. This is the GPU-friendly GLSL particle-pipeline option requested for the project, rather than CPU-drawing thousands of points each frame.

## 8. Visual snap detection and lighting

The thumb (4), middle fingertip (12), wrist (0), and middle MCP (9) define the snap features. Pixel-aspect-correct thumb/middle distance is divided by wrist-to-MCP distance. Middle fingertip position is expressed in a palm-aligned basis, relative to MCP 9 and normalized by the same palm size. This removes simple whole-hand translation, scale and in-plane rotation from the motion feature. It does not remove perspective distortion.

The per-hand state machine requires:

1. Thumb/middle ratio below 0.34, with the index fingertip away from the thumb, for at least 0.055 s. This arms the gesture.
2. Separation above 0.70, increasing faster than 3 palm lengths/s, and middle-finger travel exceeding 0.32 palm lengths, within a 0.20-second release window.
3. A 0.75-second cooldown. The engine also has a global cooldown so simultaneous snaps by both hands cause one lighting change.

A landmark gap above 0.12 s cancels the pending snap. Ordinary index pinches cannot arm it; slow middle-finger releases and a moving wrist alone do not satisfy the trigger. Features use raw relative landmarks because heavy filtering would hide a fast release. This is a visual snap proxy: a rapid middle-finger pinch release also qualifies, and an audible snap between camera frames may be missed.

Each event cycles Silver -> Solar Amber -> Violet -> Silver. C calls the same palette transition. Primary/accent colors blend with a 0.18-second exponential constant, while a 0.28-second pulse drives a brief expanding elliptical wave. The white-hot core retains highlight detail. R resets tracking, seed and palette to silver. Colors and pulse travel with the frame metadata; TD packs them into control texels 5, 9 and 10.

## Configuration reference

Edit JSON with a text editor; keep commas and double quotes valid, then restart `app.py`. The producer sends its effective visual configuration to TD on every frame. `r` resets state, not the config file.

| Setting | Meaning / tuning |
|---|---|
| `camera.index` | Usually 0; try 1 or 2 if another camera exists |
| `camera.width/height/fps` | Requested capture mode; hardware may negotiate a different one |
| `camera.mirror` | Mirror the view and coordinates together |
| `tracking.inference_width` | 768 default; 640 or 480 can reduce CPU load |
| `tracking.latest_frame_capture` | Consume the newest webcam frame instead of a queued frame |
| `tracking.*_confidence` | Detection/presence/tracking thresholds, usually 0.5..0.7 |
| `tracking.swap_handedness` | Explicit label correction after physical left/right self-check |
| `gestures.center_mode` | `palm` or `index` |
| `pinch_enter/exit` | Lower = fingertips must be closer; exit must exceed enter |
| `pinch_dwell_seconds` | Longer rejects flicker but delays the event |
| `smoothing_seconds` | Pinch, scale, angle and visibility animation time constant |
| `adaptive_min_cutoff/adaptive_beta` | Still-hand stability / fast-motion response |
| `snap.*` | Contact/release thresholds, dwell, speed, travel and cooldown |
| `velocity_smoothing_seconds` | Inertia stability |
| `lost_hold_seconds` | Bridge short hand detection gaps |
| `lost_fade_seconds` | How gently the galaxy disappears |
| `identity_hold_seconds` | How long to retain recent identity state; greater than hold |
| `two_hand_reference_distance` | Larger value makes the same hand gap produce a smaller galaxy |
| `min_scale/max_scale` | Clamp two-hand radius multiplier |
| `sensitivity` | Center travel relative to screen center |
| `momentum` | Depth-layer lag amount; reduce toward 0 for tighter following |
| `visual.stage` | 1 core, 2 particles, 3 trails/orbits/glow, 4 two-hand controls |
| `visual.quality` | Starting preset |
| `galaxy_radius` | Radius in fractions of image height |
| `flattening` | Ellipse minor/major ratio, 0..1 |
| `pinched_radius_multiplier` | Contracted radius relative to open radius |
| `color` | RGB light color, e.g. `[1.0,1.0,1.0]` for neutral white |
| `exposure` | Effect brightness before highlight compression |
| `glow/glow_radius_pixels` | Bloom strength and extent |
| `trail_seconds` | Persistence time constant; 0 disables trails |
| `orbit_count/orbit_brightness` | Number (0..12) and intensity of thin ellipse curves |
| `star_size_pixels` | Point size, separate from number of particles |
| `rotation_speed` | Analytic orbital rotation rate |
| `camera_brightness` | Backdrop brightness before adding particles |
| `nebula_brightness/filament_brightness` | Haze and split spiral detail |
| `quality_presets.*.particle_count` | Expected count/density target |
| `quality_presets.*.layers` | 1..3 GPU star layers |
| `quality_presets.*.width/height` | Capture composite/render size, maximum 1280x720 |

Try changing one number at a time and note what changed. For the assignment, explain why your chosen thresholds and smoothing values fit the physical tests you actually ran.
