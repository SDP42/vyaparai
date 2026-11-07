"use client";

/**
 * Hero visual — the data-to-decision engine.
 * Four distinct 3D data objects orbit a luminous core (Sales, Customers, Inventory,
 * Forecasts). Particles stream from each object into the core, and a beam carries the
 * result out to a "decision". Hover an object (or its legend item) to focus it.
 * Everything is procedural; essential text stays in HTML.
 */

import { useEffect, useMemo, useRef, type MutableRefObject } from "react";
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";

export const CORE_NODES = [
  { key: "sales", label: "Sales", detail: "₹18.5L net · ▼6.2%", color: "#7357e8", pos: [-1.95, 1.05, 0.2] },
  { key: "customers", label: "Customers", detail: "1,284 active · 142 lapsed", color: "#3296f5", pos: [1.95, 1.2, -0.3] },
  { key: "inventory", label: "Inventory", detail: "17 SKUs at risk", color: "#c6a66b", pos: [-1.8, -1.3, -0.2] },
  { key: "forecasts", label: "Forecasts", detail: "+4% next 14 days", color: "#9d8bf2", pos: [1.9, -1.25, 0.35] },
] as const;

// ---------- core ----------

const coreVert = /* glsl */ `
  varying vec3 vN; varying vec3 vV; varying vec3 vP;
  uniform float uTime;
  void main(){
    vec3 p = position;
    float n = sin(p.x*4.0+uTime*1.3)*sin(p.y*4.0+uTime*1.1)*sin(p.z*4.0+uTime*0.9);
    p += normal * n * 0.045;
    vec4 mv = modelViewMatrix * vec4(p,1.0);
    vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); vP = p;
    gl_Position = projectionMatrix * mv;
  }`;
const coreFrag = /* glsl */ `
  varying vec3 vN; varying vec3 vV; varying vec3 vP;
  uniform float uTime; uniform float uPulse;
  void main(){
    float f = pow(1.0 - max(dot(vN, vV), 0.0), 2.4);
    vec3 a = vec3(0.451,0.341,0.910); vec3 b = vec3(0.196,0.588,0.961);
    vec3 col = mix(a, b, 0.5 + 0.5*sin(vP.y*2.0 + uTime*0.8));
    float bands = smoothstep(0.92, 1.0, sin(vP.y*22.0 - uTime*2.0)) * 0.25;
    vec3 c = col * (0.18 + f*1.6 + bands) + vec3(1.0)*pow(f,6.0)*0.6;
    gl_FragColor = vec4(c, 0.55 + f*0.45 + uPulse*0.1);
  }`;

function Core({ pulse }: { pulse: MutableRefObject<number> }) {
  const mesh = useRef<THREE.Mesh>(null);
  const lattice = useRef<THREE.LineSegments>(null);
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: coreVert,
        fragmentShader: coreFrag,
        transparent: true,
        uniforms: { uTime: { value: 0 }, uPulse: { value: 0 } },
      }),
    [],
  );
  const latticeGeo = useMemo(() => new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(0.62, 1)), []);
  useEffect(() => () => {
    mat.dispose();
    latticeGeo.dispose();
  }, [mat, latticeGeo]);
  useFrame((s, dt) => {
    mat.uniforms.uTime.value = s.clock.elapsedTime;
    pulse.current *= Math.pow(0.04, dt);
    mat.uniforms.uPulse.value = pulse.current;
    if (mesh.current) mesh.current.scale.setScalar(1 + pulse.current * 0.06);
    if (lattice.current) {
      lattice.current.rotation.y += dt * 0.35;
      lattice.current.rotation.x += dt * 0.12;
    }
  });
  return (
    <group>
      <mesh ref={mesh} material={mat}>
        <icosahedronGeometry args={[0.95, 24]} />
      </mesh>
      <lineSegments ref={lattice} geometry={latticeGeo}>
        <lineBasicMaterial color="#5a3fd8" transparent opacity={0.45} />
      </lineSegments>
      <pointLight color="#7357e8" intensity={6} distance={7} />
    </group>
  );
}

// ---------- the four data objects ----------

