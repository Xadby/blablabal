import json
import os
from typing import List, Dict, Any
from app_paths import get_app_data_dir

DEFAULT_CONFIG_PATH = os.path.join(get_app_data_dir(), "config.json")

class Config:
    def __init__(self, path: str = DEFAULT_CONFIG_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.data: Dict[str, Any] = {
            "sounds": [],
            "settings": {
                "master_volume": 1.0,
                "primary_device": None,
                "mirror_device": None,
                "start_minimized": False,
                "minimize_to_tray": True,
            },
        }
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.data["sounds"] = loaded.get("sounds", [])
                self.data["settings"].update(loaded.get("settings", {}))
            except (json.JSONDecodeError, OSError) as e:
                print(f"Ошибка загрузки конфига: {e}")

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Ошибка сохранения конфига: {e}")

    def get_sounds(self) -> List[Dict[str, Any]]:
        return self.data["sounds"]

    def set_sounds(self, sounds: List[Dict[str, Any]]) -> None:
        self.data["sounds"] = sounds
        self.save()

    def get_setting(self, key: str, default=None):
        return self.data["settings"].get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.data["settings"][key] = value
        self.save()