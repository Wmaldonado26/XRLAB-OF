<template>
  <section class="tool-panel">
    <div class="panel-header">
      <div><span class="panel-eyebrow">ANÁLISIS</span><h4>Mediciones</h4></div>
      <button class="close-btn" @click="store.activeTool = 'navigate'" title="Cerrar mediciones" aria-label="Cerrar mediciones"><X :size="17" /></button>
    </div>
    <div class="panel-body">
      <div class="instruction"><Ruler :size="16" /> Selecciona dos puntos del modelo para medir la distancia.</div>
      <div v-if="store.measurements.length" class="measure-list">
        <div v-for="m in store.measurements" :key="m.id" class="measure-card">
          <div class="measure-info">
            <span class="measure-label">{{ m.label || 'Medición' }}</span>
            <strong class="measure-val">{{ formatDistance(m.distance, m.unit) }}</strong>
            <span class="measure-type">{{ m.measurement_type === 'exact_cad' ? 'Medición CAD exacta' : 'Medición aproximada' }}</span>
          </div>
          <button class="del-btn" @click="store.removeMeasurement(m.id!)" title="Eliminar medición" aria-label="Eliminar medición"><Trash2 :size="15" /></button>
        </div>
      </div>
      <div v-else class="empty-hint"><Ruler :size="19" /><span>Aún no hay mediciones</span></div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useViewerStore } from '../stores/viewerStore';
import { Ruler, Trash2, X } from 'lucide-vue-next';

const store = useViewerStore();
function formatDistance(dist: number, origUnit: string): string {
  let val = dist;
  if (origUnit === 'mm' && store.unit === 'm') val = dist / 1000;
  else if (origUnit === 'mm' && store.unit === 'in') val = dist / 25.4;
  else if (origUnit === 'm' && store.unit === 'mm') val = dist * 1000;
  return `${val.toFixed(2)} ${store.unit}`;
}
</script>

<style scoped>
.tool-panel { position: absolute; top: 18px; right: 158px; width: 320px; background: #fff; border: 1px solid var(--border-color); border-radius: 13px; box-shadow: 0 12px 36px rgba(23, 43, 60, .15); z-index: 15; overflow: hidden; }
.panel-header { padding: 14px 16px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; }
.panel-eyebrow { color: #8494a3; font-size: 9px; letter-spacing: 1px; font-weight: 800; }
.panel-header h4 { margin-top: 2px; font-size: 14px; color: var(--text-main); font-weight: 650; }
.close-btn { width: 30px; height: 30px; padding: 0; border: 0; background: transparent; color: var(--text-muted); }
.panel-body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 12px; }
.instruction { display: flex; align-items: flex-start; gap: 8px; padding: 10px; border-radius: 8px; background: #f2f7fa; color: #526b80; font-size: 11px; line-height: 1.5; }
.instruction svg { color: var(--primary-blue); flex: 0 0 auto; }
.measure-list { display: flex; flex-direction: column; gap: 8px; max-height: 260px; overflow-y: auto; }
.measure-card { display: flex; align-items: center; justify-content: space-between; background: #fbfcfd; padding: 10px 11px; border-radius: 9px; border: 1px solid var(--border-color); }
.measure-info { display: flex; flex-direction: column; gap: 3px; }
.measure-label { font-size: 10px; color: var(--text-muted); }
.measure-val { font-size: 16px; color: var(--primary-blue); }
.measure-type { font-size: 10px; color: #7b8c9b; }
.del-btn { width: 30px; height: 30px; padding: 0; border: 0; background: transparent; color: #8292a0; }
.del-btn:hover { color: var(--status-error); background: #fff0ef; }
.empty-hint { min-height: 80px; display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--text-muted); font-size: 11px; }
.empty-hint svg { color: #9aafc0; }
@media (max-width: 760px) { .tool-panel { right: 124px; width: min(320px, calc(100vw - 150px)); } }
</style>
