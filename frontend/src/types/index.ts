export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  assets_count?: number;
}

export interface ModelAsset {
  id: string;
  project: string;
  name: string;
  format: 'RVM' | 'DATASMITH';
  original_file_name: string;
  original_file_size: number;
  original_sha256: string;
  created_at: string;
  updated_at: string;
  latest_version?: ModelVersion;
  versions?: ModelVersion[];
}

export interface ModelVersion {
  id: string;
  asset: string;
  version_number: number;
  notes: string;
  is_active: boolean;
  triangle_count: number;
  vertex_count: number;
  component_count: number;
  bounding_box: {
    min: [number, number, number];
    max: [number, number, number];
    center: [number, number, number];
    dimensions: [number, number, number];
  };
  unit: string;
  glb_url: string;
  hierarchy_url: string;
  saved_cameras?: SavedCamera[];
  measurements?: Measurement[];
  clipping_configs?: ClippingConfiguration[];
  created_at: string;
}

export interface ComponentNode {
  node_id: string;
  name: string;
  hierarchy_path: string;
  attributes?: Record<string, any>;
  bounding_box?: Record<string, any>;
  visible?: boolean;
}

export interface SavedCamera {
  id?: string;
  model_version: string;
  name: string;
  position: [number, number, number];
  target: [number, number, number];
  up: [number, number, number];
  fov: number;
  projection: 'perspective' | 'orthographic';
  created_at?: string;
}

export interface Measurement {
  id?: string;
  model_version: string;
  point_a: [number, number, number];
  point_b: [number, number, number];
  distance: number;
  unit: 'mm' | 'm' | 'in';
  label: string;
  measurement_type: 'exact_cad' | 'mesh_approx';
  created_at?: string;
}

export interface PlaneConfig {
  enabled: boolean;
  position: number;
  inverted: boolean;
}

export interface ClippingConfiguration {
  id?: string;
  model_version: string;
  name: string;
  planes: {
    x: PlaneConfig;
    y: PlaneConfig;
    z: PlaneConfig;
  };
  created_at?: string;
  updated_at?: string;
}

export interface UploadSessionDetail {
  id: string;
  project: string;
  file_name: string;
  file_size: number;
  file_type: string;
  chunk_size: number;
  total_chunks: number;
  uploaded_chunks: number[];
  progress_percentage: number;
  expected_sha256: string;
  actual_sha256: string;
  status: 'INITIALIZED' | 'UPLOADING' | 'ASSEMBLING' | 'COMPLETED' | 'CANCELLED' | 'FAILED' | 'EXPIRED';
  error_message: string;
  created_at: string;
  expires_at: string;
}

export interface ConversionJob {
  id: string;
  project: string;
  model_asset: string;
  asset_name: string;
  model_version_id?: string;
  status: 'RECEIVED' | 'VALIDATING' | 'QUEUED' | 'PROCESSING' | 'VERIFYING' | 'READY' | 'FAILED' | 'CANCELLED' | 'RETRY_PENDING';
  can_cancel?: boolean;
  progress_percentage: number;
  progress_message: string;
  converter_adapter: string;
  converter_version: string;
  tolerance: number;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  retry_count: number;
  error_message?: string;
}
