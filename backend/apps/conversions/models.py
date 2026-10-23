import uuid
from django.db import models
from apps.projects.models import Project
from apps.models_3d.models import ModelAsset, ModelVersion

class JobStatus(models.TextChoices):
    RECEIVED = 'RECEIVED', 'Received'
    VALIDATING = 'VALIDATING', 'Validating'
    QUEUED = 'QUEUED', 'Queued'
    PROCESSING = 'PROCESSING', 'Processing'
    VERIFYING = 'VERIFYING', 'Verifying'
    READY = 'READY', 'Ready'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    RETRY_PENDING = 'RETRY_PENDING', 'Retry Pending'

class ConversionJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='conversion_jobs')
    model_asset = models.ForeignKey(ModelAsset, on_delete=models.CASCADE, related_name='conversion_jobs')
    model_version = models.ForeignKey(ModelVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversion_jobs')
    
    status = models.CharField(max_length=50, choices=JobStatus.choices, default=JobStatus.RECEIVED, db_index=True)
    converter_adapter = models.CharField(max_length=100)
    converter_version = models.CharField(max_length=50, default='1.0.0')
    celery_task_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    
    input_file_path = models.CharField(max_length=1024)
    output_dir = models.CharField(max_length=1024)
    tolerance = models.FloatField(default=0.1)
    
    # Métricas de ejecución
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    peak_memory_mb = models.FloatField(null=True, blank=True)
    
    # Manejo de fallos y reintentos
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(blank=True, default='')
    error_traceback = models.TextField(blank=True, default='')
    logs = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['model_asset', 'status']),
        ]

    def __str__(self):
        return f"Job {self.id} [{self.converter_adapter}] - {self.status}"

class ConversionArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ConversionJob, on_delete=models.CASCADE, related_name='artifacts')
    artifact_type = models.CharField(max_length=50, choices=[
        ('GLB', 'Binary glTF 2.0'),
        ('HIERARCHY_JSON', 'Hierarchy and Metadata JSON Index'),
        ('OBJ', 'Wavefront OBJ Mesh'),
        ('LOG', 'Execution Log'),
        ('THUMBNAIL', 'Model Thumbnail')
    ])
    file_path = models.CharField(max_length=1024)
    file_size = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Artifact {self.artifact_type} ({self.file_size} bytes)"
