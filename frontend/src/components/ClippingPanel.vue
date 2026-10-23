<template>
  <section class="tool-panel">
    <div class="panel-header">
      <div><span class="panel-eyebrow">ANÁLISIS</span><h4>Planos de corte</h4></div>
      <button class="close-btn" @click="store.activeTool = 'navigate'" title="Cerrar cortes" aria-label="Cerrar cortes"><X :size="17" /></button>
    </div>
    <div class="panel-body">
      <div v-for="axis in axes" :key="axis.key" class="plane-row">
        <div class="plane-title">
          <label>
            <input type="checkbox" v-model="store.clippingPlanes[axis.key].enabled" />
            <strong>Plano {{ axis.key.toUpperCase() }}</strong><span>{{ axis.description }}</span>
          </label>
          <button class="mini-btn" :disabled="!store.clippingPlanes[axis.key].enabled" @click="store.clippingPlanes[axis.key].inverted = !store.clippingPlanes[axis.key].inverted">
            {{ store.clippingPlanes[axis.key].inverted ? 'Invertido' : 'Normal' }}
          </button>
        </div>
        <div class="slider-box" v-if="store.clippingPlanes[axis.key].enabled">
          <input type="range" v-model.number="store.clippingPlanes[axis.key].position" :min="minBounds[axis.key]" :max="maxBounds[axis.key]" step="10" />
          <span class="pos-val">{{ Math.round(store.clippingPlanes[axis.key].position) }} {{ store.unit }}</span>
        </div>
      </div>
      <div class="panel-actions">
        <button @click="resetPlanes">Restablecer</button>
        <button class="primary" @click="saveConfiguration">Guardar configuración</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useViewerStore } from '../stores/viewerStore';
import { api } from '../services/api';
import { X } from 'lucide-vue-next';

const store = useViewerStore();
const axes = [
  { key: 'x' as const, description: 'Corte transversal' },
  { key: 'y' as const, description: 'Corte vertical' },
  { key: 'z' as const, description: 'Corte longitudinal' }
];
const minBounds = computed(() => {
  const bb = store.currentVersion?.bounding_box;
  return { x: bb?.min?.[0] ?? -5000, y: bb?.min?.[1] ?? -5000, z: bb?.min?.[2] ?? -5000 };
});
const maxBounds = computed(() => {
  const bb = store.currentVersion?.bounding_box;
  return { x: bb?.max?.[0] ?? 5000, y: bb?.max?.[1] ?? 5000, z: bb?.max?.[2] ?? 5000 };
});

function resetPlanes() {
  store.clippingPlanes.x = { enabled: false, position: 0, inverted: false };
  store.clippingPlanes.y = { enabled: false, position: 0, inverted: false };
  store.clippingPlanes.z = { enabled: false, position: 0, inverted: false };
}

async function saveConfiguration() {
  if (!store.currentVersion) return;
  const name = prompt('Nombre de la sección de corte:', `Sección ${new Date().toLocaleTimeString()}`);
  if (!name) return;
  try {
    await api.saveClippingConfig({ model_version: store.currentVersion.id, name, planes: store.clippingPlanes });
    alert('Configuración de corte guardada correctamente.');
  } catch (err: any) {
    alert(`Error al guardar: ${err.message}`);
  }
}
</script>

<style scoped>
.tool-panel { position: absolute; top: 18px; right: 158px; width: 320px; background: #fff; border: 1px solid var(--border-color); border-radius: 13px; box-shadow: 0 12px 36px rgba(23, 43, 60, .15); z-index: 15; overflow: hidden; }
.panel-header { padding: 14px 16px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; }
.panel-eyebrow { color: #8494a3; font-size: 9px; letter-spacing: 1px; font-weight: 800; }
.panel-header h4 { margin-top: 2px; font-size: 14px; color: var(--text-main); font-weight: 650; }
.close-btn { width: 30px; height: 30px; padding: 0; border: 0; background: transparent; color: var(--text-muted); }
.panel-body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 9px; }
.plane-row { display: flex; flex-direction: column; gap: 9px; padding: 10px; border: 1px solid var(--border-color); border-radius: 9px; background: #fbfcfd; }
.plane-title { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 12px; }
.plane-title label { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; cursor: pointer; }
.plane-title label span { width: 100%; margin-left: 22px; margin-top: -4px; color: var(--text-muted); font-size: 10px; }
.mini-btn { padding: 4px 8px; font-size: 10px; }
.slider-box { display: flex; align-items: center; gap: 8px; }
.slider-box input[type="range"] { flex: 1; accent-color: var(--primary-blue); padding: 0; }
.pos-val { width: 66px; text-align: right; color: var(--text-muted); font-size: 10px; }
.panel-actions { display: flex; justify-content: space-between; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border-color); }
.panel-actions button { padding: 7px 9px; font-size: 10px; }
@media (max-width: 760px) { .tool-panel { right: 124px; width: min(320px, calc(100vw - 150px)); } }
</style>
