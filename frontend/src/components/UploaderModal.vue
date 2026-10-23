<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-dialog">
      <div class="modal-header">
        <div><span class="modal-kicker">GESTIÓN DE ACTIVOS DIGITALES</span><h3>Cargar modelo 3D</h3></div>
        <button class="close-btn" @click="$emit('close')" :disabled="isUploading" title="Cerrar" aria-label="Cerrar"><X :size="18" /></button>
      </div>

      <div class="modal-body">
        <div v-if="uploadError" class="upload-error" role="alert">{{ uploadError }}</div>
        <!-- Paso 1: Selección de archivo -->
        <div v-if="!session" class="select-step">
          <p class="step-desc">
            Sube archivos <strong>.rvm</strong> (AVEVA PDMS) o <strong>.udatasmith</strong> con sus paquetes asociados.
            El sistema procesa bloques de hasta <strong>5 GB</strong> mediante carga reanudable e integridad SHA-256.
          </p>

          <div
            class="dropzone"
            :class="{ active: isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
          >
            <input
              type="file"
              ref="fileInputRef"
              @change="onFileSelected"
              accept=".rvm,.udatasmith,.zip"
              style="display: none"
            />
            <div class="drop-icon"><UploadCloud :size="27" /></div>
            <div class="drop-title">Arrastra tu archivo CAD aquí o selecciónalo desde tu equipo</div>
            <div class="drop-formats">Formatos permitidos: .rvm, .udatasmith, .zip (hasta 5 GB)</div>
            <button class="primary" @click="fileInputRef?.click()">Seleccionar archivo</button>
          </div>

          <div v-if="selectedFile" class="selected-file-card">
            <div class="file-details">
              <strong>{{ selectedFile.name }}</strong>
              <span>{{ formatBytes(selectedFile.size) }}</span>
            </div>
            <button class="primary" @click="startChunkedUpload">Iniciar carga</button>
          </div>
        </div>

        <!-- Paso 2: Progreso de subida por bloques -->
        <div v-else class="progress-step">
          <div class="session-info">
            <div class="info-row">
              <span class="lbl">Archivo:</span>
              <span class="val">{{ session.file_name }}</span>
            </div>
            <div class="info-row">
              <span class="lbl">Tamaño total:</span>
              <span class="val">{{ formatBytes(session.file_size) }}</span>
            </div>
            <div class="info-row">
              <span class="lbl">Bloques:</span>
              <span class="val">{{ session.uploaded_chunks.length }} / {{ session.total_chunks }}</span>
            </div>
            <div class="info-row">
              <span class="lbl">Estado:</span>
              <span class="val badge" :class="session.status.toLowerCase()">{{ labelForStatus(session.status) }}</span>
            </div>
          </div>

          <!-- Barra de progreso -->
          <div v-if="!conversionJob" class="progress-bar-container">
            <div class="progress-bar-fill" :style="{ width: `${progressPercentage}%` }"></div>
          </div>
          <div v-if="!conversionJob" class="progress-meta">
            <span>{{ progressPercentage }}% completado</span>
            <span v-if="isCompleting">Ensamblando archivo y preparando la conversión...</span>
            <span v-else-if="currentChunkIndex >= 0 && isUploading">Subiendo bloque {{ currentChunkIndex + 1 }} de {{ session?.total_chunks }}...</span>
          </div>

          <!-- Proceso de conversión -->
          <div v-if="conversionJob" class="pipeline-status">
            <h4>Proceso de conversión</h4>
            <div class="conversion-progress">
              <div class="conversion-progress-meta">
                <span>{{ conversionJob.progress_message }}</span>
                <strong>{{ conversionJob.progress_percentage }}%</strong>
              </div>
              <div class="conversion-progress-track" role="progressbar"
                :aria-valuenow="conversionJob.progress_percentage" aria-valuemin="0" aria-valuemax="100">
                <div class="conversion-progress-fill" :style="{ width: `${conversionJob.progress_percentage}%` }"></div>
              </div>
              <small>Avance estimado según la etapa del procesamiento</small>
            </div>
            <div class="pipeline-stepper">
              <div
                v-for="step in pipelineSteps"
                :key="step"
                class="step-badge"
                :class="{
                  active: conversionJob.status === step,
                  done: isStepCompleted(step),
                  failed: conversionJob.status === 'FAILED' && step === 'FAILED'
                }"
              >
                {{ labelForStep(step) }}
              </div>
            </div>

            <div v-if="conversionJob.status === 'READY'" class="ready-alert">
              <CheckCircle2 :size="18" /> Conversión completada. El modelo está listo para abrir.
              <button class="primary" @click="loadFinishedModel">Abrir en Visor</button>
            </div>

            <div v-if="conversionJob.status === 'FAILED'" class="error-alert">
              <AlertTriangle :size="17" /> Error en la conversión: {{ conversionJob.error_message }}
              <button @click="retryConversion">Reintentar</button>
            </div>
            <div v-if="conversionJob.status === 'CANCELLED'" class="cancelled-alert">
              Conversión detenida. Puedes cerrar esta ventana.
            </div>
            <div v-if="canCancelConversion" class="modal-actions">
              <button class="cancel-conversion" :disabled="isCancelling" @click="cancelConversion">
                {{ isCancelling ? 'Deteniendo…' : 'Detener conversión' }}
              </button>
            </div>
          </div>

          <div class="modal-actions" v-if="isUploading && !isCompleting">
            <button @click="cancelUpload">Cancelar carga</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { AlertTriangle, CheckCircle2, UploadCloud, X } from 'lucide-vue-next';
