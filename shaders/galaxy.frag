// Inputs: 0 controls, 1 webcam. Analytic, deterministic GPU star cells.
layout(location = 0) out vec4 fragColor;
vec4 ctl(int i) { return texelFetch(sTD2DInputs[0], ivec2(i, 0), 0); }
float hash21(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * .1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}
mat2 rotation(float a) { float c=cos(a), s=sin(a); return mat2(c,s,-s,c); }
float valueNoise(vec2 p) {
    vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(hash21(i),hash21(i+vec2(1,0)),f.x),
               mix(hash21(i+vec2(0,1)),hash21(i+1.),f.x),f.y);
}
float cloud(vec2 p) {
    return .57*valueNoise(p)+.28*valueNoise(rotation(.7)*p*2.1+8.)+.15*valueNoise(p*4.3+17.);
}
float particles(vec2 q, float cellScale, float size, float seed, float t) {
    vec2 grid=q*cellScale, base=floor(grid);
    mat2 toPixels=inverse(mat2(dFdx(grid),dFdy(grid))+mat2(1e-7));
    float light=0.;
    for(int y=-1;y<=1;++y) for(int x=-1;x<=1;++x) {
        vec2 id=base+vec2(x,y);
        float h=hash21(id+seed);
        vec2 pos=id+vec2(hash21(id+seed+7.3),hash21(id+seed+81.7));
        vec2 local=pos/cellScale;
        float r=length(local), theta=atan(local.y,local.x);
        float arm=pow(.5+.5*cos(4.*theta-9.*r),3.);
        float density=(.18+.60*exp(-1.7*r))*(.25+.75*arm);
        if(r<1.15 && h<density) {
            vec2 d=toPixels*(grid-pos);
            float bright=hash21(id+seed+121.);
            float radius=size*mix(.44,1.8,pow(bright,12.));
            float sparkle=.78+.22*pow(.5+.5*sin(t*(1.2+2.*h)+bright*60.),4.);
            float core=exp(-dot(d,d)/max(.16,radius*radius));
            float halo=.045*exp(-length(d)/max(.2,radius*2.));
            float flare=0.;
            if(bright>.985) {
                flare=.16*(exp(-abs(d.x)*5.-abs(d.y)/3.)+
                           exp(-abs(d.y)*5.-abs(d.x)/3.));
            }
            light+=(core+halo+flare)*sparkle*(.32+2.5*pow(bright,10.))*(1.-smoothstep(.80,1.15,r));
        }
    }
    return light;
}
void main() {
    vec4 pose=ctl(0), motion=ctl(1), velocity=ctl(2), shape=ctl(3), quality=ctl(4);
    vec4 color=ctl(5), effects=ctl(6), display=ctl(8), accent=ctl(9), detail=ctl(10);
    float aspect=display.x/max(display.y,1.);
    vec2 p=(vUV.st-pose.xy)*vec2(aspect,1.);
    float t=motion.z, pinch=clamp(motion.x,0.,1.), stage=velocity.w;
    float radius=shape.x*pose.z*mix(1.,shape.z,pinch);
    vec3 light=vec3(0.);
    if(stage<1.5) {
        float r=length(p);
        light=color.rgb*(exp(-r*r/.000045)+.18*exp(-r*r/.0007));
    } else {
        vec2 disk=rotation(-pose.w)*p/max(radius,.001);
        disk.y/=max(.18,shape.y);
        float r=length(disk), theta=atan(disk.y,disk.x);
        float spin=t*quality.w;
        float starLight=0.;
        for(int layer=0;layer<3;++layer) {
            float depth=float(layer);
            vec2 lag=velocity.xy*vec2(aspect,1.)*display.w*(depth-.5);
            vec2 q=rotation(-pose.w-.10*depth)*(p+lag)/max(radius*(1.+.10*depth),.001);
            q.y/=max(.18,shape.y+.075*depth);
            float qr=length(q);
            q=rotation(-spin*(1.+.16*depth)-1.8*qr)*q;
            float grid=sqrt(max(quality.x,10.)/(3.141593*max(quality.y,1.)*.40));
            float points=particles(q,grid,quality.z*(.72+.25*depth),
                                   73.*depth+velocity.z*91.,t);
            if(float(layer)<quality.y) starLight+=points*(.75+.12*depth);
        }
        float turbulence=cloud(disk*6.+vec2(t*.025,-t*.018));
        float phase=4.*(theta-spin)-11.*r+1.5*(turbulence-.5);
        float arms=pow(.5+.5*cos(phase),6.);
        float split=pow(.5+.5*cos(phase*2.+r*9.),18.);
        float envelope=(1.-smoothstep(.85,1.25,r))*smoothstep(.04,.20,r)*exp(-r*.65);
        float filaments=(arms*.24+split*.17)*envelope*(.35+.65*turbulence)*detail.w;
        float nebula=(.025+.16*arms)*envelope*turbulence*detail.z;
        float core=1.5*exp(-r*r/.0035)*(1.+pinch*.8)+.12*exp(-r*r/.10);
        vec3 whiteCore=mix(color.rgb,vec3(1.),.62);
        vec3 starColor=mix(color.rgb,whiteCore,.24*exp(-r*2.));
        light=starColor*starLight+whiteCore*core+accent.rgb*(filaments+nebula);
        if(stage>=2.5) {
            float orbits=0.;
            for(int k=0;k<12;++k) {
                if(float(k)>=shape.w) break;
                float fk=float(k);
                vec2 oval=rotation(-pose.w-.085*fk)*p/max(radius,.001);
                oval.y/=(shape.y+.032*fk);
                float a=atan(oval.y,oval.x);
                float ringRadius=.44+.11*fk+.012*sin(a*3.+t*.18+fk);
                float dist=length(oval)-ringRadius;
                float lineWidth=max(fwidth(dist)*.48,.0005);
                float arc=.12+.88*pow(.5+.5*sin(a+t*(.15+.012*fk)+fk*1.7),5.);
                orbits+=exp(-dist*dist/(lineWidth*lineWidth))*arc*effects.w;
            }
            light+=mix(color.rgb,accent.rgb,.45)*orbits;
            float waveR=detail.x*2.5, waveDist=r-waveR;
            float wave=exp(-waveDist*waveDist/.0015)*accent.a*.22*
                       smoothstep(0.,.06,detail.x)*(1.-smoothstep(.75,1.3,waveR));
            light+=accent.rgb*wave;
        }
        vec2 sparse=(vUV.st-.5)*vec2(aspect,1.)*.85+vec2(t*.001,-t*.0006);
        light+=mix(color.rgb,vec3(1.),.5)*particles(sparse,10.,quality.z*.65,
                                                302.+velocity.z*91.,t)*.14;
        light*=1.+accent.a*.16;
    }
    fragColor=TDOutputSwizzle(vec4(max(light,vec3(0.))*motion.y,1.));
}
