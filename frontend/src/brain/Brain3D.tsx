import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { BrainActivity } from "../api/client";
import { formatNumber, ui } from "../i18n/text";
import { brightness } from "./brightness";
import { BRAIN_SHELL, type BrainGeometry, geometryIndex, loadGeometry } from "./geometry3d";
import { neuropilLabel } from "./neuropils";

const READOUT_RADIUS_UM = 5;
const SHELL_OPACITY = 0.07;
const MIN_OPACITY = 0.14; // sönük bölgeler görünür ama içini göstersin
const FIT_MARGIN = 1.12;
const FOV_DEGREES = 40;

interface Props {
  activity: BrainActivity | null;
  activeReadouts: ReadonlySet<string>;
  onError: (message: string) => void;
}

interface Scene {
  /** Sahnenin yeniden çizilmesi gerektiğini işaretler (boşta çizim yapılmaz). */
  markDirty: () => void;
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  neuropils: Map<string, THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>>;
  readouts: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial>[];
  dispose: () => void;
}

function themeColor(name: string, fallback: string): THREE.Color {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return new THREE.Color(value || fallback);
}

/** Modeli görüş alanına sığdıran kamera uzaklığı (µm). */
function fitDistance(geometry: BrainGeometry, aspect: number): number {
  const [width = 1, height = 1, depth = 1] = geometry.sizeUm;
  const half = (Math.PI * FOV_DEGREES) / 360;
  const vertical = height / 2 / Math.tan(half);
  const horizontal = width / 2 / Math.tan(half) / Math.max(aspect, 0.2);
  return (Math.max(vertical, horizontal) + depth / 2) * FIT_MARGIN;
}

