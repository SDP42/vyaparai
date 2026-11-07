"use client";

/**
 * The opening: a closed Indian shopfront at night.
 *
 * Realism comes from: an HDRI environment (CC0, Poly Haven) for reflections, PBR texture sets
 * for the painted steel shutter, plaster and pavement, physically-based brass / nickel / steel,
 * a warm street-lamp spotlight with soft shadows, and a backlit acrylic sign.
 *
 * Click the key → it flies to the padlock, inserts and turns → shackle springs → lock drops →
 * the slatted shutter slides up into its drum → warm interior → camera dives in.
 */

import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useLoader, useThree, type ThreeEvent } from "@react-three/fiber";
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
import { gsap } from "gsap";
import * as THREE from "three";
import { sfx } from "@/lib/sfx";

const A = "/assets/opening/";

// ---------- shop dimensions (metres-ish) ----------
const OPEN_W = 3.6; // doorway width
const OPEN_H = 3.0; // doorway height
const BOTTOM = -1.5; // floor line
const TOP = BOTTOM + OPEN_H; // shutter top / drum
const SLATS = 30;
const SLAT_H = OPEN_H / SLATS;
const KEYHOLE = new THREE.Vector3(0, BOTTOM + 0.32, 0.27);

// ---------- textures ----------

function usePbr(name: string, repeat: [number, number]) {
  const [diff, nor, arm] = useLoader(THREE.TextureLoader, [`${A}${name}_diff.jpg`, `${A}${name}_nor.jpg`, `${A}${name}_arm.jpg`]);
  return useMemo(() => {
    const set = [diff, nor, arm].map((t) => {
      const c = t.clone();
      c.wrapS = c.wrapT = THREE.RepeatWrapping;
      c.repeat.set(repeat[0], repeat[1]);
      c.anisotropy = 8;
      c.needsUpdate = true;
      return c;
    });
    set[0].colorSpace = THREE.SRGBColorSpace;
    return { map: set[0], normalMap: set[1], aoMap: set[2], roughnessMap: set[2], metalnessMap: set[2] };
  }, [diff, nor, arm, repeat]);
}

function signTexture() {
  const css = getComputedStyle(document.documentElement);
  const display = css.getPropertyValue("--font-bricolage").trim() || "sans-serif";
  const deva = css.getPropertyValue("--font-tiro").trim() || "serif";
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 180;
  const ctx = c.getContext("2d")!;
  const g = ctx.createLinearGradient(0, 0, 0, 180);
  g.addColorStop(0, "#fff7e2");
  g.addColorStop(1, "#ffe7b0");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 1024, 180);
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#b8281f";
  ctx.textAlign = "left";
  ctx.font = `400 92px ${deva}`;
  ctx.fillText("व्यापार", 56, 98);
  ctx.textAlign = "right";
  ctx.fillStyle = "#1b1612";
  ctx.font = `800 96px ${display}`;
  ctx.fillText("VYAPAR", 968, 96);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

// ---------- geometry ----------

