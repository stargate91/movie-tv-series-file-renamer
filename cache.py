import os
import json

class CacheHandler:
    def __init__(self, cache_file):
        self.cache_dir = "data"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.cache_file = os.path.join(self.cache_dir, cache_file)

    def load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                return json.load(f)
        return {}

    def save_cache(self, data):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Cache saved to {self.cache_file}")
        except Exception as e:
            print(f"Error saving cache to {self.cache_file}: {e}") 

    def get(self, key):
        cache = self.load_cache()
        return cache.get(key)

    def set(self, key, value):
        cache = self.load_cache()
        cache[key] = value
        self.save_cache(cache)
