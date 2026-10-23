import os
import sys
import json
import struct
import subprocess
import time
from typing import Dict, Any
from pathlib import Path
from .base import BaseConverterAdapter

class RvmConverterAdapter(BaseConverterAdapter):
    adapter_name = "RvmConverterAdapter"
    adapter_version = "1.0.0 (RvmSharp + obj2gltf)"

    def __init__(self):
        # Localizar dotnet y el binario compilado de RvmSharp.Exe
        self.dotnet_exe = os.path.expanduser(r"~\.dotnet\dotnet.exe")
        # Ruta al binario compilado en Release (5 niveles arriba desde adapters/)
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        self.rvmsharp_dll = project_root / "converters" / "rvmsharp_repo" / "RvmSharp.Exe" / "bin" / "Release" / "net8.0" / "RvmSharp.Exe.dll"

    def validate_input(self, input_file_path: str) -> bool:
        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Archivo RVM no encontrado: {input_file_path}")
        size = os.path.getsize(input_file_path)
        if size < 16:
            raise ValueError(f"Archivo RVM corrupto o vacío (tamaño: {size} bytes).")
        return True

    def convert(self, input_file_path: str, output_dir: str, options: Dict[str, Any]) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        tolerance = str(options.get('tolerance', 0.1))
        progress = options.get('progress_callback', lambda percentage, message: None)
        
        base_name = Path(input_file_path).stem
        intermediate_obj = os.path.join(output_dir, f"{base_name}.obj")
        final_glb = os.path.join(output_dir, f"{base_name}.glb")
        hierarchy_json = os.path.join(output_dir, "hierarchy.json")
        log_file = os.path.join(output_dir, "conversion.log")

        # 1. Ejecutar RvmSharp.Exe para teselar RVM a Wavefront OBJ
        progress(22, 'Teselando el RVM y generando geometría OBJ')
        cmd = [
            self.dotnet_exe,
            str(self.rvmsharp_dll),
            "--input", input_file_path,
            "--output", intermediate_obj,
            "--tolerance", tolerance
        ]

        with open(log_file, "w", encoding="utf-8") as log:
            log.write(f"=== Conversión RVM Iniciada: {time.ctime()} ===\n")
            log.write(f"Comando: {' '.join(cmd)}\n\n")
            
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            log.write(f"STDOUT:\n{proc.stdout}\n")
            log.write(f"STDERR:\n{proc.stderr}\n")

            if proc.returncode != 0:
                raise RuntimeError(f"Fallo en RvmSharp (código {proc.returncode}): {proc.stderr}")

        if not os.path.exists(intermediate_obj) or os.path.getsize(intermediate_obj) == 0:
            raise FileNotFoundError(f"RvmSharp no generó el archivo OBJ esperado en {intermediate_obj}")

        # 2. Convertir OBJ a GLB binario optimizado con obj2gltf o fallback con trimesh
        progress(55, f"OBJ generado ({os.path.getsize(intermediate_obj) / (1024 ** 3):.2f} GB). Preparando GLB")
        converted_to_glb = False
        try:
            # Intentar primero con obj2gltf vía npx
            progress(60, 'Convirtiendo geometría OBJ a GLB')
            cmd_glb = ["npx", "-y", "obj2gltf", "-i", intermediate_obj, "-o", final_glb, "--binary"]
            proc_glb = subprocess.run(cmd_glb, capture_output=True, text=True, timeout=120)
            if proc_glb.returncode == 0 and os.path.exists(final_glb) and os.path.getsize(final_glb) > 0:
                converted_to_glb = True
        except Exception as e:
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"Aviso obj2gltf npx: {str(e)}. Utilizando fallback trimesh.\n")

        # Fallback con biblioteca trimesh nativa de Python
        if not converted_to_glb:
            progress(62, 'Convirtiendo OBJ a GLB con el conversor alternativo; esta etapa puede tardar')
            import trimesh
            # OBJ separa la geometrÃ­a por material en el MTL. Forzar una sola
            # malla concatena las caras y elimina sus colores y normales.
            scene = trimesh.load(intermediate_obj, file_type='obj', force='scene')
            scene.export(final_glb, file_type='glb')
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(
                    f"Fallback trimesh: GLB exportado desde escena con "
                    f"{len(scene.geometry)} geometrÃ­as agrupadas por material.\n"
                )
        progress(80, 'GLB generado. Analizando vértices, triángulos y componentes')

        # 3. Extraer métricas geométricas y jerarquía de componentes del OBJ / RVM
        triangle_count = 0
        vertex_count = 0
        min_pt = [float('inf'), float('inf'), float('inf')]
        max_pt = [float('-inf'), float('-inf'), float('-inf')]
        components = []

        current_object = "Root"
        processed_chars = 0
        obj_size = max(os.path.getsize(intermediate_obj), 1)
        with open(intermediate_obj, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                processed_chars += len(line)
                if processed_chars and processed_chars % 16_000_000 < len(line):
                    scan_progress = 80 + min(9, int((processed_chars / obj_size) * 9))
                    progress(scan_progress, f"Analizando geometría OBJ ({min(99, int(processed_chars * 100 / obj_size))}%)")
                if line.startswith("o "):
                    current_object = line[2:].strip()
                    components.append({
                        "node_id": current_object,
                        "name": current_object.split('/')[-1] if '/' in current_object else current_object,
                        "hierarchy_path": current_object
                    })
                elif line.startswith("v "):
                    parts = line.split()
                    if len(parts) >= 4:
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                        vertex_count += 1
                        min_pt[0] = min(min_pt[0], x)
                        min_pt[1] = min(min_pt[1], y)
                        min_pt[2] = min(min_pt[2], z)
                        max_pt[0] = max(max_pt[0], x)
                        max_pt[1] = max(max_pt[1], y)
                        max_pt[2] = max(max_pt[2], z)
                elif line.startswith("f "):
                    triangle_count += 1

        if vertex_count == 0:
            min_pt = [0, 0, 0]
            max_pt = [0, 0, 0]

        center = [
            round((min_pt[0] + max_pt[0]) / 2, 4),
            round((min_pt[1] + max_pt[1]) / 2, 4),
            round((min_pt[2] + max_pt[2]) / 2, 4)
        ]

        bbox = {
            "min": [round(c, 4) for c in min_pt],
            "max": [round(c, 4) for c in max_pt],
            "center": center,
            "dimensions": [
                round(max_pt[0] - min_pt[0], 4),
                round(max_pt[1] - min_pt[1], 4),
                round(max_pt[2] - min_pt[2], 4)
            ]
        }

        hierarchy_data = {
            "model_name": Path(input_file_path).name,
            "triangle_count": triangle_count,
            "vertex_count": vertex_count,
            "component_count": len(components),
            "bounding_box": bbox,
            "components": components
        }
        progress(90, 'Guardando jerarquía y metadatos del modelo')

        with open(hierarchy_json, "w", encoding="utf-8") as f:
            json.dump(hierarchy_data, f, indent=2)

        artifacts = [
            {"type": "GLB", "path": final_glb, "size": os.path.getsize(final_glb)},
            {"type": "HIERARCHY_JSON", "path": hierarchy_json, "size": os.path.getsize(hierarchy_json)},
            {"type": "OBJ", "path": intermediate_obj, "size": os.path.getsize(intermediate_obj)},
            {"type": "LOG", "path": log_file, "size": os.path.getsize(log_file)}
        ]

        return {
            "glb_path": final_glb,
            "hierarchy_json_path": hierarchy_json,
            "triangle_count": triangle_count,
            "vertex_count": vertex_count,
            "component_count": len(components),
            "bounding_box": bbox,
            "artifacts": artifacts
        }

    def verify_output(self, output_dir: str, conversion_result: Dict[str, Any]) -> bool:
        glb_path = conversion_result.get("glb_path")
        if not glb_path or not os.path.exists(glb_path):
            return False
        # Validar header binario glTF
        with open(glb_path, "rb") as f:
            header = f.read(12)
            if len(header) < 12:
                return False
            magic, version, length = struct.unpack("<4sII", header)
            if magic != b'glTF' or version != 2:
                return False
            if length != os.path.getsize(glb_path):
                return False

        # Validar que contenga geometría no degenerada
        if conversion_result.get("triangle_count", 0) <= 0:
            return False

        return True