function roundedRectShape(w: number, h: number, r: number) {
  const s = new THREE.Shape();
  const x = -w / 2;
  const y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

/** Flat pin-tumbler key in the XY plane: bow at +x, blade pointing to −x with cut teeth below. */
function keyGeometry() {
  const bow = new THREE.Shape();
  bow.absarc(0.3, 0, 0.13, 0, Math.PI * 2, false);
  const hole = new THREE.Path();
  hole.absarc(0.36, 0, 0.035, 0, Math.PI * 2, true);
  bow.holes.push(hole);

  const blade = new THREE.Shape();
  blade.moveTo(0.2, 0.035);
  blade.lineTo(-0.36, 0.035);
  blade.lineTo(-0.4, 0.0);
  // bitting: alternating cuts along the lower edge
  const cuts = [-0.36, -0.31, -0.26, -0.21, -0.16, -0.11, -0.06, -0.01, 0.04];
  cuts.forEach((x, i) => blade.lineTo(x, i % 2 ? -0.05 : -0.075));
  blade.lineTo(0.1, -0.05);
  blade.lineTo(0.2, -0.04);
  blade.lineTo(0.2, 0.035);

  const geo = new THREE.ExtrudeGeometry([bow, blade], {
    depth: 0.022,
    bevelEnabled: true,
    bevelThickness: 0.006,
    bevelSize: 0.006,
    bevelSegments: 3,
    curveSegments: 32,
  });
  geo.translate(0, 0, -0.011);
  geo.computeVertexNormals();
  return geo;
}

function padlockBodyGeometry() {
  const geo = new THREE.ExtrudeGeometry(roundedRectShape(0.46, 0.4, 0.07), {
    depth: 0.13,
    bevelEnabled: true,
    bevelThickness: 0.02,
    bevelSize: 0.02,
    bevelSegments: 5,
    curveSegments: 24,
  });
  geo.translate(0, 0, -0.065);
  geo.computeVertexNormals();
  return geo;
}

function shackleGeometry() {
  const path = new THREE.CurvePath<THREE.Vector3>();
  const r = 0.14;
  path.add(new THREE.LineCurve3(new THREE.Vector3(-r, -0.05, 0), new THREE.Vector3(-r, 0.12, 0)));
  const arc = new THREE.EllipseCurve(0, 0.12, r, r, Math.PI, 0, true);
  const pts = arc.getPoints(24).map((p) => new THREE.Vector3(p.x, p.y, 0));
  path.add(new THREE.CatmullRomCurve3(pts));
  path.add(new THREE.LineCurve3(new THREE.Vector3(r, 0.12, 0), new THREE.Vector3(r, -0.05, 0)));
  return new THREE.TubeGeometry(path, 80, 0.03, 16, false);
}

// ---------- scene ----------

type SceneProps = {
  opening: boolean;
  onKeyClick: () => void;
  onDive: () => void;
  onLoaded: () => void;
};

function Environment() {
  const { scene, gl } = useThree();
  const hdr = useLoader(RGBELoader, `${A}night_street_1k.hdr`);
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const env = pmrem.fromEquirectangular(hdr).texture;
    scene.environment = env;
    scene.environmentIntensity = 0.55;
    return () => {
      scene.environment = null;
      env.dispose();
      pmrem.dispose();
    };
  }, [hdr, gl, scene]);
  return null;
}

