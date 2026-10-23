import json
from rest_framework import serializers
from .models import ConversionJob, ConversionArtifact, JobStatus

class ConversionArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionArtifact
        fields = ['id', 'artifact_type', 'file_size', 'sha256', 'created_at']

class ConversionJobSerializer(serializers.ModelSerializer):
    artifacts = ConversionArtifactSerializer(many=True, read_only=True)
    asset_name = serializers.CharField(source='model_asset.name', read_only=True)
    model_version_id = serializers.UUIDField(source='model_version.id', read_only=True)
    can_cancel = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    progress_message = serializers.SerializerMethodField()

    def get_can_cancel(self, obj):
        return (
            obj.status not in [JobStatus.READY, JobStatus.FAILED, JobStatus.CANCELLED]
            and bool(obj.celery_task_id)
        )

    def _progress(self, obj):
        try:
            data = json.loads(obj.logs or '{}')
            if isinstance(data, dict) and 'progress_percentage' in data:
                return data
        except (TypeError, ValueError):
            pass
        defaults = {
            JobStatus.RECEIVED: (0, 'Preparando conversión'),
            JobStatus.QUEUED: (5, 'En cola'),
            JobStatus.VALIDATING: (10, 'Validando archivo RVM'),
            JobStatus.PROCESSING: (20, 'Procesando geometría 3D'),
            JobStatus.VERIFYING: (92, 'Verificando modelo generado'),
            JobStatus.READY: (100, 'Conversión completada'),
            JobStatus.FAILED: (0, 'La conversión falló'),
            JobStatus.CANCELLED: (0, 'Conversión detenida'),
            JobStatus.RETRY_PENDING: (5, 'Preparando reintento'),
        }
        percentage, message = defaults.get(obj.status, (0, 'Preparando conversión'))
        return {'progress_percentage': percentage, 'progress_message': message}

    def get_progress_percentage(self, obj):
        return self._progress(obj).get('progress_percentage', 0)

    def get_progress_message(self, obj):
        return self._progress(obj).get('progress_message', 'Procesando modelo')

    class Meta:
        model = ConversionJob
        fields = [
            'id', 'project', 'model_asset', 'asset_name', 'model_version', 'model_version_id',
            'status', 'converter_adapter', 'converter_version', 'tolerance', 'can_cancel',
            'progress_percentage', 'progress_message',
            'started_at', 'completed_at', 'duration_seconds', 'retry_count',
            'error_message', 'artifacts', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'converter_version', 'started_at', 'completed_at',
            'duration_seconds', 'retry_count', 'error_message', 'artifacts',
            'created_at', 'updated_at'
        ]
