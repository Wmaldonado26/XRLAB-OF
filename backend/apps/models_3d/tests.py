import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from apps.models_3d.models import ModelAsset, ModelVersion, SavedCamera, Measurement, ClippingConfiguration

User = get_user_model()

class ViewerToolsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username="lead_engineer")
        self.project = Project.objects.create(name="Refinería A-10", slug="refineria-a10", owner=self.user)
        self.asset = ModelAsset.objects.create(
            project=self.project,
            name="Modulo_Compresores.rvm",
            format="RVM",
            original_file_path="/storage/originals/compresores.rvm",
            original_file_name="Modulo_Compresores.rvm",
            original_file_size=1024000,
            original_sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc"
        )
        self.version = ModelVersion.objects.create(
            asset=self.asset,
            version_number=1,
            notes="Versión inicial convertida",
            glb_artifact_path="/storage/derived/compresores.glb",
            hierarchy_index_path="/storage/derived/hierarchy.json",
            triangle_count=45000,
            vertex_count=135000,
            component_count=120,
            bounding_box={"min": [0,0,0], "max": [1000, 2000, 3000], "center": [500, 1000, 1500]}
        )

    def test_saved_cameras_crud(self):
        # Crear cámara
        res = self.client.post('/api/v1/cameras/', {
            'model_version': str(self.version.id),
            'name': 'Vista Superior Bombas',
            'position': [0, 5000, 0],
            'target': [500, 0, 1500],
            'up': [0, 0, -1],
            'fov': 45.0,
            'projection': 'perspective'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        camera_id = res.data['id']

        # Listar cámaras
        list_res = self.client.get(f'/api/v1/cameras/?version_id={self.version.id}')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(list_res.data['count'], 1)

    def test_measurement_persistence(self):
        # Crear medición
        res = self.client.post('/api/v1/measurements/', {
            'model_version': str(self.version.id),
            'point_a': [100.0, 200.0, 300.0],
            'point_b': [100.0, 200.0, 1500.0],
            'distance': 1200.0,
            'unit': 'mm',
            'label': 'Altura de Brida 24"',
            'measurement_type': 'exact_cad'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['distance'], 1200.0)

    def test_clipping_configuration_persistence(self):
        # Guardar plano de corte
        planes_config = {
            "x": {"enabled": True, "position": 250.0, "inverted": False},
            "y": {"enabled": False, "position": 0.0, "inverted": False},
            "z": {"enabled": True, "position": 1200.0, "inverted": True}
        }
        res = self.client.post('/api/v1/clippings/', {
            'model_version': str(self.version.id),
            'name': 'Sección Longitudinal Sala de Máquinas',
            'planes': planes_config
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['planes']['x']['enabled'])