import { useViewerStore } from '../stores/viewerStore';
import { api } from '../services/api';
import type { UploadSessionDetail, ConversionJob } from '../types';

const emit = defineEmits(['close']);
const store = useViewerStore();

const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const isDragging = ref(false);
const uploadError = ref('');

const session = ref<UploadSessionDetail | null>(null);
const isUploading = ref(false);
const isCompleting = ref(false);
const currentChunkIndex = ref(-1);
const progressPercentage = ref(0);
const conversionJob = ref<ConversionJob | null>(null);
const isCancelling = ref(false);

const CHUNK_SIZE = 10 * 1024 * 1024; // 10 MB por bloque

const pipelineSteps = ['RECEIVED', 'VALIDATING', 'QUEUED', 'PROCESSING', 'VERIFYING', 'READY'];
const canCancelConversion = computed(() => !!conversionJob.value?.can_cancel &&
  !['READY', 'FAILED', 'CANCELLED'].includes(conversionJob.value.status));

function isStepCompleted(step: string): boolean {
  if (!conversionJob.value) return false;
  const currentIdx = pipelineSteps.indexOf(conversionJob.value.status);
  const stepIdx = pipelineSteps.indexOf(step);
  return currentIdx > stepIdx;
}

function labelForStep(step: string): string {
  const labels: Record<string, string> = {
    RECEIVED: 'Recibido', VALIDATING: 'Validando', QUEUED: 'En cola',
    PROCESSING: 'Procesando', VERIFYING: 'Verificando', READY: 'Listo', CANCELLED: 'Cancelado'
  };
  return labels[step] || step;
}

function labelForStatus(status: string): string {
  const labels: Record<string, string> = {
    INITIALIZED: 'Iniciada', UPLOADING: 'Subiendo', ASSEMBLING: 'Ensamblando',
    COMPLETED: 'Completada', CANCELLED: 'Cancelada', FAILED: 'Fallida', EXPIRED: 'Expirada'
  };
  return labels[status] || status;
}

function onDrop(e: DragEvent) {
  isDragging.value = false;
  if (e.dataTransfer?.files.length) {
    selectedFile.value = e.dataTransfer.files[0];
  }
}

