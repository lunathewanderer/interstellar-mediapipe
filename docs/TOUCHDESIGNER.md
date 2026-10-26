# Exact TouchDesigner network recipe

Target: TouchDesigner 2025.33230 Official, Windows x64, GLSL 4.60. This recipe is supplied because a `.toe` could not be created and tested here. It is intended to be executable without guessing; operator API differences must still be checked on the installed TD build.

## Fast path: the builder

Start `app.py --stage 1` first. Open a new TouchDesigner document. Open Dialogs -> Textport and enter:

```python
project_dir = r'D:/UIT.Study/NMLT/Mediapipe'
builder = project_dir + '/touchdesigner/build_network.py'
exec(compile(open(builder, encoding='utf-8').read(), builder, 'exec'))
```

If the folder moved, change only the first line. On rebuilding, a recognized Galaxy Hands network for the same project folder is preserved under `galaxy_previous_1` (or the next available number), and its frame tick is disabled. An unrelated `/project1/galaxy` is left untouched and must be renamed before building. A failed partial build is preserved for diagnosis.

Navigate into `/project1/galaxy`, right-click `OUT` -> View. Keep timeline Play and Real-Time on. The tracker preview and OUT should agree on the hand location. Save As `GalaxyHands.toe` in the project root. TD's Python uses bundled NumPy; the external `.venv` is never added to its package search path.

## Manual path: every operator

Create a **Base COMP** named `galaxy` inside `/project1`; enter it. Create the following operators with these exact names. TAB opens the operator creation dialog; pick the stated family (TOP, DAT, CHOP). Unmentioned parameters stay at defaults.

Create a string custom parameter on the Base COMP: right-click its body -> Customize Component -> add a page named Galaxy -> String parameter with internal name `Projectdir`, label `Project directory`. Its value must be the **absolute GalaxyHands folder**, e.g. `D:/UIT.Study/NMLT/Mediapipe`. No quotes in the parameter field. The alternative Textport command for this step is:

```python
b = op('/project1/galaxy')
p = b.appendCustomPage('Galaxy')
p.appendStr('Projectdir', label='Project directory')[0].val = project_dir
```

`project_dir` is the first line of the fast-path commands above.

| Operator name | Family/type | DAT contents or parameters |
|---|---|---|
| `controller` | Text DAT | Entire `touchdesigner/controller.py` |
| `webcam_callbacks` | Text DAT | Entire `touchdesigner/webcam_callbacks.py` |
| `controls_callbacks` | Text DAT | Entire `touchdesigner/controls_callbacks.py` |
| `channels_callbacks` | Text DAT | Entire `touchdesigner/channels_callbacks.py` |
| `keyboard_callbacks` | Text DAT | Entire `touchdesigner/keyboard_callbacks.py` |
| `status` | Text DAT | Initial text `Waiting for tracker.`; runtime replaces it |
| `galaxy_pixel` | Text DAT | Entire `shaders/galaxy.frag` |
| `trail_pixel` | Text DAT | Entire `shaders/trail.frag` |
| `glow_h_pixel` | Text DAT | Entire `shaders/glow_h.frag` |
| `composite_pixel` | Text DAT | Entire `shaders/composite.frag` |
| `webcam` | Script TOP | Callbacks DAT = `webcam_callbacks`; default 8-bit RGBA |
| `controls` | Script TOP | Callbacks DAT = `controls_callbacks`; Common Pixel Format = **32-bit float RGBA** (`rgba32float`) |
| `gesture_channels` | Script CHOP | Callbacks DAT = `channels_callbacks`; no inputs |
| `galaxy_raw` | GLSL TOP | Pixel Shader = `galaxy_pixel` |
| `history` | Feedback TOP | Target TOP = `trails`; Reset = Off |
| `trails` | GLSL TOP | Pixel Shader = `trail_pixel` |
| `glow_horizontal` | GLSL TOP | Pixel Shader = `glow_h_pixel` |
| `final_composite` | GLSL Multi TOP | Pixel Shader = `composite_pixel`; four ordered inputs |
| `OUT` | Null TOP | Input from `final_composite` |
| `display_window` | Window COMP | Window Operator (`winop`) = `OUT`; opens on project startup |
| `frame_tick` | Execute DAT | Entire `touchdesigner/frame_callbacks.py` in this DAT itself |
| `keyboard` | Keyboard In DAT | Callbacks DAT = `keyboard_callbacks`; Active On |

