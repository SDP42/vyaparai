"use client";

/**
 * "Vyapar breaks apart and becomes intelligence."
 *
 * Every particle has two homes:
 *   aStart  – a pixel sampled from the words "VYAPAR" + "व्यापार" drawn on a 2D canvas
 *   aTarget – a slot in the 3D business-data core (core sphere, four domain nodes,
 *             connecting filaments and an orbit ring)
 * Scroll progress (0 → 1) is passed as a uniform; the vertex shader staggers each
 * particle's journey, bursts it outward mid-flight, and lands it in the core.
 * Everything is one draw call.
 */

import { useEffect, useMemo, useRef, type MutableRefObject } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

import { NODES } from "./nodes";
export { NODES };

const PAPER = new THREE.Color("#f3ece0");
const SINDOOR = new THREE.Color("#d9362b");
const HALDI = new THREE.Color("#e9a426");
const MOR = new THREE.Color("#1f8a7f");
const DIM = new THREE.Color("#7d7266");

function sampleWord(count: number): Float32Array {
  const W = 1600;
  const H = 760;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  const css = getComputedStyle(document.documentElement);
  const display = css.getPropertyValue("--font-bricolage").trim() || "sans-serif";
  const deva = css.getPropertyValue("--font-tiro").trim() || "serif";

  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `800 330px ${display}`;
  ctx.fillText("VYAPAR", W / 2, H * 0.38);
  ctx.font = `400 150px ${deva}`;
  ctx.fillText("व्यापार", W / 2, H * 0.8);

  const data = ctx.getImageData(0, 0, W, H).data;
  const pts: number[] = [];
  const step = 3;
  for (let y = 0; y < H; y += step) {
    for (let x = 0; x < W; x += step) {
      if (data[(y * W + x) * 4 + 3] > 128) pts.push(x, y);
    }
  }
  const out = new Float32Array(count * 3);
  const n = pts.length / 2 || 1;
  for (let i = 0; i < count; i++) {
    const j = Math.floor(Math.random() * n) * 2;
    out[i * 3] = ((pts[j] ?? W / 2) - W / 2) / W;
    out[i * 3 + 1] = -((pts[j + 1] ?? H / 2) - H / 2) / W;
    out[i * 3 + 2] = (Math.random() - 0.5) * 0.012;
  }
  return out;
}

function buildTargets(count: number) {
  const target = new Float32Array(count * 3);
  const color = new Float32Array(count * 3);
  const v = new THREE.Vector3();
  const c = new THREE.Color();
  const golden = Math.PI * (3 - Math.sqrt(5));

  for (let i = 0; i < count; i++) {
    const r = Math.random();
    if (r < 0.42) {
      // Core: fibonacci sphere shell + a denser nucleus
      const k = i % 4000;
      const y = 1 - (k / 3999) * 2;
      const rad = Math.sqrt(1 - y * y);
      const th = golden * k;
      const R = Math.random() < 0.8 ? 1.35 : 0.55 * Math.random();
      v.set(Math.cos(th) * rad * R, y * R, Math.sin(th) * rad * R);
      c.copy(SINDOOR).lerp(HALDI, Math.random() * 0.25);
    } else if (r < 0.7) {
      // Four domain nodes
      const node = NODES[i % 4];
      const u = Math.random() * Math.PI * 2;
      const w = Math.acos(2 * Math.random() - 1);
      const R = 0.42 * Math.cbrt(Math.random());
      v.set(
        node.pos[0] + R * Math.sin(w) * Math.cos(u),
        node.pos[1] + R * Math.sin(w) * Math.sin(u),
        node.pos[2] + R * Math.cos(w),
      );
      c.copy(i % 2 ? HALDI : MOR);
      if (node.key === "forecast") c.copy(HALDI);
      if (node.key === "customers") c.copy(MOR);
    } else if (r < 0.85) {
      // Filaments: core ↔ node, slightly curved
      const node = NODES[i % 4];
      const t = Math.random();
      const bend = Math.sin(t * Math.PI) * 0.35;
      v.set(node.pos[0] * t, node.pos[1] * t + bend, node.pos[2] * t);
      v.addScalar((Math.random() - 0.5) * 0.04);
      c.copy(PAPER).lerp(HALDI, t * 0.6);
    } else {
      // Orbit ring, tilted like a ledger's binding thread
      const a = Math.random() * Math.PI * 2;
      const R = 2.25 + (Math.random() - 0.5) * 0.08;
      v.set(Math.cos(a) * R, Math.sin(a) * R * 0.28, Math.sin(a) * R);
      v.applyAxisAngle(new THREE.Vector3(0, 0, 1), -0.32);
      c.copy(DIM);
    }
    v.toArray(target, i * 3);
    c.toArray(color, i * 3);
  }
  return { target, color };
}

