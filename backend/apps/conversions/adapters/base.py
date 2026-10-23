from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseConverterAdapter(ABC):
    adapter_name = "BaseConverterAdapter"
    adapter_version = "1.0.0"

    @abstractmethod
    def validate_input(self, input_file_path: str) -> bool:
        """Valida que el archivo de entrada sea accesible, íntegro y del tipo esperado."""
        pass

    @abstractmethod
    def convert(self, input_file_path: str, output_dir: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la conversión del modelo.
        Debe retornar un diccionario con:
        {
            "glb_path": str,
            "hierarchy_json_path": str,
            "triangle_count": int,
            "vertex_count": int,
            "component_count": int,
            "bounding_box": dict,
            "artifacts": list
        }
        """
        pass

    @abstractmethod
    def verify_output(self, output_dir: str, conversion_result: Dict[str, Any]) -> bool:
        """Verifica la validez física y geométrica de los artefactos generados."""
        pass
