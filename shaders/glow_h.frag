// Inputs: 0 trails, 1 controls. First half of separable Gaussian bloom.
layout(location = 0) out vec4 fragColor;
void main() {
    vec4 effects=texelFetch(sTD2DInputs[1],ivec2(6,0),0);
    vec4 display=texelFetch(sTD2DInputs[1],ivec2(8,0),0);
    float sigma=max(.5,effects.y/2.5);
    vec3 sum=vec3(0.); float weight=0.;
    for(int i=-6;i<=6;++i) {
        float x=float(i)*sigma/2.;
        float w=exp(-.5*x*x/(sigma*sigma));
        sum+=texture(sTD2DInputs[0],clamp(vUV.st+vec2(x/display.x,0.),vec2(0.),vec2(1.))).rgb*w;
        weight+=w;
    }
    fragColor=TDOutputSwizzle(vec4(sum/weight,1.));
}