const vertexShader = /* glsl */ `
  uniform float uProgress;
  uniform float uTime;
  uniform float uWordScale;
  uniform float uCoreScale;
  uniform float uPixelRatio;
  uniform vec2 uMouse;
  attribute vec3 aStart;
  attribute vec3 aTarget;
  attribute vec3 aColor;
  attribute vec4 aRand;
  varying vec3 vColor;
  varying float vAlpha;

  float easeInOut(float t) { return t < 0.5 ? 4.0*t*t*t : 1.0 - pow(-2.0*t + 2.0, 3.0) / 2.0; }

  void main() {
    // Word stage → shatter → core. Stagger by a per-particle delay.
    float m = clamp((uProgress - 0.08) / 0.6, 0.0, 1.0);
    float delay = aRand.x * 0.45;
    float t = easeInOut(clamp((m - delay) / 0.55, 0.0, 1.0));

    vec3 start = aStart * uWordScale;
    // Gentle breathing while still a word
    start.z += sin(uTime * 1.3 + aStart.x * 18.0) * 0.015;
    // Pointer repulsion while still a word
    vec2 d = start.xy - uMouse;
    float push = (1.0 - t) * exp(-dot(d, d) * 6.0) * 0.35;
    start.xy += normalize(d + 0.0001) * push;

    vec3 target = aTarget * uCoreScale;
    // Idle drift once assembled
    target += vec3(
      sin(uTime * 0.7 + aRand.y * 6.28),
      cos(uTime * 0.6 + aRand.z * 6.28),
      sin(uTime * 0.5 + aRand.w * 6.28)
    ) * 0.025 * t;

    // Mid-flight burst: shards fly outward and twist before landing
    vec3 dir = normalize(vec3(aRand.y - 0.5, aRand.z - 0.5, aRand.w - 0.35));
    float burst = sin(t * 3.14159) * (1.6 + aRand.x * 2.2);
    vec3 pos = mix(start, target, t) + dir * burst;
    float ang = burst * 0.35;
    pos.xz = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * pos.xz;

    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mv;

    float size = mix(2.2, 2.9, aRand.y) + sin(t * 3.14159) * 2.2;
    gl_PointSize = size * uPixelRatio * (9.0 / -mv.z);

    vec3 paper = vec3(0.953, 0.925, 0.878);
    vec3 haldi = vec3(0.914, 0.643, 0.149);
    vColor = mix(mix(paper, aColor, t), haldi, sin(t * 3.14159) * 0.55);
    vAlpha = 0.9;
  }
`;

const fragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vAlpha;
  void main() {
    vec2 c = gl_PointCoord - 0.5;
    float r = length(c);
    if (r > 0.5) discard;
    float a = smoothstep(0.5, 0.05, r) * vAlpha;
    gl_FragColor = vec4(vColor, a);
  }
