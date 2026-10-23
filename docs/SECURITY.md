# Directrices de Seguridad y Protección de Datos

---

## 1. Integridad y Control de Archivos

* **Protección contra Path Traversal:** Todos los nombres de archivo se sanitizan y se asocian a rutas seguras validadas mediante UUIDs no predecibles. No se permite el uso de secuencias `../` ni caracteres de control del sistema.
* **Archivos Originales Inmutables:** Los archivos cargados en `/storage/originals/` se marcan con permisos de solo lectura (`chmod 0444`) tras su ensamblado y verificación por SHA-256. Nunca se sobrescriben ni eliminan durante el flujo de conversión.
* **Validación Estricta de Extensiones:** Solo se admiten archivos explícitamente autorizados (`.rvm`, `.udatasmith`, `.zip`, `.txt`, `.att`).
* **Protección contra Ejecución de Código Arbitrario:** Los archivos subidos por el usuario nunca son tratados como ejecutables ni se evalúan dentro del intérprete de Python o shell sin sanitización estricta de parámetros en `subprocess`.

---

## 2. Aislamiento y Variables de Entorno

* Las claves de seguridad (`DJANGO_SECRET_KEY`), credenciales de base de datos y puertos se gestionan a través de variables de entorno y archivos `.env`, sin ser hardcodeadas en el código fuente.
* La configuración de CORS restringe el acceso a orígenes de confianza autorizados.
* Se implementa un registro de auditoría (`AuditEvent`) que almacena las acciones críticas realizadas sobre proyectos y activos (cargas, eliminaciones, conversiones).
