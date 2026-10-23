import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type {
  Project, ModelAsset, ModelVersion, ComponentNode,
  Measurement, SavedCamera, PlaneConfig
} from '../types';
import { api } from '../services/api';

export const useViewerStore = defineStore('viewer', () => {
  // Estado de proyectos y modelos
  const projects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const assets = ref<ModelAsset[]>([]);
  const currentAsset = ref<ModelAsset | null>(null);
  const currentVersion = ref<ModelVersion | null>(null);

  // Jerarquía y selección
  const components = ref<ComponentNode[]>([]);
  const selectedNodeId = ref<string | null>(null);
  const hiddenNodeIds = ref<Set<string>>(new Set());
  const isolatedNodeId = ref<string | null>(null);
  const searchQuery = ref('');

  // Herramientas activas
  const activeTool = ref<'navigate' | 'measure' | 'clip' | 'camera'>('navigate');
  const unit = ref<'mm' | 'm' | 'in'>('mm');

  // Mediciones
  const measurements = ref<Measurement[]>([]);
  const isMeasuring = ref(false);
  const currentMeasureStart = ref<[number, number, number] | null>(null);

  // Planos de corte
  const clippingPlanes = ref<{
    x: PlaneConfig;
    y: PlaneConfig;
    z: PlaneConfig;
  }>({
    x: { enabled: false, position: 0, inverted: false },
    y: { enabled: false, position: 0, inverted: false },
    z: { enabled: false, position: 0, inverted: false },
  });

  // Cámaras guardadas
  const savedCameras = ref<SavedCamera[]>([]);

  // Estados de carga
  const isLoadingModel = ref(false);
  const loadingProgress = ref(0);
  const errorMessage = ref<string | null>(null);

  // Computed: lista filtrada de componentes
  const filteredComponents = computed(() => {
    if (!searchQuery.value.trim()) return components.value;
    const q = searchQuery.value.toLowerCase();
    return components.value.filter(c =>
      c.name.toLowerCase().includes(q) || c.node_id.toLowerCase().includes(q)
    );
  });

  const selectedComponent = computed(() => {
    if (!selectedNodeId.value) return null;
    return components.value.find(c => c.node_id === selectedNodeId.value) || null;
  });

  // Acciones
  async function loadProjects() {
    try {
      const res = await api.getProjects();
      projects.value = res.results;
      if (projects.value.length > 0 && !currentProject.value) {
        await selectProject(projects.value[0]);
      }
    } catch (err: any) {
      errorMessage.value = err.message;
    }
  }

  async function selectProject(project: Project) {
    currentProject.value = project;
    try {
      const res = await api.getAssets(project.id);
      assets.value = res.results;
      if (assets.value.length > 0) {
        await selectAsset(assets.value[0]);
      } else {
        currentAsset.value = null;
        currentVersion.value = null;
        components.value = [];
      }
    } catch (err: any) {
      errorMessage.value = err.message;
    }
  }

  async function selectAsset(asset: ModelAsset) {
    currentAsset.value = asset;
    const version = asset.latest_version || (asset.versions && asset.versions[0]);
    if (version) {
      await loadModelVersion(version.id);
    }
  }

  async function loadModelVersion(versionId: string) {
    isLoadingModel.value = true;
    loadingProgress.value = 10;
    errorMessage.value = null;
    selectedNodeId.value = null;
    hiddenNodeIds.value.clear();
    isolatedNodeId.value = null;

    try {
      const version = await api.getVersion(versionId);
      currentVersion.value = version;
      loadingProgress.value = 40;

      // Cargar Jerarquía
      try {
        const hierarchyData = await api.getHierarchy(versionId);
        components.value = hierarchyData.components || [];
      } catch {
        components.value = [];
      }
      loadingProgress.value = 60;

      // Cargar Cámaras y Mediciones
      const [cams, meas] = await Promise.all([
        api.getSavedCameras(versionId),
        api.getMeasurements(versionId)
      ]);
      savedCameras.value = cams.results;
      measurements.value = meas.results;
      loadingProgress.value = 100;
    } catch (err: any) {
      errorMessage.value = `Error cargando modelo: ${err.message}`;
    } finally {
      isLoadingModel.value = false;
    }
  }

  function toggleVisibility(nodeId: string) {
    if (hiddenNodeIds.value.has(nodeId)) {
      hiddenNodeIds.value.delete(nodeId);
    } else {
      hiddenNodeIds.value.add(nodeId);
    }
  }

  function isolateComponent(nodeId: string) {
    if (isolatedNodeId.value === nodeId) {
      isolatedNodeId.value = null;
    } else {
      isolatedNodeId.value = nodeId;
    }
  }

  function showAll() {
    hiddenNodeIds.value.clear();
    isolatedNodeId.value = null;
  }

  function selectNode(nodeId: string | null) {
    selectedNodeId.value = nodeId;
  }

  async function addMeasurement(m: Measurement) {
    if (!currentVersion.value) return;
    try {
      const saved = await api.saveMeasurement(m);
      measurements.value.unshift(saved);
    } catch (err: any) {
      errorMessage.value = err.message;
    }
  }

  async function removeMeasurement(id: string) {
    try {
      await api.deleteMeasurement(id);
      measurements.value = measurements.value.filter(m => m.id !== id);
    } catch (err: any) {
      errorMessage.value = err.message;
    }
  }

  async function addSavedCamera(c: SavedCamera) {
    if (!currentVersion.value) return;
    try {
      const saved = await api.saveCamera(c);
      savedCameras.value.unshift(saved);
    } catch (err: any) {
      errorMessage.value = err.message;
    }
  }

  async function removeSavedCamera(id: string) {
    try {
      await api.deleteCamera(id);
      savedCameras.value = savedCameras.value.filter(c => c.id !== id);
    } catch (err: any) {
      errorMessage.value = err.message;
    }
  }

  return {
    projects,
    currentProject,
    assets,
    currentAsset,
    currentVersion,
    components,
    filteredComponents,
    selectedNodeId,
    selectedComponent,
    hiddenNodeIds,
    isolatedNodeId,
    searchQuery,
    activeTool,
    unit,
    measurements,
    isMeasuring,
    currentMeasureStart,
    clippingPlanes,
    savedCameras,
    isLoadingModel,
    loadingProgress,
    errorMessage,
    loadProjects,
    selectProject,
    selectAsset,
    loadModelVersion,
    toggleVisibility,
    isolateComponent,
    showAll,
    selectNode,
    addMeasurement,
    removeMeasurement,
    addSavedCamera,
    removeSavedCamera,
  };
});