For full DAT contents, open the indicated source file and copy **all of it** into the matching DAT. Alternatively, after creating the DATs, paste these complete Textport lines to load the exact files:

```python
b = op('/project1/galaxy')
sources = {'controller':'touchdesigner/controller.py', 'webcam_callbacks':'touchdesigner/webcam_callbacks.py', 'controls_callbacks':'touchdesigner/controls_callbacks.py', 'channels_callbacks':'touchdesigner/channels_callbacks.py', 'keyboard_callbacks':'touchdesigner/keyboard_callbacks.py', 'galaxy_pixel':'shaders/galaxy.frag', 'trail_pixel':'shaders/trail.frag', 'glow_h_pixel':'shaders/glow_h.frag', 'composite_pixel':'shaders/composite.frag', 'frame_tick':'touchdesigner/frame_callbacks.py'}
for name, filename in sources.items(): b.op(name).text = open(project_dir + '/' + filename, encoding='utf-8').read()
```

All shader/DAT contents are included as complete files in the project. Do not replace TouchDesigner callbacks with snippets in the Textport: they need to live in their corresponding DATs. Auto-created docked callback DATs can stay unused; the explicit Callbacks DAT path selects the intended one.

## GLSL TOP parameters

Apply these to **all four shader TOPs** (`galaxy_raw`, `trails`, `glow_horizontal`, `final_composite`). The first three are GLSL TOPs; `final_composite` must be a **GLSL Multi TOP**, because it uses four inputs. A regular GLSL TOP supports only three inputs.

| Page | Parameter label (internal name) | Value |
|---|---|---|
| GLSL | Mode (`mode`) | Vertex/Pixel Shader; default |
| GLSL | GLSL Version (`glslversion`) | 4.60 (`glsl460`) |
| GLSL | Pixel Shader (`pixeldat`) | Matching Text DAT above |
| GLSL | Vertex Shader | Leave default fullscreen vertex behavior |
| Common | Pixel Format (`format`) | 16-bit float RGBA (`rgba16float`) |
| Common | Output Resolution (`outputresolution`) | Custom (`custom`) |
| Common | Resolution W (`resolutionw`) | Python expression below |
| Common | Resolution H (`resolutionh`) | Python expression below |
| Common | Input Smoothness (`inputfiltertype`) | Interpolate Pixels / Linear |

Set W to **Expression mode**, then enter:

```python
int(op('controller').module.state(parent()).controls[0,8,0]) or 960
```

H, also Expression mode:

```python
int(op('controller').module.state(parent()).controls[0,8,1]) or 540
```

