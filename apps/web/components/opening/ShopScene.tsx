"use client";

/**
 * The opening: a closed Indian shopfront at night.
 *
 * Two timelines:
 *  - introTl (time-based, on click): the key arcs to the padlock, rolls into orientation and
 *    enters the keyway while the camera moves in on the lock.
 *  - scrollTl (paused, driven by scroll progress, fully reversible):
 *      0–20 %  key settles · 20–45 % key turns clockwise · 45–60 % mechanism releases ·
 *      60–75 % padlock opens and falls · 75–100 % shutter rises; then the camera walks in.
 *
 * Realism: CC0 HDRI image-based lighting, PBR texture sets, physically based metals, soft
 * shadows, depth of field focused on whatever the camera is looking at, bloom on practical lights.
 */

import { Suspense, useEffect, useMemo, useRef, type MutableRefObject } from "react";
import { Canvas, useFrame, useLoader, useThree, type ThreeEvent } from "@react-three/fiber";
import { Bloom, DepthOfField, EffectComposer, Noise, Vignette } from "@react-three/postprocessing";
import type { DepthOfFieldEffect } from "postprocessing";
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
import { gsap } from "gsap";
import * as THREE from "three";
import { sfx } from "@/lib/sfx";

const A = "/assets/opening/";

const OPEN_W = 3.6;
const OPEN_H = 3.0;
const BOTTOM = -1.5;
const TOP = BOTTOM + OPEN_H;
const SLATS = 30;
const SLAT_H = OPEN_H / SLATS;
const KEYHOLE = new THREE.Vector3(0, BOTTOM + 0.32, 0.27);

/** Scroll-timeline cue points (in timeline seconds) used for sound sync. */
const CUE = { turn: 2, release: 4.5, open: 6, shutter: 7.5, walk: 10, end: 12 };

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

function fonts() {
  const css = getComputedStyle(document.documentElement);
  return {
    display: css.getPropertyValue("--font-bricolage").trim() || "sans-serif",
    deva: css.getPropertyValue("--font-tiro").trim() || "serif",
    mono: css.getPropertyValue("--font-jetbrains").trim() || "monospace",
  };
}

