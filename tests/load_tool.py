import importlib.util
from pathlib import Path
import sys


def load_tool():
    path = Path(__file__).resolve().parents[1] / "splatter-upload.py"
    spec = importlib.util.spec_from_file_location("splatter_upload", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
