import os
import shutil
import hashlib
import multiprocessing
from django.conf import settings
from django.utils import timezone
from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UploadSession, UploadStatus
from .serializers import UploadSessionCreateSerializer, UploadSessionDetailSerializer
from apps.models_3d.models import ModelAsset, FormatChoice
from apps.conversions.models import ConversionJob, JobStatus


class InitUploadView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UploadSessionCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            session = serializer.save()
            return Response(UploadSessionDetailSerializer(session).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UploadChunkView(views.APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, session_id):
        try:
            session = UploadSession.objects.get(id=session_id)
        except UploadSession.DoesNotExist:
            return Response({"error": "Sesión de carga no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if session.status in [UploadStatus.COMPLETED, UploadStatus.CANCELLED, UploadStatus.FAILED]:
            return Response({"error": f"La sesión se encuentra en estado terminal: {session.status}."}, status=status.HTTP_400_BAD_REQUEST)

        chunk_index_raw = request.data.get('chunk_index')
        if chunk_index_raw is None:
            return Response({"error": "Parámetro 'chunk_index' requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chunk_index = int(chunk_index_raw)
        except ValueError:
            return Response({"error": "'chunk_index' debe ser un número entero."}, status=status.HTTP_400_BAD_REQUEST)

        if chunk_index < 0 or chunk_index >= session.total_chunks:
            return Response({"error": f"'chunk_index' fuera de rango (0 a {session.total_chunks - 1})."}, status=status.HTTP_400_BAD_REQUEST)

        chunk_file = request.FILES.get('chunk')
        if not chunk_file:
            return Response({"error": "Archivo de bloque 'chunk' no recibido."}, status=status.HTTP_400_BAD_REQUEST)

        # Escribir el bloque a disco directamente mediante chunks de lectura (evitando RAM saturada)
        chunk_dest_path = os.path.join(session.temp_dir, f"chunk_{chunk_index:06d}.part")
        with open(chunk_dest_path, 'wb') as dest:
            for piece in chunk_file.chunks(chunk_size=1024 * 1024):
                dest.write(piece)

        # Actualizar lista de chunks de manera idempotente
        uploaded_set = set(session.uploaded_chunks)
        uploaded_set.add(chunk_index)
        session.uploaded_chunks = sorted(list(uploaded_set))
        session.status = UploadStatus.UPLOADING
        session.save(update_fields=['uploaded_chunks', 'status', 'updated_at'])

        return Response({
            "message": f"Bloque {chunk_index} recibido exitosamente.",
            "chunk_index": chunk_index,
            "uploaded_chunks_count": len(session.uploaded_chunks),
            "total_chunks": session.total_chunks,
            "progress_percentage": round((len(session.uploaded_chunks) / session.total_chunks) * 100, 2)
        }, status=status.HTTP_200_OK)

class CompleteUploadView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, session_id):
        try:
            session = UploadSession.objects.get(id=session_id)
        except UploadSession.DoesNotExist:
            return Response({"error": "Sesión de carga no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == UploadStatus.COMPLETED:
            return Response({"message": "La sesión ya fue completada previamente.", "session": UploadSessionDetailSerializer(session).data})

        # 1. Validar que todos los bloques estén presentes
        missing_chunks = [i for i in range(session.total_chunks) if i not in session.uploaded_chunks]
        if missing_chunks:
            return Response({
                "error": "Faltan bloques por subir para completar el archivo.",
                "missing_chunks_count": len(missing_chunks),
                "missing_chunks_sample": missing_chunks[:10]
            }, status=status.HTTP_400_BAD_REQUEST)

        session.status = UploadStatus.ASSEMBLING
        session.save(update_fields=['status', 'updated_at'])

        # 2. Ensamblar los bloques en disco mediante streaming y calcular SHA-256 en vuelo
        final_filename = f"{session.id}_{session.file_name}"
        final_file_path = os.path.join(settings.ORIGINALS_DIR, final_filename)
        sha256_hasher = hashlib.sha256()

        try:
            with open(final_file_path, 'wb') as outfile:
                for chunk_idx in range(session.total_chunks):
                    chunk_path = os.path.join(session.temp_dir, f"chunk_{chunk_idx:06d}.part")
                    if not os.path.exists(chunk_path):
                        raise FileNotFoundError(f"Bloque no encontrado en disco: {chunk_path}")
                    with open(chunk_path, 'rb') as infile:
                        while piece := infile.read(1024 * 1024):
                            outfile.write(piece)
                            sha256_hasher.update(piece)

            actual_sha256 = sha256_hasher.hexdigest()
            session.actual_sha256 = actual_sha256
            session.final_file_path = final_file_path

            # 3. Validar integridad si se especificó expected_sha256
            if session.expected_sha256 and session.expected_sha256.lower() != actual_sha256.lower():
                session.status = UploadStatus.FAILED
                session.error_message = f"Incompatibilidad de hash SHA-256. Esperado: {session.expected_sha256}, Actual: {actual_sha256}"
                session.save()
                if os.path.exists(final_file_path):
                    os.remove(final_file_path)
                return Response({"error": session.error_message}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # 4. Establecer permisos de solo lectura en el archivo original para preservar integridad absoluta
            try:
                os.chmod(final_file_path, 0o444)
            except Exception:
                pass

            session.status = UploadStatus.COMPLETED
            session.save()

            # 5. Limpieza segura de los fragmentos temporales en disco
            try:
                shutil.rmtree(session.temp_dir, ignore_errors=True)
            except Exception as e:
                pass

            # 6. Registrar ModelAsset inmutable
            fmt = FormatChoice.RVM if session.file_name.lower().endswith('.rvm') else FormatChoice.DATASMITH
            asset = ModelAsset.objects.create(
                project=session.project,
                name=session.file_name,
                format=fmt,
                original_file_path=final_file_path,
                original_file_name=session.file_name,
                original_file_size=os.path.getsize(final_file_path),
                original_sha256=actual_sha256
            )

            # 7. Crear y encolar ConversionJob automáticamente
            adapter_name = 'RvmConverterAdapter' if fmt == FormatChoice.RVM else 'DatasmithConverterAdapter'
            job_output_dir = os.path.join(settings.DERIVED_DIR, str(asset.id))
            os.makedirs(job_output_dir, exist_ok=True)

            job = ConversionJob.objects.create(
                project=session.project,
                model_asset=asset,
                status=JobStatus.RECEIVED,
                converter_adapter=adapter_name,
                input_file_path=final_file_path,
                output_dir=job_output_dir
            )

            # Encolar tarea de Celery. En desarrollo, permitir procesamiento local
            # en segundo plano cuando Celery está configurado en modo eager.
            from apps.conversions.tasks import run_conversion_pipeline_task
            if settings.CELERY_TASK_ALWAYS_EAGER:
                job.status = JobStatus.QUEUED
                job.save(update_fields=['status', 'updated_at'])
                from apps.conversions.local_worker import run_local_conversion
                worker = multiprocessing.get_context('spawn').Process(
                    target=run_local_conversion,
                    args=(str(job.id),),
                    name=f'conversion-{job.id}',
                    daemon=False,
                )
                worker.start()
                job.celery_task_id = f'local:{worker.pid}'
                job.save(update_fields=['celery_task_id', 'updated_at'])
            else:
                task = run_conversion_pipeline_task.delay(str(job.id))
                job.refresh_from_db()
                job.celery_task_id = task.id
                update_fields = ['celery_task_id', 'updated_at']
                if job.status == JobStatus.RECEIVED:
                    job.status = JobStatus.QUEUED
                    update_fields.append('status')
                job.save(update_fields=update_fields)

            return Response({
                "message": "Archivo ensamblado, verificado e ingresado al pipeline de conversión.",
                "session": UploadSessionDetailSerializer(session).data,
                "asset_id": str(asset.id),
                "conversion_job_id": str(job.id)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            session.status = UploadStatus.FAILED
            session.error_message = f"Error durante ensamblado: {str(e)}"
            session.save()
            return Response({"error": session.error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CancelUploadView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, session_id):
        try:
            session = UploadSession.objects.get(id=session_id)
        except UploadSession.DoesNotExist:
            return Response({"error": "Sesión de carga no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        session.status = UploadStatus.CANCELLED
        session.save(update_fields=['status', 'updated_at'])

        # Limpiar directorio temporal
        if os.path.exists(session.temp_dir):
            shutil.rmtree(session.temp_dir, ignore_errors=True)

        return Response({"message": "Carga cancelada y archivos temporales liberados."}, status=status.HTTP_200_OK)

class UploadStatusView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, session_id):
        try:
            session = UploadSession.objects.get(id=session_id)
        except UploadSession.DoesNotExist:
            return Response({"error": "Sesión de carga no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UploadSessionDetailSerializer(session).data)
