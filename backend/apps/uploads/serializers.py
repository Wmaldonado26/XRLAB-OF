import os
from rest_framework import serializers
from .models import UploadSession, UploadStatus
from apps.projects.models import Project

class UploadSessionCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = UploadSession
        fields = [
            'id', 'project_id', 'file_name', 'file_size', 'file_type',
            'chunk_size', 'total_chunks', 'expected_sha256', 'status',
            'uploaded_chunks', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'status', 'uploaded_chunks', 'created_at', 'expires_at']

    def validate_file_type(self, value):
        ext = value.lower().strip()
        allowed = ['.rvm', '.udatasmith', '.zip', '.txt', '.att']
        if not any(ext.endswith(a) for a in allowed):
            raise serializers.ValidationError(f"Formato no permitido: {value}. Formatos admitidos: {allowed}")
        return ext

    def validate_file_size(self, value):
        # Límite máximo: 5 GB por archivo
        max_size = 5 * 1024 * 1024 * 1024
        if value <= 0:
            raise serializers.ValidationError("El tamaño del archivo debe ser mayor a 0 bytes.")
        if value > max_size:
            raise serializers.ValidationError(f"El archivo excede el límite máximo de 5 GB ({value} bytes).")
        return value

    def create(self, validated_data):
        from django.conf import settings
        import uuid
        from datetime import timedelta
        from django.utils import timezone

        project_id = validated_data.pop('project_id')
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError({"project_id": "Proyecto no encontrado."})

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        session_id = uuid.uuid4()
        temp_dir = os.path.join(settings.TEMP_UPLOADS_DIR, str(session_id))
        os.makedirs(temp_dir, exist_ok=True)

        chunk_size = validated_data.get('chunk_size', 10 * 1024 * 1024)
        file_size = validated_data['file_size']
        total_chunks = (file_size + chunk_size - 1) // chunk_size

        session = UploadSession.objects.create(
            id=session_id,
            project=project,
            user=user,
            file_name=validated_data['file_name'],
            file_size=file_size,
            file_type=validated_data['file_type'],
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            expected_sha256=validated_data.get('expected_sha256', ''),
            temp_dir=temp_dir,
            expires_at=timezone.now() + timedelta(hours=24),
            status=UploadStatus.INITIALIZED
        )
        return session

class UploadSessionDetailSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = UploadSession
        fields = [
            'id', 'project', 'file_name', 'file_size', 'file_type',
            'chunk_size', 'total_chunks', 'uploaded_chunks', 'progress_percentage',
            'expected_sha256', 'actual_sha256', 'status', 'error_message',
            'created_at', 'updated_at', 'expires_at'
        ]

    def get_progress_percentage(self, obj):
        if not obj.total_chunks:
            return 0.0
        return round((len(obj.uploaded_chunks) / obj.total_chunks) * 100, 2)