Use no custom vector uniforms: **there are none to configure**. Controls are supplied as a 16x1 floating-point Script TOP and read by `texelFetch`. This avoids error-prone uniform menu setup. The controls Script TOP must not be quantized to 8-bit or resized. The shader itself supplies `fragColor`, uses `vUV.st`, and calls `TDOutputSwizzle`. Do not add `#version` or redeclare `sTD2DInputs` inside the supplied TD DATs; TouchDesigner supplies these. The standalone test harness adds its own shim only outside TD. [Official GLSL TOP guide](https://derivative.ca/UserGuide/Write_a_GLSL_TOP).

## Exact wires (zero-based shader input indexes)

Connect in this order; each line identifies the **destination input**:

The builder uses `OP.setInputs([source0, source1, ...])`, as defined by the installed TouchDesigner 2025 Python API. The singular `setInput` method does not exist. The input-list order below is the shader interface.

| Destination | Input 0 | Input 1 | Input 2 | Input 3 |
|---|---|---|---|---|
| `galaxy_raw` | `controls` | `webcam` | - | - |
| `history` | `galaxy_raw` | - | - | - |
| `trails` | `galaxy_raw` | `history` | `controls` | - |
| `glow_horizontal` | `trails` | `controls` | - | - |
| `final_composite` | `webcam` | `trails` | `glow_horizontal` | `controls` |
| `OUT` | `final_composite` | - | - | - |

Set `history` Target TOP (`top`) to `trails`, Reset (`reset`) Off. Pulse Reset Pulse (`resetpulse`) once. **Do not wire `trails` physically back into `history`.** The Feedback TOP's target implements the previous-frame dependency. This keeps a valid feedback loop. [Official Feedback TOP behavior](https://derivative.ca/UserGuide/Feedback_TOP).

`frame_tick` parameters: Active **On**, Start **On**, Frame Start **On**, Exit **On**; Create, Frame End, Play State Change and Device Change **Off**. Its `onStart()` opens `display_window`; `onFrameStart(frame)` calls the controller, which force-cooks the two Script TOPs and Script CHOP once per TD frame. Enable Active last, after all nodes and wires exist.

`keyboard` callback signature follows the official [keyboardinDAT class](https://derivative.ca/UserGuide/KeyboardinDAT_Class). For predictable keyboard focus during the initial test, use the external tracker preview. A TD viewer window may need to be clicked before keyboard callbacks arrive.

## CHOP channel names

`gesture_channels` contains one sample per channel. They are diagnostics and convenient hooks for future TD controls; the supplied shaders read the texture directly.

| Channel | Meaning |
|---|---|
| `center_x`, `center_y` | Display UV center, bottom-left origin |
| `scale` | Two-hand scale, otherwise 1 after smoothing |
| `angle` | Galaxy line orientation in radians, periodic modulo pi |
| `pinch` | Smoothed contraction amount, 0..1 |
| `visibility` | Smoothed hand visibility multiplied by stale-data fade |
| `velocity_x`, `velocity_y` | Display UV velocity per second |
| `hand_count` | Fresh detections, 0..2; not retained ghost hands |
| `alive` | 1 for a fresh running tracker; 0 for stale/stopped |
| `frame_age` | Seconds since producer timestamp |
| `stage` | 1..4 |

Control texture layout, each row is RGBA of one texel at `(index,0)`:

| Index | R | G | B | A |
|---|---|---|---|---|
| 0 | center X | center Y | scale | angle |
| 1 | pinch | visibility | elapsed seconds | TD delta seconds |
| 2 | velocity X | velocity Y | reset epoch | stage |
| 3 | galaxy radius | flattening | pinch radius factor | orbit count |
| 4 | particle count target | layers | star size | rotation speed |
| 5 | color R | color G | color B | exposure |
| 6 | glow | glow pixel radius | trail seconds | orbit brightness |
| 7 | camera brightness | debug enabled | hand count | 0 |
| 8 | render width | render height | alive | momentum |
| 9 | accent R | accent G | accent B | snap pulse |
| 10 | seconds since lighting change | palette index | nebula brightness | filament brightness |
| 11..15 | 0 | 0 | 0 | 0 |

## Verify in small steps

1. View `webcam`: live, correctly mirrored camera image. Script TOP arrays are RGBA uint8 `(H,W,4)`; controller reverses the row order once for TD's origin. No second camera operator is present.
2. View `status`: `TRACKING | hands ...` or `SYNTHETIC`. `WAITING` means no producer. `STOPPED / STALE` means timestamps stopped.
3. Inspect `gesture_channels`: move your hand right in the mirrored display; `center_x` must increase. Move up; `center_y` increases. Pinch; `pinch` approaches 1.
4. Stage 1: view `galaxy_raw`; a core appears on black only while a hand is present. OUT puts this over the webcam.
5. Stage 2: `galaxy_raw` adds particles. Stage 3: `trails` retains fading arcs and `glow_horizontal` is visibly blurred. Stage 4: two hands scale and tilt the disk.
6. Stop the tracker. Its final image is zeroed; OUT becomes black. With an abrupt process crash, TD fades effects and hides a frozen image after one second.

For shader errors create an **Info DAT**, point its Operator (`op`) parameter at the failing GLSL TOP, and read compiler output. In Textport:

```python
print(op('/project1/galaxy/galaxy_raw').errors())
print(op('/project1/galaxy/final_composite').errors())
```

## Opening later, moving folders and fullscreen

Open the saved `.toe` in Explorer or with PowerShell:

```powershell
Invoke-Item -LiteralPath 'D:\UIT.Study\NMLT\Mediapipe\GalaxyHands.toe'
```

Or run `main.py`, which opens the saved project and starts tracking together. If the folder moved, update the Base COMP's `Projectdir`, save and reopen the `.toe`. New projects load current sources on startup through `refresh_project.py`. Older saved projects need the one-time **UpdateProject.bat** refresh and Ctrl+S first; see [UPGRADE.md](UPGRADE.md).

The builder creates a Window COMP named `display_window`, with Window Operator (`winop`) set to `OUT`. The Start callback opens it when the saved project loads, so `main.py` can open the visual application directly. If needed, pulse Open (`winopen`) manually, or right-click OUT -> View. Closing the display leaves the project intact. Startup reopening, shader refresh and the generated-input display were checked in the local TouchDesigner 2025.33230 installation.
