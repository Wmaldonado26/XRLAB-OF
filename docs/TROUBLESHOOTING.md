# Diagnóstico y Resolución de Problemas (Troubleshooting)

---

## 1. Problemas Comunes y Soluciones

### Error: "UnauthorizedAccessException: Access to the path ... is denied" en RvmSharp
* **Causa:** El argumento `--output` de `RvmSharp.Exe` requiere la ruta completa del archivo `.obj` de salida, no una carpeta existente.
* **Solución:** Pasar la ruta completa con nombre de archivo (ej. `.../output/model.obj`).

### Error: "El SDK de .NET actual no admite el destino .NET 10.0"
* **Causa:** El repositorio de `rvmsharp` en master fue actualizado recientemente para pruebas a .NET 10 preview.
* **Solución:** Utilizar el commit estable `600f3dd` (versión compatible con .NET 8.0 LTS) que compila con cero advertencias y cero errores en .NET 8 SDK.

### Error: "Incompatibilidad de hash SHA-256" al completar la carga
* **Causa:** Uno de los bloques se transmitió corrupto o incompleto.
* **Solución:** El backend rechaza el ensamblado para proteger la integridad. La sesión permite reenviar el bloque afectado consultando `/api/v1/uploads/{id}/`.

### El visor no muestra el modelo o aparece en blanco
* **Causa:** El modelo original tiene coordenadas muy alejadas del origen o la escala no coincide con las unidades de Three.js.
* **Solución:** Hacer clic en el botón **Fit** en la esquina superior derecha del visor 3D para centrar y encuadrar automáticamente la cámara en el centro geométrico del modelo.
