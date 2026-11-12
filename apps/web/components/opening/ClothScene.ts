import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

/**
 * The closed shop, simulated: a cotton cloth hangs from a rail in front of a wall, tied down the middle with a
 * satin ribbon and bow. The cloth and (after the cut) the ribbon are particle systems integrated with Verlet steps
 * and distance constraints, so the sway, the folds and the fall are computed, not keyframed.
 *
 * cut(y) severs the ribbon at a height; a moment later the pins along the rail let go from the middle outward and
 * the cloth falls under gravity. Everything is drawn with three.js (MIT); textures are generated here, no files.
 */

type Opts = { onDone: () => void; lowPower: boolean };

const GRAVITY = -7.5;
const DAMP = 0.986;
const STEP = 1 / 60;

class Verlet {
  pos: Float32Array;
  prev: Float32Array;
  pinned: Uint8Array;
  private a: number[] = [];
  private b: number[] = [];
  private rest: number[] = [];
  constructor(public n: number) {
    this.pos = new Float32Array(n * 3);
    this.prev = new Float32Array(n * 3);
    this.pinned = new Uint8Array(n);
  }
  set(i: number, x: number, y: number, z: number) {
    this.pos.set([x, y, z], i * 3);
    this.prev.set([x, y, z], i * 3);
  }
  link(i: number, j: number) {
    const p = this.pos;
    this.a.push(i);
    this.b.push(j);
    this.rest.push(Math.hypot(p[i * 3] - p[j * 3], p[i * 3 + 1] - p[j * 3 + 1], p[i * 3 + 2] - p[j * 3 + 2]));
  }
  /** Remove every link for which `test` is true (used to sever the ribbon). */
  unlink(test: (i: number, j: number) => boolean) {
    for (let k = this.a.length - 1; k >= 0; k--) {
      if (test(this.a[k], this.b[k])) {
        this.a.splice(k, 1);
        this.b.splice(k, 1);
        this.rest.splice(k, 1);
      }
    }
  }
  step(force: (i: number, out: [number, number, number]) => void, iterations: number) {
    const { pos, prev, pinned, n } = this;
    const f: [number, number, number] = [0, 0, 0];
    for (let i = 0; i < n; i++) {
      if (pinned[i]) continue;
      const k = i * 3;
      f[0] = 0;
      f[1] = GRAVITY;
      f[2] = 0;
      force(i, f);
      for (let c = 0; c < 3; c++) {
        const cur = pos[k + c];
        pos[k + c] = cur + (cur - prev[k + c]) * DAMP + f[c] * STEP * STEP;
        prev[k + c] = cur;
      }
    }
    const { a, b, rest } = this;
    for (let it = 0; it < iterations; it++) {
      for (let k = 0; k < a.length; k++) {
        const i = a[k] * 3;
        const j = b[k] * 3;
        const dx = pos[j] - pos[i];
        const dy = pos[j + 1] - pos[i + 1];
        const dz = pos[j + 2] - pos[i + 2];
        const d = Math.hypot(dx, dy, dz) || 1e-6;
        const diff = (d - rest[k]) / d;
        const pi = pinned[a[k]];
        const pj = pinned[b[k]];
        if (pi && pj) continue;
        const wi = pi ? 0 : pj ? 1 : 0.5;
        const wj = pj ? 0 : pi ? 1 : 0.5;
        pos[i] += dx * diff * wi;
        pos[i + 1] += dy * diff * wi;
        pos[i + 2] += dz * diff * wi;
        pos[j] -= dx * diff * wj;
        pos[j + 1] -= dy * diff * wj;
        pos[j + 2] -= dz * diff * wj;
      }
    }
  }
}

