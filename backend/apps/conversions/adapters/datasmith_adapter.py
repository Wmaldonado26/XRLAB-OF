import os
import json
import struct
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any
from pathlib import Path
from .base import BaseConverterAdapter

class DatasmithConverterAdapter(BaseConverterAdapter):
    adapter_name = "DatasmithConverterAdapter"
    adapter_version = "1.0.0 (XML SceneGraph + Proxy Engine)"

    def validate_input(self, input_file_path: str) -> bool:
        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Archivo Datasmith no encontrado: {input_file_path}")
        size = os.path.getsize(input_file_path)
        if size < 20:
            raise ValueError(f"Archivo Datasmith inválido o vacío ({size} bytes).")
        return True

    def convert(self, input_file_path: str, output_dir: str, options: Dict[str, Any]) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(input_file_path).stem
        final_glb = os.path.join(output_dir, f"{base_name}.glb")
        hierarchy_json = os.path.join(output_dir, "hierarchy.json")
        log_file = os.path.join(output_dir, "conversion.log")

        with open(log_file, "w", encoding="utf-8") as log:
            log.write(f"=== Conversión Datasmith Iniciada: {time.ctime()} ===\n")
            log.write(f"Archivo: {input_file_path}\n")

            # 1. Parsear estructura XML del documento .udatasmith
            tree = ET.parse(input_file_path)
            root = tree.getroot()

            actors = []
            materials = []

            for actor in root.findall('.//ActorMesh') + root.findall('.//Actor'):
                actor_id = actor.get('id', actor.get('name', 'Actor'))
                label = actor.get('label', actor_id)
                transform_elem = actor.find('Transform')
                transform_matrix = transform_elem.text.strip() if transform_elem is not None and transform_elem.text else ""
                
                meta_dict = {}
                for meta in actor.findall('.//MetaData'):
                    for prop in meta.findall('.//Property'):
                        prop_name = prop.get('name')
                        prop_val = prop.get('value')
                        if prop_name:
                            meta_dict[prop_name] = prop_val

                actors.append({
                    "node_id": actor_id,
                    "name": label,
                    "transform": transform_matrix,
                    "attributes": meta_dict,
                    "hierarchy_path": f"/Datasmith/{label}"
                })

            log.write(f"Nodos de escena extraídos: {len(actors)}\n")

            # 2. Generar proxy 3D estructurado en GLB con Trimesh representativo de los componentes
            import trimesh
            import numpy as np

            scene = trimesh.Scene()
            # Crear geometría de referencia espacial para visualización de los actores
            if actors:
                step = 1000.0  # mm
                for idx, act in enumerate(actors[:50]): # Límite de actores para bounding proxies
                    box = trimesh.creation.box(extents=[400, 400, 400])
                    box.visual.vertex_colors = [35, 75, 161, 255] # Azul corporativo #234BA1
                    translation = [(idx % 5) * step, ((idx // 5) % 5) * step, (idx // 25) * step]
                    box.apply_translation(translation)
                    scene.add_geometry(box, node_name=act["name"])
            else:
                box = trimesh.creation.box(extents=[1000, 1000, 1000])
                scene.add_geometry(box, node_name="DatasmithScene")

            scene.export(final_glb, file_type='glb')
            log.write(f"Archivo GLB exportado: {final_glb} ({os.path.getsize(final_glb)} bytes)\n")

        # 3. Métricas y Bounding Box
        bounds = scene.bounds if hasattr(scene, 'bounds') and scene.bounds is not None else np.array([[0,0,0], [1000,1000,1000]])
        min_pt = [float(bounds[0][0]), float(bounds[0][1]), float(bounds[0][2])]
        max_pt = [float(bounds[1][0]), float(bounds[1][1]), float(bounds[1][2])]
        center = [round((min_pt[i] + max_pt[i])/2, 4) for i in range(3)]

        bbox = {
            "min": [round(c, 4) for c in min_pt],
            "max": [round(c, 4) for c in max_pt],
            "center": center,
            "dimensions": [round(max_pt[i] - min_pt[i], 4) for i in range(3)]
        }

        triangle_count = int(sum(len(geom.faces) for geom in scene.geometry.values())) if hasattr(scene, 'geometry') else 12

        hierarchy_data = {
            "model_name": Path(input_file_path).name,
            "triangle_count": triangle_count,
            "vertex_count": triangle_count * 3,
            "component_count": len(actors),
            "bounding_box": bbox,
            "components": actors
        }

        with open(hierarchy_json, "w", encoding="utf-8") as f:
            json.dump(hierarchy_data, f, indent=2)

        artifacts = [
            {"type": "GLB", "path": final_glb, "size": os.path.getsize(final_glb)},
            {"type": "HIERARCHY_JSON", "path": hierarchy_json, "size": os.path.getsize(hierarchy_json)},
            {"type": "LOG", "path": log_file, "size": os.path.getsize(log_file)}
        ]

        return {
            "glb_path": final_glb,
            "hierarchy_json_path": hierarchy_json,
            "triangle_count": triangle_count,
            "vertex_count": triangle_count * 3,
            "component_count": len(actors),
            "bounding_box": bbox,
            "artifacts": artifacts
        }

    def verify_output(self, output_dir: str, conversion_result: Dict[str, Any]) -> bool:
        glb_path = conversion_result.get("glb_path")
        if not glb_path or not os.path.exists(glb_path):
            return False
        with open(glb_path, "rb") as f:
            header = f.read(12)
            if len(header) < 12:
                return False
            magic, version, length = struct.unpack("<4sII", header)
            if magic != b'glTF' or version != 2:
                return False
        return True
