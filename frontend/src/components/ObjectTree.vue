<template>
  <aside class="object-tree-panel" aria-label="Árbol de componentes">
    <div class="panel-header">
      <div class="panel-title-row">
        <div>
          <span class="panel-eyebrow">ESTRUCTURA DEL MODELO</span>
          <h3>Árbol de componentes</h3>
        </div>
        <span class="count-badge" :title="`${store.filteredComponents.length.toLocaleString()} componentes`">{{ store.filteredComponents.length.toLocaleString() }}</span>
      </div>
      <label class="search-box">
        <Search :size="15" aria-hidden="true" />
        <input v-model="store.searchQuery" type="search" placeholder="Buscar componente o ID..." />
      </label>
      <button @click="store.showAll" class="show-all-btn" title="Mostrar todos los objetos">
        <Eye :size="14" /> Mostrar todo
      </button>
    </div>

    <div class="tree-content">
      <div v-if="!store.currentVersion" class="empty-state">
        <div class="empty-icon"><Boxes :size="22" /></div>
        <strong>Sin modelo cargado</strong>
        <span>Selecciona un modelo para explorar su estructura.</span>
      </div>
      <div v-else-if="store.filteredComponents.length === 0" class="empty-state">
        <div class="empty-icon"><Search :size="20" /></div>
        <strong>No hay resultados</strong>
        <span>No se encontraron componentes con ese nombre o ID.</span>
      </div>
      <div v-else class="node-list">
        <div
          v-for="node in visibleComponents"
          :key="node.node_id"
          class="node-item"
          :class="{
            selected: store.selectedNodeId === node.node_id,
            isolated: store.isolatedNodeId === node.node_id,
            hidden: store.hiddenNodeIds.has(node.node_id)
          }"
          :title="node.hierarchy_path"
          @click="store.selectNode(node.node_id)"
        >
          <Box :size="15" class="node-icon" aria-hidden="true" />
          <span class="node-name">{{ node.name }}</span>
          <div class="node-controls" @click.stop>
            <button
              class="icon-btn"
              @click="store.toggleVisibility(node.node_id)"
              :title="store.hiddenNodeIds.has(node.node_id) ? 'Mostrar componente' : 'Ocultar componente'"
              :aria-label="store.hiddenNodeIds.has(node.node_id) ? 'Mostrar componente' : 'Ocultar componente'"
            >
              <EyeOff v-if="store.hiddenNodeIds.has(node.node_id)" :size="15" />
              <Eye v-else :size="15" />
            </button>
            <button
              class="icon-btn"
              :class="{ active: store.isolatedNodeId === node.node_id }"
              @click="store.isolateComponent(node.node_id)"
              title="Aislar componente"
              aria-label="Aislar componente"
            >
              <Focus :size="15" />
            </button>
          </div>
        </div>
        <div v-if="visibleCount < store.filteredComponents.length" class="tree-more">
          <span>Mostrando {{ visibleCount.toLocaleString() }} de {{ store.filteredComponents.length.toLocaleString() }}</span>
          <button class="load-more-btn" @click="showMore">Cargar siguientes {{ PAGE_SIZE.toLocaleString() }}</button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useViewerStore } from '../stores/viewerStore';
import { Box, Boxes, Eye, EyeOff, Focus, Search } from 'lucide-vue-next';

const store = useViewerStore();
const PAGE_SIZE = 300;
const visibleCount = ref(PAGE_SIZE);
const visibleComponents = computed(() => store.filteredComponents.slice(0, visibleCount.value));

watch(() => store.searchQuery, () => { visibleCount.value = PAGE_SIZE; });
watch(() => store.currentVersion?.id, () => { visibleCount.value = PAGE_SIZE; });

function showMore() {
  visibleCount.value = Math.min(visibleCount.value + PAGE_SIZE, store.filteredComponents.length);
}
</script>

<style scoped>
.object-tree-panel {
  width: var(--sidebar-width);
  height: calc(100vh - var(--header-height));
  background: #fff;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.panel-header { padding: 19px 16px 13px; border-bottom: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 12px; }
.panel-title-row { display: flex; align-items: center; justify-content: space-between; }
.panel-title-row h3 { margin-top: 3px; font-size: 14px; font-weight: 650; color: var(--text-main); }
.panel-eyebrow { font-size: 9px; letter-spacing: 1px; font-weight: 800; color: #8293a4; }
.count-badge { min-width: 26px; text-align: center; background: #edf3f7; border: 1px solid var(--border-color); font-size: 11px; padding: 3px 7px; border-radius: 20px; color: var(--text-muted); }
.search-box { display: flex; align-items: center; gap: 8px; padding: 0 10px; border: 1px solid var(--border-color); border-radius: 8px; color: #8798a8; background: #fbfcfd; }
.search-box:focus-within { border-color: var(--border-focus); box-shadow: 0 0 0 3px #2474a81a; }
.search-box input { width: 100%; border: 0; padding: 9px 0; background: transparent; box-shadow: none; }
.search-box input:focus { box-shadow: none; }
.show-all-btn { align-self: flex-start; border-color: transparent; background: transparent; color: var(--primary-blue); padding: 4px 2px; font-size: 11px; }
.tree-content { flex: 1; overflow-y: auto; padding: 8px 0; }
.empty-state { min-height: 220px; padding: 45px 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 9px; text-align: center; color: var(--text-muted); font-size: 12px; }
.empty-state strong { color: var(--text-main); font-size: 13px; }
.empty-icon { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 13px; background: var(--primary-blue-light); color: var(--primary-blue); margin-bottom: 3px; }
.node-list { display: flex; flex-direction: column; }
.tree-more { display: flex; flex-direction: column; align-items: center; gap: 9px; padding: 16px 12px; color: var(--text-muted); font-size: 11px; }
.load-more-btn { padding: 7px 12px; border: 1px solid var(--border-color); border-radius: 7px; background: #fff; color: var(--primary-blue); font-size: 11px; }
.load-more-btn:hover { background: var(--primary-blue-light); }
.node-item { min-height: 40px; display: flex; align-items: center; gap: 9px; padding: 6px 11px 6px 14px; cursor: pointer; border-bottom: 1px solid #f2f5f7; border-left: 3px solid transparent; transition: background .12s ease; }
.node-item:hover { background: #f6f9fb; }
.node-item.selected { background: var(--primary-blue-light); border-left-color: var(--primary-blue); color: var(--primary-blue); font-weight: 600; }
.node-item.hidden { opacity: .48; }
.node-item.isolated { background: #fff7e8; border-left-color: #c87920; }
.node-icon { color: #7590a6; flex: 0 0 auto; }
.node-name { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; }
.node-controls { display: flex; gap: 2px; opacity: .55; }
.node-item:hover .node-controls, .node-item.selected .node-controls { opacity: 1; }
.icon-btn { width: 28px; height: 28px; padding: 5px; border: 0; background: transparent; color: #77899a; border-radius: 6px; }
.icon-btn:hover { background: #e5edf3; }
.icon-btn.active { background: #ffebc7; color: #a56210; }
</style>
