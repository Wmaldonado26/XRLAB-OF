# Especificación de la API REST (v1)

La API sigue los estándares RESTful con soporte OpenAPI 3 / Swagger disponible en `/api/docs/`.

---

## 1. Endpoints de Proyectos y Modelos

* `GET /api/v1/projects/`: Lista los proyectos activos.
* `POST /api/v1/projects/`: Crea un nuevo proyecto.
* `GET /api/v1/assets/?project_id={id}`: Lista los modelos asociados a un proyecto.
* `GET /api/v1/versions/{id}/`: Consulta el detalle de una versión, incluyendo estadísticas geométricas (`triangle_count`, `bounding_box`, `unit`).
* `GET /api/v1/versions/{id}/glb/`: Descarga o transmite el archivo binario GLB (`model/gltf-binary`).
* `GET /api/v1/versions/{id}/hierarchy/`: Retorna el JSON lateral con el árbol completo de componentes y atributos.

---

## 2. Endpoints de Carga por Bloques (Chunked Upload)

* `POST /api/v1/uploads/initialize/`: Inicia una sesión de carga. Requiere `project_id`, `file_name`, `file_size`, `file_type`.
* `POST /api/v1/uploads/{id}/chunk/`: Sube un fragmento binario (`chunk`) con su índice (`chunk_index`).
* `POST /api/v1/uploads/{id}/complete/`: Valida la presencia de todos los bloques, los ensambla en disco, calcula el hash SHA-256 e inicia la conversión.
* `POST /api/v1/uploads/{id}/cancel/`: Cancela la carga y elimina los archivos temporales.
* `GET /api/v1/uploads/{id}/`: Consulta el estado actual de la sesión y el progreso porcentual.

---

## 3. Endpoints de Herramientas del Visor

* `GET / POST /api/v1/cameras/`: Consulta o persiste cámaras guardadas (`name`, `position`, `target`, `up`, `fov`, `projection`).
* `GET / POST / DELETE /api/v1/measurements/`: Consulta, guarda o elimina mediciones entre puntos.
* `GET / POST /api/v1/clippings/`: Consulta o guarda configuraciones de planos de corte X, Y, Z.
* `GET /api/v1/jobs/{id}/`: Consulta el estado de un trabajo de conversión en el pipeline.
* `POST /api/v1/jobs/{id}/retry/`: Reintenta un trabajo de conversión fallido.
