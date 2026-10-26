# Industrial 3D Backend

Microservicio REST para gestionar proyectos y modelos CAD industriales, recibir archivos por bloques, ejecutar conversiones y servir artefactos 3D. La interfaz Vue vive en un proyecto separado y no está incluida en este repositorio.

## Arquitectura

- **API:** Python 3.12, Django 5.1, Django REST Framework y OpenAPI.
- **Procesamiento:** Celery y Redis para conversiones asíncronas.
- **Persistencia:** PostgreSQL en Docker Compose; SQLite como alternativa para desarrollo local sin `DB_NAME`.
- **Almacenamiento:** archivos originales, temporales y derivados en `STORAGE_ROOT`.
- **Conversores:** adaptadores para RVM y Datasmith. La ejecución del adaptador RVM depende del runtime y binario RvmSharp configurados para el entorno.

Rutas principales: `/api/health/`, `/api/schema/`, `/api/docs/` y `/api/v1/`. La especificación OpenAPI permite que el proyecto de interfaz integre el contrato de este microservicio.

## Ejecución local

Desde la raíz del repositorio, crea y activa un entorno virtual, instala las dependencias y ejecuta Django:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:CELERY_ALWAYS_EAGER = "True"
.venv\Scripts\python.exe backend\manage.py migrate
.venv\Scripts\python.exe backend\manage.py runserver 0.0.0.0:8000
```

Sin `DB_NAME`, el backend usa `backend/db.sqlite3`. Para conversiones locales, `CELERY_ALWAYS_EAGER=True` usa el worker local existente; algunas conversiones pueden tardar durante la petición. No uses esta modalidad para cargas productivas grandes.

## Ejecución independiente con Docker

Copia `.env.example` a `.env`, reemplaza los secretos y credenciales, y arranca únicamente el microservicio y sus dependencias:

```powershell
docker compose up --build db redis backend celery_worker
```

La API queda disponible en `http://localhost:8000`; la documentación interactiva en `/api/docs/`. No se inicia ningún frontend desde Compose. PostgreSQL conserva sus datos en el volumen `pgdata`; los archivos se guardan en `./storage`.

Para permitir que el proyecto Vue externo llame directamente a la API desde un navegador, configura `CORS_ALLOWED_ORIGINS` con el origen exacto de esa aplicación y configura en ella la URL base de esta API. `DJANGO_ALLOWED_HOSTS` debe contener los nombres de host usados para acceder al backend. No habilites `CORS_ALLOW_ALL_ORIGINS` en producción.

## Configuración de entorno

Variables principales (ver `.env.example`):

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `CORS_ALLOWED_ORIGINS`
- `STORAGE_ROOT`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

El archivo `.env` no debe contener secretos de producción en el repositorio. Las migraciones de base de datos se ejecutan explícitamente con `python manage.py migrate`.

## Validación

```powershell
.venv\Scripts\python.exe backend\manage.py check
.venv\Scripts\python.exe backend\manage.py test
```

En Docker, comprueba la configuración con `docker compose config` y consulta `http://localhost:8000/api/health/`.

## Licencia

El código original se distribuye bajo MIT; consulta [LICENSE](LICENSE). Los componentes de terceros conservan sus propias licencias y condiciones. En particular, `converters/rvmsharp_repo` conserva su licencia y atribución originales. Esta licencia no concede derechos sobre Unreal Engine, Datasmith ni otros productos o SDK de terceros.

