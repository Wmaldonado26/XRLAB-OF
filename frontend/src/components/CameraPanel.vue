<template>
  <section class="tool-panel">
    <div class="panel-header">
      <div><span class="panel-eyebrow">NAVEGACIÓN</span><h4>Vistas guardadas</h4></div>
      <button class="close-btn" @click="store.activeTool = 'navigate'" title="Cerrar vistas" aria-label="Cerrar vistas"><X :size="17" /></button>
    </div>
    <div class="panel-body">
      <button class="primary add-btn" @click="saveCurrentView"><Camera :size="15" /> Guardar vista actual</button>
      <div v-if="store.savedCameras.length" class="camera-list">
        <div v-for="cam in store.savedCameras" :key="cam.id" class="camera-card">
          <button class="camera-title" @click="applyCamera(cam)">
            <span class="cam-icon"><Camera :size="15" /></span><span class="cam-name">{{ cam.name }}</span><ChevronRight :size="15" class="cam-open" />
          </button>
          <button class="del-btn" @click="store.removeSavedCamera(cam.id!)" title="Eliminar vista" aria-label="Eliminar vista"><Trash2 :size="14" /></button>
        </div>
      </div>
      <div v-else class="empty-hint"><Camera :size="20" /><span>No hay vistas guardadas para este modelo.</span></div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useViewerStore } from '../stores/viewerStore';
import { Camera, ChevronRight, Trash2, X } from 'lucide-vue-next';

const emit = defineEmits(['restore-camera', 'capture-camera']);
const store = useViewerStore();

function saveCurrentView() {
  if (!store.currentVersion) return;
  const name = prompt('Nombre de la vista:', `Vista ${store.savedCameras.length + 1}`);
  if (!name) return;
  emit('capture-camera', (cameraState: any) => {
    store.addSavedCamera({
      model_version: store.currentVersion!.id,
      name,
      position: cameraState.position,
      target: cameraState.target,
      up: cameraState.up,
      fov: cameraState.fov,
      projection: cameraState.projection
    });
  });
}

function applyCamera(cam: any) { emit('restore-camera', cam); }
</script>

<style scoped>
.tool-panel { position: absolute; top: 18px; right: 158px; width: 320px; background: #fff; border: 1px solid var(--border-color); border-radius: 13px; box-shadow: 0 12px 36px rgba(23, 43, 60, .15); z-index: 15; overflow: hidden; }
.panel-header { padding: 14px 16px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; }
.panel-eyebrow { color: #8494a3; font-size: 9px; letter-spacing: 1px; font-weight: 800; }
.panel-header h4 { margin-top: 2px; font-size: 14px; color: var(--text-main); font-weight: 650; }
.close-btn { width: 30px; height: 30px; padding: 0; border: 0; background: transparent; color: var(--text-muted); }
.panel-body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 12px; }
.add-btn { width: 100%; justify-content: center; min-height: 38px; }
.camera-list { display: flex; flex-direction: column; gap: 7px; max-height: 260px; overflow-y: auto; }
.camera-card { display: flex; align-items: center; gap: 3px; padding: 5px 6px 5px 9px; border-radius: 9px; border: 1px solid var(--border-color); background: #fbfcfd; }
.camera-card:hover { background: #f1f7fa; border-color: var(--primary-blue-border); }
.camera-title { min-width: 0; flex: 1; display: flex; align-items: center; justify-content: flex-start; gap: 9px; border: 0; padding: 5px 0; background: transparent; text-align: left; }
.cam-icon { width: 29px; height: 29px; display: grid; place-items: center; border-radius: 7px; color: var(--primary-blue); background: #e6f0f6; }
.cam-name { flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 12px; font-weight: 600; }
.cam-open { color: #93a1ad; }
.del-btn { width: 30px; height: 30px; padding: 0; border: 0; background: transparent; color: #8292a0; }
.del-btn:hover { color: var(--status-error); background: #fff0ef; }
.empty-hint { min-height: 80px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--text-muted); font-size: 11px; text-align: center; }
.empty-hint svg { color: #9aafc0; }
@media (max-width: 760px) { .tool-panel { right: 124px; width: min(320px, calc(100vw - 150px)); } }
</style>
