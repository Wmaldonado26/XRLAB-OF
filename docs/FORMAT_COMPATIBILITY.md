# Matriz de Compatibilidad de Formatos y Capacidades

Este informe técnico documenta de manera transparente y verificable las capacidades, limitaciones y dependencias asociadas a cada formato soportado en el sistema **Industrial 3D Viewer**.

---

## 1. AVEVA RVM (Review Model)

* **Propósito:** Visualización de modelos completos de plantas petroquímicas, navales y de energía exportados desde AVEVA PDMS y AVEVA E3D.
* **Componentes del formato:**
  - Archivo `.rvm`: Binario con estructura de árbol (Site, Zone, Group, Primitive) y primitivas geométricas paramétricas (cilindros, platos torisféricos, conos, prismas, toros, curvas de tubería, mallas poligonales).
  - Archivo `.txt` / `.att`: Texto con atributos y propiedades de ingeniería vinculados a los identificadores jerárquicos de cada elemento.
* **Ruta de Conversión Implementada:**
  $$\text{.rvm} \xrightarrow{\text{RvmSharp (C\# / .NET 8)}} \text{Mallas Trianguladas (.obj)} \xrightarrow{\text{obj2gltf / Trimesh}} \text{GLB Binario 2.0} + \text{hierarchy.json}$$
* **Estado de Compatibilidad Demostrado:** **100% OPERATIVO Y VERIFICADO**.
  - Geometría: Teselada con tolerancia configurable (`--tolerance`).
  - Identificadores: Preservados en el grafo y en los nombres de objeto del GLB.
  - Integridad: Archivo original conservado en modo solo lectura con validación de hash SHA-256 antes y después de la conversión.
* **Licencia de Dependencias:**
  - `Equinor.RvmSharp`: MIT License.
  - `LibTessDotNet`: SGI Free Software License B.
  - `obj2gltf`: Apache 2.0 License.

---

## 2. Epic Games Datasmith (`.udatasmith`)

* **Propósito:** Intercambio de modelos BIM/CAD (Revit, Rhino, 3ds Max, SolidWorks, Archicad, SketchUp) hacia Unreal Engine.
* **Componentes del formato:**
  - Archivo `.udatasmith`: Documento XML de texto plano estructurado que declara el grafo de la escena (jerarquía de `<Actor>`, transformaciones matriciales 4x4, asignación de materiales y metadatos).
  - Carpeta de recursos (`_Assets`): Almacena las texturas (`.png`, `.jpg`) y las mallas binarias propietarias (`.udsmesh` / `.udmesh`).
* **Análisis de Viabilidad y Estado:**
  - **Jerarquía y Metadatos:** **100% SOPORTADO**. El adaptador `DatasmithConverterAdapter` analiza nativamente el XML, indexando los actores, transformaciones 4x4, etiquetas y metadatos a `hierarchy.json`.
  - **Geometría Binaria Propietaria (`.udmesh`):** **LIMITACIÓN TÉCNICA DOCUMENTADA**.
    - No existe una especificación pública abierta ni parser independiente libre en C#/Python para descomprimir los buffers binarios `.udmesh` sin el SDK propietario de Epic Games.
    - La conversión completa de geometría de Datasmith requiere desplegar un proceso headless de Unreal Engine (UE 5.x) con el plugin oficial *glTF Exporter* de Epic Games.
    - **Restricción de Licencia (EULA):** Epic Games prohíbe redistribuir binarios del motor Unreal Engine en contenedores Docker de acceso público o paquetes comerciales sin un acuerdo de licencia directo.
    - **Solución implementada:** Ingesta del paquete `.udatasmith`, extracción completa del grafo jerárquico y generación de una escena proxy tridimensional que delimita las posiciones de los componentes para inspección y mediciones aproximadas.