function buildScene(container: HTMLDivElement, geometry: BrainGeometry): Scene {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV_DEGREES, 1, 1, 10_000);
  camera.position.set(0, 0, fitDistance(geometry, 1));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = geometry.radiusUm * 0.6;
  controls.maxDistance = geometry.radiusUm * 8;
  controls.rotateSpeed = 0.9;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x404040, 2.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(1, 1.4, 2);
  scene.add(key);

  const positions = new THREE.BufferAttribute(geometry.positions, 3);
  const neuropils = new Map<string, THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>>();
  const shellColor = themeColor("--brain-stroke", "#9a9991");
  const regionColor = themeColor("--region-fill", "#1d1d1b").lerp(shellColor, 0.55);

  for (const part of geometry.parts) {
    const buffer = new THREE.BufferGeometry();
    buffer.setAttribute("position", positions);
    buffer.setIndex(
      new THREE.BufferAttribute(
        geometry.indices.subarray(part.index_offset, part.index_offset + part.index_count),
        1,
      ),
    );
    buffer.computeVertexNormals();
    const shell = part.name === BRAIN_SHELL;
    const material = new THREE.MeshStandardMaterial({
      color: shell ? shellColor : regionColor,
      transparent: true,
      opacity: shell ? SHELL_OPACITY : MIN_OPACITY,
      roughness: 0.85,
      metalness: 0,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(buffer, material);
    mesh.scale.setScalar(geometry.scale);
    mesh.renderOrder = shell ? 0 : 1;
    mesh.userData.neuropil = shell ? null : part.name;
    scene.add(mesh);
    if (!shell) neuropils.set(part.name, mesh);
  }

  const readouts: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial>[] = [];
  const sphere = new THREE.SphereGeometry(READOUT_RADIUS_UM, 16, 12);
  const readoutColor = themeColor("--readout", "#eb6834");
  for (const group of geometryIndex.readouts) {
    for (const neuron of group.neurons) {
      const [x = 0, y = 0, z = 0] = neuron.point;
      const mesh = new THREE.Mesh(
        sphere,
        new THREE.MeshStandardMaterial({ color: readoutColor, emissive: readoutColor.clone() }),
      );
      mesh.material.emissiveIntensity = 0.15;
      mesh.position.set(x, y, z);
      mesh.userData.group = group.group;
      scene.add(mesh);
      readouts.push(mesh);
    }
  }

  return {
    markDirty: () => {},
    renderer,
    scene,
    camera,
    controls,
    neuropils,
    readouts,
    dispose: () => {
      controls.dispose();
      for (const mesh of neuropils.values()) {
        mesh.geometry.dispose();
        mesh.material.dispose();
      }
      for (const mesh of readouts) mesh.material.dispose();
      sphere.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

/** Nöropil renk, saydamlık ve davranış nöronu vurgusunu etkinliğe göre günceller. */
function applyActivity(
  built: Scene,
  activity: BrainActivity | null,
  activeReadouts: ReadonlySet<string>,
): void {
  const glow = themeColor("--glow-3d", "#3987e5");
  const base = themeColor("--region-fill", "#1d1d1b").lerp(
    themeColor("--brain-stroke", "#9a9991"),
    0.55,
  );
  for (const [name, mesh] of built.neuropils) {
    const rate = activity?.neuropil_rates_hz[name] ?? 0;
    const level = activity ? brightness(rate, activity.scale) : 0;
    mesh.material.color.copy(base).lerp(glow, level);
    mesh.material.emissive.copy(glow).multiplyScalar(level ** 1.5 * 0.5);
    mesh.material.opacity = MIN_OPACITY + level * 0.8;
    mesh.material.depthWrite = level > 0.75;
  }
  for (const mesh of built.readouts) {
    const active = activeReadouts.has(String(mesh.userData.group));
    mesh.scale.setScalar(active ? 1.6 : 1);
    mesh.material.emissiveIntensity = active ? 0.9 : 0.15;
  }
  built.markDirty();
}

/** Döndürülebilir 3B beyin. Geometri 2B şemayla aynı FlyWire ağlarından üretilir. */
export function Brain3D({ activity, activeReadouts, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<Scene | null>(null);
  const [hover, setHover] = useState<{ code: string; x: number; y: number } | null>(null);
  // Sahne kurulduğunda son etkinliği hemen uygulayabilmek için güncel değerler ref'te tutulur.
  const latest = useRef({ activity, activeReadouts });
  latest.current = { activity, activeReadouts };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let cancelled = false;
    let frame = 0;

    loadGeometry()
      .then((geometry) => {
        if (cancelled || !containerRef.current) return;
        const built = buildScene(container, geometry);
        sceneRef.current = built;
        applyActivity(built, latest.current.activity, latest.current.activeReadouts);

        let fitted = false;
        const resize = () => {
          const { clientWidth, clientHeight } = container;
          if (!clientWidth || !clientHeight) return;
          const aspect = clientWidth / clientHeight;
          built.renderer.setSize(clientWidth, clientHeight, false);
          built.camera.aspect = aspect;
          built.camera.updateProjectionMatrix();
          if (!fitted) {
            fitted = true;
            built.camera.position.setZ(fitDistance(geometry, aspect));
            built.controls.update();
          }
          built.markDirty();
        };
        resize();
        const observer = new ResizeObserver(resize);
        observer.observe(container);

        // Boşta çizim yapılmaz: yalnızca kamera hareket ettiğinde ya da veri değiştiğinde çizilir.
        let dirty = true;
        built.markDirty = () => {
          dirty = true;
        };
        const tick = () => {
          const moved = built.controls.update();
          if (moved || dirty) {
            built.renderer.render(built.scene, built.camera);
            dirty = false;
          }
          frame = requestAnimationFrame(tick);
        };
        tick();

        built.dispose = ((previous) => () => {
          observer.disconnect();
          previous();
        })(built.dispose);
      })
      .catch((error: Error) => {
        if (!cancelled) onError(error.message);
      });

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      sceneRef.current?.dispose();
      sceneRef.current = null;
    };
  }, [onError]);

  // Etkinlik değiştiğinde renk ve saydamlık güncellenir (geometri yeniden kurulmaz).
  useEffect(() => {
    if (sceneRef.current) applyActivity(sceneRef.current, activity, activeReadouts);
  }, [activity, activeReadouts]);

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    const built = sceneRef.current;
    const container = containerRef.current;
    if (!built || !container) return;
    const box = container.getBoundingClientRect();
    const x = event.clientX - box.left;
    const y = event.clientY - box.top;
    const pointer = new THREE.Vector2((x / box.width) * 2 - 1, -(y / box.height) * 2 + 1);
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(pointer, built.camera);
    const hits = raycaster.intersectObjects([...built.neuropils.values()], false);
    const code = hits.find((hit) => hit.object.userData.neuropil)?.object.userData.neuropil;
    setHover(code ? { code: String(code), x, y } : null);
  }

  const label = hover ? neuropilLabel(hover.code) : null;

  return (
    <div
      className="brain3d"
      ref={containerRef}
      onPointerMove={onPointerMove}
      onPointerLeave={() => setHover(null)}
    >
      {hover && label && (
        <div className="tooltip" style={{ left: hover.x, top: hover.y }} role="presentation">
          <strong>{label.name}</strong>
          <span className="tooltip__sub">
            {label.code} · {label.english}
          </span>
          {activity && (
            <span className="tooltip__value">
              {formatNumber(activity.neuropil_rates_hz[hover.code] ?? 0, 2)} Hz
            </span>
          )}
        </div>
      )}
      {!sceneRef.current && <p className="brain3d__loading">{ui.brain.loading_3d}</p>}
    </div>
  );
}
