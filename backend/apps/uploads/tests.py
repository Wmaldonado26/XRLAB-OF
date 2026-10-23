import os
import shutil
import hashlib
from io import BytesIO
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.projects.models import Project
from apps.uploads.models import UploadSession, UploadStatus
from apps.models_3d.models import ModelAsset, ModelVersion

class ChunkedUploadTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create(username="test_engineer")
        self.client = APIClient()
        self.project = Project.objects.create(name="Planta Industrial Test", slug="planta-test", owner=self.user)

    from unittest.mock import patch

    @patch('apps.conversions.tasks.run_conversion_pipeline_task.delay')
    def test_chunked_upload_and_assembly(self, mock_celery_delay):
        from unittest.mock import MagicMock
        mock_task = MagicMock()
        mock_task.id = 'mocked-task-id-12345'
        mock_celery_delay.return_value = mock_task

        # 1. Crear contenido binario simulado de 3 chunks exactos (2800 bytes c/u)
        chunk1 = b"PART_1_HEADER_" * 200
        chunk2 = b"PART_2_VALVES_" * 200
        chunk3 = b"PART_3_VESSEL_" * 200
        full_content = chunk1 + chunk2 + chunk3
        expected_sha = hashlib.sha256(full_content).hexdigest()

        # 2. Inicializar sesión de carga
        init_res = self.client.post('/api/v1/uploads/initialize/', {
            'project_id': str(self.project.id),
            'file_name': 'test_plant_model.rvm',
            'file_size': len(full_content),
            'file_type': '.rvm',
            'chunk_size': len(chunk1),
            'expected_sha256': expected_sha
        }, format='json')
        self.assertEqual(init_res.status_code, status.HTTP_201_CREATED)
        session_id = init_res.data['id']
        self.assertEqual(init_res.data['total_chunks'], 3)

        # 3. Subir chunks en orden y verificar idempotencia
        chunks = [chunk1, chunk2, chunk3]
        for idx, chunk_bytes in enumerate(chunks):
            chunk_file = BytesIO(chunk_bytes)
            chunk_file.name = f"chunk_{idx}.bin"
            upload_res = self.client.post(
                f'/api/v1/uploads/{session_id}/chunk/',
                {'chunk_index': idx, 'chunk': chunk_file},
                format='multipart'
            )
            self.assertEqual(upload_res.status_code, status.HTTP_200_OK)
            self.assertIn(idx, upload_res.data['uploaded_chunks_count'] and [idx])

        # 4. Completar y ensamblar
        comp_res = self.client.post(f'/api/v1/uploads/{session_id}/complete/')
        self.assertEqual(comp_res.status_code, status.HTTP_201_CREATED)
        self.assertIn('asset_id', comp_res.data)

        # 5. Verificar integridad del archivo ensamblado en disco
        session = UploadSession.objects.get(id=session_id)
        self.assertEqual(session.status, UploadStatus.COMPLETED)
        self.assertEqual(session.actual_sha256, expected_sha)
        self.assertTrue(os.path.exists(session.final_file_path))

        with open(session.final_file_path, 'rb') as f:
            assembled_content = f.read()
        self.assertEqual(assembled_content, full_content)

        # Verificar ModelAsset
        asset = ModelAsset.objects.get(id=comp_res.data['asset_id'])
        self.assertEqual(asset.original_sha256, expected_sha)
        self.assertEqual(asset.original_file_size, len(full_content))