function Shop({ opening, onKeyClick, onDive, onLoaded }: SceneProps) {
  const { viewport, size, camera } = useThree();
  const portrait = size.width / size.height < 0.85;

  const shutterPbr = usePbr("painted_metal_shutter", [3, 0.12]);
  const plasterPbr = usePbr("grey_plaster", [3, 3]);
  const pavePbr = usePbr("concrete_pavement", [4, 2]);
  const sign = useMemo(() => signTexture(), []);
  const keyGeo = useMemo(() => keyGeometry(), []);
  const bodyGeo = useMemo(() => padlockBodyGeometry(), []);
  const shackleGeo = useMemo(() => shackleGeometry(), []);
  useEffect(() => () => {
    sign.dispose();
    keyGeo.dispose();
    bodyGeo.dispose();
    shackleGeo.dispose();
  }, [sign, keyGeo, bodyGeo, shackleGeo]);

  useEffect(() => {
    onLoaded();
  }, [onLoaded]);

  const root = useRef<THREE.Group>(null);
  const shutter = useRef<THREE.Group>(null);
  const slatRefs = useRef<(THREE.Mesh | null)[]>([]);
  const lock = useRef<THREE.Group>(null);
  const shackle = useRef<THREE.Group>(null);
  const keyOuter = useRef<THREE.Group>(null);
  const keyInner = useRef<THREE.Group>(null);
  const interior = useRef<THREE.PointLight>(null);
  const interior2 = useRef<THREE.PointLight>(null);
  const halo = useRef<THREE.Mesh>(null);
  const idle = useRef(true);
  const mouse = useRef(new THREE.Vector2());
  const look = useRef(new THREE.Vector3());

  const keyHome = useMemo(
    () => (portrait ? new THREE.Vector3(1.05, BOTTOM + 0.95, 1.6) : new THREE.Vector3(2.75, BOTTOM + 0.9, 1.4)),
    [portrait],
  );

  const goods = useMemo(() => {
    const palette = ["#8c2f24", "#c9a03f", "#2f5d55", "#d8cfbf", "#7a4b2a", "#3b4a6b", "#b75f2c", "#e3d9c6"];
    const out: { p: [number, number, number]; s: [number, number, number]; c: string }[] = [];
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    [BOTTOM + 0.55, BOTTOM + 1.3, BOTTOM + 2.05].forEach((y) => {
      let x = -1.6;
      while (x < 1.55) {
        const w = 0.12 + rnd() * 0.16;
        const h = 0.18 + rnd() * 0.28;
        out.push({ p: [x + w / 2, y + h / 2, -0.9 + rnd() * 0.08], s: [w, h, 0.16 + rnd() * 0.08], c: palette[Math.floor(rnd() * palette.length)] });
        x += w + 0.025;
      }
    });
    return out;
  }, []);

  useEffect(() => {
    const onMove = (e: PointerEvent) => mouse.current.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useEffect(() => {
    if (!keyOuter.current) return;
    keyOuter.current.position.copy(keyHome);
    keyOuter.current.rotation.set(0.25, -0.6, 0.4);
  }, [keyHome]);

  // ---------- the unlock sequence ----------
  useEffect(() => {
    if (!opening) return;
    const k = keyOuter.current!;
    const ki = keyInner.current!;
    const l = lock.current!;
    const sh = shackle.current!;
    const sg = shutter.current!;
    const sc = root.current!.scale.x;
    idle.current = false;
    document.body.style.cursor = "";

    const rootP = root.current!.position.clone();
    const kh = KEYHOLE.clone().multiplyScalar(sc).add(rootP);
    const inside = new THREE.Vector3(rootP.x, rootP.y + (BOTTOM + 1.2) * sc, -0.9 * sc);
    const state = { roll: 0 };

    const tl = gsap.timeline();
    tl.to(halo.current!.scale, { x: 0.01, y: 0.01, z: 0.01, duration: 0.2 })
      // key travels: arc up and toward the lock, rolling into orientation
      .to(k.position, { x: KEYHOLE.x + 0.15, y: KEYHOLE.y + 0.35, z: KEYHOLE.z + 0.9, duration: 0.6, ease: "power2.out" }, 0)
      .to(k.position, { x: KEYHOLE.x, y: KEYHOLE.y, z: KEYHOLE.z + 0.55, duration: 0.5, ease: "power2.inOut" }, 0.6)
      .to(k.rotation, { x: 0, y: -Math.PI / 2, z: 0, duration: 1.0, ease: "power2.inOut" }, 0.1)
      .to(camera.position, { x: kh.x + 0.55 * sc, y: kh.y + 0.35 * sc, z: kh.z + 2.6, duration: 1.2, ease: "power2.inOut" }, 0)
      .to(look.current, { x: kh.x, y: kh.y, z: kh.z, duration: 1.2, ease: "power2.inOut" }, 0)
      // insert
      .to(k.position, { z: KEYHOLE.z + 0.06, duration: 0.3, ease: "power1.in" }, ">")
      .call(() => sfx.insert(), [], "<0.05")
      // turn clockwise with a little resistance
      .to(ki.rotation, { x: Math.PI / 2, duration: 0.55, ease: "back.out(1.6)" }, "+=0.15")
      .call(() => sfx.turn(), [], "<")
      // shackle releases
      .to(sh.position, { y: "+=0.16", duration: 0.14, ease: "power3.out" }, "+=0.12")
      .call(() => sfx.unlock(), [], "<")
      .to(sh.rotation, { y: 1.2, duration: 0.35, ease: "power2.out" }, ">-0.02")
      // lock and key drop away
      .to([l.position, k.position], { y: "-=3.5", duration: 0.75, ease: "power2.in" }, "+=0.2")
      .to(l.rotation, { z: 0.9, x: 0.5, duration: 0.75, ease: "power1.in" }, "<")
      .to(k.rotation, { z: -1.2, duration: 0.75, ease: "power1.in" }, "<")
      .call(() => sfx.drop(), [], "<0.5")
      // pull back to watch the shutter
      .to(camera.position, { x: rootP.x, y: rootP.y + 0.3 * sc, z: 7.6, duration: 0.9, ease: "power2.inOut" }, "<0.15")
      .to(look.current, { x: rootP.x, y: rootP.y + 0.1 * sc, z: 0, duration: 0.9, ease: "power2.inOut" }, "<")
      .call(() => sfx.shutter(1.4), [], "-=0.3")
      .to(
        state,
        {
          roll: 1,
          duration: 1.4,
          ease: "power2.inOut",
          onUpdate: () => {
            // slats slide up into the drum; any slat above the opening is hidden inside it
            const lift = state.roll * OPEN_H;
            sg.position.y = lift;
            slatRefs.current.forEach((s, i) => {
              if (!s) return;
              const y = BOTTOM + SLAT_H * (i + 0.5) + lift;
              s.visible = y < TOP + 0.02;
            });
            const glow = state.roll * 9;
            interior.current!.intensity = glow;
            interior2.current!.intensity = glow * 0.6;
          },
        },
        "<",
      )
      // walk in
      .to(look.current, { x: inside.x, y: inside.y, z: inside.z, duration: 0.7, ease: "power2.inOut" }, "-=0.35")
      .call(() => {
        sfx.whoosh();
        onDive();
      })
      .to(camera.position, { x: inside.x, y: inside.y, z: 0.5, duration: 1.1, ease: "power3.in" }, "<");

    return () => {
      tl.kill();
    };
  }, [opening, camera, onDive]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (root.current && idle.current) {
      const sc = portrait
        ? THREE.MathUtils.clamp(viewport.width / 5.4, 0.3, 1)
        : THREE.MathUtils.clamp(Math.min(viewport.width / 11, viewport.height / 7.2), 0.4, 1.1);
      root.current.scale.setScalar(sc);
      root.current.position.set(portrait ? 0 : viewport.width * 0.21, portrait ? viewport.height * 0.1 : -0.1, 0);
      look.current.set(portrait ? 0 : viewport.width * 0.08, portrait ? viewport.height * 0.06 : 0, 0);
    }
    if (!idle.current) {
      camera.lookAt(look.current);
      return;
    }
    if (keyOuter.current) {
      keyOuter.current.position.y = keyHome.y + Math.sin(t * 1.3) * 0.06;
      keyOuter.current.rotation.y = -0.6 + Math.sin(t * 0.7) * 0.25;
      keyOuter.current.rotation.z = 0.4 + Math.sin(t * 1.1) * 0.05;
    }
    if (halo.current) {
      const p = 1 + Math.sin(t * 2.4) * 0.1;
      halo.current.scale.setScalar(p);
      (halo.current.material as THREE.MeshBasicMaterial).opacity = 0.32 - Math.sin(t * 2.4) * 0.12;
    }
    // slow, handheld-feeling drift
    camera.position.x += (look.current.x + mouse.current.x * 0.45 + Math.sin(t * 0.21) * 0.08 - camera.position.x) * 0.04;
    camera.position.y += (look.current.y + 0.15 + mouse.current.y * 0.25 + Math.sin(t * 0.17) * 0.05 - camera.position.y) * 0.04;
    camera.lookAt(look.current);
  });

  const onKeyOver = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (idle.current) document.body.style.cursor = "pointer";
  };
  const onKeyOut = () => {
    document.body.style.cursor = "";
  };
  const onKeyDown = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (idle.current) onKeyClick();
  };

  // per-slat UV slices of the shutter texture so the paint wear is continuous
  const slatMaterials = useMemo(
    () =>
      Array.from({ length: SLATS }, (_, i) => {
        const clone = (t: THREE.Texture) => {
          const c = t.clone();
          c.repeat.set(1.2, 1 / SLATS);
          c.offset.set(0, i / SLATS);
          c.needsUpdate = true;
          return c;
        };
        return new THREE.MeshStandardMaterial({
          map: clone(shutterPbr.map),
          normalMap: clone(shutterPbr.normalMap),
          roughnessMap: clone(shutterPbr.roughnessMap),
          aoMap: clone(shutterPbr.aoMap),
          color: "#c7cdd0",
          metalness: 0.55,
          roughness: 0.62,
          normalScale: new THREE.Vector2(1.4, 1.4),
        });
      }),
    [shutterPbr],
  );
  useEffect(() => () => slatMaterials.forEach((m) => m.dispose()), [slatMaterials]);

  const brass = useMemo(
    () => new THREE.MeshPhysicalMaterial({ color: "#d4ab55", metalness: 1, roughness: 0.32, clearcoat: 0.3, clearcoatRoughness: 0.4, envMapIntensity: 1.5 }),
    [],
  );
  const nickel = useMemo(() => new THREE.MeshPhysicalMaterial({ color: "#e4e2da", metalness: 0.92, roughness: 0.28, clearcoat: 0.5, envMapIntensity: 1.6 }), []);
  const steel = useMemo(() => new THREE.MeshStandardMaterial({ color: "#9aa2a6", metalness: 1, roughness: 0.18 }), []);
  useEffect(() => () => [brass, nickel, steel].forEach((m) => m.dispose()), [brass, nickel, steel]);

  return (
    <group ref={root}>
      {/* street lamp: warm, from above-left, soft shadows */}
      <spotLight
        position={[-2.6, 4.6, 3.4]}
        angle={0.62}
        penumbra={0.85}
        intensity={70}
        distance={14}
        decay={2}
        color="#ffcf8a"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0004}
      />
      {/* cool moon / sky fill */}
      <directionalLight position={[3, 3, 4]} intensity={0.35} color="#9fb4ff" />

      {/* pavement */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, BOTTOM - 0.18, 1.6]} receiveShadow>
        <planeGeometry args={[14, 6]} />
        <meshStandardMaterial {...pavePbr} />
      </mesh>
      {/* step */}
      <mesh position={[0, BOTTOM - 0.09, 0.35]} castShadow receiveShadow>
        <boxGeometry args={[OPEN_W + 1.2, 0.18, 0.7]} />
        <meshStandardMaterial color="#8d8a84" roughness={0.85} />
      </mesh>

      {/* facade wall with doorway cut-out (four plaster panels) */}
      <group>
        <mesh position={[-(OPEN_W / 2 + 1.6), 3.5, -0.05]} receiveShadow>
          <boxGeometry args={[3.2, 12, 0.3]} />
          <meshStandardMaterial {...plasterPbr} color="#e9e1d2" />
        </mesh>
        <mesh position={[OPEN_W / 2 + 1.6, 3.5, -0.05]} receiveShadow>
          <boxGeometry args={[3.2, 12, 0.3]} />
          <meshStandardMaterial {...plasterPbr} color="#e9e1d2" />
        </mesh>
        <mesh position={[0, TOP + 3.0, -0.05]} receiveShadow>
          <boxGeometry args={[OPEN_W, 6, 0.3]} />
          <meshStandardMaterial {...plasterPbr} color="#e9e1d2" />
        </mesh>
        {/* pillars framing the opening */}
        {[-1, 1].map((sgn) => (
          <mesh key={sgn} position={[sgn * (OPEN_W / 2 + 0.16), 0.2, 0.12]} castShadow receiveShadow>
            <boxGeometry args={[0.32, OPEN_H + 1.6, 0.36]} />
            <meshStandardMaterial {...plasterPbr} color="#d7ccb9" />
          </mesh>
        ))}
      </group>

      {/* backlit sign + tube light */}
      <mesh position={[0, TOP + 0.62, 0.22]} castShadow>
        <boxGeometry args={[OPEN_W + 0.5, 0.72, 0.16]} />
        <meshStandardMaterial color="#2a2522" metalness={0.6} roughness={0.4} />
      </mesh>
      <mesh position={[0, TOP + 0.62, 0.305]}>
        <planeGeometry args={[OPEN_W + 0.3, 0.56]} />
        <meshStandardMaterial map={sign} emissiveMap={sign} emissive="#ffffff" emissiveIntensity={0.85} roughness={0.3} />
      </mesh>
      <mesh position={[0, TOP + 1.12, 0.32]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.025, 0.025, 1.2, 12]} />
        <meshStandardMaterial color="#ffffff" emissive="#e8f4ff" emissiveIntensity={3} />
      </mesh>
      <pointLight position={[0, TOP + 1.05, 0.7]} intensity={2.2} distance={4} color="#e8f4ff" />

      {/* drum housing the shutter rolls into */}
      <mesh position={[0, TOP + 0.13, 0.17]} castShadow>
        <boxGeometry args={[OPEN_W + 0.1, 0.26, 0.3]} />
        <meshStandardMaterial color="#6f7579" metalness={0.8} roughness={0.45} />
      </mesh>
      {/* guide rails */}
      {[-1, 1].map((sgn) => (
        <mesh key={sgn} position={[sgn * (OPEN_W / 2 - 0.02), BOTTOM + OPEN_H / 2, 0.12]} castShadow>
          <boxGeometry args={[0.06, OPEN_H, 0.08]} />
          <meshStandardMaterial color="#7d8488" metalness={0.85} roughness={0.35} />
        </mesh>
      ))}

      {/* interior (revealed on open) */}
      <mesh position={[0, BOTTOM + OPEN_H / 2, -1.05]} receiveShadow>
        <planeGeometry args={[OPEN_W, OPEN_H]} />
        <meshStandardMaterial color="#6b4a33" roughness={0.9} />
      </mesh>
      {[BOTTOM + 0.53, BOTTOM + 1.28, BOTTOM + 2.03].map((y) => (
        <mesh key={y} position={[0, y, -0.9]} castShadow receiveShadow>
          <boxGeometry args={[OPEN_W - 0.1, 0.04, 0.34]} />
          <meshStandardMaterial color="#8e9399" metalness={0.7} roughness={0.4} />
        </mesh>
      ))}
      {goods.map((g, i) => (
        <mesh key={i} position={g.p} castShadow>
          <boxGeometry args={g.s} />
          <meshStandardMaterial color={g.c} roughness={0.55} />
        </mesh>
      ))}
      <mesh position={[0, BOTTOM + 0.45, -0.25]} castShadow receiveShadow>
        <boxGeometry args={[2.0, 0.9, 0.5]} />
        <meshStandardMaterial color="#5b3a26" roughness={0.6} />
      </mesh>
      <pointLight ref={interior} position={[0, TOP - 0.3, -0.4]} intensity={0} distance={5} decay={2} color="#ffb35c" castShadow />
      <pointLight ref={interior2} position={[0, BOTTOM + 1.0, 0.6]} intensity={0} distance={6} decay={2} color="#ffc27a" />

      {/* the shutter: individual slats */}
      <group ref={shutter}>
        {slatMaterials.map((m, i) => (
          <mesh
            key={i}
            ref={(mesh) => {
              slatRefs.current[i] = mesh;
            }}
            position={[0, BOTTOM + SLAT_H * (i + 0.5), 0.1 + Math.sin(i * 0.9) * 0.002]}
            material={m}
            castShadow
            receiveShadow
          >
            <boxGeometry args={[OPEN_W - 0.06, SLAT_H * 0.96, 0.025]} />
          </mesh>
        ))}
        {/* bottom bar with hasp */}
        <mesh position={[0, BOTTOM + 0.05, 0.13]} castShadow>
          <boxGeometry args={[OPEN_W - 0.06, 0.1, 0.06]} />
          <meshStandardMaterial color="#5f6569" metalness={0.85} roughness={0.35} />
        </mesh>
        <mesh position={[0, BOTTOM + 0.47, 0.155]} material={steel} castShadow>
          <boxGeometry args={[0.32, 0.05, 0.03]} />
        </mesh>
      </group>

      {/* padlock */}
      <group ref={lock} position={[KEYHOLE.x, KEYHOLE.y, 0.2]}>
        <mesh geometry={bodyGeo} material={brass} castShadow />
        <mesh position={[0, -0.02, 0.087]} rotation={[Math.PI / 2, 0, 0]} material={nickel}>
          <cylinderGeometry args={[0.045, 0.045, 0.02, 32]} />
        </mesh>
        <mesh position={[0, -0.02, 0.098]}>
          <boxGeometry args={[0.012, 0.05, 0.004]} />
          <meshBasicMaterial color="#0d0c0b" />
        </mesh>
        <group ref={shackle} position={[0, 0.2, 0]}>
          <mesh geometry={shackleGeo} material={steel} castShadow />
        </group>
      </group>

      {/* key */}
      <group ref={keyOuter}>
        <pointLight position={[0.4, 0.5, 0.8]} intensity={1.6} distance={2.2} decay={2} color="#fff1dc" />
        <group ref={keyInner}>
          <mesh geometry={keyGeo} material={nickel} castShadow />
        </group>
        <mesh ref={halo} position={[0.05, 0, -0.04]}>
          <ringGeometry args={[0.48, 0.5, 64]} />
          <meshBasicMaterial color="#ffd38a" transparent opacity={0.3} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.05, 0, 0]} onPointerOver={onKeyOver} onPointerOut={onKeyOut} onClick={onKeyDown}>
          <sphereGeometry args={[0.55, 12, 12]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      </group>
    </group>
  );
}

export default function ShopScene(props: SceneProps) {
  return (
    <Canvas
      shadows
      camera={{ position: [0, 0.2, 9], fov: 32 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
    >
      <fog attach="fog" args={["#0d0f16", 9, 22]} />
      <ambientLight intensity={0.08} color="#8ea0d8" />
      <Suspense fallback={null}>
        <Environment />
        <Shop {...props} />
      </Suspense>
    </Canvas>
  );
}
