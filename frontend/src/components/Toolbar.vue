<template>
  <header class="app-toolbar">
    <div class="brand">
      <img class="brand-logo" :src="cotecmarLogo" alt="COTECMAR · #SeguimosAvante" />
    </div>

    <!-- Selectores de Proyecto y Modelo -->
    <div class="project-selector">
      <div class="selector-field">
        <label for="project-select">PROYECTO</label>
        <select id="project-select" v-model="selectedProjectId" @change="onProjectChange">
          <option value="" disabled>{{ store.projects.length ? 'Seleccionar proyecto' : 'Sin proyectos disponibles' }}</option>
          <option v-for="p in store.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>
      <div class="selector-field model-field">
        <label for="model-select">MODELO 3D</label>
        <select id="model-select" v-model="selectedAssetId" @change="onAssetChange" :disabled="!store.assets.length">
          <option value="" disabled>{{ store.assets.length ? 'Seleccionar modelo' : 'Sin modelos disponibles' }}</option>
          <option v-for="a in store.assets" :key="a.id" :value="a.id">{{ a.name }} ({{ a.format }})</option>
        </select>
      </div>
    </div>

    <!-- Herramientas principales -->
    <div class="tool-group" aria-label="Herramientas del visor">
      <button
        :class="{ active: store.activeTool === 'navigate' }"
        @click="store.activeTool = 'navigate'"
        title="Navegación e inspección"
      >
        <MousePointer2 :size="16" /><span>Inspección</span>
      </button>

      <button
        :class="{ active: store.activeTool === 'measure' }"
        @click="store.activeTool = 'measure'"
        title="Medición entre puntos"
      >
        <Ruler :size="16" /><span>Medir</span>
      </button>

      <button
        :class="{ active: store.activeTool === 'clip' }"
        @click="store.activeTool = 'clip'"
        title="Planos de corte"
      >
        <Scissors :size="16" /><span>Cortes</span>
      </button>

      <button
        :class="{ active: store.activeTool === 'camera' }"
        @click="store.activeTool = 'camera'"
        title="Cámaras y vistas guardadas"
      >
        <Camera :size="16" /><span>Vistas</span>
      </button>
    </div>

    <!-- Unidades y acción de carga -->
    <div class="actions">
      <div class="unit-selector">
        <label for="unit-select">UNIDAD</label>
        <select id="unit-select" v-model="store.unit">
          <option value="mm">Milímetros (mm)</option>
          <option value="m">Metros (m)</option>
          <option value="in">Pulgadas (in)</option>
        </select>
      </div>

      <button class="primary" @click="$emit('open-uploader')">
        <Upload :size="16" /><span>Cargar modelo</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useViewerStore } from '../stores/viewerStore';
import cotecmarLogo from '../assets/cotecmar.png';
import { Camera, MousePointer2, Ruler, Scissors, Upload } from 'lucide-vue-next';

defineEmits(['open-uploader']);
const store = useViewerStore();

const selectedProjectId = ref<string>('');
const selectedAssetId = ref<string>('');

watch(() => store.currentProject, (p) => {
  if (p) selectedProjectId.value = p.id;
});

watch(() => store.currentAsset, (a) => {
  if (a) selectedAssetId.value = a.id;
});

function onProjectChange() {
  const proj = store.projects.find(p => p.id === selectedProjectId.value);
  if (proj) store.selectProject(proj);
}

function onAssetChange() {
  const asset = store.assets.find(a => a.id === selectedAssetId.value);
  if (asset) store.selectAsset(asset);
}
</script>

<style scoped>
.app-toolbar {
  height: var(--header-height);
  flex-shrink: 0;
  background: #0b2340;
  border-bottom: 1px solid #203e5d;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  gap: 24px;
  z-index: 30;
  box-shadow: 0 2px 14px rgba(6, 20, 36, .2);
}

.brand {
  display: flex;
  align-items: center;
  min-width: 270px;
}

.brand-logo {
  display: block;
  width: 254px;
  height: 58px;
  object-fit: contain;
  padding: 5px 9px;
  border-radius: 8px;
  background: transparent;
}

.brand-copy { display: flex; flex-direction: column; gap: 1px; }
.brand-subtitle {
  font-size: 8px;
  color: var(--text-muted);
  font-weight: 700;
  letter-spacing: 1.1px;
}

.brand-title {
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 1.4px;
  color: var(--primary-blue);
}

.project-selector {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 24px;
  border-left: 1px solid #294867;
  min-width: 0;
  flex: 1;
}

.selector-field { display: flex; flex-direction: column; gap: 4px; min-width: 150px; }
.selector-field label, .unit-selector label { font-size: 9px; font-weight: 800; letter-spacing: .9px; color: #b8c9d9; }
.selector-field select { width: 100%; max-width: 220px; padding: 7px 30px 7px 10px; }
.selector-field.model-field { min-width: 200px; }
.selector-field select:disabled { color: #9aa8b5; background: #f6f8fa; }

.tool-group {
  position: fixed;
  z-index: 40;
  top: calc(var(--header-height) + (100vh - var(--header-height)) / 2);
  right: 20px;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 5px;
  background: rgba(255, 255, 255, .96);
  padding: 6px;
  border-radius: 10px;
  border: 1px solid #dce5ed;
  box-shadow: 0 6px 20px rgba(28, 56, 78, .12);
}

.tool-group button {
  justify-content: flex-start;
  min-width: 116px;
  border: 1px solid transparent;
  background: transparent;
  padding: 8px 10px;
  border-radius: 7px;
}

.tool-group button.active {
  background: #FFFFFF;
  color: var(--primary-blue);
  font-weight: 600;
  border-color: #d8e5ef;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}


.actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.unit-selector {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.unit-selector select { min-width: 138px; }
.actions .primary { min-height: 38px; padding: 0 15px; }
.app-toolbar .actions .primary { background: #2d5f91; border-color: #4f7ca7; color: #fff; }
.app-toolbar .actions .primary:hover:not(:disabled) { background: #3973aa; border-color: #6c96bd; }
.tool-group svg { flex: 0 0 auto; }
.tool-group span { white-space: nowrap; }

@media (max-width: 1100px) {
  .brand { min-width: auto; }
  .brand-logo { width: 190px; height: 46px; padding: 4px 7px; }
  .brand-subtitle, .unit-selector { display: none; }
  .project-selector { padding: 0 12px; }
  .app-toolbar { gap: 10px; padding: 0 14px; }
  .selector-field.model-field { min-width: 150px; }
}

@media (max-width: 760px) {
  .app-toolbar { flex-wrap: wrap; height: auto; padding: 10px 12px; }
  .project-selector { order: 3; width: 100%; border: 0; padding: 8px 0 0; flex: 0 0 100%; }
  .tool-group { right: 10px; }
  .actions { margin-left: auto; }
  .tool-group button { min-width: 106px; padding: 7px 8px; }
}
</style>