function onFileSelected(e: Event) {
  const target = e.target as HTMLInputElement;
  if (target.files?.length) {
    selectedFile.value = target.files[0];
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

async function startChunkedUpload() {
  uploadError.value = '';
  if (!selectedFile.value) return;
  if (!store.currentProject) {
    uploadError.value = store.errorMessage
      ? `No se pudo conectar con el servidor: ${store.errorMessage}`
      : 'Selecciona un proyecto para poder cargar el archivo.';
    return;
  }
  isUploading.value = true;
  progressPercentage.value = 0;

  try {
    // 1. Inicializar sesión en backend
    const file = selectedFile.value;
    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;

    const newSession = await api.initUpload({
      project_id: store.currentProject.id,
      file_name: file.name,
      file_size: file.size,
      file_type: ext,
      chunk_size: CHUNK_SIZE
    });

    session.value = newSession;

    // 2. Subir bloques secuencialmente para cuidar la memoria
    const totalChunks = newSession.total_chunks;
    for (let i = 0; i < totalChunks; i++) {
      if (!isUploading.value) break; // Cancelado

      currentChunkIndex.value = i;
      const start = i * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunkBlob = file.slice(start, end);

      const res = await api.uploadChunk(newSession.id, i, chunkBlob);
      progressPercentage.value = res.progress_percentage;
      if (session.value) {
        session.value = {
          ...session.value,
          uploaded_chunks: [...session.value.uploaded_chunks, i],
          progress_percentage: res.progress_percentage,
          status: 'UPLOADING'
        };
      }
    }

    if (!isUploading.value) return;

    // 3. Completar y ensamblar en backend
    isCompleting.value = true;
    if (session.value) session.value = { ...session.value, status: 'ASSEMBLING' };
    const compRes = await api.completeUpload(newSession.id);
    session.value = compRes.session;
    progressPercentage.value = 100;
    isUploading.value = false;
    isCompleting.value = false;

    // 4. Consultar el estado de la conversión
    pollConversionJob(compRes.conversion_job_id);
  } catch (err: any) {
    uploadError.value = `No se pudo completar la carga: ${err.message}`;
    isUploading.value = false;
    isCompleting.value = false;
  }
}

async function pollConversionJob(jobId: string) {
  const poll = async () => {
    try {
      const job = await api.getJob(jobId);
      conversionJob.value = job;
      if (job.status === 'READY' || job.status === 'FAILED' || job.status === 'CANCELLED') {
        clearInterval(interval);
        if (job.status === 'READY') {
          // Recargar lista de assets del proyecto
          if (store.currentProject) {
            await store.selectProject(store.currentProject);
          }
        }
      }
    } catch (err: any) {
      clearInterval(interval);
      uploadError.value = `No se pudo consultar el estado de conversión: ${err.message}`;
    }
  };
  const interval = setInterval(poll, 1500);
  await poll();
}

async function loadFinishedModel() {
  if (conversionJob.value?.model_version_id) {
    try {
      await store.loadModelVersion(conversionJob.value.model_version_id);
      if (!store.errorMessage) emit('close');
      else uploadError.value = `El archivo se convirtió, pero no se pudo abrir: ${store.errorMessage}`;
    } catch (err: any) {
      uploadError.value = `El archivo se convirtió, pero no se pudo abrir: ${err.message}`;
    }
  }
}

async function cancelUpload() {
  if (session.value && !isCompleting.value) {
    isUploading.value = false;
    await api.cancelUpload(session.value.id);
    session.value = null;
    selectedFile.value = null;
  }
}

async function retryConversion() {
  if (conversionJob.value) {
    await api.retryJob(conversionJob.value.id);
    pollConversionJob(conversionJob.value.id);
  }
}

async function cancelConversion() {
  if (!conversionJob.value || isCancelling.value) return;
  isCancelling.value = true;
  try {
    conversionJob.value = await api.cancelJob(conversionJob.value.id);
  } catch (err: any) {
    uploadError.value = `No se pudo detener la conversión: ${err.message}`;
  } finally {
    isCancelling.value = false;
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(17, 39, 57, .48);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-dialog {
  background: #FFFFFF;
  border-radius: 16px;
  width: 620px;
  max-width: 90vw;
  max-height: 90vh;
  box-shadow: 0 24px 70px rgba(10, 28, 43, .24);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(180deg, #fff, #fbfcfd);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-kicker { display: block; color: #8494a3; font-size: 9px; letter-spacing: 1px; font-weight: 800; margin-bottom: 3px; }

.modal-header h3 {
  font-size: 17px;
  color: var(--primary-blue);
  font-weight: 600;
}

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.upload-error { margin: 0 20px 12px; padding: 10px 12px; border: 1px solid #f2c4bf; border-radius: 8px; color: #9d3930; background: #fff4f2; font-size: 12px; line-height: 1.5; }

.step-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
  line-height: 1.5;
}

.dropzone {
  border: 1.5px dashed #c5d3de;
  border-radius: 13px;
  padding: 40px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background: linear-gradient(180deg, #fbfdfe, #f5f9fb);
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropzone.active {
  border-color: var(--primary-blue);
  background: var(--primary-blue-light);
}

.dropzone:hover { border-color: #8eafc7; background: #f1f7fa; }

.drop-icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: var(--primary-blue);
  background: #e8f1f7;
}

.drop-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-main);
}

.drop-formats {
  font-size: 11px;
  color: var(--text-muted);
}

.selected-file-card {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-details span {
  font-size: 11px;
  color: var(--text-muted);
}

.session-info {
  background: var(--bg-main);
  padding: 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.lbl {
  color: var(--text-muted);
}

.val.badge {
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.val.badge.uploading { background: #E0F2FE; color: #0369A1; }
.val.badge.completed { background: #DCFCE7; color: #15803D; }
.val.badge.failed { background: #FEE2E2; color: #B91C1C; }

.progress-bar-container {
  height: 8px;
  background: #E2E8F0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar-fill {
  height: 100%;
  background: var(--primary-blue);
  transition: width 0.2s ease;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
}

.pipeline-status {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.pipeline-status h4 {
  font-size: 12px;
  margin-bottom: 10px;
  color: var(--text-muted);
}

.conversion-progress { margin: 0 0 14px; }
.conversion-progress-meta { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 7px; color: var(--text-main); font-size: 11px; }
.conversion-progress-meta span { line-height: 1.45; }
.conversion-progress-meta strong { color: var(--primary-blue); font-size: 12px; white-space: nowrap; }
.conversion-progress-track { height: 8px; overflow: hidden; border-radius: 99px; background: #e7edf2; }
.conversion-progress-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, #234b7c, #4f82b4); transition: width .45s ease; }
.conversion-progress small { display: block; margin-top: 6px; color: var(--text-muted); font-size: 10px; }

.pipeline-stepper {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.step-badge {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #F1F5F9;
  color: #64748B;
  border: 1px solid #E2E8F0;
}

.step-badge.active {
  background: #DBEAFE;
  color: #1E40AF;
  border-color: #93C5FD;
  font-weight: 600;
}

.step-badge.done {
  background: #DCFCE7;
  color: #166534;
  border-color: #86EFAC;
}

.step-badge.failed {
  background: #FEE2E2;
  color: #991B1B;
  border-color: #FCA5A5;
}

.ready-alert {
  margin-top: 12px;
  background: #F0FDF4;
  border: 1px solid #BBF7D0;
  padding: 10px 14px;
  border-radius: 9px;
  color: #166534;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.error-alert {
  margin-top: 12px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  padding: 10px 14px;
  border-radius: 9px;
  color: #991B1B;
  font-size: 12px;
}

.cancelled-alert {
  margin-top: 12px;
  padding: 10px 14px;
  border: 1px solid #d8e0e8;
  border-radius: 9px;
  color: #526477;
  background: #f4f7f9;
  font-size: 12px;
}

.cancel-conversion {
  color: #9d3930;
  border-color: #efc4bf;
  background: #fff8f7;
}

.ready-alert svg, .error-alert svg { flex: 0 0 auto; }
.ready-alert { gap: 9px; }
.error-alert { display: flex; align-items: center; gap: 8px; }

@media (max-width: 620px) {
  .modal-dialog { width: calc(100vw - 24px); max-width: none; }
  .modal-header, .modal-body { padding: 16px; }
  .dropzone { padding: 30px 16px; }
  .selected-file-card { align-items: stretch; flex-direction: column; gap: 12px; }
}

.modal-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

