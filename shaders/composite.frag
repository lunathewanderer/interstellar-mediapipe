// Inputs: 0 webcam, 1 trails, 2 horizontal bloom, 3 controls.
layout(location = 0) out vec4 fragColor;
void main() {
    vec4 velocity=texelFetch(sTD2DInputs[3],ivec2(2,0),0);
    vec4 color=texelFetch(sTD2DInputs[3],ivec2(5,0),0);
    vec4 effects=texelFetch(sTD2DInputs[3],ivec2(6,0),0);
    vec4 settings=texelFetch(sTD2DInputs[3],ivec2(7,0),0);
    vec4 display=texelFetch(sTD2DInputs[3],ivec2(8,0),0);
    vec4 accent=texelFetch(sTD2DInputs[3],ivec2(9,0),0);
    vec3 camera=texture(sTD2DInputs[0],vUV.st).rgb*settings.x;
    vec3 stars=texture(sTD2DInputs[1],vUV.st).rgb;
    float sigma=max(.5,effects.y/2.5);
    vec3 bloom=vec3(0.); float weight=0.;
    for(int i=-6;i<=6;++i) {
        float y=float(i)*sigma/2.;
        float w=exp(-.5*y*y/(sigma*sigma));
        bloom+=texture(sTD2DInputs[2],clamp(vUV.st+vec2(0.,y/display.y),vec2(0.),vec2(1.))).rgb*w;
        weight+=w;
    }
    float glow=velocity.w>=2.5 ? effects.x : 0.;
    // Additive radiance with exponential tone mapping keeps a silver-white core.
    vec3 radiance=(stars+glow*bloom/weight)*color.w;
    vec3 luminous=1.-exp(-max(radiance,vec3(0.)));
    float illumination=clamp(dot(bloom/weight,vec3(.2126,.7152,.0722)),0.,.2);
    camera+=camera*accent.rgb*illumination*.30;
    vec3 result=clamp(camera+luminous,0.,1.);
    fragColor=TDOutputSwizzle(vec4(result*display.z,1.));
}