`;

type Props = {
  progress: MutableRefObject<number>;
  labelRefs: MutableRefObject<(HTMLDivElement | null)[]>;
};

function Particles({ progress, labelRefs }: Props) {
  const { viewport, size, camera, gl } = useThree();
  const count = size.width < 768 ? 8000 : 16000;
  const points = useRef<THREE.Points>(null);
  const group = useRef<THREE.Group>(null);
  const smooth = useRef(0);
  const mouse = useRef(new THREE.Vector2(99, 99));

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const start = sampleWord(count);
    const { target, color } = buildTargets(count);
    const rand = new Float32Array(count * 4);
    for (let i = 0; i < rand.length; i++) rand[i] = Math.random();
    g.setAttribute("position", new THREE.BufferAttribute(start, 3));
    g.setAttribute("aStart", new THREE.BufferAttribute(start, 3));
    g.setAttribute("aTarget", new THREE.BufferAttribute(target, 3));
    g.setAttribute("aColor", new THREE.BufferAttribute(color, 3));
    g.setAttribute("aRand", new THREE.BufferAttribute(rand, 4));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 20);
    return g;
  }, [count]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: {
          uProgress: { value: 0 },
          uTime: { value: 0 },
          uWordScale: { value: 8 },
          uCoreScale: { value: 1 },
          uPixelRatio: { value: 1 },
          uMouse: { value: new THREE.Vector2(99, 99) },
        },
      }),
    [],
  );

  useEffect(() => () => {
    geometry.dispose();
    material.dispose();
  }, [geometry, material]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      mouse.current.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  const tmp = useMemo(() => new THREE.Vector3(), []);

  useFrame((state, delta) => {
    smooth.current += (progress.current - smooth.current) * Math.min(1, delta * 4);
    const p = smooth.current;
    const u = material.uniforms;
    u.uProgress.value = p;
    u.uTime.value = state.clock.elapsedTime;
    u.uPixelRatio.value = gl.getPixelRatio();
    u.uWordScale.value = Math.min(viewport.width * 0.86, 11);
    u.uCoreScale.value = THREE.MathUtils.clamp(viewport.width / 10.5, 0.36, 0.9);
    (u.uMouse.value as THREE.Vector2).set(
      (mouse.current.x * viewport.width) / 2,
      (mouse.current.y * viewport.height) / 2,
    );

    // Zoom: camera pushes in as the core assembles, then eases back slightly.
    const zoom = THREE.MathUtils.smoothstep(p, 0.35, 0.8);
    camera.position.z = 9 - zoom * 1.6 + THREE.MathUtils.smoothstep(p, 0.85, 1) * 0.9;
    camera.position.y = THREE.MathUtils.lerp(0, 0.35, zoom);
    camera.lookAt(0, 0, 0);

    if (group.current) {
      const spin = THREE.MathUtils.smoothstep(p, 0.45, 1);
      // Gentle sway (not a full spin) so the four domain nodes stay readable.
      group.current.rotation.y = spin * (0.25 * Math.sin(state.clock.elapsedTime * 0.3)) + mouse.current.x * 0.12 * spin;
      group.current.rotation.x = mouse.current.y * -0.05 * spin;
    }

    // Project node centres to screen to position the HTML labels.
    const reveal = THREE.MathUtils.smoothstep(p, 0.72, 0.86);
    NODES.forEach((node, i) => {
      const el = labelRefs.current[i];
      if (!el || !group.current) return;
      tmp.set(node.pos[0], node.pos[1], node.pos[2]).multiplyScalar(u.uCoreScale.value as number);
      tmp.applyMatrix4(group.current.matrixWorld).project(camera);
      const x = (tmp.x * 0.5 + 0.5) * size.width;
      const y = (-tmp.y * 0.5 + 0.5) * size.height;
      el.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -150%)`;
      el.style.opacity = String(reveal * (tmp.z < 1 ? 1 : 0));
    });
  });

  return (
    <group ref={group}>
      <points ref={points} geometry={geometry} material={material} frustumCulled={false} />
    </group>
  );
}

export default function ShatterScene({ progress, labelRefs, active }: Props & { active: boolean }) {
  return (
    <Canvas
      camera={{ position: [0, 0, 9], fov: 35 }}
      dpr={[1, 1.75]}
      gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
      frameloop={active ? "always" : "never"}
      aria-hidden
    >
      <Particles progress={progress} labelRefs={labelRefs} />
    </Canvas>
  );
}
