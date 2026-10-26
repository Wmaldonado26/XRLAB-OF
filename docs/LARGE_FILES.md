# Estrategia de Carga y Procesamiento de Archivos Grandes (3 a 5 GB)

La manipulaciÃ³n de modelos de ingenierÃ­a de varios gigabytes presenta desafÃ­os severos de agotamiento de memoria RAM, saturaciÃ³n de disco y desconexiones de red.

---

## 1. Principio Fundamental: Streaming de Fragmentos

* **DivisiÃ³n en el Cliente:** Los archivos grandes se segmentan en bloques de 10 MB utilizando `File.slice()` de la API estÃ¡ndar de JavaScript.
* **Control de Memoria en Backend:**
  - Django nunca invoca `request.FILES.read()` en su totalidad.
  - La lectura de chunks se limita a bloques de 1 MB (`chunks(chunk_size=1024*1024)`), garantizando un consumo de RAM plano menor a 25 MB en cualquier peticiÃ³n HTTP.
  - Los chunks se persisten atÃ³micamente como `chunk_XXXXXX.part` en una carpeta temporal con identificador UUID de sesiÃ³n.

---

## 2. Integridad y Ensamblado Reanudable

* **CÃ¡lculo de Hash en Vuelo:** El frontend calcula el hash SHA-256 acumulado y lo envÃ­a en el encabezado de inicializaciÃ³n. Durante el ensamblado en el backend, se calcula el SHA-256 progresivo sin reabrir copias adicionales.
* **ReanudaciÃ³n tras DesconexiÃ³n:** Si una subida se interrumpe, el cliente consulta `/api/v1/uploads/{id}/` y recibe la lista de bloques ya subidos (`uploaded_chunks`), retomando la carga exclusivamente de los fragmentos faltantes.
* **PolÃ­tica de Limpieza y Cuotas de Disco:** Las sesiones abandonadas tienen expiraciÃ³n de 24 horas y los bloques temporales se eliminan tras el ensamblado o al invocar `/cancel/`.

