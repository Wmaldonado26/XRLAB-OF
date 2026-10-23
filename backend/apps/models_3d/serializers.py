from rest_framework import serializers
from .models import ModelAsset, ModelVersion, ModelObjectMetadata, SavedCamera, Measurement, ClippingConfiguration

class ModelObjectMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelObjectMetadata
        fields = ['id', 'node_id', 'parent_node_id', 'name', 'hierarchy_path', 'attributes', 'bounding_box']

class SavedCameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedCamera
        fields = ['id', 'model_version', 'name', 'position', 'target', 'up', 'fov', 'projection', 'created_at']
        read_only_fields = ['id', 'created_at']

class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = ['id', 'model_version', 'point_a', 'point_b', 'distance', 'unit', 'label', 'measurement_type', 'created_at']
        read_only_fields = ['id', 'created_at']

class ClippingConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClippingConfiguration
        fields = ['id', 'model_version', 'name', 'planes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ModelVersionSerializer(serializers.ModelSerializer):
    saved_cameras = SavedCameraSerializer(many=True, read_only=True)
    measurements = MeasurementSerializer(many=True, read_only=True)
    clipping_configs = ClippingConfigurationSerializer(many=True, read_only=True)
    glb_url = serializers.SerializerMethodField()
    hierarchy_url = serializers.SerializerMethodField()

    class Meta:
        model = ModelVersion
        fields = [
            'id', 'asset', 'version_number', 'notes', 'is_active',
            'triangle_count', 'vertex_count', 'component_count', 'bounding_box', 'unit',
            'glb_url', 'hierarchy_url', 'saved_cameras', 'measurements', 'clipping_configs', 'created_at'
        ]

    def get_glb_url(self, obj):
        return f"/api/v1/versions/{obj.id}/glb/"

    def get_hierarchy_url(self, obj):
        return f"/api/v1/versions/{obj.id}/hierarchy/"

class ModelAssetSerializer(serializers.ModelSerializer):
    versions = ModelVersionSerializer(many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = ModelAsset
        fields = [
            'id', 'project', 'name', 'format', 'original_file_name',
            'original_file_size', 'original_sha256', 'versions', 'latest_version',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'original_sha256', 'original_file_size', 'created_at', 'updated_at']

    def get_latest_version(self, obj):
        latest = obj.versions.filter(is_active=True).first()
        if latest:
            return ModelVersionSerializer(latest).data
        return None