function SalesBars({ active }: { active: boolean }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const N = 14;
  useFrame((s) => {
    const m = ref.current;
    if (!m) return;
    for (let i = 0; i < N; i++) {
      const a = (i / N) * Math.PI * 2;
      const h = 0.15 + 0.45 * (0.5 + 0.5 * Math.sin(s.clock.elapsedTime * 2.2 + i * 0.9)) * (i > 9 ? 0.55 : 1);
      dummy.position.set(Math.cos(a) * 0.42, h / 2 - 0.2, Math.sin(a) * 0.42);
      dummy.scale.set(1, h, 1);
      dummy.rotation.y = -a;
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  });
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, N]}>
      <boxGeometry args={[0.08, 1, 0.08]} />
      <meshStandardMaterial color="#8f78ff" emissive="#7357e8" emissiveIntensity={active ? 1.4 : 0.6} metalness={0.3} roughness={0.35} />
    </instancedMesh>
  );
}

function CustomerCloud({ active }: { active: boolean }) {
  const ref = useRef<THREE.Points>(null);
  const geo = useMemo(() => {
    const n = 420;
    const p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random() * 2 - 1;
      const t = Math.random() * Math.PI * 2;
      const r = 0.45 * Math.cbrt(Math.random()) + 0.05;
      const s = Math.sqrt(1 - u * u);
      p.set([Math.cos(t) * s * r, u * r, Math.sin(t) * s * r], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    return g;
  }, []);
  useEffect(() => () => geo.dispose(), [geo]);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.5;
  });
  return (
    <points ref={ref} geometry={geo}>
      <pointsMaterial color={active ? "#a9d4ff" : "#5fb0fb"} size={0.035} sizeAttenuation transparent opacity={0.95} depthWrite={false} />
    </points>
  );
}

function InventoryGrid({ active }: { active: boolean }) {
  const ref = useRef<THREE.Group>(null);
  const cells = useMemo(() => {
    const out: { p: [number, number, number]; low: boolean }[] = [];
    for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) out.push({ p: [x * 0.2, y * 0.2, z * 0.2], low: (x + 2 * y + 3 * z + 9) % 7 === 0 });
    return out;
  }, []);
  useFrame((s) => {
    if (!ref.current) return;
    ref.current.rotation.y = s.clock.elapsedTime * 0.4;
    ref.current.rotation.x = Math.sin(s.clock.elapsedTime * 0.5) * 0.3;
  });
  return (
    <group ref={ref}>
      {cells.map((c, i) => (
        <mesh key={i} position={c.p}>
          <boxGeometry args={[0.14, 0.14, 0.14]} />
          <meshStandardMaterial
            color={c.low ? "#e9c27e" : "#3a4a6b"}
            emissive={c.low ? "#c6a66b" : "#1a2440"}
            emissiveIntensity={c.low ? (active ? 1.6 : 0.9) : 0.4}
            metalness={0.5}
            roughness={0.3}
          />
        </mesh>
      ))}
    </group>
  );
}

