# Pipeline de Conversión y Adaptadores

El pipeline de conversión transforma archivos CAD pesados en paquetes de visualización web optimizados sin alterar el archivo original.

---

## 1. Máquina de Estados Finita

| Estado | Descripción | Transición Siguiente |
| :--- | :--- | :--- |
| **RECEIVED** | Archivo original recibido, íntegro y validado con hash SHA-256 en almacenamiento seguro. | `VALIDATING` |
| **VALIDATING** | El adaptador comprueba la extensión, el encabezado binario y que el archivo no esté vacío. | `QUEUED` / `FAILED` |
| **QUEUED** | El trabajo está encolado en Redis a la espera de un worker Celery disponible. | `PROCESSING` |
| **PROCESSING** | El conversor externo (RvmSharp, parser XML) tesela la geometría y genera los derivados. | `VERIFYING` / `FAILED` |
| **VERIFYING** | Validación física del GLB generado: verificación de encabezado glTF 2.0 y conteo de triángulos > 0. | `READY` / `FAILED` |
| **READY** | Todos los artefactos están verificados y la versión del modelo queda activa para visualización. | Terminal (Éxito) |
| **FAILED** | Ocurrió un error en alguna fase. Se registra la traza y el mensaje descriptivo sin exponer rutas privadas. | `RETRY_PENDING` |
| **RETRY_PENDING**| En espera de reintento controlado (hasta 3 reintentos configurables). | `QUEUED` |

---

## 2. Contrato de Adaptadores (`BaseConverterAdapter`)

Cada conversor debe implementar tres métodos obligatorios:
1. `validate_input(input_file_path: str) -> bool`: Comprueba la accesibilidad y validez de la entrada.
2. `convert(input_file_path: str, output_dir: str, options: dict) -> dict`: Ejecuta el proceso de teselado y exportación.
3. `verify_output(output_dir: str, conversion_result: dict) -> bool`: Comprueba los artefactos generados.

---

## 3. Manejo de Errores y Aislamiento

* Los comandos de conversión se ejecutan con timeout explícito y captura estricta de `stdout` y `stderr` hacia un archivo de registro (`conversion.log`).
* Si el proceso de conversión falla o es abortado, los archivos temporales se eliminan y el archivo original permanece **intacto y protegido contra escritura**.
