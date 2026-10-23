<template>
  <div class="app-layout">
    <!-- Barra superior de navegación y herramientas -->
    <Toolbar @open-uploader="showUploader = true" />

    <!-- Área de trabajo principal -->
    <div class="workspace">
      <!-- Árbol de objetos lateral -->
      <Transition name="tree-panel">
        <ObjectTree v-if="treeVisible" />
      </Transition>

      <!-- Ventana 3D Principal Three.js -->
      <main class="viewport-wrapper">
        <button
          class="tree-edge-toggle"
          :class="{ 'is-collapsed': !treeVisible }"
          @click="treeVisible = !treeVisible"
          :aria-label="treeVisible ? 'Ocultar árbol de componentes' : 'Mostrar árbol de componentes'"
          :title="treeVisible ? 'Ocultar árbol' : 'Mostrar árbol'"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m10 3-5 5 5 5" /></svg>
        </button>
        <Viewport3D ref="viewportRef" @open-uploader="showUploader = true" />

        <!-- Herramientas flotantes según la selección -->
        <ClippingPanel v-if="store.activeTool === 'clip'" />
        <MeasurementPanel v-if="store.activeTool === 'measure'" />
        <CameraPanel
          v-if="store.activeTool === 'camera'"
          @capture-camera="onCaptureCamera"
          @restore-camera="onRestoreCamera"
        />
        <PropertiesPanel />
      </main>
    </div>

    <!-- Modal de Carga de Archivos de hasta 5 GB -->
    <UploaderModal v-if="showUploader" @close="showUploader = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useViewerStore } from './stores/viewerStore';
import Toolbar from './components/Toolbar.vue';
import ObjectTree from './components/ObjectTree.vue';
import Viewport3D from './components/Viewport3D.vue';
import ClippingPanel from './components/ClippingPanel.vue';
import MeasurementPanel from './components/MeasurementPanel.vue';
import CameraPanel from './components/CameraPanel.vue';
import PropertiesPanel from './components/PropertiesPanel.vue';
import UploaderModal from './components/UploaderModal.vue';

const store = useViewerStore();
const showUploader = ref(false);
const treeVisible = ref(true);
const viewportRef = ref<any>(null);

onMounted(async () => {
  await store.loadProjects();
});

function onCaptureCamera(callback: (state: any) => void) {
  // Captura la posición de cámara y target
  const cam = (viewportRef.value as any)?.camera;
  const controls = (viewportRef.value as any)?.controls;
  if (cam && controls) {
    callback({
      position: [cam.position.x, cam.position.y, cam.position.z],
      target: [controls.target.x, controls.target.y, controls.target.z],
      up: [cam.up.x, cam.up.y, cam.up.z],
      fov: cam.fov,
      projection: 'perspective'
    });
  } else {
    // Valores de respaldo si no están inicializados
    callback({
      position: [5000, 5000, 5000],
      target: [0, 0, 0],
      up: [0, 1, 0],
      fov: 45,
      projection: 'perspective'
    });
  }
}

function onRestoreCamera(camState: any) {
  const cam = (viewportRef.value as any)?.camera;
  const controls = (viewportRef.value as any)?.controls;
  if (cam && controls) {
    cam.position.set(...camState.position);
    controls.target.set(...camState.target);
    cam.up.set(...camState.up);
    controls.update();
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-main);
}

.workspace {
  display: flex;
  flex: 1;
  height: calc(100vh - var(--header-height));
  position: relative;
  isolation: isolate;
  overflow: hidden;
}

.viewport-wrapper {
  flex: 1;
  position: relative;
  z-index: 2;
  height: 100%;
  overflow: visible;
}

.tree-edge-toggle {
  position: absolute;
  z-index: 50;
  left: 0;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 28px;
  height: 56px;
  padding: 0;
  border: 1px solid #d5e0e9;
  border-radius: 0 11px 11px 0;
  background: #fff;
  color: var(--primary-blue);
  box-shadow: 0 3px 12px #17334a1a;
}

.tree-edge-toggle:hover { background: #f1f6fa; }
.tree-edge-toggle svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.8; transition: transform .2s ease; }
.tree-edge-toggle.is-collapsed svg { transform: rotate(180deg); }
.tree-edge-toggle.is-collapsed { left: 0; transform: translateY(-50%); }
:deep(.tree-panel-enter-active), :deep(.tree-panel-leave-active) { transition: width .2s ease, opacity .16s ease; overflow: hidden; }
:deep(.tree-panel-enter-from), :deep(.tree-panel-leave-to) { width: 0; opacity: 0; }
</style>

