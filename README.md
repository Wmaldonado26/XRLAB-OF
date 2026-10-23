# Industrial 3D Viewer

Sistema profesional de alta disponibilidad para la ingesta, conversión y visualización web interactiva de modelos CAD industriales de gran tamaño (3 a 5 GB) en formatos **AVEVA RVM** y **Datasmith**.

---

## 🚀 Características Principales

* **Carga Robusta de Archivos Grandes (3 a 5 GB):**
  - Carga reanudable por bloques (chunks de 10 MB).
  - Ensamblado mediante streaming en disco sin sobrecargar la memoria RAM.
  - Validación de integridad estricta con hash SHA-256 en vuelo.
  - El archivo original se conserva **inmutable al 100%** (protegido contra escritura).

* **Pipeline Asíncrono de Conversión:**
  - Máquina de estados: `RECEIVED` $\rightarrow$ `VALIDATING` $\rightarrow$ `QUEUED` $\rightarrow$ `PROCESSING` $\rightarrow$ `VERIFYING` $\rightarrow$ `READY`.
  - Adaptadores desacoplados (`RvmConverterAdapter`, `DatasmithConverterAdapter`).
  - Teselación paramétrica de alta velocidad y exportación a **glTF 2.0 / GLB binario**.
  - Registro de auditoría, duración, consumo y recuperación ante fallos.

* **Visor 3D Industrial (Three.js + Vue 3):**
  - Tema corporativo con azul `#234BA1` y fondos neutros según especificación técnica.
  - Navegación CAD orbital con ajuste automático a los límites del modelo (`Fit`).
  - Vistas ortogonales estándar (Superior, Frontal, Lateral, Isométrica).
  - Árbol jerárquico de componentes con buscador en tiempo real, ocultado y aislamiento (`Isolate`).
  - Herramienta de medición euclidiana tridimensional con soporte de unidades (`mm`, `m`, `in`).
  - Planos de corte dinámicos X, Y, Z con control de posición e inversión normal.
  - Gestión y persistencia de vistas de cámara en base de datos.

---

## 🛠️ Stack Tecnológico

* **Backend:** Python 3.12, Django 5.1, Django REST Framework, PostgreSQL 18, Celery 5.4, Redis, drf-spectacular (OpenAPI 3 / Swagger).
* **Conversión:** .NET SDK 8.0, Equinor RvmSharp, obj2gltf, Trimesh.
* **Frontend:** Vue 3, Vite, TypeScript, Three.js, Pinia.

---

## ⚡ Comandos para Ejecutar el Proyecto

```powershell
# 1. Backend (desde la carpeta raíz)
$env:CELERY_ALWAYS_EAGER = "True"
.\venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8001

# 2. Frontend (en otra terminal)
cd frontend
npm run dev
```

La interfaz web estará activa en `http://localhost:5173`. En desarrollo, Vite reenvía `/api/*` a Django en `http://127.0.0.1:8001`. `CELERY_ALWAYS_EAGER=True` permite ejecutar conversiones locales sin Redis; las cargas grandes pueden tardar mientras se procesa el modelo.

## Licencia

El código original de este proyecto se distribuye bajo la licencia MIT; consulta [LICENSE](LICENSE). Los componentes de terceros conservan sus propias licencias y condiciones. En particular, el código de RvmSharp incluido en `converters/rvmsharp_repo` mantiene su licencia MIT y atribución originales. Esta licencia no concede derechos sobre Unreal Engine, Datasmith ni otros productos o SDK de terceros.
