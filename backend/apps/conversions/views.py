import os
import signal
import subprocess
import multiprocessing
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ConversionJob, JobStatus
from .serializers import ConversionJobSerializer
from .tasks import run_conversion_pipeline_task

class ConversionJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ConversionJob.objects.all().select_related('model_asset', 'model_version').prefetch_related('artifacts')
    serializer_class = ConversionJobSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status in [JobStatus.READY, JobStatus.FAILED, JobStatus.CANCELLED]:
            return Response({"error": "Este trabajo ya terminó."}, status=status.HTTP_400_BAD_REQUEST)
        if not job.celery_task_id:
            return Response(
                {"error": "Este trabajo comenzó antes de habilitar la cancelación."},
                status=status.HTTP_409_CONFLICT,
            )

        local_pid = None
        if job.celery_task_id.startswith('local:'):
            try:
                local_pid = int(job.celery_task_id.split(':', 1)[1])
            except ValueError:
                local_pid = None

        celery_task_id = job.celery_task_id if local_pid is None else ''
        job.status = JobStatus.CANCELLED
        job.error_message = 'Conversión detenida por el usuario.'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])

        if local_pid is not None:
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/PID', str(local_pid), '/T', '/F'],
                        capture_output=True,
                        check=False,
                    )
                else:
                    os.kill(local_pid, signal.SIGTERM)
            except (OSError, subprocess.SubprocessError):
                pass
        elif celery_task_id:
            try:
                from celery import current_app
                current_app.control.revoke(celery_task_id, terminate=True)
            except Exception:
                pass

        return Response({"message": "Conversión detenida.", "job": ConversionJobSerializer(job).data})

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
            return Response({"error": "Solo se pueden reintentar trabajos fallidos o cancelados."}, status=status.HTTP_400_BAD_REQUEST)

        job.status = JobStatus.QUEUED
        job.retry_count += 1
        job.error_message = ''
        job.error_traceback = ''
        job.save()

        if settings.CELERY_TASK_ALWAYS_EAGER:
            from apps.conversions.local_worker import run_local_conversion
            worker = multiprocessing.get_context('spawn').Process(
                target=run_local_conversion,
                args=(str(job.id),),
                name=f'conversion-{job.id}',
                daemon=False,
            )
            worker.start()
            job.celery_task_id = f'local:{worker.pid}'
        else:
            task = run_conversion_pipeline_task.delay(str(job.id))
            job.celery_task_id = task.id
        job.save(update_fields=['celery_task_id'])

        return Response({"message": f"Trabajo reencolado (reintento #{job.retry_count}).", "job": ConversionJobSerializer(job).data})