function ForecastRibbon({ active }: { active: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  const curve = useMemo(() => {
    const pts = Array.from({ length: 9 }, (_, i) => new THREE.Vector3(-0.5 + i * 0.125, Math.sin(i * 0.9) * 0.15 + i * 0.03, Math.cos(i * 0.7) * 0.12));
    return new THREE.CatmullRomCurve3(pts);
  }, []);
  const geo = useMemo(() => new THREE.TubeGeometry(curve, 80, 0.025, 8), [curve]);
  const bandGeo = useMemo(() => new THREE.TubeGeometry(curve, 80, 0.09, 8), [curve]);
  useEffect(() => () => {
    geo.dispose();
    bandGeo.dispose();
  }, [geo, bandGeo]);
  useFrame((s) => {
    if (ref.current) ref.current.rotation.y = Math.sin(s.clock.elapsedTime * 0.6) * 0.6;
  });
  return (
    <mesh ref={ref} geometry={geo}>
      <meshStandardMaterial color="#cfc4ff" emissive="#9d8bf2" emissiveIntensity={active ? 1.8 : 0.9} />
      <mesh geometry={bandGeo}>
        <meshBasicMaterial color="#9d8bf2" transparent opacity={0.12} depthWrite={false} />
      </mesh>
    </mesh>
  );
}

// ---------- streams: particles flowing node → core → decision ----------

function Streams({ activeKey, pulse }: { activeKey: string | null; pulse: MutableRefObject<number> }) {
  const PER = 26;
  const curves = useMemo(
    () =>
      CORE_NODES.map((n) => {
        const a = new THREE.Vector3(...n.pos);
        const mid = a.clone().multiplyScalar(0.5).add(new THREE.Vector3(0, 0.6 * Math.sign(n.pos[1]), 0.8));
        return new THREE.QuadraticBezierCurve3(a, mid, new THREE.Vector3(0, 0, 0));
      }),
    [],
  );
  const out = useMemo(
    () => new THREE.CubicBezierCurve3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(0.2, 0.9, 0.8), new THREE.Vector3(0.1, 1.9, 0.6), new THREE.Vector3(0, 2.7, 0.2)),
    [],
  );
  const lines = useMemo(
    () =>
      curves.map(
        (c, i) =>
          new THREE.Line(
            new THREE.BufferGeometry().setFromPoints(c.getPoints(48)),
            new THREE.LineBasicMaterial({ color: CORE_NODES[i].color, transparent: true, opacity: 0.22 }),
          ),
      ),
    [curves],
  );
  const outLine = useMemo(
    () =>
      new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(out.getPoints(48)),
        new THREE.LineBasicMaterial({ color: "#e8ecf5", transparent: true, opacity: 0.35 }),
      ),
    [out],
  );
  useEffect(() => () => {
    [...lines, outLine].forEach((l) => {
      l.geometry.dispose();
      (l.material as THREE.Material).dispose();
    });
  }, [lines, outLine]);
  useEffect(() => {
    lines.forEach((l, i) => {
      (l.material as THREE.LineBasicMaterial).opacity = activeKey === CORE_NODES[i].key ? 0.7 : 0.22;
    });
  }, [activeKey, lines]);

  const inst = useRef<THREE.InstancedMesh>(null);
  const outInst = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);
  const offsets = useMemo(() => Array.from({ length: CORE_NODES.length * PER }, () => Math.random()), []);
  const lastArrive = useRef(0);

  useFrame((s) => {
    const t = s.clock.elapsedTime;
    const m = inst.current;
    if (m) {
      CORE_NODES.forEach((n, ni) => {
        const boost = activeKey === n.key ? 1.8 : activeKey ? 0.6 : 1;
        for (let k = 0; k < PER; k++) {
          const idx = ni * PER + k;
          const u = (offsets[idx] + t * 0.18 * boost) % 1;
          curves[ni].getPoint(u, dummy.position);
          const sc = 0.025 + 0.02 * Math.sin(u * Math.PI);
          dummy.scale.setScalar(sc * (activeKey === n.key ? 1.6 : 1));
          dummy.updateMatrix();
          m.setMatrixAt(idx, dummy.matrix);
          color.set(n.color);
          m.setColorAt(idx, color);
        }
      });
      m.instanceMatrix.needsUpdate = true;
      if (m.instanceColor) m.instanceColor.needsUpdate = true;
    }
    // a pulse every ~1.1s as "decisions" are emitted
    if (t - lastArrive.current > 1.1) {
      lastArrive.current = t;
      pulse.current = 1;
    }
    const o = outInst.current;
    if (o) {
      for (let k = 0; k < 10; k++) {
        const u = (k / 10 + t * 0.25) % 1;
        out.getPoint(u, dummy.position);
        dummy.scale.setScalar(0.03 + 0.03 * (1 - u));
        dummy.updateMatrix();
        o.setMatrixAt(k, dummy.matrix);
      }
      o.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <group>
      {lines.map((l, i) => (
        <primitive key={i} object={l} />
      ))}
      <primitive object={outLine} />
      <instancedMesh ref={inst} args={[undefined, undefined, CORE_NODES.length * PER]}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshBasicMaterial toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={outInst} args={[undefined, undefined, 10]}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} />
      </instancedMesh>
    </group>
  );
}

// ---------- scene ----------

type Props = {
  activeKey: string | null;
  setActiveKey: (k: string | null) => void;
  labelRefs: MutableRefObject<(HTMLElement | null)[]>;
  decisionRef: MutableRefObject<HTMLElement | null>;
  scrollProgress: MutableRefObject<number>;
};

