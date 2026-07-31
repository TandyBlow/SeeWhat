export const particleFragmentShader = /* glsl */ `
uniform vec3 uParticleColor;
uniform vec3 uLightDir;
uniform float uParticleShape;

varying vec2 vUv;
varying vec3 vNormal;
varying float vAlphaFade;

// --- Procedural shape SDFs (centered at p=0, range ~-0.5 to 0.5) ---

float leafSDF(vec2 p) {
  p.y *= 2.0; // elongate
  float t = clamp(p.y + 0.5, 0.0, 1.0);
  float profile = sin(3.14159 * t);
  float width = 0.18 * profile;
  return abs(p.x) - width;
}

float petalSDF(vec2 p) {
  p.y *= 1.8;
  float t = clamp(p.y + 0.5, 0.0, 1.0);
  float profile = sin(3.14159 * t);
  profile *= smoothstep(-0.35, -0.05, p.y); // notch at base
  float width = 0.22 * profile;
  return abs(p.x) - width;
}

float diamondSDF(vec2 p) {
  p *= 1.5;
  return (abs(p.x) + abs(p.y)) - 0.35;
}

float circleSDF(vec2 p) {
  return length(p * vec2(1.0, 1.2)) - 0.22;
}

void main() {
  vec2 p = vUv - 0.5;

  // Select shape by SDF
  float d;
  if (uParticleShape < 0.5) {
    d = leafSDF(p);
  } else if (uParticleShape < 1.5) {
    d = petalSDF(p);
  } else if (uParticleShape < 2.5) {
    d = diamondSDF(p);
  } else {
    d = circleSDF(p);
  }

  // Anti-aliased edge
  float alpha = 1.0 - smoothstep(-0.02, 0.02, d);
  alpha *= vAlphaFade;
  if (alpha < 0.01) discard;

  // 2-tone toon shading
  vec3 normal = normalize(vNormal);
  float lighting = dot(normal, normalize(uLightDir));
  float shadowMask = smoothstep(-0.3, 0.3, lighting);
  vec3 color = uParticleColor * (0.6 + 0.4 * shadowMask);

  // Leaf: center vein line
  if (uParticleShape < 0.5) {
    float vein = 1.0 - smoothstep(0.0, 0.015, abs(p.x));
    float veinMask = smoothstep(-0.4, 0.0, p.y) * smoothstep(0.45, 0.15, p.y);
    color = mix(color, color * 0.45, vein * veinMask * 0.8);
  }

  // Cyberpunk: edge glow
  if (uParticleShape > 1.5 && uParticleShape < 2.5) {
    float edge = 1.0 - smoothstep(-0.01, 0.03, abs(d));
    color += uParticleColor * edge * 1.5;
  }

  // Ink: soft vignette + desaturate
  if (uParticleShape > 2.5) {
    float vignette = smoothstep(0.0, -0.15, d);
    alpha *= 0.6 + 0.4 * vignette;
    float lum = dot(color, vec3(0.299, 0.587, 0.114));
    color = mix(color, vec3(lum), 0.3);
  }

  gl_FragColor = vec4(color, alpha);
}
`;
