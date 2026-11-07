"use client";

/**
 * INTERIM opening scene (to be replaced by the photoreal StorefrontScene in the opening phases).
 * A shopfront with a rolling shutter and a brass padlock. Clicking the key flies it into the
 * lock, turns it, pops the shackle, drops the lock, rolls the shutter and dives into the shop.
 */

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { gsap } from "gsap";
import * as THREE from "three";
import { sfx } from "@/lib/sfx";

const C = {
  red: "#c8352b",
  redDeep: "#9b2820",
  sign: "#f1efe9",
  teal: "#0f7a6f",
  violet: "#7357e8",
  blue: "#3296f5",
  cream: "#f6f7fb",
  ink: "#0b1020",
  brass: "#c6a66b",
  steel: "#b9c2c6",
};

function fonts() {
  const css = getComputedStyle(document.documentElement);
  return {
    display: css.getPropertyValue("--font-geist").trim() || "sans-serif",
    deva: css.getPropertyValue("--font-tiro").trim() || "serif",
    mono: css.getPropertyValue("--font-geist-mono").trim() || "monospace",
  };
}

function makeTexture(w: number, h: number, draw: (ctx: CanvasRenderingContext2D) => void) {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  draw(canvas.getContext("2d")!);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function shutterTexture() {
  const f = fonts();
  return makeTexture(1024, 920, (ctx) => {
    for (let y = 0; y < 920; y += 40) {
      const g = ctx.createLinearGradient(0, y, 0, y + 40);
      g.addColorStop(0, "#c9d0d3");
      g.addColorStop(0.45, "#e7ecee");
      g.addColorStop(0.55, "#a9b3b8");
      g.addColorStop(1, "#bfc8cb");
      ctx.fillStyle = g;
      ctx.fillRect(0, y, 1024, 40);
    }
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = C.ink;
    ctx.font = `700 200px ${f.display}`;
    ctx.fillText("VYAPAR", 512, 380);
    ctx.fillStyle = C.violet;
    ctx.font = `500 46px ${f.mono}`;
    ctx.fillText("GENERAL STORE · OPEN 9 AM – 10 PM", 512, 530);
    ctx.globalAlpha = 0.16;
    for (let i = 0; i < 900; i++) {
      ctx.fillStyle = Math.random() > 0.5 ? "#ffffff" : "#7d8487";
      ctx.fillRect(Math.random() * 1024, Math.random() * 920, 2 + Math.random() * 3, 1);
    }
    ctx.globalAlpha = 1;
  });
}

function signTexture() {
  const f = fonts();
  return makeTexture(1024, 200, (ctx) => {
    ctx.fillStyle = C.sign;
    ctx.fillRect(0, 0, 1024, 200);
    ctx.fillStyle = C.ink;
    ctx.fillRect(0, 0, 1024, 14);
    ctx.fillRect(0, 186, 1024, 14);
    ctx.textBaseline = "middle";
    ctx.textAlign = "left";
    ctx.fillStyle = C.red;
    ctx.font = `400 96px ${f.deva}`;
    ctx.fillText("व्यापार", 60, 108);
    ctx.textAlign = "right";
    ctx.fillStyle = C.ink;
    ctx.font = `700 92px ${f.display}`;
    ctx.fillText("VYAPAR", 964, 104);
  });
}

function awningTexture() {
  return makeTexture(512, 64, (ctx) => {
    for (let i = 0; i < 16; i++) {
      ctx.fillStyle = i % 2 ? "#f4f1ea" : C.red;
      ctx.fillRect(i * 32, 0, 32, 64);
    }
  });
}

function shadowTexture() {
  return makeTexture(256, 256, (ctx) => {
    const g = ctx.createRadialGradient(128, 128, 10, 128, 128, 128);
    g.addColorStop(0, "rgba(11,16,32,0.28)");
    g.addColorStop(1, "rgba(11,16,32,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 256, 256);
  });
}

const SHUTTER = { w: 3.8, h: 3.4, top: 1.6, z: 0.08 };
const KEYHOLE = new THREE.Vector3(0, -1.42, 0.33);

type SceneProps = {
  opening: boolean;
  onKeyClick: () => void;
  onDive: () => void;
  onOpened: () => void;
};

function Shop({ opening, onKeyClick, onDive, onOpened }: SceneProps) {
  const { viewport, size, camera } = useThree();
  const portrait = size.width / size.height < 0.85;

  const root = useRef<THREE.Group>(null);
  const shutter = useRef<THREE.Mesh>(null);
  const roll = useRef<THREE.Mesh>(null);
  const lock = useRef<THREE.Group>(null);
  const shackle = useRef<THREE.Group>(null);
  const keyOuter = useRef<THREE.Group>(null);
  const keyInner = useRef<THREE.Group>(null);
  const glow = useRef<THREE.PointLight>(null);
  const halo = useRef<THREE.Mesh>(null);
  const idle = useRef(true);
  const mouse = useRef(new THREE.Vector2());
  const look = useRef(new THREE.Vector3());

  const tex = useMemo(
    () => ({ shutter: shutterTexture(), sign: signTexture(), awning: awningTexture(), shadow: shadowTexture() }),
    [],
  );
  useEffect(() => () => Object.values(tex).forEach((t) => t.dispose()), [tex]);

  const keyHome = useMemo(
    () => (portrait ? new THREE.Vector3(1.3, -1.0, 1.4) : new THREE.Vector3(2.55, -0.8, 1.3)),
    [portrait],
  );

  const products = useMemo(() => {
    const colors = [C.red, "#f2a93b", C.teal, C.blue, "#efe9dc", C.violet];
    const out: { p: [number, number, number]; s: [number, number, number]; c: string }[] = [];
    [-0.65, 0.25, 1.1].forEach((y, row) => {
      let x = -1.55;
      while (x < 1.5) {
        const w = 0.18 + ((row * 7 + Math.round(x * 10)) % 4) * 0.05;
        const h = 0.25 + ((Math.round(x * 13) + row) % 3) * 0.12;
        out.push({ p: [x + w / 2, y + h / 2, -0.45], s: [w, h, 0.22], c: colors[(out.length * 5 + row) % colors.length] });
        x += w + 0.06;
      }
    });
    return out;
  }, []);

  useEffect(() => {
    const onMove = (e: PointerEvent) =>
      mouse.current.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useEffect(() => {
    if (!keyOuter.current) return;
    keyOuter.current.position.copy(keyHome);
    keyOuter.current.rotation.set(0.2, -0.5, 0.35);
  }, [keyHome]);

  useEffect(() => {
    if (!opening) return;
    const k = keyOuter.current!;
    const ki = keyInner.current!;
    const l = lock.current!;
    const sh = shackle.current!;
    const s = shutter.current!;
    const r = roll.current!;
    const g = glow.current!;
    const sc = root.current!.scale.x;
    idle.current = false;
    document.body.style.cursor = "";

    const rootP = root.current!.position.clone();
    const kh = KEYHOLE.clone().multiplyScalar(sc).add(rootP);
    const inside = new THREE.Vector3(rootP.x, rootP.y - 0.1 * sc, -0.6 * sc);

    const state = { roll: 0 };
    const tl = gsap.timeline({ onComplete: onOpened });
    tl.to(halo.current!.scale, { x: 0.01, y: 0.01, z: 0.01, duration: 0.2 })
      .to(k.position, { x: KEYHOLE.x, y: KEYHOLE.y, z: KEYHOLE.z + 0.75, duration: 0.85, ease: "power3.inOut" }, 0)
      .to(k.rotation, { x: 0, y: -Math.PI / 2, z: 0, duration: 0.85, ease: "power3.inOut" }, 0)
      .to(camera.position, { x: kh.x + 0.9 * sc, y: kh.y + 0.7 * sc, z: 4.2, duration: 0.95, ease: "power2.inOut" }, 0)
      .to(look.current, { x: kh.x, y: kh.y, z: kh.z, duration: 0.95, ease: "power2.inOut" }, 0)
      .to(k.position, { z: KEYHOLE.z + 0.1, duration: 0.22, ease: "power2.in" })
      .call(() => sfx.insert(), [], "<0.05")
      .to(ki.rotation, { x: Math.PI / 2, duration: 0.38, ease: "back.out(2.5)" }, "+=0.08")
      .call(() => sfx.turn(), [], "<")
      .to(sh.position, { y: "+=0.2", duration: 0.16, ease: "power2.out" }, "+=0.1")
      .call(() => sfx.unlock(), [], "<")
      .to(sh.rotation, { y: 1.3, duration: 0.3, ease: "power2.out" }, ">-0.05")
      .to([l.position, k.position], { y: "-=5", duration: 0.8, ease: "power2.in" }, "+=0.12")
      .to(l.rotation, { z: 1.1, x: 0.7, duration: 0.8, ease: "power1.in" }, "<")
      .to(k.rotation, { z: -1.4, duration: 0.8, ease: "power1.in" }, "<")
      .call(() => sfx.drop(), [], "<0.55")
      .to(camera.position, { x: rootP.x, y: rootP.y + 0.2 * sc, z: 7.2, duration: 0.8, ease: "power2.inOut" }, "<0.2")
      .to(look.current, { x: rootP.x, y: rootP.y, z: 0, duration: 0.8, ease: "power2.inOut" }, "<")
      .call(() => sfx.shutter(1.15), [], "-=0.35")
      .to(
        state,
        {
          roll: 1,
          duration: 1.15,
          ease: "power3.inOut",
          onUpdate: () => {
            const v = 1 - state.roll * 0.97;
            s.scale.y = v;
            s.position.y = SHUTTER.top - (SHUTTER.h * v) / 2;
            // only the lower part of the painted shutter stays visible; the rest is on the drum
            const map = (s.material as THREE.MeshStandardMaterial).map;
            if (map) map.repeat.y = v;
            const rr = 1 + state.roll * 1.6;
            r.scale.set(rr, 1, rr);
            g.intensity = state.roll * 14;
          },
        },
        "<",
      )
      .to(look.current, { x: inside.x, y: inside.y, z: inside.z, duration: 0.6, ease: "power2.inOut" }, "-=0.3")
      .call(() => {
        sfx.whoosh();
        onDive();
      })
      .to(camera.position, { x: inside.x, y: inside.y, z: 0.4, duration: 1.0, ease: "power3.in" }, "<");

    return () => {
      tl.kill();
    };
  }, [opening, camera, onDive, onOpened]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (root.current && idle.current) {
      const sc = portrait
        ? THREE.MathUtils.clamp(viewport.width / 5.6, 0.32, 1)
        : THREE.MathUtils.clamp(Math.min(viewport.width / 11.8, viewport.height / 7.8), 0.4, 1);
      root.current.scale.setScalar(sc);
      root.current.position.set(portrait ? 0 : viewport.width * 0.22, portrait ? viewport.height * 0.12 : -0.05, 0);
      look.current.set(portrait ? 0 : viewport.width * 0.08, portrait ? viewport.height * 0.06 : 0, 0);
    }
    if (!idle.current) {
      camera.lookAt(look.current);
      return;
    }
    if (keyOuter.current) {
      keyOuter.current.position.y = keyHome.y + Math.sin(t * 1.6) * 0.12;
      keyOuter.current.rotation.y = -0.5 + Math.sin(t * 0.9) * 0.35;
      keyOuter.current.rotation.z = 0.35 + Math.sin(t * 1.3) * 0.08;
    }
    if (halo.current) {
      const p = 1 + Math.sin(t * 3) * 0.12;
      halo.current.scale.setScalar(p);
      (halo.current.material as THREE.MeshBasicMaterial).opacity = 0.35 - Math.sin(t * 3) * 0.15;
    }
    camera.position.x += (look.current.x + mouse.current.x * 0.6 - camera.position.x) * 0.05;
    camera.position.y += (look.current.y + 0.25 + mouse.current.y * 0.35 - camera.position.y) * 0.05;
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

  const brass = <meshStandardMaterial color={C.brass} metalness={0.75} roughness={0.28} />;

  return (
    <group ref={root}>
      <mesh position={[0, -2.08, 0.4]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[8, 3]} />
        <meshBasicMaterial map={tex.shadow} transparent depthWrite={false} />
      </mesh>

      <mesh position={[0, -0.15, -0.6]}>
        <planeGeometry args={[3.9, 3.5]} />
        <meshStandardMaterial color="#6d3a24" roughness={0.9} />
      </mesh>
      {[-0.65, 0.25, 1.1].map((y) => (
        <mesh key={y} position={[0, y - 0.03, -0.42]}>
          <boxGeometry args={[3.7, 0.06, 0.4]} />
          <meshStandardMaterial color="#4f2a18" />
        </mesh>
      ))}
      {products.map((p, i) => (
        <mesh key={i} position={p.p}>
          <boxGeometry args={p.s} />
          <meshStandardMaterial color={p.c} roughness={0.6} />
        </mesh>
      ))}
      <pointLight ref={glow} position={[0, 0.6, 0.4]} color="#ffb347" intensity={0} distance={6} decay={1.5} />

      {[-2.1, 2.1].map((x) => (
        <mesh key={x} position={[x, -0.15, 0.1]}>
          <boxGeometry args={[0.4, 3.9, 0.55]} />
          <meshStandardMaterial color={C.red} roughness={0.7} />
        </mesh>
      ))}
      <mesh position={[0, -2.0, 0.25]}>
        <boxGeometry args={[5.0, 0.22, 0.95]} />
        <meshStandardMaterial color="#d9dbe2" roughness={0.9} />
      </mesh>
      <mesh position={[0, 2.18, 0.12]}>
        <boxGeometry args={[4.9, 0.95, 0.5]} />
        <meshStandardMaterial color={C.sign} roughness={0.6} />
      </mesh>
      <mesh position={[0, 2.18, 0.375]}>
        <planeGeometry args={[4.8, 0.86]} />
        <meshStandardMaterial map={tex.sign} roughness={0.55} />
      </mesh>
      <mesh position={[0, 2.95, 0.55]} rotation={[-0.95, 0, 0]}>
        <planeGeometry args={[5.3, 1.1]} />
        <meshStandardMaterial map={tex.awning} side={THREE.DoubleSide} roughness={0.8} />
      </mesh>

      <mesh ref={shutter} position={[0, SHUTTER.top - SHUTTER.h / 2, SHUTTER.z]}>
        <planeGeometry args={[SHUTTER.w, SHUTTER.h]} />
        <meshStandardMaterial map={tex.shutter} metalness={0.35} roughness={0.5} />
      </mesh>
      <mesh ref={roll} position={[0, SHUTTER.top + 0.02, SHUTTER.z + 0.04]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.07, 0.07, SHUTTER.w + 0.05, 24]} />
        <meshStandardMaterial color={C.steel} metalness={0.6} roughness={0.35} />
      </mesh>
      <mesh position={[0, -1.33, SHUTTER.z + 0.05]}>
        <boxGeometry args={[0.9, 0.06, 0.06]} />
        <meshStandardMaterial color="#8d979b" metalness={0.7} roughness={0.3} />
      </mesh>

      <group ref={lock} position={[KEYHOLE.x, KEYHOLE.y - 0.08, SHUTTER.z + 0.14]}>
        <mesh>
          <boxGeometry args={[0.5, 0.42, 0.18]} />
          {brass}
        </mesh>
        <mesh position={[0, 0.0, 0.095]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.045, 0.045, 0.02, 20]} />
          <meshStandardMaterial color={C.ink} />
        </mesh>
        <group ref={shackle} position={[0, 0.2, 0]}>
          <mesh>
            <torusGeometry args={[0.16, 0.035, 12, 32, Math.PI]} />
            <meshStandardMaterial color="#c8cdd0" metalness={0.9} roughness={0.2} />
          </mesh>
        </group>
      </group>

      <group ref={keyOuter}>
        <group ref={keyInner}>
          <mesh position={[0.42, 0, 0]}>
            <torusGeometry args={[0.15, 0.045, 14, 36]} />
            {brass}
          </mesh>
          <mesh position={[0.1, 0, 0]}>
            <boxGeometry args={[0.5, 0.06, 0.05]} />
            {brass}
          </mesh>
          <mesh position={[-0.08, -0.06, 0]}>
            <boxGeometry args={[0.06, 0.1, 0.05]} />
            {brass}
          </mesh>
          <mesh position={[0, -0.05, 0]}>
            <boxGeometry args={[0.05, 0.07, 0.05]} />
            {brass}
          </mesh>
        </group>
        <mesh ref={halo} position={[0.2, 0, -0.05]}>
          <ringGeometry args={[0.42, 0.47, 48]} />
          <meshBasicMaterial color={C.violet} transparent opacity={0.35} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0.2, 0, 0]} onPointerOver={onKeyOver} onPointerOut={onKeyOut} onClick={onKeyDown}>
          <sphereGeometry args={[0.55, 12, 12]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      </group>
    </group>
  );
}

export default function ShopScene(props: SceneProps) {
  return (
    <Canvas camera={{ position: [0, 0.25, 9], fov: 35 }} dpr={[1, 1.75]} gl={{ antialias: true, alpha: true }}>
      <hemisphereLight args={["#ffffff", "#dfe3ee", 1.15]} />
      <directionalLight position={[3, 5, 6]} intensity={1.7} color="#fff6e8" />
      <directionalLight position={[-4, 2, 3]} intensity={0.45} color="#dfe6ff" />
      <Shop {...props} />
    </Canvas>
  );
}