/** A grid of particles with structural, shear and bend links, and a mesh that follows it. */
function grid(cols: number, rows: number, at: (c: number, r: number) => [number, number, number]) {
  const sim = new Verlet(cols * rows);
  const id = (c: number, r: number) => r * cols + c;
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) sim.set(id(c, r), ...at(c, r));
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (c + 1 < cols) sim.link(id(c, r), id(c + 1, r));
      if (r + 1 < rows) sim.link(id(c, r), id(c, r + 1));
      if (c + 1 < cols && r + 1 < rows) {
        sim.link(id(c, r), id(c + 1, r + 1));
        sim.link(id(c + 1, r), id(c, r + 1));
      }
      if (c + 2 < cols) sim.link(id(c, r), id(c + 2, r));
      if (r + 2 < rows) sim.link(id(c, r), id(c, r + 2));
    }
  }
  const geo = new THREE.BufferGeometry();
  const uv = new Float32Array(cols * rows * 2);
  const index: number[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      uv.set([c / (cols - 1), 1 - r / (rows - 1)], id(c, r) * 2);
      if (c + 1 < cols && r + 1 < rows) index.push(id(c, r), id(c, r + 1), id(c + 1, r), id(c + 1, r), id(c, r + 1), id(c + 1, r + 1));
    }
  }
  geo.setAttribute("position", new THREE.BufferAttribute(sim.pos, 3));
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  geo.setIndex(index);
  return { sim, geo, id };
}

/** Woven cotton: a colour map with uneven dye and a bump map of warp and weft threads. */
function cottonTextures() {
  const size = 256;
  const make = () => {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    return c;
  };
  const colour = make();
  const g = colour.getContext("2d")!;
  g.fillStyle = "#c5861a";
  g.fillRect(0, 0, size, size);
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = `rgba(${Math.random() < 0.5 ? "90,48,0" : "255,226,150"},${Math.random() * 0.06})`;
    const vertical = Math.random() < 0.5;
    g.fillRect(Math.random() * size, Math.random() * size, vertical ? 1 : 12 + Math.random() * 40, vertical ? 12 + Math.random() * 40 : 1);
  }
  const bump = make();
  const b = bump.getContext("2d")!;
  b.fillStyle = "#808080";
  b.fillRect(0, 0, size, size);
  const t = 8; // thread pitch in pixels
  for (let y = 0; y < size; y += t) {
    for (let x = 0; x < size; x += t) {
      const over = (x / t + y / t) % 2 === 0; // plain weave: over, under
      const grad = over ? b.createLinearGradient(x, y, x + t, y) : b.createLinearGradient(x, y, x, y + t);
      grad.addColorStop(0, "#5a5a5a");
      grad.addColorStop(0.5, over ? "#f0f0f0" : "#b8b8b8");
      grad.addColorStop(1, "#5a5a5a");
      b.fillStyle = grad;
      b.fillRect(x, y, t, t);
    }
  }
  const tex = (c: HTMLCanvasElement, srgb: boolean) => {
    const x = new THREE.CanvasTexture(c);
    x.wrapS = x.wrapT = THREE.RepeatWrapping;
    if (srgb) x.colorSpace = THREE.SRGBColorSpace;
    x.anisotropy = 8;
    return x;
  };
  return { map: tex(colour, true), bump: tex(bump, false) };
}