function signTexture() {
  const f = fonts();
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
  ctx.font = `400 92px ${f.deva}`;
  ctx.fillText("व्यापार", 56, 98);
  ctx.textAlign = "right";
  ctx.fillStyle = "#1b1612";
  ctx.font = `800 96px ${f.display}`;
  ctx.fillText("VYAPAR", 968, 96);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** A sheet of generic, unbranded product labels; each cell is one package face. */
const LABELS = [
  ["ATTA", "5 KG", "#c9a03f", "#5a2a14"],
  ["TOOR DAL", "1 KG", "#e8d9b0", "#8a3b1f"],
  ["TEA", "500 G", "#2f5d55", "#f3e8cf"],
  ["RICE", "5 KG", "#efe7d6", "#2b4d7a"],
  ["SUGAR", "1 KG", "#f6f2ea", "#b23a2b"],
  ["GHEE", "1 L", "#e9b949", "#3b2a14"],
  ["SOAP", "4 × 100 G", "#7cb7c9", "#ffffff"],
  ["OIL", "1 L", "#d8b33a", "#2b3a1d"],
  ["BISCUITS", "FAMILY", "#b5452e", "#fff3d6"],
  ["SALT", "1 KG", "#ffffff", "#2f4f8a"],
  ["MASALA", "100 G", "#8c2f24", "#f6d27a"],
  ["NOODLES", "PACK OF 4", "#f2c230", "#b0261c"],
] as const;

function labelAtlas() {
  const f = fonts();
  const cols = 4;
  const rows = 3;
  const cw = 256;
  const ch = 320;
  const c = document.createElement("canvas");
  c.width = cols * cw;
  c.height = rows * ch;
  const ctx = c.getContext("2d")!;
  LABELS.forEach(([name, size, bg, fg], i) => {
    const x = (i % cols) * cw;
    const y = Math.floor(i / cols) * ch;
    ctx.fillStyle = bg;
    ctx.fillRect(x, y, cw, ch);
    ctx.fillStyle = fg;
    ctx.globalAlpha = 0.18;
    ctx.fillRect(x, y + ch * 0.62, cw, ch * 0.12);
    ctx.globalAlpha = 1;
    ctx.textAlign = "center";
    ctx.font = `800 ${name.length > 6 ? 40 : 54}px ${f.display}`;
    ctx.fillText(name, x + cw / 2, y + ch * 0.42);
    ctx.font = `500 26px ${f.mono}`;
    ctx.fillText(size, x + cw / 2, y + ch * 0.85);
    ctx.strokeStyle = fg;
    ctx.lineWidth = 3;
    ctx.strokeRect(x + 14, y + 14, cw - 28, ch - 28);
  });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return { texture: t, cols, rows };
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
  [-0.36, -0.31, -0.26, -0.21, -0.16, -0.11, -0.06, -0.01, 0.04].forEach((x, i) => blade.lineTo(x, i % 2 ? -0.05 : -0.075));
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
  path.add(new THREE.CatmullRomCurve3(arc.getPoints(24).map((p) => new THREE.Vector3(p.x, p.y, 0))));
  path.add(new THREE.LineCurve3(new THREE.Vector3(r, 0.12, 0), new THREE.Vector3(r, -0.05, 0)));
  return new THREE.TubeGeometry(path, 80, 0.03, 16, false);
}

// ---------- scene ----------

export type ShopSceneProps = {
  /** True once the visitor has clicked the key. */
  started: boolean;
  /** Scroll progress through the unlock sequence, 0..1 (written by the parent). */
  progress: MutableRefObject<number>;
  lowPower: boolean;
  onKeyClick: () => void;
  onInserted: () => void;
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

function Shop({ started, progress, lowPower, onKeyClick, onInserted, onLoaded, look }: ShopSceneProps & { look: MutableRefObject<THREE.Vector3> }) {
  const { viewport, size, camera } = useThree();
  const portrait = size.width / size.height < 0.85;

  const shutterPbr = usePbr("painted_metal_shutter", [3, 0.12]);
  const plasterPbr = usePbr("grey_plaster", [3, 3]);
  const pavePbr = usePbr("concrete_pavement", [4, 2]);
  const sign = useMemo(() => signTexture(), []);
  const labels = useMemo(() => labelAtlas(), []);
  const keyGeo = useMemo(() => keyGeometry(), []);
  const bodyGeo = useMemo(() => padlockBodyGeometry(), []);
  const shackleGeo = useMemo(() => shackleGeometry(), []);
  useEffect(() => () => {
    sign.dispose();
    labels.texture.dispose();
    keyGeo.dispose();
    bodyGeo.dispose();
    shackleGeo.dispose();
  }, [sign, labels, keyGeo, bodyGeo, shackleGeo]);

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
  const mode = useRef<"idle" | "intro" | "scroll">("idle");
  const scrollTl = useRef<gsap.core.Timeline | null>(null);
  const smooth = useRef(0);
  const lastT = useRef(0);
  const mouse = useRef(new THREE.Vector2());

  const keyHome = useMemo(
    () => (portrait ? new THREE.Vector3(1.05, BOTTOM + 0.95, 1.6) : new THREE.Vector3(2.75, BOTTOM + 0.9, 1.4)),
    [portrait],
  );

  // Interior goods: labelled packets, jars and grain sacks.
  const goods = useMemo(() => {
    let seed = 11;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const packets: { p: [number, number, number]; s: [number, number, number]; label: number }[] = [];
    const jars: { p: [number, number, number]; r: number; h: number; c: string }[] = [];
    [BOTTOM + 0.55, BOTTOM + 1.3, BOTTOM + 2.05].forEach((y, row) => {
      let x = -1.6;
      while (x < 1.5) {
        if (row === 1 && rnd() < 0.3) {
          const r = 0.06 + rnd() * 0.03;
          const h = 0.18 + rnd() * 0.1;
          jars.push({ p: [x + r, y + h / 2, -0.88], r, h, c: rnd() > 0.5 ? "#c9842c" : "#7a2f1d" });
          x += r * 2 + 0.03;
          continue;
        }
        const w = 0.14 + rnd() * 0.12;
        const h = 0.22 + rnd() * 0.24;
        packets.push({ p: [x + w / 2, y + h / 2, -0.88 + rnd() * 0.05], s: [w, h, 0.12 + rnd() * 0.06], label: Math.floor(rnd() * LABELS.length) });
        x += w + 0.02;
      }
    });
    return { packets, jars };
  }, []);

  const packetMaterials = useMemo(
    () =>
      LABELS.map((_, i) => {
        const t = labels.texture.clone();
        t.repeat.set(1 / labels.cols, 1 / labels.rows);
        t.offset.set((i % labels.cols) / labels.cols, 1 - (Math.floor(i / labels.cols) + 1) / labels.rows);
        t.needsUpdate = true;
        const face = new THREE.MeshStandardMaterial({ map: t, roughness: 0.55 });
        const side = new THREE.MeshStandardMaterial({ color: LABELS[i][2], roughness: 0.6 });
        // box faces: +x, -x, +y, -y, +z (front), -z
        return [side, side, side, side, face, side];
      }),
    [labels],
  );
  useEffect(() => () => packetMaterials.forEach((m) => [...new Set(m)].forEach((x) => x.dispose())), [packetMaterials]);

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

  // ---------- intro (time-based, on click) → builds the scroll timeline ----------
  useEffect(() => {
    if (!started || mode.current !== "idle") return;
    mode.current = "intro";
    document.body.style.cursor = "";
    const k = keyOuter.current!;
    const ki = keyInner.current!;
    const l = lock.current!;
    const sh = shackle.current!;
    const sg = shutter.current!;
    const sc = root.current!.scale.x;
    const rootP = root.current!.position.clone();
    const kh = KEYHOLE.clone().multiplyScalar(sc).add(rootP);
    const inside = new THREE.Vector3(rootP.x, rootP.y + (BOTTOM + 1.2) * sc, -0.9 * sc);
    const closeCam = new THREE.Vector3(kh.x + 0.55 * sc, kh.y + 0.32 * sc, kh.z + 2.4);

    sfx.keyMove();
    const intro = gsap.timeline({
      onComplete: () => {
        mode.current = "scroll";
        onInserted();
      },
    });
    intro
      .to(halo.current!.scale, { x: 0.01, y: 0.01, z: 0.01, duration: 0.2 })
      .to(k.position, { x: KEYHOLE.x + 0.15, y: KEYHOLE.y + 0.35, z: KEYHOLE.z + 0.9, duration: 0.6, ease: "power2.out" }, 0)
      .to(k.position, { x: KEYHOLE.x, y: KEYHOLE.y, z: KEYHOLE.z + 0.5, duration: 0.55, ease: "power2.inOut" }, 0.6)
      .to(k.rotation, { x: 0, y: -Math.PI / 2, z: 0, duration: 1.05, ease: "power2.inOut" }, 0.1)
      .to(camera.position, { x: closeCam.x, y: closeCam.y, z: closeCam.z, duration: 1.3, ease: "power2.inOut" }, 0)
      .to(look.current, { x: kh.x, y: kh.y, z: kh.z, duration: 1.3, ease: "power2.inOut" }, 0)
      .to(k.position, { z: KEYHOLE.z + 0.09, duration: 0.32, ease: "power1.in" }, ">")
      .call(() => sfx.insert(), [], "<0.1");

    // The scroll-driven, reversible sequence. Positions are in timeline seconds (see CUE).
    const roll = { v: 0 };
    const tl = gsap.timeline({ paused: true, defaults: { ease: "none" } });
    tl
      // 0–2 · settle: seat fully with a tiny recoil; camera leans in
      .to(k.position, { z: KEYHOLE.z + 0.05, duration: 1.2, ease: "power2.inOut" }, 0)
      .to(k.position, { z: KEYHOLE.z + 0.06, duration: 0.8, ease: "power1.out" }, 1.2)
      .to(camera.position, { x: closeCam.x - 0.15 * sc, z: closeCam.z - 0.4, duration: 2, ease: "power1.inOut" }, 0)
      // 2–4.5 · rotate clockwise
      .to(ki.rotation, { x: Math.PI / 2, duration: 2.5, ease: "power1.inOut" }, CUE.turn)
      // 4.5–6 · mechanism releases: shackle springs up, body jolts
      .to(sh.position, { y: "+=0.17", duration: 0.6, ease: "back.out(3)" }, CUE.release)
      .to(l.rotation, { z: 0.06, duration: 0.3, ease: "power2.out", yoyo: true, repeat: 1 }, CUE.release)
      // 6–7.5 · padlock opens: shackle swings, lock + key fall; camera pulls back
      .to(sh.rotation, { y: 1.25, duration: 0.6, ease: "power2.out" }, CUE.open)
      .to([l.position, k.position], { y: "-=3.5", duration: 1.0, ease: "power2.in" }, CUE.open + 0.4)
      .to(l.rotation, { z: 0.9, x: 0.5, duration: 1.0, ease: "power1.in" }, CUE.open + 0.4)
      .to(k.rotation, { z: -1.2, duration: 1.0, ease: "power1.in" }, CUE.open + 0.4)
      .to(camera.position, { x: rootP.x, y: rootP.y + 0.3 * sc, z: 7.6, duration: 1.5, ease: "power2.inOut" }, CUE.open)
      .to(look.current, { x: rootP.x, y: rootP.y + 0.1 * sc, z: 0, duration: 1.5, ease: "power2.inOut" }, CUE.open)
      // 7.5–10 · shutter rises slat by slat into the drum, warm light spills out
      .to(
        roll,
        {
          v: 1,
          duration: 2.5,
          ease: "power1.inOut",
          onUpdate: () => {
            const lift = roll.v * OPEN_H;
            sg.position.y = lift;
            slatRefs.current.forEach((s, i) => {
              if (s) s.visible = BOTTOM + SLAT_H * (i + 0.5) + lift < TOP + 0.02;
            });
            interior.current!.intensity = roll.v * 9;
            interior2.current!.intensity = roll.v * 5;
          },
        },
        CUE.shutter,
      )
      // 10–12 · walk through the storefront
      .to(look.current, { x: inside.x, y: inside.y, z: inside.z, duration: 1.0, ease: "power2.inOut" }, CUE.walk - 0.3)
      .to(camera.position, { x: inside.x, y: inside.y + 0.05, z: 1.2, duration: 2.0, ease: "power2.in" }, CUE.walk);
    scrollTl.current = tl;

    return () => {
      intro.kill();
    };
  }, [started, camera, look, onInserted]);

  useEffect(() => () => {
    scrollTl.current?.kill();
  }, []);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;

    if (mode.current === "idle" && root.current) {
      const sc = portrait
        ? THREE.MathUtils.clamp(viewport.width / 5.4, 0.3, 1)
        : THREE.MathUtils.clamp(Math.min(viewport.width / 11, viewport.height / 7.2), 0.4, 1.1);
      root.current.scale.setScalar(sc);
      root.current.position.set(portrait ? 0 : viewport.width * 0.21, portrait ? viewport.height * 0.1 : -0.1, 0);
      look.current.set(portrait ? 0 : viewport.width * 0.08, portrait ? viewport.height * 0.06 : 0, 0);
      if (keyOuter.current) {
        keyOuter.current.position.y = keyHome.y + Math.sin(t * 1.3) * 0.06;
        keyOuter.current.rotation.y = -0.6 + Math.sin(t * 0.7) * 0.25;
        keyOuter.current.rotation.z = 0.4 + Math.sin(t * 1.1) * 0.05;
      }
      if (halo.current) {
        halo.current.scale.setScalar(1 + Math.sin(t * 2.4) * 0.1);
        (halo.current.material as THREE.MeshBasicMaterial).opacity = 0.32 - Math.sin(t * 2.4) * 0.12;
      }
      camera.position.x += (look.current.x + mouse.current.x * 0.45 + Math.sin(t * 0.21) * 0.08 - camera.position.x) * 0.04;
      camera.position.y += (look.current.y + 0.15 + mouse.current.y * 0.25 + Math.sin(t * 0.17) * 0.05 - camera.position.y) * 0.04;
    }

    if (mode.current === "scroll" && scrollTl.current) {
      smooth.current += (progress.current - smooth.current) * Math.min(1, delta * 6);
      const tl = scrollTl.current;
      tl.progress(smooth.current);
      // sound cues fire when crossing a threshold going forward
      const now = tl.time();
      const prev = lastT.current;
      const crossed = (c: number) => prev < c && now >= c;
      if (crossed(0.4)) sfx.seat();
      if (crossed(CUE.turn + 0.2)) sfx.turn();
      if (crossed(CUE.release + 0.1)) sfx.unlock();
      if (crossed(CUE.open + 1.2)) sfx.drop();
      if (crossed(CUE.shutter + 0.1)) sfx.shutter(1.6);
      if (crossed(CUE.walk)) sfx.ambience(true);
      if (prev >= CUE.walk && now < CUE.walk) sfx.ambience(false);
      lastT.current = now;
    }

    camera.lookAt(look.current);
  });

  const onKeyOver = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (mode.current === "idle") document.body.style.cursor = "pointer";
  };
  const onKeyOut = () => {
    document.body.style.cursor = "";
  };
  const onKeyDown = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (mode.current === "idle") onKeyClick();
  };

  const slatMaterials = useMemo(
    () =>
      Array.from({ length: SLATS }, (_, i) => {
        const clone = (tex: THREE.Texture) => {
          const c = tex.clone();
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
  const nickel = useMemo(
    () => new THREE.MeshPhysicalMaterial({ color: "#e4e2da", metalness: 0.92, roughness: 0.28, clearcoat: 0.5, envMapIntensity: 1.6 }),
    [],
  );
  const steel = useMemo(() => new THREE.MeshStandardMaterial({ color: "#9aa2a6", metalness: 1, roughness: 0.18 }), []);
  const sack = useMemo(() => new THREE.MeshStandardMaterial({ color: "#c8b48a", roughness: 0.95 }), []);
  useEffect(() => () => [brass, nickel, steel, sack].forEach((m) => m.dispose()), [brass, nickel, steel, sack]);

  return (
    <group ref={root}>
      <spotLight
        position={[-2.6, 4.6, 3.4]}
        angle={0.62}
        penumbra={0.85}
        intensity={70}
        distance={14}
        decay={2}
        color="#ffcf8a"
        castShadow={!lowPower}
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0004}
      />
      <directionalLight position={[3, 3, 4]} intensity={0.35} color="#9fb4ff" />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, BOTTOM - 0.18, 1.6]} receiveShadow>
        <planeGeometry args={[14, 6]} />
        <meshStandardMaterial {...pavePbr} />
      </mesh>
      <mesh position={[0, BOTTOM - 0.09, 0.35]} castShadow receiveShadow>
        <boxGeometry args={[OPEN_W + 1.2, 0.18, 0.7]} />
        <meshStandardMaterial color="#8d8a84" roughness={0.85} />
      </mesh>

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
        {[-1, 1].map((sgn) => (
          <mesh key={sgn} position={[sgn * (OPEN_W / 2 + 0.16), 0.2, 0.12]} castShadow receiveShadow>
            <boxGeometry args={[0.32, OPEN_H + 1.6, 0.36]} />
            <meshStandardMaterial {...plasterPbr} color="#d7ccb9" />
          </mesh>
        ))}
      </group>

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
        <meshStandardMaterial color="#ffffff" emissive="#e8f4ff" emissiveIntensity={3} toneMapped={false} />
      </mesh>
      <pointLight position={[0, TOP + 1.05, 0.7]} intensity={2.2} distance={4} color="#e8f4ff" />

      <mesh position={[0, TOP + 0.13, 0.17]} castShadow>
        <boxGeometry args={[OPEN_W + 0.1, 0.26, 0.3]} />
        <meshStandardMaterial color="#6f7579" metalness={0.8} roughness={0.45} />
      </mesh>
      {[-1, 1].map((sgn) => (
        <mesh key={sgn} position={[sgn * (OPEN_W / 2 - 0.02), BOTTOM + OPEN_H / 2, 0.12]} castShadow>
          <boxGeometry args={[0.06, OPEN_H, 0.08]} />
          <meshStandardMaterial color="#7d8488" metalness={0.85} roughness={0.35} />
        </mesh>
      ))}

      {/* interior */}
      <mesh position={[0, BOTTOM + OPEN_H / 2, -1.05]} receiveShadow>
        <planeGeometry args={[OPEN_W, OPEN_H]} />
        <meshStandardMaterial color="#6b4a33" roughness={0.9} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, BOTTOM + 0.005, -0.4]} receiveShadow>
        <planeGeometry args={[OPEN_W, 1.4]} />
        <meshStandardMaterial color="#8a7a66" roughness={0.7} />
      </mesh>
      {[BOTTOM + 0.53, BOTTOM + 1.28, BOTTOM + 2.03].map((y) => (
        <mesh key={y} position={[0, y, -0.9]} castShadow receiveShadow>
          <boxGeometry args={[OPEN_W - 0.1, 0.035, 0.34]} />
          <meshStandardMaterial color="#8e9399" metalness={0.7} roughness={0.4} />
        </mesh>
      ))}
      {goods.packets.map((g, i) => (
        <mesh key={`p${i}`} position={g.p} material={packetMaterials[g.label]} castShadow>
          <boxGeometry args={g.s} />
        </mesh>
      ))}
      {goods.jars.map((j, i) => (
        <group key={`j${i}`} position={j.p}>
          <mesh castShadow>
            <cylinderGeometry args={[j.r, j.r, j.h, 24]} />
            <meshPhysicalMaterial color={j.c} roughness={0.15} transmission={0.2} thickness={0.1} />
          </mesh>
          <mesh position={[0, j.h / 2 + 0.012, 0]}>
            <cylinderGeometry args={[j.r * 0.95, j.r * 0.95, 0.025, 24]} />
            <meshStandardMaterial color="#b8b8b0" metalness={1} roughness={0.3} />
          </mesh>
        </group>
      ))}
      {/* counter + grain sacks */}
      <mesh position={[0, BOTTOM + 0.45, -0.25]} castShadow receiveShadow>
        <boxGeometry args={[2.0, 0.9, 0.5]} />
        <meshStandardMaterial color="#5b3a26" roughness={0.6} />
      </mesh>
      <mesh position={[0, BOTTOM + 0.915, -0.25]}>
        <boxGeometry args={[2.04, 0.03, 0.54]} />
        <meshPhysicalMaterial color="#d8e6e4" roughness={0.05} transmission={0.6} thickness={0.03} />
      </mesh>
      {[-1.45, 1.4].map((x, i) => (
        <mesh key={x} position={[x, BOTTOM + 0.28, 0.05]} scale={[1, 1.25, 0.9]} rotation={[0, i * 0.6, 0]} material={sack} castShadow>
          <sphereGeometry args={[0.24, 24, 16]} />
        </mesh>
      ))}
      <pointLight ref={interior} position={[0, TOP - 0.3, -0.4]} intensity={0} distance={5} decay={2} color="#ffb35c" castShadow={!lowPower} />
      <pointLight ref={interior2} position={[0, BOTTOM + 1.0, 0.6]} intensity={0} distance={6} decay={2} color="#ffc27a" />

      {/* shutter */}
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

