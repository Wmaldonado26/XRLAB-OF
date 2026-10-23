# Arquitectura del Sistema Industrial 3D Viewer

El sistema **Industrial 3D Viewer** está diseñado bajo los principios de desacoplamiento, escalabilidad horizontal, integridad de datos inmutables y optimización de recursos para modelos de ingeniería industrial de gran tamaño (3 a 5 GB).

---

## 1. Diagrama de Arquitectura Global

```mermaid
graph TD
    subgraph Frontend [Cliente Web - Vue 3 + Three.js]
        UI[Workspace UI - Tema Claro #234BA1]
        V3D[Viewport 3D Three.js - OrbitControls, Clipping, Snap]
        Tree[Object Tree - Filtrado y Selección Sincronizada]
        Upl[Chunked Uploader - Stream y SHA-256 en Cliente]
        Store[Pinia State Store]
    end

    subgraph API [Servicios Backend - Django REST Framework]
        Auth[Autenticación y Permisos por Proyecto]
        UpAPI[Chunked Upload API - Sessions, Assembly & Hashes]
        ModelAPI[Models & Versions API - Streaming GLB]
        ToolsAPI[SavedCameras, Measurements & Clipping API]
    end

    subgraph Storage [Capa de Almacenamiento Persistente]
        PG[(PostgreSQL 18 - Proyectos, Metadatos, Estados)]
        DiskOrig[Disco /storage/originals - Solo Lectura Inmutable]
        DiskDeriv[Disco /storage/derived - GLB y JSON Index]
        DiskTmp[Disco /storage/temp_chunks - Bloques Temporales]
    end

    subgraph Queue [Cola y Tareas en Segundo Plano]
        RedisQueue[(Redis Broker & Task Backend)]
        CeleryWorkers[Workers Celery Distribuidos]
    end

    subgraph Converters [Capa Aislada de Conversores]
        AdapterRVM[RvmConverterAdapter - RvmSharp .NET 8]
        AdapterDS[DatasmithConverterAdapter - XML SceneGraph]
        Verifier[Model Verification & Sanity Checks]
    end

    Upl -->|HTTP POST Chunks (10 MB)| UpAPI
    UpAPI --> DiskTmp
    UpAPI --> DiskOrig
    UpAPI --> PG
    UpAPI -->|Encolar Job| RedisQueue
    RedisQueue --> CeleryWorkers
    CeleryWorkers --> AdapterRVM
    CeleryWorkers --> AdapterDS
    AdapterRVM --> Verifier
    AdapterDS --> Verifier
    Verifier --> DiskDeriv
    Verifier --> PG
    V3D -->|HTTP GET Stream GLB| ModelAPI
    Tree -->|HTTP GET Hierarchy JSON| ModelAPI
```

---

## 2. Componentes Arquitectónicos

### A. Backend (Django 5 + DRF + Celery + PostgreSQL 18)
* **Gestión de Carga:** No satura la memoria del servidor. Los fragmentos se reciben como streams y se escriben directamente a disco.
* **Máquina de Estados de Conversión:**
  $$\text{RECEIVED} \rightarrow \text{VALIDATING} \rightarrow \text{QUEUED} \rightarrow \text{PROCESSING} \rightarrow \text{VERIFYING} \rightarrow \text{READY}$$
* **Desacoplamiento de Conversores:** Los adaptadores implementan la interfaz `BaseConverterAdapter` sin acoplar la API a herramientas de terceros.
* **Manejo de Metadatos de Gran Escala:** Los metadatos de cientos de miles de componentes se almacenan en archivos JSON laterales indexados (`hierarchy.json`), evitando millones de inserciones que degraden la base de datos relacional.

### B. Frontend (Vue 3 + Vite + TypeScript + Three.js + Pinia)
* **Motor de Renderizado:** Three.js con `WebGLRenderer` optimizado con frustum culling y planos de corte locales (`localClippingEnabled = true`).
* **Navegación:** `OrbitControls` con soporte de paneo en espacio de pantalla y ajuste automático de encuadre según la esfera envolvente del modelo.
* **Herramientas de Inspección:**
  - Planos de corte X, Y, Z independientes con inversión normal.
  - Mediciones tridimensionales exactas con etiquetas de distancia física y cambio de unidades dinámico (`mm`, `m`, `in`).
  - Cámaras guardadas con persistencia de posición, objetivo, vector UP y campo visual (FOV).
