<template>
  <aside v-if="store.selectedComponent" class="properties-panel" aria-label="Propiedades del componente">
    <div class="prop-header">
      <div><span class="panel-eyebrow">INSPECCIÓN</span><h4>Propiedades</h4></div>
      <button class="close-btn" @click="store.selectNode(null)" title="Cerrar propiedades" aria-label="Cerrar propiedades"><X :size="17" /></button>
    </div>

    <div class="prop-body">
      <div class="component-heading">
        <div class="component-icon"><Box :size="19" /></div>
        <div class="component-title"><span>COMPONENTE</span><strong>{{ store.selectedComponent.name }}</strong></div>
      </div>
      <div class="prop-item">
        <span class="prop-label"><Fingerprint :size="13" /> ID estable</span>
        <span class="prop-val code">{{ store.selectedComponent.node_id }}</span>
      </div>
      <div class="prop-item">
        <span class="prop-label"><Waypoints :size="13" /> Jerarquía</span>
        <span class="prop-val code">{{ store.selectedComponent.hierarchy_path }}</span>
      </div>

      <div v-if="store.selectedComponent.attributes && Object.keys(store.selectedComponent.attributes).length" class="prop-section">
        <h5>Atributos de ingeniería</h5>
        <div class="attr-table">
          <div v-for="(val, key) in store.selectedComponent.attributes" :key="key" class="attr-row">
            <span class="attr-key">{{ key }}</span><span class="attr-val">{{ val }}</span>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useViewerStore } from '../stores/viewerStore';
import { Box, Fingerprint, Waypoints, X } from 'lucide-vue-next';

const store = useViewerStore();
</script>

<style scoped>
.properties-panel { position: absolute; bottom: 18px; right: 18px; width: 320px; max-height: min(440px, calc(100% - 36px)); background: #fff; border: 1px solid var(--border-color); border-radius: 13px; box-shadow: 0 12px 36px rgba(23, 43, 60, .15); display: flex; flex-direction: column; z-index: 15; overflow: hidden; }
.prop-header { padding: 14px 16px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; }
.panel-eyebrow { color: #8494a3; font-size: 9px; letter-spacing: 1px; font-weight: 800; }
.prop-header h4 { margin-top: 2px; font-size: 14px; color: var(--text-main); font-weight: 650; }
.close-btn { width: 30px; height: 30px; padding: 0; border: 0; background: transparent; color: var(--text-muted); }
.prop-body { padding: 14px 16px 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
.component-heading { display: flex; align-items: center; gap: 11px; padding: 11px; border: 1px solid #e3edf4; background: #f5f9fc; border-radius: 9px; }
.component-icon { height: 36px; width: 36px; border-radius: 9px; display: grid; place-items: center; color: var(--primary-blue); background: #e2eef6; flex: 0 0 auto; }
.component-title { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.component-title span { color: #8293a4; font-size: 9px; font-weight: 800; letter-spacing: .8px; }
.component-title strong { font-size: 13px; overflow-wrap: anywhere; }
.prop-item { display: flex; flex-direction: column; gap: 5px; }
.prop-label { display: flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .45px; color: var(--text-muted); }
.prop-val { font-size: 12px; overflow-wrap: anywhere; }
.prop-val.code { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; background: #f4f7f9; border: 1px solid #e8edf1; padding: 7px 8px; border-radius: 6px; font-size: 10px; color: #43576a; }
.prop-section { border-top: 1px solid var(--border-color); padding-top: 12px; }
.prop-section h5 { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .6px; margin-bottom: 8px; }
.attr-table { display: flex; flex-direction: column; gap: 6px; }
.attr-row { display: flex; justify-content: space-between; gap: 12px; font-size: 11px; border-bottom: 1px solid #f1f4f6; padding: 4px 0; }
.attr-key { color: var(--text-muted); }
.attr-val { font-weight: 600; text-align: right; overflow-wrap: anywhere; }
</style>
