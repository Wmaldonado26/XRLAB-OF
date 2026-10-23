# Estrategia de Carga y Procesamiento de Archivos Grandes (3 a 5 GB)

La manipulación de modelos de ingeniería de varios gigabytes presenta desafíos severos de agotamiento de memoria RAM, saturación de disco y desconexiones de red.

---

## 1. Principio Fundamental: Streaming de Fragmentos

* **División en el Cliente:** Los archivos grandes se segmentan en bloques de 10 MB utilizando `File.slice()` de la API estándar de JavaScript.
* **Control de Memoria en Backend:**
  - Django nunca invoca `request.FILES.read()` en su totalidad.
  - La lectura de chunks se limita a bloques de 1 MB (`chunks(chunk_size=1024*1024)`), garantizando un consumo de RAM plano menor a 25 MB en cualquier petición HTTP.
  - Los chunks se persisten atómicamente como `chunk_XXXXXX.part` en una carpeta temporal con identificador UUID de sesión.

---

## 2. Integridad y Ensamblado Reanudable

* **Cálculo de Hash en Vuelo:** El frontend calcula el hash SHA-256 acumulado y lo envía en el encabezado de inicialización. Durante el ensamblado en el backend, se calcula el SHA-256 progresivo sin reabrir copias adicionales.
* **Reanudación tras Desconexión:** Si una subida se interrumpe, el cliente consulta `/api/v1/uploads/{id}/` y recibe la lista de bloques ya subidos (`uploaded_chunks`), retomando la carga exclusivamente de los fragmentos faltantes.
* **Política de Limpieza y Cuotas de Disco:** Las sesiones abandonadas tienen expiración de 24 horas y los bloques temporales se eliminan tras el ensamblado o al invocar `/cancel/`.
