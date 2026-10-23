import os


def run_local_conversion(job_id):
    """Run one eager-mode conversion in a killable child process."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()

    from apps.conversions.tasks import run_conversion_pipeline_task
    run_conversion_pipeline_task.apply(args=[job_id], throw=False)
