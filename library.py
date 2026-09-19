import json
import os
import shutil
import uuid
import zipfile
from typing import List, Dict, Any, Optional
from app_paths import get_app_data_dir

class SoundLibrary:
    def __init__(self):
        self.base_dir = os.path.join(get_app_data_dir(), "library")
        self.sounds_dir = os.path.join(self.base_dir, "sounds")
        self.db_path = os.path.join(self.base_dir, "library.json")

        os.makedirs(self.sounds_dir, exist_ok=True)
        self.sounds: List[Dict[str, Any]] = []
        self._load()

    def add_sound(self, source_path: str, name: str = "",
                  category: str = "Без категории",
                  tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        if not os.path.exists(source_path):
            return None
        ext = os.path.splitext(source_path)[1].lower()
        if ext not in (".mp3", ".wav", ".ogg", ".flac", ".m4a"):
            return None

        sound_id = uuid.uuid4().hex[:12]
        dest_name = f"{sound_id}{ext}"
        dest_path = os.path.join(self.sounds_dir, dest_name)
        shutil.copy2(source_path, dest_path)

        if not name:
            name = os.path.splitext(os.path.basename(source_path))[0]

        entry = {
            "id": sound_id,
            "name": name,
            "file": dest_path,
            "category": category,
            "tags": tags or [],
        }
        self.sounds.append(entry)
        self._save()
        return entry

    def remove_sound(self, sound_id: str) -> bool:
        for i, s in enumerate(self.sounds):
            if s["id"] == sound_id:
                try:
                    if os.path.exists(s["file"]):
                        os.remove(s["file"])
                except OSError:
                    pass
                self.sounds.pop(i)
                self._save()
                return True
        return False

    def update_sound(self, sound_id: str, **fields) -> bool:
        for s in self.sounds:
            if s["id"] == sound_id:
                s.update(fields)
                self._save()
                return True
        return False

    def get_categories(self) -> List[str]:
        cats = set()
        for s in self.sounds:
            cats.add(s.get("category", "Без категории"))
        return sorted(cats)

    def search(self, query: str = "", category: str = "", tag: str = "") -> List[Dict[str, Any]]:
        q = query.lower().strip()
        result = []
        for s in self.sounds:
            if category and s.get("category") != category:
                continue
            if tag and tag not in s.get("tags", []):
                continue
            if q:
                haystack = (s.get("name", "") + " " + " ".join(s.get("tags", []))).lower()
                if q not in haystack:
                    continue
            result.append(s)
        return result

    def export_to_zip(self, zip_path: str) -> None:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("library.json", json.dumps(self.sounds, indent=2, ensure_ascii=False))
            for s in self.sounds:
                if os.path.exists(s["file"]):
                    arcname = "sounds/" + os.path.basename(s["file"])
                    zf.write(s["file"], arcname)

    def import_from_zip(self, zip_path: str) -> int:
        imported = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "library.json" not in zf.namelist():
                return 0
            data = json.loads(zf.read("library.json").decode("utf-8"))

            for entry in data:
                src_name = os.path.basename(entry.get("file", ""))
                if not src_name or f"sounds/{src_name}" not in zf.namelist():
                    continue

                dest_name = f"{uuid.uuid4().hex[:12]}{os.path.splitext(src_name)[1]}"
                dest_path = os.path.join(self.sounds_dir, dest_name)
                with zf.open(f"sounds/{src_name}") as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())

                new_entry = {
                    "id": uuid.uuid4().hex[:12],
                    "name": entry.get("name", "Импортировано"),
                    "file": dest_path,
                    "category": entry.get("category", "Импортированные"),
                    "tags": entry.get("tags", []),
                }
                self.sounds.append(new_entry)
                imported += 1

        self._save()
        return imported

    def _load(self) -> None:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.sounds = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.sounds = []
        self.sounds = [s for s in self.sounds if os.path.exists(s.get("file", ""))]

    def _save(self) -> None:
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.sounds, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"Ошибка сохранения библиотеки: {e}")