import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.projects.models import Project

User = get_user_model()

class UploadStatus(models.TextChoices):
    INITIALIZED = 'INITIALIZED', 'Initialized'
    UPLOADING = 'UPLOADING', 'Uploading Chunks'
    ASSEMBLING = 'ASSEMBLING', 'Assembling File'
    COMPLETED = 'COMPLETED', 'Completed and Verified'
    CANCELLED = 'CANCELLED', 'Cancelled'
    FAILED = 'FAILED', 'Failed'
    EXPIRED = 'EXPIRED', 'Expired'

class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='upload_sessions')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="Tamaño total declarado en bytes")
    file_type = models.CharField(max_length=50, help_text="Extensión validada (.rvm, .udatasmith, .zip)")
    chunk_size = models.IntegerField(default=10 * 1024 * 1024, help_text="Tamaño del bloque en bytes (por defecto 10 MB)")
    total_chunks = models.IntegerField(default=1)
    uploaded_chunks = models.JSONField(default=list, help_text="Lista de índices enteros de chunks recibidos con éxito")
    expected_sha256 = models.CharField(max_length=64, blank=True, default='', help_text="Hash SHA-256 esperado")
    actual_sha256 = models.CharField(max_length=64, blank=True, default='', help_text="Hash SHA-256 calculado tras ensamblado")
    status = models.CharField(max_length=50, choices=UploadStatus.choices, default=UploadStatus.INITIALIZED, db_index=True)
    temp_dir = models.CharField(max_length=1024, help_text="Directorio temporal aislado donde se guardan los bloques")
    final_file_path = models.CharField(max_length=1024, blank=True, default='', help_text="Ruta final del archivo ensamblado")
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
        ]

    def __str__(self):
        return f"Upload {self.file_name} ({self.status}) - {len(self.uploaded_chunks)}/{self.total_chunks} chunks"
