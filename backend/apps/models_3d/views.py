import os
from django.http import FileResponse, Http404, JsonResponse
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ModelAsset, ModelVersion, ModelObjectMetadata, SavedCamera, Measurement, ClippingConfiguration
from .serializers import (
    ModelAssetSerializer, ModelVersionSerializer, ModelObjectMetadataSerializer,
    SavedCameraSerializer, MeasurementSerializer, ClippingConfigurationSerializer
)

class ModelAssetViewSet(viewsets.ModelViewSet):
    queryset = ModelAsset.objects.all().prefetch_related('versions')
    serializer_class = ModelAssetSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'original_file_name']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

class ModelVersionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelVersion.objects.all().select_related('asset').prefetch_related('saved_cameras', 'measurements', 'clipping_configs')
    serializer_class = ModelVersionSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def glb(self, request, pk=None):
        version = self.get_object()
        if not version.glb_artifact_path or not os.path.exists(version.glb_artifact_path):
            raise Http404("El archivo de geometría GLB no se encuentra en el servidor.")
        
        # Enviar archivo como respuesta binaria con tipo MIME model/gltf-binary
        response = FileResponse(open(version.glb_artifact_path, 'rb'), content_type='model/gltf-binary')
        response['Content-Disposition'] = f'inline; filename="{version.asset.name}.glb"'
        return response

    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        version = self.get_object()
        if not version.hierarchy_index_path or not os.path.exists(version.hierarchy_index_path):
            raise Http404("El índice de jerarquía no se encuentra en el servidor.")
        
        response = FileResponse(open(version.hierarchy_index_path, 'rb'), content_type='application/json')
        response['Content-Disposition'] = f'inline; filename="{version.asset.name}_hierarchy.json"'
        return response

class ModelObjectMetadataViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelObjectMetadata.objects.all()
    serializer_class = ModelObjectMetadataSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'node_id', 'hierarchy_path']

    def get_queryset(self):
        qs = super().get_queryset()
        version_id = self.request.query_params.get('version_id')
        if version_id:
            qs = qs.filter(model_version_id=version_id)
        return qs

class SavedCameraViewSet(viewsets.ModelViewSet):
    queryset = SavedCamera.objects.all()
    serializer_class = SavedCameraSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        version_id = self.request.query_params.get('version_id')
        if version_id:
            qs = qs.filter(model_version_id=version_id)
        return qs

class MeasurementViewSet(viewsets.ModelViewSet):
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        version_id = self.request.query_params.get('version_id')
        if version_id:
            qs = qs.filter(model_version_id=version_id)
        return qs

class ClippingConfigurationViewSet(viewsets.ModelViewSet):
    queryset = ClippingConfiguration.objects.all()
    serializer_class = ClippingConfigurationSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        version_id = self.request.query_params.get('version_id')
        if version_id:
            qs = qs.filter(model_version_id=version_id)
        return qs
