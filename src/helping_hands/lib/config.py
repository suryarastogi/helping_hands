import os
from typing import Optional, Dict, Any

def get_config_path() -> str:
    return os.getenv("HELPING_HANDS_CONFIG_PATH", "config.yaml")

def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    if path is None:
        path = get_config_path()
    if os.path.exists(path):
        # Just a stub for loading config to illustrate typing improvement
        return {"config_loaded": True}
    else:
        return {}