function tagTexture() {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 300;
  const g = c.getContext("2d")!;
  const grad = g.createLinearGradient(0, 0, 512, 300);
  grad.addColorStop(0, "#f4e6c8");
  grad.addColorStop(1, "#dcc79c");
  g.fillStyle = grad;
  g.fillRect(0, 0, 512, 300);
  for (let i = 0; i < 900; i++) {
    g.fillStyle = `rgba(120,90,40,${Math.random() * 0.05})`;
    g.fillRect(Math.random() * 512, Math.random() * 300, 1 + Math.random() * 3, 1);
  }
  g.fillStyle = "#1b1612";
  g.textAlign = "center";
  g.font = "800 104px 'Bricolage Grotesque', system-ui, sans-serif";
  g.fillText("vyapar", 268, 150);
  g.fillStyle = "#a3241c";
  g.font = "italic 92px 'Instrument Serif', Georgia, serif";
  g.fillText(".ai", 268, 248);
  g.strokeStyle = "rgba(120,90,40,.5)";
  g.lineWidth = 4;
  g.strokeRect(10, 10, 492, 280);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/** A band of ribbon swept along a curve; `lean` tilts its width toward the camera so loops read as satin, not wire. */
function band(points: THREE.Vector3[], width: number, closed: boolean, lean = 0.55) {
  const curve = new THREE.CatmullRomCurve3(points, closed, "catmullrom", 0.5);
  const n = 48;
  const pos: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  const z = new THREE.Vector3(0, 0, 1);
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const p = curve.getPointAt(t);
    const tan = curve.getTangentAt(t);
    const side = new THREE.Vector3().crossVectors(tan, z).normalize().multiplyScalar(1 - lean).addScaledVector(z, lean).normalize();
    const taper = closed ? 0.55 + 0.45 * Math.sin(Math.PI * t) : 1; // loops pinch into the knot
    pos.push(...p.clone().addScaledVector(side, (width / 2) * taper).toArray(), ...p.clone().addScaledVector(side, (-width / 2) * taper).toArray());
    uv.push(t, 0, t, 1);
    if (i < n) idx.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 2, i * 2 + 1, i * 2 + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

export class ClothScene {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(32, 1, 0.1, 60);
  private cloth: ReturnType<typeof grid>;
  private ribbon: ReturnType<typeof grid>;
  private cols: number;
  private rows: number;
  private rRows: number;
  private bow = new THREE.Group();
  private tag = new THREE.Group();
  private wall: THREE.Mesh;
  private bowRow: number;
  private visH = 1;
  private visW = 1;
  private raf = 0;
  private last = 0;
  private acc = 0;
  private time = 0;
  private cutAt: number | null = null;
  private release: Float32Array;
  private done = false;
  private pointer = new THREE.Vector3(99, 99, 0);

  constructor(private canvas: HTMLCanvasElement, private opts: Opts) {
    const { lowPower } = opts;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: !lowPower, alpha: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, lowPower ? 1.25 : 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.95;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    this.camera.position.set(0, 0, 11);
    this.fit(w, h);

    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.32;
    pmrem.dispose();

    // light from the upper left, as from a street lamp or morning sun, plus a soft fill
    const key = new THREE.DirectionalLight(0xfff1d6, 3.1);
    key.position.set(-8, 3.5, 4.2); // low and from the side, so every fold throws a shadow
    key.castShadow = true;
    key.shadow.mapSize.set(lowPower ? 1024 : 2048, lowPower ? 1024 : 2048);
    const sc = key.shadow.camera;
    sc.left = -9;
    sc.right = 9;
    sc.top = 6;
    sc.bottom = -6;
    sc.near = 1;
    sc.far = 30;
    key.shadow.bias = -0.0015;
    key.shadow.radius = 5;
    this.scene.add(key, new THREE.HemisphereLight(0xfff7e6, 0x4a2a08, 0.42));
    const rim = new THREE.DirectionalLight(0xffd9a0, 0.7);
    rim.position.set(5, -1, 5);
    this.scene.add(rim);

    // the wall and shutter behind the cloth: it takes the cloth's shadow, and fades as the cloth falls
    this.wall = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 24),
      new THREE.MeshStandardMaterial({ color: 0x2a1c12, roughness: 0.95, transparent: true }),
    );
    this.wall.position.z = -0.9;
    this.wall.receiveShadow = true;
    this.scene.add(this.wall);

    // ---- the cloth: wider than the rail it hangs from, so it gathers into real folds
    this.cols = lowPower ? 34 : 52;
    this.rows = lowPower ? 22 : 32;
    const width = this.visW * 1.3;
    const height = this.visH * 1.16;
    const top = this.visH / 2 + this.visH * 0.07;
    const gather = 0.8;
    // links are measured on the flat cloth; then the cloth is gathered onto a shorter rail, so the spare width
    // has to go somewhere: it buckles into folds, as real fabric does
    this.cloth = grid(this.cols, this.rows, (c, r) => {
      const u = c / (this.cols - 1) - 0.5;
      return [u * width, top - (r / (this.rows - 1)) * height, 0];
    });
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const u = c / (this.cols - 1) - 0.5;
        const sag = r / (this.rows - 1);
        const g = gather + (1 - gather) * sag * 0.6; // gathered tight at the rail, freer at the hem
        const fold = Math.sin(u * 46 + Math.sin(u * 7) * 2) * 0.16 * (1 - sag * 0.5);
        this.cloth.sim.set(this.cloth.id(c, r), u * width * g, top - sag * height, fold);
      }
    }
    this.release = new Float32Array(this.cols);
    for (let c = 0; c < this.cols; c++) {
      this.cloth.sim.pinned[this.cloth.id(c, 0)] = 1;
      this.release[c] = Infinity;
    }
    const tex = cottonTextures();
    tex.map.repeat.set(10, 7);
    tex.bump.repeat.set(this.visW * 5.5, this.visH * 5.5);
    const cotton = new THREE.MeshPhysicalMaterial({
      map: tex.map,
      bumpMap: tex.bump,
      bumpScale: 0.9,
      roughness: 0.94,
      sheen: 1,
      sheenRoughness: 0.75,
      sheenColor: new THREE.Color(0xffd98a),
      side: THREE.DoubleSide,
    });
    const clothMesh = new THREE.Mesh(this.cloth.geo, cotton);
    clothMesh.castShadow = true;
    clothMesh.receiveShadow = true;
    clothMesh.frustumCulled = false;
    this.scene.add(clothMesh);

    // ---- the ribbon: follows the cloth until it is cut, then becomes its own falling strip
    this.rRows = this.rows * 2 - 1;
    const rw = Math.max(0.3, Math.min(0.5, this.visW * 0.045));
    this.ribbon = grid(3, this.rRows, (c, r) => [(c - 1) * (rw / 2), top - (r / (this.rRows - 1)) * height, 0.1]);
    const satin = new THREE.MeshPhysicalMaterial({
      color: 0x9a1812,
      roughness: 0.36,
      metalness: 0.02,
      sheen: 0.45,
      sheenRoughness: 0.3,
      sheenColor: new THREE.Color(0xff5a48),
      clearcoat: 0.18,
      clearcoatRoughness: 0.45,
      anisotropy: 0.7,
      side: THREE.DoubleSide,
    });
    const ribbonMesh = new THREE.Mesh(this.ribbon.geo, satin);
    ribbonMesh.castShadow = true;
    ribbonMesh.frustumCulled = false;
    this.scene.add(ribbonMesh);
    this.bowRow = Math.round(this.rRows * 0.42);

    // ---- the bow: two loops, two tails and a knot, all satin bands
    const v = (x: number, y: number, z = 0) => new THREE.Vector3(x, y, z);
    const loop = (s: number) => band([v(0, 0, 0.05), v(0.34 * s, 0.3, 0.2), v(0.9 * s, 0.36, 0.14), v(1.12 * s, 0.06, 0.02), v(0.92 * s, -0.2, 0.12), v(0.4 * s, -0.12, 0.18)], 0.42, true);
    const tail = (s: number) => band([v(0.02 * s, -0.04, 0.06), v(0.2 * s, -0.42, 0.14), v(0.3 * s, -0.86, 0.06), v(0.5 * s, -1.22, 0.1)], 0.3, false, 0.35);
    for (const s of [-1, 1]) {
      const l = new THREE.Mesh(loop(s), satin);
      const t = new THREE.Mesh(tail(s), satin);
      l.castShadow = t.castShadow = true;
      l.name = "loop";
      this.bow.add(l, t);
    }
    const knot = new THREE.Mesh(new THREE.SphereGeometry(0.19, 24, 16), satin);
    knot.scale.set(1, 1.15, 0.8);
    knot.position.z = 0.14;
    knot.castShadow = true;
    this.bow.add(knot);
    this.bow.scale.setScalar(Math.max(0.62, Math.min(1.05, this.visW * 0.1)));
    this.scene.add(this.bow);

    // ---- the paper tag on a string
    const paper = new THREE.Mesh(
      new THREE.PlaneGeometry(0.92, 0.54),
      new THREE.MeshStandardMaterial({ map: tagTexture(), roughness: 0.85, side: THREE.DoubleSide }),
    );
    paper.position.set(0.46, -0.62, 0);
    paper.castShadow = true;
    const string = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([v(0, 0, 0), v(0.08, -0.36, 0)]),
      new THREE.LineBasicMaterial({ color: 0x5a3d1c }),
    );
    this.tag.add(paper, string);
    this.bow.add(this.tag);
    this.tag.position.set(0.1, -0.2, 0.3);

    // let the cloth settle into its folds before the first frame is shown
    for (let i = 0; i < 150; i++) this.simulate();
    this.followCloth();
    this.loop = this.loop.bind(this);
  }

  private fit(w: number, h: number) {
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.visH = 2 * this.camera.position.z * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    this.visW = this.visH * this.camera.aspect;
  }

  resize() {
    this.fit(this.canvas.clientWidth, this.canvas.clientHeight);
  }

  /** Where the pointer is, in pixels, so the cloth gives a little under it. */
  point(x: number, y: number) {
    const r = this.canvas.getBoundingClientRect();
    this.pointer.set(((x - r.left) / r.width - 0.5) * this.visW, (0.5 - (y - r.top) / r.height) * this.visH, 0);
  }

  /** Screen position (px, within the canvas) of the ribbon at a fraction of the height from the top. */
  ribbonPoint(fromTop: number) {
    const row = Math.round(fromTop * (this.rRows - 1) * (1 / 1.16) + this.rRows * 0.06);
    const k = this.ribbon.id(1, Math.min(this.rRows - 1, Math.max(0, row))) * 3;
    const p = new THREE.Vector3(this.ribbon.sim.pos[k], this.ribbon.sim.pos[k + 1], this.ribbon.sim.pos[k + 2]).project(this.camera);
    return { x: (p.x * 0.5 + 0.5) * this.canvas.clientWidth, y: (-p.y * 0.5 + 0.5) * this.canvas.clientHeight, row };
  }

  start() {
    this.last = performance.now();
    this.raf = requestAnimationFrame(this.loop);
  }

  /** Sever the ribbon at this row; the rail lets go a moment later. */
  cut(row: number) {
    if (this.cutAt !== null) return;
    this.cutAt = this.time;
    const cols = 3;
    const rowOf = (i: number) => Math.floor(i / cols);
    this.ribbon.sim.unlink((i, j) => Math.min(rowOf(i), rowOf(j)) <= row && Math.max(rowOf(i), rowOf(j)) > row);
    const { sim } = this.ribbon;
    for (let i = 0; i < sim.n; i++) {
      sim.prev.set(sim.pos.subarray(i * 3, i * 3 + 3), i * 3);
      const near = 1 - Math.min(1, Math.abs(rowOf(i) - row) / 6);
      sim.prev[i * 3 + 2] -= 0.02 * near; // the cut ends spring toward the viewer
      sim.prev[i * 3] -= (rowOf(i) > row ? 0.012 : -0.012) * near;
    }
    for (let c = 0; c < cols; c++) {
      sim.pinned[this.ribbon.id(c, 0)] = 1;
      sim.pinned[this.ribbon.id(c, this.rRows - 1)] = 1;
    }
    const mid = (this.cols - 1) / 2;
    for (let c = 0; c < this.cols; c++) this.release[c] = this.time + 0.55 + (Math.abs(c - mid) / mid) * 0.5 + Math.random() * 0.05;
  }

  private followCloth() {
    // before the cut the ribbon lies on the cloth: each ribbon point sits just in front of the cloth's middle
    const { sim } = this.ribbon;
    const mid = Math.floor(this.cols / 2);
    const rw = Math.abs(sim.pos[this.ribbon.id(2, 0) * 3] - sim.pos[this.ribbon.id(0, 0) * 3]);
    for (let r = 0; r < this.rRows; r++) {
      const cr = r / 2;
      const a = this.cloth.id(mid, Math.floor(cr)) * 3;
      const b = this.cloth.id(mid, Math.min(this.rows - 1, Math.ceil(cr))) * 3;
      const p = this.cloth.sim.pos;
      for (let c = 0; c < 3; c++) {
        const x = (p[a] + p[b]) / 2 + (c - 1) * (rw / 2);
        sim.set(this.ribbon.id(c, r), x, (p[a + 1] + p[b + 1]) / 2, (p[a + 2] + p[b + 2]) / 2 + 0.07 + (c === 1 ? 0.012 : 0));
      }
    }
  }

  private simulate() {
    const t = this.time;
    const cut = this.cutAt;
    const cloth = this.cloth.sim;
    for (let c = 0; c < this.cols; c++) {
      if (t >= this.release[c]) cloth.pinned[this.cloth.id(c, 0)] = 0;
    }
    const falling = cut !== null && t > cut + 0.55;
    const px = this.pointer.x;
    const py = this.pointer.y;
    cloth.step((i, f) => {
      const k = i * 3;
      const x = cloth.pos[k];
      const y = cloth.pos[k + 1];
      // a slow, uneven draught; stronger once the cloth is loose so it billows as it drops
      const gust = Math.sin(t * 0.9 + x * 0.7) * Math.cos(t * 0.53 + y * 0.9);
      f[2] += gust * (falling ? 2.2 : 0.55);
      f[0] += Math.sin(t * 0.4 + y) * 0.12;
      if (falling) f[1] -= 2.2;
      const d = Math.hypot(x - px, y - py);
      if (d < 0.9) f[2] -= (0.9 - d) * 7; // the cloth gives under the pointer
    }, 8);
    if (cut === null) {
      this.followCloth();
    } else {
      const rib = this.ribbon.sim;
      if (falling) for (let c = 0; c < 3; c++) rib.pinned[this.ribbon.id(c, 0)] = rib.pinned[this.ribbon.id(c, this.rRows - 1)] = 0;
      rib.step((i, f) => {
        f[2] += 0.9 + Math.sin(t * 3 + i) * 0.4;
        if (falling) f[1] -= 2.6;
      }, 10);
    }
    this.time += STEP;
  }

  private loop(now: number) {
    this.raf = requestAnimationFrame(this.loop);
    this.acc += Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    while (this.acc >= STEP) {
      this.simulate();
      this.acc -= STEP;
    }
    for (const g of [this.cloth.geo, this.ribbon.geo]) {
      g.attributes.position.needsUpdate = true;
      g.computeVertexNormals();
    }
    // the bow rides on the ribbon and leans with it
    const rp = this.ribbon.sim.pos;
    const k = this.ribbon.id(1, this.bowRow) * 3;
    const up = this.ribbon.id(1, Math.max(0, this.bowRow - 2)) * 3;
    this.bow.position.set(rp[k], rp[k + 1], rp[k + 2] + 0.04);
    this.bow.rotation.z = Math.atan2(rp[up] - rp[k], rp[up + 1] - rp[k + 1]) * -1;
    this.tag.rotation.z = Math.sin(this.time * 1.3) * 0.07 + this.bow.rotation.z * -0.6;
    if (this.cutAt !== null) {
      const since = this.time - this.cutAt;
      // the loops go slack once nothing pulls the knot tight
      const slack = Math.min(1, since / 0.5);
      this.bow.children.forEach((m) => {
        if (m.name === "loop") m.scale.set(1 - slack * 0.12, 1 - slack * 0.3, 1);
      });
      (this.wall.material as THREE.MeshStandardMaterial).opacity = Math.max(0, 1 - Math.max(0, since - 0.75) / 0.8);
      const lowest = this.cloth.sim.pos[this.cloth.id(Math.floor(this.cols / 2), 0) * 3 + 1];
      if (!this.done && (lowest < -this.visH * 0.75 || since > 3.2)) {
        this.done = true;
        this.opts.onDone();
      }
    }
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      m.geometry?.dispose();
      const mat = m.material as THREE.Material | THREE.Material[] | undefined;
      (Array.isArray(mat) ? mat : mat ? [mat] : []).forEach((x) => x.dispose());
    });
    this.renderer.dispose();
  }
}
