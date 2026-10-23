import os
import time
import traceback
import hashlib
import json
from celery import shared_task
from django.utils import timezone
from .models import ConversionJob, JobStatus, ConversionArtifact
from .adapters import RvmConverterAdapter, DatasmithConverterAdapter
from apps.models_3d.models import ModelVersion, ModelObjectMetadata


def set_conversion_progress(job_id, percentage, message):
    ConversionJob.objects.filter(id=job_id).update(
        logs=json.dumps({
            'progress_percentage': max(0, min(100, int(percentage))),
            'progress_message': message,
        }, ensure_ascii=False)
    )

def get_file_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

@shared_task(bind=True, max_retries=3)
def run_conversion_pipeline_task(self, job_id):
    try:
        job = ConversionJob.objects.get(id=job_id)
    except ConversionJob.DoesNotExist:
        return f"Job {job_id} no encontrado."

    start_time = time.perf_counter()
    set_conversion_progress(job_id, 3, 'Preparando conversión')
    job.started_at = timezone.now()
    job.status = JobStatus.VALIDATING
    job.save(update_fields=['status', 'started_at', 'updated_at'])

    try:
        # 1. Seleccionar adaptador
        if job.converter_adapter == 'RvmConverterAdapter':
            adapter = RvmConverterAdapter()
        elif job.converter_adapter == 'DatasmithConverterAdapter':
            adapter = DatasmithConverterAdapter()
        else:
            raise ValueError(f"Adaptador de conversión desconocido: {job.converter_adapter}")

        job.converter_version = adapter.adapter_version

        # 2. Validación
        set_conversion_progress(job_id, 8, 'Validando archivo de entrada')
        adapter.validate_input(job.input_file_path)

        # 3. Procesamiento
        job.status = JobStatus.PROCESSING
        job.save(update_fields=['status', 'converter_version', 'updated_at'])
        set_conversion_progress(job_id, 20, 'Procesando geometría 3D')

        conversion_result = adapter.convert(
            input_file_path=job.input_file_path,
            output_dir=job.output_dir,
            options={
                'tolerance': job.tolerance,
                'progress_callback': lambda percentage, message: set_conversion_progress(
                    job_id, percentage, message
                ),
            }
        )

        # 4. Verificación de artefactos
        job.status = JobStatus.VERIFYING
        job.save(update_fields=['status', 'updated_at'])
        set_conversion_progress(job_id, 92, 'Verificando el GLB y sus artefactos')

        is_valid = adapter.verify_output(job.output_dir, conversion_result)
        if not is_valid:
            raise ValueError("Verificación geométrica fallida: el archivo GLB generado no es válido o está degenerado.")

        # 5. Registro de artefactos
        for art in conversion_result.get('artifacts', []):
            art_sha = get_file_sha256(art['path'])
            ConversionArtifact.objects.create(
                job=job,
                artifact_type=art['type'],
                file_path=art['path'],
                file_size=art['size'],
                sha256=art_sha
            )

        # 6. Crear o actualizar ModelVersion
        asset = job.model_asset
        current_version_count = asset.versions.count()
        new_version_num = current_version_count + 1

        model_version = ModelVersion.objects.create(
            asset=asset,
            version_number=new_version_num,
            notes=f"Generado automáticamente mediante {job.converter_adapter} ({adapter.adapter_version})",
            is_active=True,
            glb_artifact_path=conversion_result['glb_path'],
            hierarchy_index_path=conversion_result['hierarchy_json_path'],
            triangle_count=conversion_result['triangle_count'],
            vertex_count=conversion_result['vertex_count'],
            component_count=conversion_result['component_count'],
            bounding_box=conversion_result['bounding_box'],
            unit='mm'
        )

        # 7. Indexar metadatos de componentes (lote de hasta 5,000 para optimización)
        # Importante: para millones de filas, la jerarquía completa reside en el JSON lateral
        components = conversion_result.get('components', [])
        metadata_objs = []
        for comp in components[:2000]:
            metadata_objs.append(ModelObjectMetadata(
                model_version=model_version,
                node_id=comp['node_id'],
                name=comp['name'],
                hierarchy_path=comp['hierarchy_path'],
                attributes=comp.get('attributes', {}),
                bounding_box=comp.get('bounding_box', {})
            ))
        if metadata_objs:
            set_conversion_progress(job_id, 97, 'Guardando jerarquía de componentes')
            ModelObjectMetadata.objects.bulk_create(metadata_objs, batch_size=500)

        # 8. Finalización con éxito
        elapsed = time.perf_counter() - start_time
        job.completed_at = timezone.now()
        job.duration_seconds = round(elapsed, 3)
        job.status = JobStatus.READY
        job.logs = json.dumps({'progress_percentage': 100, 'progress_message': 'Conversión completada'}, ensure_ascii=False)
        job.model_version = model_version
        job.save(update_fields=['status', 'completed_at', 'duration_seconds', 'model_version', 'logs', 'updated_at'])

        return f"Job {job_id} completado con éxito en {job.duration_seconds}s."

    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        job.completed_at = timezone.now()
        job.duration_seconds = round(elapsed, 3)
        job.error_message = str(exc)
        job.error_traceback = traceback.format_exc()
        job.status = JobStatus.FAILED
        job.logs = json.dumps({'progress_percentage': 0, 'progress_message': 'Falló: ' + str(exc)[:180]}, ensure_ascii=False)
        job.save(update_fields=['status', 'completed_at', 'duration_seconds', 'error_message', 'error_traceback', 'logs', 'updated_at'])
        return f"Job {job_id} falló: {str(exc)}"
