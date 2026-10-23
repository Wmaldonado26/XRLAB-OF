import os
import sys
import django
import shutil
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from apps.models_3d.models import ModelAsset, ModelVersion, ModelObjectMetadata, SavedCamera, Measurement, ClippingConfiguration
from apps.conversions.adapters.rvm_adapter import RvmConverterAdapter

User = get_user_model()

def seed_huldra_model():
    print("[*] Iniciando siembra de modelo industrial real Huldra...")
    
    # 1. Crear usuario y proyecto
    user, _ = User.objects.get_or_create(
        username='lead_engineer',
        defaults={'email': 'engineer@industrial3d.local', 'is_staff': True, 'is_superuser': True}
    )
    user.set_password('Admin1234!')
    user.save()

    project, _ = Project.objects.get_or_create(
        slug='plataforma-huldra',
        defaults={
            'name': 'Plataforma Offshore Huldra (Equinor)',
            'description': 'Instalación de procesamiento de gas y condensado en el Mar del Norte. Modelo AVEVA PDMS verificado.',
            'owner': user
        }
    )

    # 2. Rutas a los archivos reales de prueba
    source_rvm = Path(__file__).resolve().parent.parent / "converters" / "rvmsharp_repo" / "TestSamples" / "Huldra" / "WD1-PSUP.RVM"
    if not source_rvm.exists():
        print(f"[!] No se encontró el archivo {source_rvm}")
        return

    # Copiar original inmutable a storage/originals/
    os.makedirs(settings.ORIGINALS_DIR, exist_ok=True)
    target_original = settings.ORIGINALS_DIR / "WD1-PSUP.RVM"
    shutil.copyfile(source_rvm, target_original)

    # Calcular SHA256
    import hashlib
    h = hashlib.sha256()
    with open(target_original, 'rb') as f:
        while chunk := f.read(1024*1024):
            h.update(chunk)
    file_sha = h.hexdigest()

    asset, _ = ModelAsset.objects.get_or_create(
        project=project,
        name='Planta de Compresión WD1-PSUP',
        defaults={
            'format': 'RVM',
            'original_file_path': str(target_original),
            'original_file_name': 'WD1-PSUP.RVM',
            'original_file_size': os.path.getsize(target_original),
            'original_sha256': file_sha
        }
    )

    # 3. Ejecutar conversión con el adaptador oficial
    output_dir = os.path.join(settings.DERIVED_DIR, str(asset.id))
    os.makedirs(output_dir, exist_ok=True)

    adapter = RvmConverterAdapter()
    result = adapter.convert(str(target_original), output_dir, {'tolerance': 0.1})

    # 4. Crear ModelVersion
    version, _ = ModelVersion.objects.get_or_create(
        asset=asset,
        version_number=1,
        defaults={
            'notes': 'Teselado CAD con tolerancia 0.1 y exportación glTF 2.0 binaria optimizada',
            'glb_artifact_path': result['glb_path'],
            'hierarchy_index_path': result['hierarchy_json_path'],
            'triangle_count': result['triangle_count'],
            'vertex_count': result['vertex_count'],
            'component_count': result['component_count'],
            'bounding_box': result['bounding_box'],
            'unit': 'mm'
        }
    )

    # 5. Indexar componentes en base de datos
    components = result.get('components', [])
    metadata_objs = []
    for c in components[:1500]:
        metadata_objs.append(ModelObjectMetadata(
            model_version=version,
            node_id=c['node_id'],
            name=c['name'],
            hierarchy_path=c['hierarchy_path']
        ))
    if metadata_objs:
        ModelObjectMetadata.objects.filter(model_version=version).delete()
        ModelObjectMetadata.objects.bulk_create(metadata_objs, batch_size=500)

    # 6. Añadir mediciones de ejemplo
    Measurement.objects.filter(model_version=version).delete()
    Measurement.objects.create(
        model_version=version,
        point_a=[12000.0, 5500.0, -2000.0],
        point_b=[15500.0, 5500.0, -2000.0],
        distance=3500.0,
        unit='mm',
        label='Distancia entre soportes principales',
        measurement_type='exact_cad',
        created_by=user
    )

    # 7. Añadir vista de cámara guardada
    SavedCamera.objects.filter(model_version=version).delete()
    SavedCamera.objects.create(
        model_version=version,
        name='Perspectiva Global de la Estructura',
        position=[25000, 20000, 30000],
        target=[result['bounding_box']['center'][0], result['bounding_box']['center'][1], result['bounding_box']['center'][2]],
        up=[0, 1, 0],
        fov=45.0,
        projection='perspective',
        created_by=user
    )

    print(f"[+] Semilla creada con éxito.")
    print(f"    Proyecto: {project.name}")
    print(f"    Modelo: {asset.name}")
    print(f"    Triángulos: {version.triangle_count}")
    print(f"    Componentes: {version.component_count}")
    print(f"    GLB generado: {version.glb_artifact_path} ({os.path.getsize(version.glb_artifact_path)} bytes)")

if __name__ == '__main__':
    seed_huldra_model()
