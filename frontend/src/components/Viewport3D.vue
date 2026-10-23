<template>
  <div class="viewport-container" ref="containerRef">
    <canvas ref="canvasRef" class="viewport-canvas"></canvas>

    <div v-if="!store.currentVersion && !store.isLoadingModel" class="viewport-empty-state">
      <div class="empty-mark"><Anchor :size="21" /></div>
      <span class="empty-kicker">COTECMAR · VISUALIZACIÓN TÉCNICA</span>
      <h1>Tu espacio de trabajo está listo</h1>
      <p>Selecciona un modelo del proyecto o carga un archivo CAD para comenzar la inspección.</p>
      <button class="primary empty-upload" @click="emit('open-uploader')"><Upload :size="16" /> Cargar modelo</button>
      <div class="format-note"><span>RVM</span><span>Datasmith</span><span>GLB</span></div>
    </div>

    <div v-if="store.currentVersion && store.currentAsset" class="model-context">
      <div class="context-indicator"><Box :size="15" /></div>
      <div class="context-copy"><strong>{{ store.currentAsset.name }}</strong><span>VERSIÓN {{ store.currentVersion.version_number }} · {{ store.currentAsset.format }}</span></div>
    </div>

    <!-- Indicador de carga de modelo -->
    <div v-if="store.isLoadingModel || isLoadingGeometry" class="loader-overlay">
      <div class="loader-box">
        <div class="spinner"></div>
        <div class="loader-text">{{ isLoadingGeometry ? 'Cargando geometría 3D...' : 'Preparando modelo...' }}</div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${store.loadingProgress}%` }"></div>
        </div>
        <div v-if="isLoadingGeometry" class="loader-percent">{{ store.loadingProgress }}%</div>
      </div>
    </div>

    <!-- Cubo de orientación -->
    <div class="view-cube-controls">
      <div
        class="orientation-cube"
        role="group"
        aria-label="Cubo de orientación. Arrastre para girar la vista."
        @pointerdown="onCubePointerDown"
        @pointermove="onCubePointerMove"
        @pointerup="onCubePointerUp"
        @pointercancel="onCubePointerUp"
      >
        <div class="cube-3d" :style="cubeRotationStyle">
          <button class="cube-face face-front" @click="onCubeFace('front')" title="Vista frontal">FRENTE</button>
          <button class="cube-face face-back" @click="onCubeFace('back')" title="Vista posterior">ATRÁS</button>
          <button class="cube-face face-right" @click="onCubeFace('side')" title="Vista derecha">DERECHA</button>
          <button class="cube-face face-left" @click="onCubeFace('left')" title="Vista izquierda">IZQUIERDA</button>
          <button class="cube-face face-top" @click="onCubeFace('top')" title="Vista superior">SUPERIOR</button>
          <button class="cube-face face-bottom" @click="onCubeFace('bottom')" title="Vista inferior">INFERIOR</button>
        </div>
      </div>
    </div>

    <!-- Medición activa en tiempo real -->
    <div v-if="store.activeTool === 'measure'" class="measure-hud">
      <div v-if="!store.currentMeasureStart">
        <span><MapPin :size="15" /> Haz clic en el <strong>primer punto</strong> del modelo.</span>
      </div>
      <div v-else>
        <span><MapPin :size="15" /> Haz clic en el <strong>segundo punto</strong> para terminar la medición.</span>
        <button @click="cancelMeasurement" class="hud-btn">Cancelar</button>
      </div>
    </div>

    <!-- Coordenadas e info rápida en esquina -->
    <div class="info-overlay" v-if="store.currentVersion">
      <div><strong>Triángulos:</strong> {{ store.currentVersion.triangle_count.toLocaleString() }}</div>
      <div><strong>Componentes:</strong> {{ store.currentVersion.component_count.toLocaleString() }}</div>
      <div><strong>Unidades:</strong> {{ store.unit }}</div>
    </div>

    <div class="navigation-hint" aria-label="Clic derecho y arrastrar para mirar; W A S D para moverse; Q y E para bajar y subir; rueda para zoom">
      <div class="hint-row"><span class="hint-keys"><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd></span><span>Mover cámara</span></div>
      <div class="hint-row"><span class="hint-mouse">Doble clic</span><span>Seleccionar componente</span></div>
      <div class="hint-row"><span class="hint-mouse">Clic derecho + arrastrar</span><span>Mirar alrededor</span></div>
      <div class="hint-row"><span class="hint-keys"><kbd>Q</kbd><kbd>E</kbd></span><span>Bajar / subir · rueda: zoom</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { useViewerStore } from '../stores/viewerStore';
import { api } from '../services/api';
import { Anchor, Box, MapPin, Upload } from 'lucide-vue-next';

const store = useViewerStore();
const emit = defineEmits(['open-uploader']);
const cubeRotationX = ref(-28);
const cubeRotationY = ref(-35);
const isLoadingGeometry = ref(false);
const cubePointer = ref<{ id: number; x: number; y: number; moved: boolean } | null>(null);
const suppressCubeClick = ref(false);
const cubeRotationStyle = computed(() => ({
  transform: `rotateX(${cubeRotationX.value}deg) rotateY(${cubeRotationY.value}deg)`
}));
const containerRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let modelGroup: THREE.Group;
let raycaster: THREE.Raycaster;
let mouse: THREE.Vector2;
let modelBounds: THREE.Box3 = new THREE.Box3();
let gridHelper: THREE.GridHelper;
let floorSurface: THREE.Mesh;
let axesHelper: THREE.AxesHelper;

// Planos de corte Three.js
const clipPlaneX = new THREE.Plane(new THREE.Vector3(1, 0, 0), 0);
const clipPlaneY = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const clipPlaneZ = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);

// Grupos para mediciones
let measurementGroup: THREE.Group;

// Mapa de nodos para búsqueda rápida por node_id
const nodeMeshMap = new Map<string, THREE.Mesh[]>();
const pressedNavigationKeys = new Set<string>();
const navigationClock = new THREE.Clock();
let shiftNavigation = false;

onMounted(() => {
  initThree();
  window.addEventListener('resize', onWindowResize);
  window.addEventListener('keydown', onNavigationKeyDown);
  window.addEventListener('keyup', onNavigationKeyUp);
  window.addEventListener('blur', clearNavigationKeys);
});

onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize);
  window.removeEventListener('keydown', onNavigationKeyDown);
  window.removeEventListener('keyup', onNavigationKeyUp);
  window.removeEventListener('blur', clearNavigationKeys);
  canvasRef.value?.removeEventListener('contextmenu', preventViewportContextMenu);
  canvasRef.value?.removeEventListener('dblclick', onDoubleClick);
  disposeScene();
});

function initThree() {
  if (!containerRef.value || !canvasRef.value) return;

  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  // Escena
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xFFFFFF); // Fondo blanco de alto contraste

  // Cámara
  camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000000);
  camera.position.set(5000, 5000, 5000);

  // Renderer
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: false,
    powerPreference: 'low-power'
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
  renderer.localClippingEnabled = true;

  // Controles Orbitales tipo CAD
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.screenSpacePanning = true;
  controls.rotateSpeed = 0.75;
  controls.panSpeed = 0.8;
  controls.zoomSpeed = 0.8;
  controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
  controls.mouseButtons.MIDDLE = THREE.MOUSE.PAN;
  controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;

  // Iluminación amplia para distinguir cubierta, casco y superestructura.
  const ambientLight = new THREE.HemisphereLight(0xdceaff, 0x52647a, 0.72);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffffff, 0.95);
  keyLight.position.set(1, 2, 1.5);
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0xb8d7ff, 0.42);
  fillLight.position.set(-1, 0.6, -1);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xffffff, 0.25);
  rimLight.position.set(0, -0.25, 1);
  scene.add(rimLight);

  // Rejilla de referencia de suelo
  // Escala inicial moderada; al cargar un modelo se ajusta a sus dimensiones.
  floorSurface = new THREE.Mesh(
    new THREE.PlaneGeometry(1000, 1000),
    new THREE.MeshBasicMaterial({ color: 0x0B2340, side: THREE.DoubleSide })
  );
  floorSurface.rotation.x = -Math.PI / 2;
  floorSurface.position.y = -0.5;
  scene.add(floorSurface);

  gridHelper = new THREE.GridHelper(1000, 50, 0xA9C3DB, 0x45617E);
  scene.add(gridHelper);

  // Ejes de coordenadas (Rojo=X, Verde=Y, Azul=Z)
  axesHelper = new THREE.AxesHelper(100);
  scene.add(axesHelper);

  // Contenedores
  modelGroup = new THREE.Group();
  scene.add(modelGroup);

  measurementGroup = new THREE.Group();
  scene.add(measurementGroup);

  raycaster = new THREE.Raycaster();
  mouse = new THREE.Vector2();

  // Eventos de interacción de puntero
  canvasRef.value.addEventListener('pointerdown', onPointerDown);
  canvasRef.value.addEventListener('dblclick', onDoubleClick);
  canvasRef.value.addEventListener('pointermove', onPointerMove);
  canvasRef.value.addEventListener('contextmenu', preventViewportContextMenu);

  animate();
}

function animate() {
  requestAnimationFrame(animate);
  updateKeyboardNavigation(navigationClock.getDelta());
  controls.update();
  renderer.render(scene, camera);
}

function onNavigationKeyDown(event: KeyboardEvent) {
  if (event.key === 'Shift') {
    shiftNavigation = true;
    return;
  }
  const key = event.key.toLowerCase();
  if (!['w', 'a', 's', 'd', 'q', 'e'].includes(key)) return;

  const target = event.target as HTMLElement | null;
  const active = document.activeElement as HTMLElement | null;
  const typing = [target, active].some(element =>
    element?.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(element?.tagName || '')
  );
  if (typing || !containerRef.value?.matches(':hover')) return;

  event.preventDefault();
  pressedNavigationKeys.add(key);
}

function onNavigationKeyUp(event: KeyboardEvent) {
  if (event.key === 'Shift') shiftNavigation = false;
  pressedNavigationKeys.delete(event.key.toLowerCase());
}

function clearNavigationKeys() {
  pressedNavigationKeys.clear();
  shiftNavigation = false;
}

function updateKeyboardNavigation(deltaSeconds: number) {
  if (!controls || !camera || pressedNavigationKeys.size === 0) return;

  const forward = camera.getWorldDirection(new THREE.Vector3());
  forward.y = 0;
  if (forward.lengthSq() < 1e-6) forward.set(0, 0, -1);
  forward.normalize();
  const right = forward.clone().cross(new THREE.Vector3(0, 1, 0)).normalize();

  const movement = new THREE.Vector3();
  if (pressedNavigationKeys.has('w')) movement.add(forward);
  if (pressedNavigationKeys.has('s')) movement.sub(forward);
  if (pressedNavigationKeys.has('d')) movement.add(right);
  if (pressedNavigationKeys.has('a')) movement.sub(right);
  if (pressedNavigationKeys.has('e')) movement.y += 1;
  if (pressedNavigationKeys.has('q')) movement.y -= 1;
  if (movement.lengthSq() === 0) return;

  const modelSize = modelBounds.isEmpty() ? 100 : modelBounds.getSize(new THREE.Vector3()).length();
  const speed = Math.max(modelSize * 0.2, 0.1) * (shiftNavigation ? 2 : 1);
  movement.normalize().multiplyScalar(speed * Math.min(deltaSeconds, 0.05));
  camera.position.add(movement);
  controls.target.add(movement);
  controls.update();
}

function preventViewportContextMenu(event: MouseEvent) {
  event.preventDefault();
}

function onWindowResize() {
  if (!containerRef.value || !renderer || !camera) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

// Carga de modelos GLB
watch(() => store.currentVersion, (newVer) => {
  if (newVer) {
    loadGlbModel(store.currentVersion?.id || '');
  } else {
    clearModel();
  }
});

function loadGlbModel(versionId: string) {
  clearModel();
  isLoadingGeometry.value = true;
  store.loadingProgress = 0;
  const url = api.getGlbUrl(versionId);
  const loader = new GLTFLoader();

  loader.load(url, (gltf) => {
    nodeMeshMap.clear();

    const activePlanes = getActiveClippingPlanes();

    gltf.scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;

        // Algunos GLB de RVM no incluyen normales. Calcularlas permite que la
        // iluminaciÃ³n revele las superficies y el relieve del modelo.
        if (!mesh.geometry.attributes.normal) {
          store.loadingProgress = 99;
          mesh.geometry.computeVertexNormals();
          mesh.material = new THREE.MeshStandardMaterial({
            color: 0x9aabba,
            metalness: 0.08,
            roughness: 0.78,
            side: THREE.DoubleSide,
          });
        }
        
        // Habilitar planos de corte en el material
        if (mesh.material) {
          if (Array.isArray(mesh.material)) {
            mesh.material.forEach(m => {
              m.clippingPlanes = activePlanes;
              m.clipShadows = true;
            });
          } else {
            mesh.material.clippingPlanes = activePlanes;
            mesh.material.clipShadows = true;
          }
        }

        // Mapear por nombre de objeto
        const name = mesh.name || 'Component';
        if (!nodeMeshMap.has(name)) {
          nodeMeshMap.set(name, []);
        }
        nodeMeshMap.get(name)!.push(mesh);
      }
    });

    modelGroup.add(gltf.scene);
    modelBounds.setFromObject(modelGroup);
    updateReferenceScale();
    fitModel();
    renderSavedMeasurements();
    store.loadingProgress = 100;
    isLoadingGeometry.value = false;
  }, (event) => {
    if (event.total > 0) {
      store.loadingProgress = Math.min(99, Math.round((event.loaded / event.total) * 100));
    }
  }, (err: any) => {
    isLoadingGeometry.value = false;
    store.errorMessage = `Error al cargar archivo GLB en el visor: ${err.message || err}`;
  });
}

function clearModel() {
  while (modelGroup.children.length > 0) {
    const obj = modelGroup.children[0];
    modelGroup.remove(obj);
    if ((obj as THREE.Mesh).geometry) (obj as THREE.Mesh).geometry.dispose();
  }
  nodeMeshMap.clear();
  clearMeasurements();
}

// Vistas Estándar de Cámara
function setView(view: 'top' | 'bottom' | 'front' | 'back' | 'left' | 'side' | 'iso') {
  const center = new THREE.Vector3();
  modelBounds.getCenter(center);
  const size = modelBounds.getSize(new THREE.Vector3()).length() || 2000;
  const dist = size * 1.5;

  controls.target.copy(center);

  switch (view) {
    case 'top':
      camera.position.set(center.x, center.y + dist, center.z);
      camera.up.set(0, 0, -1);
      break;
    case 'bottom':
      camera.position.set(center.x, center.y - dist, center.z);
      camera.up.set(0, 0, 1);
      break;
    case 'front':
      camera.position.set(center.x, center.y, center.z + dist);
      camera.up.set(0, 1, 0);
      break;
    case 'back':
      camera.position.set(center.x, center.y, center.z - dist);
      camera.up.set(0, 1, 0);
      break;
    case 'side':
      camera.position.set(center.x + dist, center.y, center.z);
      camera.up.set(0, 1, 0);
      break;
    case 'left':
      camera.position.set(center.x - dist, center.y, center.z);
      camera.up.set(0, 1, 0);
      break;
    case 'iso':
      camera.position.set(center.x + dist * 0.7, center.y + dist * 0.7, center.z + dist * 0.7);
      camera.up.set(0, 1, 0);
      break;
  }
  camera.lookAt(center);
  controls.update();
}

function onCubeFace(view: 'top' | 'bottom' | 'front' | 'back' | 'left' | 'side') {
  if (suppressCubeClick.value) {
    suppressCubeClick.value = false;
    return;
  }
  const orientations = {
    top: [90, 0], bottom: [-90, 0], front: [0, 0], back: [0, 180],
    side: [0, -90], left: [0, 90]
  } as const;
  [cubeRotationX.value, cubeRotationY.value] = orientations[view];
  setView(view);
}

function onCubePointerDown(event: PointerEvent) {
  if (event.button !== 0) return;
  cubePointer.value = { id: event.pointerId, x: event.clientX, y: event.clientY, moved: false };
  const captureTarget = event.target instanceof HTMLElement ? event.target : event.currentTarget as HTMLElement;
  captureTarget.setPointerCapture(event.pointerId);
}

function onCubePointerMove(event: PointerEvent) {
  const pointer = cubePointer.value;
  if (!pointer || pointer.id !== event.pointerId) return;
  const dx = event.clientX - pointer.x;
  const dy = event.clientY - pointer.y;
  if (Math.abs(dx) + Math.abs(dy) > 2) pointer.moved = true;
  if (!pointer.moved) return;
  cubeRotationY.value += dx * 0.9;
  cubeRotationX.value = Math.max(-170, Math.min(170, cubeRotationX.value + dy * 0.9));
  pointer.x = event.clientX;
  pointer.y = event.clientY;
}

function onCubePointerUp(event: PointerEvent) {
  const pointer = cubePointer.value;
  if (!pointer || pointer.id !== event.pointerId) return;
  if (pointer.moved) {
    suppressCubeClick.value = true;
    const center = new THREE.Vector3();
    modelBounds.getCenter(center);
    const distance = modelBounds.getSize(new THREE.Vector3()).length() * 1.5 || 2000;
    const euler = new THREE.Euler(
      THREE.MathUtils.degToRad(cubeRotationX.value),
      THREE.MathUtils.degToRad(cubeRotationY.value),
      0,
      'XYZ'
    );
    const direction = new THREE.Vector3(0, 0, 1).applyEuler(euler).normalize();
    controls.target.copy(center);
    camera.position.copy(center).addScaledVector(direction, distance);
    camera.up.set(0, Math.abs(direction.y) > 0.94 ? 0 : 1, Math.abs(direction.y) > 0.94 ? 1 : 0);
    camera.lookAt(center);
    controls.update();
  }
  cubePointer.value = null;
}

function fitModel() {
  if (modelGroup.children.length === 0) return;
  modelBounds.setFromObject(modelGroup);
  const center = new THREE.Vector3();
  modelBounds.getCenter(center);
  const size = modelBounds.getSize(new THREE.Vector3()).length();

  const dist = size / (2 * Math.tan((camera.fov * Math.PI) / 360));
  camera.position.set(center.x + dist * 0.7, center.y + dist * 0.7, center.z + dist * 0.7);
  camera.lookAt(center);
  controls.target.copy(center);
  controls.update();
}

function updateReferenceScale() {
  if (!scene || !modelGroup.children.length) return;

  const dimensions = modelBounds.getSize(new THREE.Vector3());
  const modelScale = Math.max(dimensions.x, dimensions.y, dimensions.z, 1);
  const gridSize = modelScale * 2.5;
  const center = modelBounds.getCenter(new THREE.Vector3());
  const groundY = modelBounds.min.y;

  scene.remove(floorSurface);
  floorSurface.geometry.dispose();
  (floorSurface.material as THREE.Material).dispose();
  floorSurface = new THREE.Mesh(
    new THREE.PlaneGeometry(gridSize, gridSize),
    new THREE.MeshBasicMaterial({ color: 0x0B2340, side: THREE.DoubleSide })
  );
  floorSurface.rotation.x = -Math.PI / 2;
  floorSurface.position.set(center.x, groundY - modelScale * 0.002, center.z);
  scene.add(floorSurface);

  scene.remove(gridHelper);
  gridHelper.geometry.dispose();
  const oldGridMaterials = Array.isArray(gridHelper.material) ? gridHelper.material : [gridHelper.material];
  oldGridMaterials.forEach(material => material.dispose());
  gridHelper = new THREE.GridHelper(gridSize, 50, 0xA9C3DB, 0x45617E);
  gridHelper.position.set(center.x, groundY, center.z);
  scene.add(gridHelper);

  scene.remove(axesHelper);
  axesHelper.geometry.dispose();
  const oldAxisMaterials = Array.isArray(axesHelper.material) ? axesHelper.material : [axesHelper.material];
  oldAxisMaterials.forEach(material => material.dispose());
  axesHelper = new THREE.AxesHelper(modelScale * 0.45);
  scene.add(axesHelper);
}

// Planos de Corte Dinámicos
function getActiveClippingPlanes(): THREE.Plane[] {
  const planes: THREE.Plane[] = [];
  const p = store.clippingPlanes;

  if (p.x.enabled) {
    clipPlaneX.normal.set(p.x.inverted ? -1 : 1, 0, 0);
    clipPlaneX.constant = p.x.inverted ? p.x.position : -p.x.position;
    planes.push(clipPlaneX);
  }
  if (p.y.enabled) {
    clipPlaneY.normal.set(0, p.y.inverted ? -1 : 1, 0);
    clipPlaneY.constant = p.y.inverted ? p.y.position : -p.y.position;
    planes.push(clipPlaneY);
  }
  if (p.z.enabled) {
    clipPlaneZ.normal.set(0, 0, p.z.inverted ? -1 : 1);
    clipPlaneZ.constant = p.z.inverted ? p.z.position : -p.z.position;
    planes.push(clipPlaneZ);
  }
  return planes;
}

watch(() => store.clippingPlanes, () => {
  const activePlanes = getActiveClippingPlanes();
  modelGroup.traverse((child) => {
    if ((child as THREE.Mesh).isMesh && (child as THREE.Mesh).material) {
      const mat = (child as THREE.Mesh).material;
      if (Array.isArray(mat)) {
        mat.forEach(m => m.clippingPlanes = activePlanes);
      } else {
        mat.clippingPlanes = activePlanes;
      }
    }
  });
}, { deep: true });

// Sincronización de Visibilidad y Aislamiento
watch([() => store.hiddenNodeIds, () => store.isolatedNodeId], () => {
  const isolated = store.isolatedNodeId;
  const hidden = store.hiddenNodeIds;

  nodeMeshMap.forEach((meshes, name) => {
    let isVisible = true;
    if (isolated) {
      isVisible = (name === isolated);
    } else if (hidden.has(name)) {
      isVisible = false;
    }
    meshes.forEach(m => m.visible = isVisible);
  });
}, { deep: true });

// Resaltado de Selección
watch(() => store.selectedNodeId, (newId, oldId) => {
  if (oldId && nodeMeshMap.has(oldId)) {
    nodeMeshMap.get(oldId)!.forEach(m => {
      if ((m.material as any)._originalColor) {
        (m.material as THREE.MeshStandardMaterial).color.copy((m.material as any)._originalColor);
      }
    });
  }
  if (newId && nodeMeshMap.has(newId)) {
    nodeMeshMap.get(newId)!.forEach(m => {
      const mat = m.material as THREE.MeshStandardMaterial;
      if (!(mat as any)._originalColor) {
        (mat as any)._originalColor = mat.color.clone();
      }
      mat.color.set(0x234BA1); // Resaltado azul corporativo
    });
  }
});

// Eventos de Puntero y Raycasting
function onPointerDown(e: MouseEvent) {
  if (e.button !== 0 || store.activeTool !== 'measure') return; // El clic simple se reserva para medir
  updateMouse(e);
  raycaster.setFromCamera(mouse, camera);

  const intersects = raycaster.intersectObjects(modelGroup.children, true);
  if (intersects.length > 0) {
    const hitPoint = intersects[0].point;
    if (!store.currentMeasureStart) {
      // Punto inicial A
      store.currentMeasureStart = [hitPoint.x, hitPoint.y, hitPoint.z];
    } else {
      // Punto final B -> Calcular distancia euclidiana física
      const pA = new THREE.Vector3(...store.currentMeasureStart);
      const pB = hitPoint;
      const dist = pA.distanceTo(pB);

      store.addMeasurement({
        model_version: store.currentVersion?.id || '',
        point_a: [pA.x, pA.y, pA.z],
        point_b: [pB.x, pB.y, pB.z],
        distance: Math.round(dist * 100) / 100,
        unit: store.unit,
        label: `Medición ${store.measurements.length + 1}`,
        measurement_type: 'exact_cad'
      });

      store.currentMeasureStart = null;
      renderSavedMeasurements();
    }
  }
}

function onDoubleClick(e: MouseEvent) {
  if (e.button !== 0 || store.activeTool !== 'navigate') return;
  updateMouse(e);
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(modelGroup.children, true);
  if (intersects.length > 0) {
    const mesh = intersects[0].object as THREE.Mesh;
    store.selectNode(mesh.name || 'Component');
  } else {
    store.selectNode(null);
  }
}

function onPointerMove(e: MouseEvent) {
  updateMouse(e);
}

function updateMouse(e: MouseEvent) {
  if (!containerRef.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
}

function cancelMeasurement() {
  store.currentMeasureStart = null;
}

// Renderizado de Mediciones en Escena 3D
function renderSavedMeasurements() {
  clearMeasurements();
  store.measurements.forEach((m) => {
    const pA = new THREE.Vector3(...m.point_a);
    const pB = new THREE.Vector3(...m.point_b);

    // Línea de medición
    const geom = new THREE.BufferGeometry().setFromPoints([pA, pB]);
    const mat = new THREE.LineBasicMaterial({ color: 0xDC2626, linewidth: 2 });
    const line = new THREE.Line(geom, mat);
    measurementGroup.add(line);

    // Esferas en extremos
    const sphereGeom = new THREE.SphereGeometry(25);
    const sphereMat = new THREE.MeshBasicMaterial({ color: 0xDC2626 });
    const sphereA = new THREE.Mesh(sphereGeom, sphereMat);
    sphereA.position.copy(pA);
    const sphereB = new THREE.Mesh(sphereGeom, sphereMat);
    sphereB.position.copy(pB);
    measurementGroup.add(sphereA);
    measurementGroup.add(sphereB);
  });
}

function clearMeasurements() {
  while (measurementGroup.children.length > 0) {
    const obj = measurementGroup.children[0];
    measurementGroup.remove(obj);
    if ((obj as THREE.Mesh).geometry) (obj as THREE.Mesh).geometry.dispose();
  }
}

watch(() => store.measurements, () => {
  renderSavedMeasurements();
}, { deep: true });

function disposeScene() {
  clearModel();
  if (renderer) renderer.dispose();
}
</script>

<style scoped>
.viewport-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: #fff;
}

.viewport-empty-state {
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(420px, calc(100% - 48px));
  padding: 30px 32px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  border: 1px solid rgba(218, 229, 237, .9);
  border-radius: 18px;
  background: rgba(255, 255, 255, .91);
  backdrop-filter: blur(12px);
  box-shadow: 0 18px 55px rgba(34, 62, 83, .12);
}
.empty-mark { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 14px; color: #fff; background: linear-gradient(145deg, #286a96, #174b78); box-shadow: 0 8px 18px rgba(23, 75, 120, .2); }
.empty-kicker { margin-top: 17px; color: #71869a; font-size: 9px; font-weight: 800; letter-spacing: 1.2px; }
.viewport-empty-state h1 { margin-top: 7px; font-size: 19px; line-height: 1.3; color: #18364d; letter-spacing: -.35px; }
.viewport-empty-state p { max-width: 310px; margin-top: 8px; color: #718296; font-size: 12px; line-height: 1.65; }
.empty-upload { margin-top: 19px; min-height: 39px; padding: 0 16px; }
.format-note { display: flex; align-items: center; gap: 7px; margin-top: 17px; }
.format-note span { padding: 4px 8px; border-radius: 5px; border: 1px solid #e2eaf0; background: #f8fafc; color: #758799; font-size: 9px; font-weight: 700; letter-spacing: .4px; }
.model-context { position: absolute; z-index: 4; top: 18px; left: 18px; display: flex; align-items: center; gap: 9px; max-width: min(360px, calc(100% - 190px)); padding: 8px 12px 8px 8px; border: 1px solid rgba(218, 229, 237, .95); border-radius: 10px; background: rgba(255, 255, 255, .92); box-shadow: 0 4px 16px rgba(28, 56, 78, .08); backdrop-filter: blur(8px); }
.context-indicator { width: 30px; height: 30px; display: grid; place-items: center; flex: 0 0 auto; border-radius: 7px; background: #e8f1f7; color: var(--primary-blue); }
.context-copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.context-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; color: #233e53; }
.context-copy span { font-size: 8px; font-weight: 800; letter-spacing: .75px; color: #8293a4; }

.viewport-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.loader-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(244, 246, 249, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.loader-box {
  background: #FFFFFF;
  padding: 24px 32px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  width: 260px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #E2E8F0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-blue);
  transition: width 0.2s ease;
}

.loader-percent { color: var(--text-muted); font-size: 11px; font-variant-numeric: tabular-nums; }

.view-cube-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.94);
  padding: 12px 10px;
  border-radius: 12px;
  border: 1px solid #dce5ed;
  box-shadow: 0 8px 24px rgba(28, 56, 78, 0.12);
  z-index: 10;
}

.orientation-cube { width: 104px; height: 104px; perspective: 320px; display: grid; place-items: center; cursor: grab; touch-action: none; user-select: none; }
.orientation-cube:active { cursor: grabbing; }
.cube-3d { position: relative; width: 56px; height: 56px; transform-style: preserve-3d; }
.cube-face {
  position: absolute;
  width: 56px;
  height: 56px;
  padding: 2px;
  border: 1px solid #9db4c7;
  border-radius: 5px;
  background: linear-gradient(145deg, #fff, #e9f1f7);
  color: #244b68;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: .35px;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.75);
  backface-visibility: hidden;
}
.cube-face:hover { background: #d8eaf6; border-color: #4c86ad; color: #123c5c; }
.face-front { transform: translateZ(28px); }
.face-back { transform: rotateY(180deg) translateZ(28px); }
.face-right { transform: rotateY(90deg) translateZ(28px); }
.face-left { transform: rotateY(-90deg) translateZ(28px); }
.face-top { transform: rotateX(90deg) translateZ(28px); }
.face-bottom { transform: rotateX(-90deg) translateZ(28px); }

.measure-hud {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #1E293B;
  color: #FFFFFF;
  padding: 8px 16px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 10;
}

.measure-hud span { display: inline-flex; align-items: center; gap: 7px; }
.measure-hud span svg { color: #92c4e3; }

.hud-btn {
  background: transparent;
  color: #94A3B8;
  border-color: #475569;
  padding: 3px 8px;
}

.hud-btn:hover {
  color: #FFFFFF;
  border-color: #FFFFFF;
}

.info-overlay {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 2px;
  pointer-events: none;
}

.navigation-hint {
  position: absolute;
  right: 20px;
  bottom: 18px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 10px;
  border: 1px solid rgba(218, 229, 237, .95);
  border-radius: 8px;
  background: rgba(255, 255, 255, .9);
  color: #718296;
  font-size: 10px;
  box-shadow: 0 4px 14px rgba(28, 56, 78, .07);
  pointer-events: none;
}

.navigation-hint > span:first-child { display: flex; gap: 3px; }
.navigation-hint kbd {
  min-width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border: 1px solid #d7e1e9;
  border-radius: 4px;
  background: #fff;
  color: #315d7c;
  font-family: inherit;
  font-size: 9px;
  font-weight: 700;
  box-shadow: 0 1px 1px rgba(20, 44, 62, .08);
}
</style>
