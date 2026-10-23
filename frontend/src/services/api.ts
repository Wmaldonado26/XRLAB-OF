import type {
  Project, ModelAsset, ModelVersion, ComponentNode,
  SavedCamera, Measurement, ClippingConfiguration,
  UploadSessionDetail, ConversionJob
} from '../types';

const API_BASE = `${import.meta.env.VITE_API_BASE || '/api/v1'}`;

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = `Error HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.error || errJson.detail || JSON.stringify(errJson);
    } catch {
      // Ignorar si no es JSON
    }
    throw new Error(errorDetail);
  }

  // Si la respuesta es de tipo blob/binary o no tiene body
  if (response.status === 204) return {} as T;
  return response.json();
}

export const api = {
  // Proyectos
  async getProjects(): Promise<{ results: Project[] }> {
    return request<{ results: Project[] }>('/projects/');
  },
  async createProject(name: string, description: string): Promise<Project> {
    return request<Project>('/projects/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description })
    });
  },

  // Modelos y Versiones
  async getAssets(projectId?: string): Promise<{ results: ModelAsset[] }> {
    const query = projectId ? `?project_id=${projectId}` : '';
    return request<{ results: ModelAsset[] }>(`/assets/${query}`);
  },
  async getVersion(versionId: string): Promise<ModelVersion> {
    return request<ModelVersion>(`/versions/${versionId}/`);
  },
  async getHierarchy(versionId: string): Promise<{ components: ComponentNode[] }> {
    const url = `${API_BASE}/versions/${versionId}/hierarchy/`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("No se pudo cargar el archivo de jerarquía");
    return res.json();
  },
  getGlbUrl(versionId: string): string {
    return `${API_BASE}/versions/${versionId}/glb/`;
  },

  // Herramientas: Cámaras
  async getSavedCameras(versionId: string): Promise<{ results: SavedCamera[] }> {
    return request<{ results: SavedCamera[] }>(`/cameras/?version_id=${versionId}`);
  },
  async saveCamera(camera: SavedCamera): Promise<SavedCamera> {
    return request<SavedCamera>('/cameras/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(camera)
    });
  },
  async deleteCamera(id: string): Promise<void> {
    await request(`/cameras/${id}/`, { method: 'DELETE' });
  },

  // Herramientas: Mediciones
  async getMeasurements(versionId: string): Promise<{ results: Measurement[] }> {
    return request<{ results: Measurement[] }>(`/measurements/?version_id=${versionId}`);
  },
  async saveMeasurement(measurement: Measurement): Promise<Measurement> {
    return request<Measurement>('/measurements/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(measurement)
    });
  },
  async deleteMeasurement(id: string): Promise<void> {
    await request(`/measurements/${id}/`, { method: 'DELETE' });
  },

  // Herramientas: Planos de corte
  async getClippingConfigs(versionId: string): Promise<{ results: ClippingConfiguration[] }> {
    return request<{ results: ClippingConfiguration[] }>(`/clippings/?version_id=${versionId}`);
  },
  async saveClippingConfig(config: ClippingConfiguration): Promise<ClippingConfiguration> {
    return request<ClippingConfiguration>('/clippings/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
  },

  // Subidas reanudables (Chunked Uploading)
  async initUpload(data: {
    project_id: string;
    file_name: string;
    file_size: number;
    file_type: string;
    chunk_size: number;
    expected_sha256?: string;
  }): Promise<UploadSessionDetail> {
    return request<UploadSessionDetail>('/uploads/initialize/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  },

  async uploadChunk(sessionId: string, chunkIndex: number, chunkBlob: Blob): Promise<{
    progress_percentage: number;
    uploaded_chunks_count: number;
    total_chunks: number;
    chunk_index: number;
  }> {
    const formData = new FormData();
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('chunk', chunkBlob, `chunk_${chunkIndex}.part`);

    const res = await fetch(`${API_BASE}/uploads/${sessionId}/chunk/`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Error subiendo bloque ${chunkIndex}`);
    }
    return res.json();
  },

  async completeUpload(sessionId: string): Promise<{
    asset_id: string;
    conversion_job_id: string;
    session: UploadSessionDetail;
  }> {
    return request<{ asset_id: string; conversion_job_id: string; session: UploadSessionDetail }>(`/uploads/${sessionId}/complete/`, {
      method: 'POST'
    });
  },

  async cancelUpload(sessionId: string): Promise<void> {
    await request(`/uploads/${sessionId}/cancel/`, { method: 'POST' });
  },

  async getUploadStatus(sessionId: string): Promise<UploadSessionDetail> {
    return request<UploadSessionDetail>(`/uploads/${sessionId}/`);
  },

  // Conversión
  async getJob(jobId: string): Promise<ConversionJob> {
    return request<ConversionJob>(`/jobs/${jobId}/`);
  },
  async retryJob(jobId: string): Promise<void> {
    await request(`/jobs/${jobId}/retry/`, { method: 'POST' });
  },
  async cancelJob(jobId: string): Promise<ConversionJob> {
    const res = await request<{ job: ConversionJob }>(`/jobs/${jobId}/cancel/`, { method: 'POST' });
    return res.job;
  }
};
