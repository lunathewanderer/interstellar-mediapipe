"""Optional actual OpenGL compilation/render check; NOT a TouchDesigner test."""
from pathlib import Path
import argparse
import importlib.util
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    import moderngl
    from PIL import Image
    from galaxy.settings import load_config
    cfg=load_config()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quality',choices=('low','medium','high'),default='medium')
    args=parser.parse_args()
    ctx=moderngl.create_standalone_context(require=460)
    print('OpenGL:',ctx.info['GL_VERSION'],'Renderer:',ctx.info['GL_RENDERER'])
    vertex='''#version 460
    in vec2 in_pos;
    out vec3 vUV;
    void main() { vUV=vec3(in_pos*.5+.5,0.); gl_Position=vec4(in_pos,0.,1.); }
    '''
    prefix='''#version 460
    uniform sampler2D sTD2DInputs[INPUT_COUNT];
    in vec3 vUV;
    vec4 TDOutputSwizzle(vec4 c) { return c; }
    '''
    buffer=ctx.buffer(np.array([-1,-1,1,-1,-1,1,1,1],np.float32).tobytes())
    programs={}
    arrays={}
    input_counts={'galaxy':2, 'trail':3, 'glow_h':2, 'composite':4}
    for name in ('galaxy','trail','glow_h','composite'):
        shader_prefix=prefix.replace('INPUT_COUNT',str(input_counts[name]))
        programs[name]=ctx.program(vertex_shader=vertex,fragment_shader=shader_prefix+(ROOT/'shaders'/f'{name}.frag').read_text())
        # Declare the actual binding count; compilers may remove unused elements.
        uniform=programs[name]['sTD2DInputs']
        uniform.value=tuple(range(uniform.array_length)) if uniform.array_length>1 else 0
        arrays[name]=ctx.vertex_array(programs[name],[(buffer,'2f','in_pos')])
        print('PASS: compiled',name)
    p=cfg['quality_presets'][args.quality]
    width,height=p['width'],p['height']
    c=np.zeros((1,16,4),np.float32)
    c[0,0]=[.5,.5,1.,-.24]
    c[0,1]=[0.,1.,4.,1/60]
    c[0,2]=[0.,0.,0.,4.]
    v=cfg['visual']
    c[0,3]=[v['galaxy_radius'],v['flattening'],v['pinched_radius_multiplier'],v['orbit_count']]
    c[0,4]=[p['particle_count'],p['layers'],v['star_size_pixels'],v['rotation_speed']]
    c[0,5]=[*v['color'],v['exposure']]
    c[0,6]=[v['glow'],v['glow_radius_pixels'],v['trail_seconds'],v['orbit_brightness']]
    c[0,7]=[v['camera_brightness'],0,1,0]
    c[0,8]=[width,height,1,.035]
    c[0,9]=[.60,.78,1.,0.]
    c[0,10]=[100.,0.,v['nebula_brightness'],v['filament_brightness']]
    controls=ctx.texture((16,1),4,c.tobytes(),dtype='f4')
    controls.filter=(moderngl.NEAREST,moderngl.NEAREST)
    # Render over a plain dark swatch so no webcam footage is involved.
    backdrop=np.zeros((height,width,4),np.uint8)
    backdrop[:]=[12,15,21,255]
    camera=ctx.texture((width,height),4,backdrop.tobytes(),dtype='f1')
    textures={}
    targets={}
    for name in ('raw','history','trails','glow','final'):
        textures[name]=ctx.texture((width,height),4,dtype='f4')
        textures[name].repeat_x=textures[name].repeat_y=False
        textures[name].filter=(moderngl.LINEAR,moderngl.LINEAR)
        targets[name]=ctx.framebuffer(color_attachments=[textures[name]])
        targets[name].clear()

    def draw(shader,target,inputs):
        for i,texture in enumerate(inputs):
            texture.use(location=i)
        targets[target].use()
        arrays[shader].render(moderngl.TRIANGLE_STRIP)

    output=ROOT/'test-output'
    output.mkdir(exist_ok=True)
    started=time.perf_counter()
    for frame in range(30):
        c[0,1,2]=4+frame/60
        controls.write(c.tobytes())
        draw('galaxy','raw',[controls,camera])
        draw('trail','trails',[textures['raw'],textures['history'],controls])
        draw('glow_h','glow',[textures['trails'],controls])
        draw('composite','final',[camera,textures['trails'],textures['glow'],controls])
        ctx.copy_framebuffer(targets['history'],targets['trails'])
    ctx.finish()
    seconds=time.perf_counter()-started
    values=np.frombuffer(targets['final'].read(components=4,dtype='f4'),np.float32).reshape(height,width,4)
    assert np.isfinite(values).all()
    assert values[:,:,:3].max()>.7, 'Expected a bright core'
    image=np.uint8(np.clip(values[::-1,:,:3],0,1)*255)
    Image.fromarray(image).save(output/'galaxy_shader_preview.png')
    silver_values = values.copy()
    from galaxy.lighting import PALETTES
    for index, (name, primary, accent) in enumerate(PALETTES[1:], start=1):
        c[0,5,:3]=primary
        c[0,9,:3]=accent
        controls.write(c.tobytes())
        draw('galaxy','raw',[controls,camera])
        # Clear old-colored history; a static preview represents a settled palette.
        draw('glow_h','glow',[textures['raw'],controls])
        draw('composite','final',[camera,textures['raw'],textures['glow'],controls])
        palette_values=np.frombuffer(targets['final'].read(components=4,dtype='f4'),np.float32).reshape(height,width,4)
        assert np.isfinite(palette_values).all()
        assert np.mean(abs(palette_values-silver_values)) > .0002
        Image.fromarray(np.uint8(np.clip(palette_values[::-1,:,:3],0,1)*255)).save(output/f'galaxy_{index}.png')
        print('PASS: distinct finite palette',name)
    c[0,5,:3]=v['color']
    c[0,9,:3]=[.60,.78,1.]
    print(f'PASS: 30 generated frames at {width}x{height} in {seconds:.3f}s; finite pixels and bright core')
    def raw_values():
        controls.write(c.tobytes())
        draw('galaxy','raw',[controls,camera])
        return np.frombuffer(targets['raw'].read(components=4,dtype='f4'),np.float32).reshape(height,width,4)[:,:,:3].copy()
    c[0,2,3]=1
    c[0,0,:2]=[.3,.7]
    raw=raw_values().mean(axis=2)
    y,x=np.unravel_index(raw.argmax(),raw.shape)
    assert abs(x-width*.3)<=2 and abs(y-height*.7)<=2, (x,y)
    print('PASS: shader core matches bottom-left control coordinates')
    c[0,0,:2]=[.5,.5]
    c[0,2,3]=4
    open_values=raw_values()
    c[0,1,0]=1
    pinch_values=raw_values()
    open_area=np.count_nonzero(open_values.mean(axis=2)>.03)
    pinch_area=np.count_nonzero(pinch_values.mean(axis=2)>.03)
    assert pinch_area<open_area*.3, (pinch_area,open_area)
    print('PASS: pinch reduces rendered footprint')
    c[0,1,0]=0
    c[0,2,2]=1
    reseeded=raw_values()
    assert np.mean(abs(reseeded-open_values))>.001
    print('PASS: reset epoch changes particle seed')
    c[0,1,1]=0
    assert np.max(raw_values())<1e-7
    print('PASS: zero visibility produces no raw particle radiance')
    print('Saved shader-only preview. This is NOT a TouchDesigner or webcam test.')


if __name__=='__main__':
    main()
