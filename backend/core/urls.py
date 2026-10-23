from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import JsonResponse
import os
import shutil

# Routers DRF
router = DefaultRouter()

from apps.projects.views import ProjectViewSet, AuditEventViewSet
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'audit', AuditEventViewSet, basename='audit')

from apps.models_3d.views import (
    ModelAssetViewSet, ModelVersionViewSet, ModelObjectMetadataViewSet,
    SavedCameraViewSet, MeasurementViewSet, ClippingConfigurationViewSet
)
router.register(r'assets', ModelAssetViewSet, basename='asset')
router.register(r'versions', ModelVersionViewSet, basename='version')
router.register(r'objects', ModelObjectMetadataViewSet, basename='object')
router.register(r'cameras', SavedCameraViewSet, basename='camera')
router.register(r'measurements', MeasurementViewSet, basename='measurement')
router.register(r'clippings', ClippingConfigurationViewSet, basename='clipping')

from apps.conversions.views import ConversionJobViewSet
router.register(r'jobs', ConversionJobViewSet, basename='job')

from apps.uploads.views import (
    InitUploadView, UploadChunkView, CompleteUploadView,
    CancelUploadView, UploadStatusView
)

def health_check(request):
    disk_usage = shutil.disk_usage('.')
    free_gb = round(disk_usage.free / (1024**3), 2)
    total_gb = round(disk_usage.total / (1024**3), 2)

    return JsonResponse({
        "status": "healthy",
        "service": "Industrial 3D Viewer Backend",
        "version": "1.0.0",
        "storage": {
            "free_gb": free_gb,
            "total_gb": total_gb,
            "percent_free": round((disk_usage.free / disk_usage.total) * 100, 1)
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # OpenAPI Schema & Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/health/', health_check, name='health-check'),

    # API v1 Router
    path('api/v1/', include(router.urls)),

    # Carga Robusta de Archivos Grandes (Chunked Uploads)
    path('api/v1/uploads/initialize/', InitUploadView.as_view(), name='upload-init'),
    path('api/v1/uploads/<uuid:session_id>/chunk/', UploadChunkView.as_view(), name='upload-chunk'),
    path('api/v1/uploads/<uuid:session_id>/complete/', CompleteUploadView.as_view(), name='upload-complete'),
    path('api/v1/uploads/<uuid:session_id>/cancel/', CancelUploadView.as_view(), name='upload-cancel'),
    path('api/v1/uploads/<uuid:session_id>/', UploadStatusView.as_view(), name='upload-status'),
]