function Scene({ activeKey, setActiveKey, labelRefs, decisionRef, scrollProgress }: Props) {
  const { size, camera, viewport } = useThree();
  const root = useRef<THREE.Group>(null);
  const nodeRefs = useRef<(THREE.Group | null)[]>([]);
  const pulse = useRef(0);
  const mouse = useRef(new THREE.Vector2());
  const v = useMemo(() => new THREE.Vector3(), []);

  useEffect(() => {
    const onMove = (e: PointerEvent) => mouse.current.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useFrame((s) => {
    const t = s.clock.elapsedTime;
    const g = root.current;
    if (!g) return;
    const fit = THREE.MathUtils.clamp(viewport.width / 6.4, 0.5, 1);
    const sp = scrollProgress.current;
    g.scale.setScalar(fit * (1 + sp * 0.25));
    g.rotation.y += (mouse.current.x * 0.35 + Math.sin(t * 0.15) * 0.15 + sp * 0.8 - g.rotation.y) * 0.04;
    g.rotation.x += (-mouse.current.y * 0.18 - g.rotation.x) * 0.04;
    g.position.y = sp * 0.6;

    CORE_NODES.forEach((n, i) => {
      const node = nodeRefs.current[i];
      if (!node) return;
      const target = activeKey === n.key ? 1.25 : 1;
      node.scale.setScalar(THREE.MathUtils.lerp(node.scale.x, target, 0.12));
      node.position.y = n.pos[1] + Math.sin(t * 0.9 + i) * 0.06;
      const el = labelRefs.current[i];
      if (el) {
        node.getWorldPosition(v);
        v.project(camera);
        const half = el.offsetWidth / 2 + 6;
        const x = THREE.MathUtils.clamp((v.x * 0.5 + 0.5) * size.width, half, size.width - half);
        const y = (-v.y * 0.5 + 0.5) * size.height;
        el.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, ${n.pos[1] > 0 ? "-170%" : "70%"})`;
      }
    });
    const d = decisionRef.current;
    if (d) {
      v.set(0, 2.75, 0.2).applyMatrix4(g.matrixWorld).project(camera);
      // keep the decision card clear of the navigation bar and inside the canvas
      const dx = THREE.MathUtils.clamp((v.x * 0.5 + 0.5) * size.width, 130, size.width - 130);
      const dy = Math.max((-v.y * 0.5 + 0.5) * size.height, 210);
      d.style.transform = `translate3d(${dx}px, ${dy}px, 0) translate(-50%, -110%)`;
    }
  });

  const over = (k: string) => (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    setActiveKey(k);
    document.body.style.cursor = "pointer";
  };
  const outFn = () => {
    setActiveKey(null);
    document.body.style.cursor = "";
  };

  const objects = [SalesBars, CustomerCloud, InventoryGrid, ForecastRibbon];

  return (
    <group ref={root}>
      <Core pulse={pulse} />
      <Streams activeKey={activeKey} pulse={pulse} />
      {CORE_NODES.map((n, i) => {
        const Obj = objects[i];
        return (
          <group
            key={n.key}
            ref={(g) => {
              nodeRefs.current[i] = g;
            }}
            position={n.pos as unknown as [number, number, number]}
          >
            <Obj active={activeKey === n.key} />
            <mesh rotation={[Math.PI / 2, 0, 0]}>
              <ringGeometry args={[0.6, 0.62, 64]} />
              <meshBasicMaterial color={n.color} transparent opacity={activeKey === n.key ? 0.8 : 0.25} side={THREE.DoubleSide} />
            </mesh>
            <mesh onPointerOver={over(n.key)} onPointerOut={outFn}>
              <sphereGeometry args={[0.65, 12, 12]} />
              <meshBasicMaterial transparent opacity={0} depthWrite={false} />
            </mesh>
          </group>
        );
      })}
      {/* orbit guides */}
      {[2.6, 3.1].map((r, i) => (
        <mesh key={r} rotation={[Math.PI / 2 + 0.25 * (i ? -1 : 1), 0, 0]}>
          <torusGeometry args={[r, 0.004, 6, 160]} />
          <meshBasicMaterial color="#c9cedd" transparent opacity={0.9} />
        </mesh>
      ))}
    </group>
  );
}

export default function DataCore(props: Props & { active: boolean }) {
  const { active, ...rest } = props;
  return (
    <Canvas
      camera={{ position: [0, 0.3, 8.2], fov: 42 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      frameloop={active ? "always" : "never"}
      aria-hidden
    >
      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 6, 5]} intensity={1.4} color="#dfe6ff" />
      <directionalLight position={[-5, -2, 2]} intensity={0.6} color="#7357e8" />
      <Scene {...rest} />
    </Canvas>
  );
}

