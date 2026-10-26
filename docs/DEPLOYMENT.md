# Guía de Despliegue del Microservicio

## Requisitos

- Python 3.12 para ejecución local.
- Docker Compose para iniciar el backend junto con PostgreSQL y Redis.
- .NET 8 y el binario RvmSharp si se habilita la conversión RVM en ese entorno.

## Ejecución local

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe backend\manage.py migrate
.venv\Scripts\python.exe backend\manage.py runserver 0.0.0.0:8000
```

Sin configurar `DB_NAME`, Django usa `backend/db.sqlite3`. Para conversiones asíncronas, configura PostgreSQL y Redis, y ejecuta un worker en otra terminal:

```powershell
.venv\Scripts\celery.exe -A core worker -l info --workdir backend
```

## Docker Compose

Copia `.env.example` a `.env`, cambia los secretos de ejemplo y ejecuta:

```powershell
docker compose up --build db redis backend celery_worker
```

La API queda disponible en el puerto `8000`. Compose no incluye ni sirve un frontend. El cliente web externo debe establecer la URL de este servicio y su origen debe estar enumerado en `CORS_ALLOWED_ORIGINS`.

## Variables de entorno

Consulta `.env.example` para `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, las credenciales `DB_*`, `CORS_ALLOWED_ORIGINS` y `STORAGE_ROOT`. Configura `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` según el broker utilizado. No uses secretos de ejemplo en producción.
