import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.projects.models import Project

User = get_user_model()

class FormatChoice(models.TextChoices):
    RVM = 'RVM', 'AVEVA RVM'
    DATASMITH = 'DATASMITH', 'Epic Datasmith'

class ModelAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='model_assets')
    name = models.CharField(max_length=255, db_index=True)
    format = models.CharField(max_length=50, choices=FormatChoice.choices)
    original_file_path = models.CharField(max_length=1024, help_text="Ruta persistente al archivo original inmutable")
    original_file_name = models.CharField(max_length=255)
    original_file_size = models.BigIntegerField(help_text="Tamaño en bytes del archivo original")
    original_sha256 = models.CharField(max_length=64, db_index=True, help_text="Checksum inmutable SHA-256")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'name']),
            models.Index(fields=['original_sha256']),
        ]

    def __str__(self):
        return f"{self.name} ({self.format})"

class ModelVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(ModelAsset, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    
    # Derivados de visualización
    glb_artifact_path = models.CharField(max_length=1024, blank=True, null=True, help_text="Ruta al archivo GLB optimizado")
    hierarchy_index_path = models.CharField(max_length=1024, blank=True, null=True, help_text="Ruta al JSON lateral de jerarquía y metadatos")
    
    # Métricas y estadísticas de inspección
    triangle_count = models.BigIntegerField(default=0)
    vertex_count = models.BigIntegerField(default=0)
    component_count = models.IntegerField(default=0)
    bounding_box = models.JSONField(default=dict, blank=True, help_text="Min, Max y Center del modelo")
    unit = models.CharField(max_length=20, default='mm')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['asset', '-version_number']
        unique_together = ('asset', 'version_number')

    def __str__(self):
        return f"{self.asset.name} v{self.version_number}"

class ModelObjectMetadata(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='metadata_records')
    node_id = models.CharField(max_length=255, db_index=True)
    parent_node_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    hierarchy_path = models.TextField(help_text="Ej: /Site/Zone/Equip/SubEquip")
    attributes = models.JSONField(default=dict, blank=True)
    bounding_box = models.JSONField(default=dict, blank=True)
    material_info = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['model_version', 'node_id']),
            models.Index(fields=['model_version', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.node_id})"

class SavedCamera(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='saved_cameras')
    name = models.CharField(max_length=150)
    position = models.JSONField(help_text="[x, y, z]")
    target = models.JSONField(help_text="[x, y, z]")
    up = models.JSONField(default=list, help_text="[x, y, z]")
    fov = models.FloatField(default=45.0)
    projection = models.CharField(max_length=20, default='perspective', choices=[('perspective', 'Perspective'), ('orthographic', 'Orthographic')])
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Camera: {self.name} ({self.model_version})"

class Measurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='measurements')
    point_a = models.JSONField(help_text="[x, y, z]")
    point_b = models.JSONField(help_text="[x, y, z]")
    distance = models.FloatField(help_text="Distancia calculada")
    unit = models.CharField(max_length=20, default='mm')
    label = models.CharField(max_length=150, blank=True, default='')
    measurement_type = models.CharField(
        max_length=50,
        choices=[('exact_cad', 'Exact CAD Geometry'), ('mesh_approx', 'Mesh Triangulation Approximation')],
        default='exact_cad'
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Measurement {self.label or self.id}: {self.distance} {self.unit}"

class ClippingConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='clipping_configs')
    name = models.CharField(max_length=150)
    planes = models.JSONField(default=dict, help_text="Configuración de planos X, Y, Z con posición, estado e inversión")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Clipping: {self.name} ({self.model_version})"