function Effects({ look }: { look: MutableRefObject<THREE.Vector3> }) {
  const dof = useRef<DepthOfFieldEffect>(null);
  useEffect(() => {
    // auto-focus on whatever the camera is looking at (key → lock → shop)
    if (dof.current) dof.current.target = look.current;
  }, [look]);
  return (
    <EffectComposer multisampling={4}>
      <DepthOfField ref={dof} focusRange={2.5} bokehScale={2.6} />
      <Bloom intensity={0.55} luminanceThreshold={0.82} luminanceSmoothing={0.2} mipmapBlur />
      <Vignette offset={0.32} darkness={0.62} />
      <Noise opacity={0.035} />
    </EffectComposer>
  );
}

export default function ShopScene(props: ShopSceneProps) {
  const look = useRef(new THREE.Vector3());
  return (
    <Canvas
      shadows={!props.lowPower}
      camera={{ position: [0, 0.2, 9], fov: 32 }}
      dpr={props.lowPower ? [1, 1.4] : [1, 1.75]}
      gl={{ antialias: !props.lowPower, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
    >
      <fog attach="fog" args={["#0d0f16", 9, 22]} />
      <ambientLight intensity={0.08} color="#8ea0d8" />
      <Suspense fallback={null}>
        <Environment />
        <Shop {...props} look={look} />
        {!props.lowPower && <Effects look={look} />}
      </Suspense>
    </Canvas>
  );
}
