// Inputs: 0 current stars, 1 Feedback TOP (previous trails), 2 controls.
layout(location = 0) out vec4 fragColor;
void main() {
    vec4 motion=texelFetch(sTD2DInputs[2],ivec2(1,0),0);
    vec4 velocity=texelFetch(sTD2DInputs[2],ivec2(2,0),0);
    vec4 effects=texelFetch(sTD2DInputs[2],ivec2(6,0),0);
    vec4 display=texelFetch(sTD2DInputs[2],ivec2(8,0),0);
    vec3 current=texture(sTD2DInputs[0],vUV.st).rgb;
    float decay=(velocity.w>=2.5 && effects.z>0.) ? exp(-motion.w/max(effects.z,.001)) : 0.;
    // A small advection step gives motion gentle inertia. Screen UV displacement
    // uses the same bottom-left convention as the tracking controls.
    vec2 offset=velocity.xy*motion.w*.10;
    vec2 uv=vUV.st-offset;
    vec3 previous=vec3(0.);
    if(all(greaterThanEqual(uv,vec2(0.))) && all(lessThanEqual(uv,vec2(1.))))
        previous=texture(sTD2DInputs[1],uv).rgb;
    // Max accumulation keeps stationary stars from growing without bound.
    vec3 result=max(current,previous*decay)*display.z;
    fragColor=TDOutputSwizzle(vec4(result,1.));
}
