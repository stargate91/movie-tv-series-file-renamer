import json
import os

class DataStore:
    """Simple JSON-based persistent cache."""
    def __init__(self, filename):
        # Use local data/cache folder in project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(base_dir, 'data', 'cache')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.path = os.path.join(cache_dir, f"{filename}.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        self._save()

    def _save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except:
            pass
